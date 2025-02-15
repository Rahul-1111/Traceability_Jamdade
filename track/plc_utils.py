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

# Define Modbus Register Addresses for Each Station
REGISTERS = {
    "st1": {"qr": 5100, "result": 5150, "trigger": 5152},
    "st2": {"qr": 5200, "result": 5250, "trigger": 5252},
    "st3": {"qr": 5300, "result": 5350, "trigger": 5352},
    "st4": {"qr": 5400, "result": 5450, "trigger": 5452},
    "st5": {"qr": 5500, "result": 5550, "trigger": 5552},
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
        return decoded_string.replace("\x00", "").strip()
    except Exception as e:
        logger.error(f"❌ Error converting register data to string: {e}")
        return ""

def fetch_station_data(client):
    station_data = {}

    for station, reg in REGISTERS.items():
        try:
            qr_registers = read_register(client, reg["qr"], 50)
            result = read_register(client, reg["result"], 1)

            if qr_registers is None or result is None:
                logger.error(f"❌ Failed to fetch data for {station}")
                continue

            qr_string = convert_registers_to_string(qr_registers).strip()
            qr_string = qr_string.replace("\x01", "")  # ✅ Remove unwanted characters
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
                    logger.info(f"📝 Storing {station}: Part {part_number} → Result {result_value}")

                    try:
                        # ✅ Update existing row instead of creating a duplicate
                        obj, created = TraceabilityData.objects.get_or_create(
                            part_number=part_number,
                            date=datetime.today().date(),
                            defaults={"time": datetime.now().time(), "shift": get_current_shift()},
                        )

                        setattr(obj, f"{station}_result", result_value)  # ✅ Set correct station result
                        obj.save()

                        logger.info(f"{'✅ Created' if created else '🔄 Updated'} record for {obj.part_number}")

                        # ✅ WRITE RESULT BACK TO PLC TRIGGER REGISTER
                        trigger_value = 1 if result_value == "OK" else 0  
                        write_register(client, reg["trigger"], trigger_value)
                        logger.info(f"✅ {station} trigger register {reg['trigger']} updated to {trigger_value}")

                    except Exception as e:
                        logger.error(f"❌ Error updating traceability data for {station}: {e}")

                time.sleep(5)

        except Exception as e:
            logger.error(f"🚨 Critical error in traceability update: {e}")
            logger.warning("🔄 Reconnecting to Modbus server in 5 seconds...")
            time.sleep(5)

        finally:
            client.close()
