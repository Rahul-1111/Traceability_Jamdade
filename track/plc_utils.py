from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusIOException
import time
import logging
from track.models import TraceabilityData
from datetime import datetime
import struct
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_current_shift():
    now = datetime.now().time()
    if now >= datetime.strptime("07:00", "%H:%M").time() and now < datetime.strptime("15:30", "%H:%M").time():
        return 'Shift 1'
    elif now >= datetime.strptime("15:30", "%H:%M").time() and now < datetime.strptime("23:59", "%H:%M").time():
        return 'Shift 2'
    else:
        return 'Shift 3'

# Modbus Connection Details
PLC_HOST = "192.168.1.130"
PLC_PORT = 502

# Define Station Registers for 8 Stations
REGISTERS = {
    "st1": {"qr": 5100, "result": 5154, "scan_trigger": 5156, "write_signal": 5158},
    "st2": {"qr": 5200, "result": 5254, "scan_trigger": 5256, "write_signal": 5258},
    "st3": {"qr": 5300, "result": 5354, "scan_trigger": 5356, "write_signal": 5358},
    "st4": {"qr": 5400, "result": 5454, "scan_trigger": 5456, "write_signal": 5458},
    "st5": {"qr": 5500, "result": 5554, "scan_trigger": 5556, "write_signal": 5558},
    "st6": {"qr": 5600, "result": 5654, "scan_trigger": 5656, "write_signal": 5658},
    "st7": {"qr": 5700, "result": 5754, "scan_trigger": 5756, "write_signal": 5758},
    "st8": {"qr": 5800, "result": 5854, "scan_trigger": 5856, "write_signal": 5858},
}

def connect_to_modbus_client():
    client = ModbusTcpClient(PLC_HOST, port=PLC_PORT, timeout=5)
    
    while True:
        if client.connect():
            logger.info("✅ Successfully connected to Modbus server.")
            return client
        else:
            logger.warning("🔴 Modbus connection failed. Retrying in 5 seconds...")
            time.sleep(5)

def read_register(client, address, num_registers=1):
    try:
        response = client.read_holding_registers(address, num_registers)
        if response and not response.isError():
            return response.registers
        logger.error(f"❌ Error reading register {address}: {response}")
    except ModbusIOException as e:
        logger.error(f"❌ Modbus IO error while reading register {address}: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error while reading register {address}: {e}")
    return None

def write_register(client, address, value):
    try:
        response = client.write_register(address, value)
        if response and not response.isError():
            logger.info(f"✅ Successfully wrote {value} to register {address}")
        else:
            logger.error(f"❌ Error writing to register {address}: {response}")
    except Exception as e:
        logger.error(f"❌ Error writing to register {address}: {e}")

def convert_registers_to_string(registers):
    try:
        byte_array = b"".join(struct.pack("<H", reg) for reg in registers)
        decoded_string = byte_array.decode("ascii", errors="ignore")
        return decoded_string.replace("\x00", "").replace("\x01", "").strip()
    except Exception as e:
        logger.error(f"❌ Error converting register data to string: {e}")
        return ""

import re  # ✅ Use regex for format validation

# Define the valid QR format pattern (Example: "PDU-S-10594-1-21022513746")
QR_PATTERN = re.compile(r"^[A-Z]+-S-\d+-\d+-\d{11}$")  

# ✅ First 10 valid QR prefixes
VALID_QR_PREFIXES = {
    "PDU-S-10594-1", "PDB-S-10779-1", "PDB-S-10697-1"
    # ✅ Add more as needed...
}

