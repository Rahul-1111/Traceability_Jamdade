from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusIOException
import time
import logging
from track.models import TraceabilityData
from datetime import datetime
import struct

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
PLC_HOST = "192.168.1.100"
PLC_PORT = 502

# Define Station Registers
REGISTERS = {
    "st1": {"qr": 5100, "result": 5150, "scan_trigger": 5152, "write_signal": 5154},
    "st2": {"qr": 5200, "result": 5250, "scan_trigger": 5252, "write_signal": 5254},
    "st3": {"qr": 5300, "result": 5350, "scan_trigger": 5352, "write_signal": 5354},
    "st4": {"qr": 5400, "result": 5450, "scan_trigger": 5452, "write_signal": 5454},
    "st5": {"qr": 5500, "result": 5550, "scan_trigger": 5552, "write_signal": 5554},
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

            qr_string = convert_registers_to_string(qr_registers)
            result_value = result[0] if result else -1

            logger.info(f"🔹 {station}: QR Data: {qr_string} | Raw Result Register: {result_value}")

            result_status = "OK" if result_value == 1 else "NOT OK"

            station_data[station] = {
                "qr": qr_string,
                "result": result_status,
            }

        except Exception as e:
            logger.error(f"❌ Error fetching data for {station}: {e}")

    return station_data

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
                        continue  

                    result_value = station_data.get(station, {}).get("result", "UNKNOWN")
                    logger.info(f"📝 Checking {station}: Part {part_number} → Result {result_value}")

                    try:
                        obj, created = TraceabilityData.objects.get_or_create(
                            part_number=part_number,
                            date=datetime.today().date(),
                            defaults={"time": datetime.now().time(), "shift": get_current_shift()},
                        )

                        # Check if the part was already stored and if the result was "OK" or "NOT OK"
                        part_exists = TraceabilityData.objects.filter(part_number=part_number, date=datetime.today().date()).exists()

                        if part_exists:
                            last_status = getattr(obj, f"{station}_result", "UNKNOWN")
                            if last_status == "OK":
                                trigger_value = 0  # ✅ Don't reprocess if already OK
                            else:
                                trigger_value = 1  # ✅ Reprocess if NOT OK
                        else:
                            trigger_value = 1  # ✅ New part, process it

                        # ✅ Store the new result in the database
                        setattr(obj, f"{station}_result", result_value)
                        obj.save()

                        logger.info(f"{'✅ Created' if created else '🔄 Updated'} record for {obj.part_number}")

                        # ✅ Send Signal to PLC: 1 if new/NOT OK, 0 if already OK
                        write_register(client, reg["write_signal"], trigger_value)
                        logger.info(f"✅ {station}: Feedback Sent (Register {reg['write_signal']} = {trigger_value})")

                    except Exception as e:
                        logger.error(f"❌ Error updating traceability data for {station}: {e}")

                time.sleep(5)

        except Exception as e:
            logger.error(f"🚨 Critical error in traceability update: {e}")
            logger.warning("🔄 Reconnecting to Modbus server in 5 seconds...")
            time.sleep(5)

        finally:
            client.close()