def fetch_station_data(client):
    station_data = {}

    for station, reg in REGISTERS.items():
        try:
            scan_trigger = read_register(client, reg["scan_trigger"], 1)
            if not scan_trigger or scan_trigger[0] != 1:
                logger.info(f"🚫 {station}: Skipping read (Scan Trigger {reg['scan_trigger']} = 0)")
                continue  

            logger.info(f"✅ {station}: Scan Trigger Active (Register {reg['scan_trigger']} = 1), Scanning QR...")

            qr_registers = read_register(client, reg["qr"], 50)
            result = read_register(client, reg["result"], 1)

            if qr_registers is None or result is None:
                logger.error(f"❌ Failed to fetch data for {station}")
                continue

            qr_string = convert_registers_to_string(qr_registers).strip()

            # ✅ Log the scanned QR for debugging
            logger.info(f"🔹 {station}: Scanned QR Data: '{qr_string}'")

            result_value = result[0] if result else -1

            # ✅ Step 1: Check QR format
            if not QR_PATTERN.match(qr_string):
                logger.warning(f"🚫 {station}: Invalid QR format - '{qr_string}'. Ignoring...")
                continue  # Skip processing

            logger.info(f"✅ {station}: QR format valid")

            # ✅ Step 2: Check if QR exists in the database
            qr_exists = TraceabilityData.objects.filter(part_number=qr_string).exists()

            # ✅ Step 3: Allow first 10 valid QR prefixes
            qr_prefix = "-".join(qr_string.split("-")[:4])  # Extract "PDU-S-10594-1"
            if not qr_exists and qr_prefix not in VALID_QR_PREFIXES:
                logger.warning(f"🚨 {station}: Unknown QR Code ({qr_string}) scanned! Ignoring...")

                # 🔍 Debugging: Log all existing QRs for comparison
                all_qrs = list(TraceabilityData.objects.values_list('part_number', flat=True))
                logger.warning(f"🧐 Debug: Existing QRs in DB → {all_qrs[:10]}... (Showing first 10)")

                continue  # Skip processing

            # Convert result to readable status
            result_status = "OK" if result_value == 1 else "NOT OK"

            station_data[station] = {
                "qr": qr_string,
                "result": result_status,
            }

        except Exception as e:
            logger.error(f"❌ Error fetching data for {station}: {e}")

    return station_data

from datetime import datetime, timedelta

# Track when parts were scanned
last_scan_times = {}
first_scan_done = {}

def update_traceability_data():
    while True:
        client = connect_to_modbus_client()

        try:
            while True:
                station_data = fetch_station_data(client)
                logger.info(f"📡 Fetched Data from PLC: {station_data}")

                for station, reg in REGISTERS.items():
                    part_number = station_data.get(station, {}).get("qr", "").strip()
                    if not part_number:
                        continue  # Skip if no QR was read

                    result_value = station_data.get(station, {}).get("result", "NOT OK")
                    logger.info(f"📝 Checking {station}: Part {part_number} → Result {result_value}")

                    now = datetime.now()

                    try:
                        # 🔍 Step 1: Check database
                        obj, created = TraceabilityData.objects.get_or_create(
                            part_number=part_number,
                            date=datetime.today().date(),
                            defaults={"time": now.time(), "shift": get_current_shift()},
                        )

                        last_status = getattr(obj, f"{station}_result", None)
                        last_scan_time = last_scan_times.get(part_number)

                        # 🚫 Prevent sending `2` immediately after `4`
                        recently_scanned = last_scan_time and (now - last_scan_time) < timedelta(seconds=5)

                        # 🚀 Determine PLC Signal:
                        if created:
                            if result_value == "OK":
                                write_signal = 4  # First scan & OK
                            else:
                                write_signal = 1  # First scan & NOT OK
                            first_scan_done[part_number] = True  # Mark first scan
                        elif last_status == "OK" and not first_scan_done.get(part_number) and not recently_scanned:
                            write_signal = 2  # Already OK, send 2
                        elif last_status == "NOT OK" and result_value == "OK":
                            write_signal = 4  # Was NOT OK before, now OK
                        else:
                            write_signal = 1  # Remains NOT OK

                        # 🔄 Step 3: Update database **before sending signal**
                        setattr(obj, f"{station}_result", result_value)
                        obj.save()
                        last_scan_times[part_number] = now  # Store scan time

                        # ✅ Step 4: Write to PLC
                        write_register(client, reg["write_signal"], write_signal)
                        logger.info(f"✅ {station}: Sent {write_signal} to PLC")

                        # 🔄 Step 5: After writing 4, reset scan trigger to 0
                        if write_signal == 4:
                            write_register(client, reg["scan_trigger"], 0)
                            logger.info(f"🔄 {station}: Reset scan trigger (Sent 0 to {reg['scan_trigger']})")
                            first_scan_done[part_number] = False

                    except Exception as e:
                        logger.error(f"❌ Error updating traceability data for {station}: {e}")

                time.sleep(5)

        except Exception as e:
            logger.error(f"🚨 Critical error in traceability update: {e}")
            logger.warning("🔄 Reconnecting to Modbus server in 5 seconds...")
            time.sleep(5)

        finally:
            client.close()
 