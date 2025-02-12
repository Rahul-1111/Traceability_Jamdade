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
    """ Determines the current shift based on time """
    now = datetime.now().time()
    if now >= datetime.strptime("07:00", "%H:%M").time() and now < datetime.strptime("15:30", "%H:%M").time():
        return 'Shift 1'
    elif now >= datetime.strptime("15:30", "%H:%M").time() and now < datetime.strptime("23:59", "%H:%M").time():
        return 'Shift 2'
    else:
        return 'Shift 3'

# Modbus Connection Details
PLC_HOST = "192.168.3.99"
PLC_PORT = 502

# Define Modbus Register Addresses for Each Station
REGISTERS = {
    "st1": {"qr": 5100, "result": 5150, "trigger": 5152},
    "st2": {"qr": 5200, "result": 5250, "trigger": 5252},
    "st3": {"qr": 5300, "result": 5350, "trigger": 5352},
    "st4": {"qr": 5400, "result": 5450, "trigger": 5452},
    "st5": {"qr": 5500, "result": 5550, "trigger": 5552},
}

def connect_to_modbus_client(client, retries=3, delay=2):
    """ Attempts to connect to the Modbus server with retries """
    for attempt in range(retries):
        if client.connect():
            logger.info("Successfully connected to Modbus server.")
            return True
        logger.warning(f"Connection attempt {attempt + 1} failed. Retrying in {delay} seconds...")
        time.sleep(delay)
    logger.error("Failed to connect to Modbus server after multiple attempts.")
    return False

def read_register(client, address, num_registers=1):
    """ Reads Modbus registers and returns the data """
    try:
        response = client.read_holding_registers(address, num_registers)
        if response and not response.isError():
            return response.registers
        logger.error(f"Error reading register {address}: {response}")
    except ModbusIOException as e:
        logger.error(f"Modbus IO error while reading register {address}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while reading register {address}: {e}")
    return None

def write_register(client, address, value):
    """ Writes a value to a Modbus register """
    try:
        response = client.write_register(address, value)
        if response and not response.isError():
            logger.info(f"Successfully wrote {value} to register {address}")
        else:
            logger.error(f"Error writing to register {address}: {response}")
    except Exception as e:
        logger.error(f"Error writing to register {address}: {e}")

def reset_station_trigger(client, station):
    """ Resets the station trigger by writing 0 to the trigger register """
    try:
        trigger_address = REGISTERS[station]["trigger"]
        write_register(client, trigger_address, 0)
        logger.info(f"Reset trigger for {station}")
    except KeyError:
        logger.error(f"Trigger register not defined for {station}")

def convert_registers_to_string(registers):
    """ Converts Modbus register values into a clean ASCII string (Little-Endian Fix). """
    try:
        byte_array = b"".join(struct.pack("<H", reg) for reg in registers)
        decoded_string = byte_array.decode("ascii", errors="ignore")
        return decoded_string.replace("\x00", "").strip()
    except Exception as e:
        logger.error(f"Error converting register data to string: {e}")
        return ""

def fetch_station_data(client):
    """ Fetch QR code and result values from all stations (removes trigger read) """
    station_data = {}

    for station, reg in REGISTERS.items():
        try:
            qr_registers = read_register(client, reg["qr"], 50)  # Read 50 registers for QR
            result = read_register(client, reg["result"], 1)  # Read 1 register for result

            if qr_registers is None or result is None:
                logger.error(f"Failed to fetch data for {station}")
                continue

            # Convert registers into clean ASCII string
            qr_string = convert_registers_to_string(qr_registers)
            result_value = result[0] if result else -1  # Default to -1 if result is missing

            logger.info(f"{station}: QR Data: {qr_string} | Raw Result Register: {result_value}")

            # Ensure correct result mapping
            if result_value == 1:
                result_status = "OK"
            elif result_value == 0:
                result_status = "NOT OK"
            else:
                result_status = "UNKNOWN"

            logger.info(f"{station}: Final Processed Result: {result_status}")

            station_data[station] = {
                "qr": qr_string,
                "result": result_status,
            }

        except Exception as e:
            logger.error(f"Error fetching data for {station}: {e}")

    return station_data

def update_traceability_data():
    """ Continuously fetch data from Modbus and update the database """
    shift = get_current_shift()
    client = ModbusTcpClient(PLC_HOST, port=PLC_PORT, timeout=5)

    if not connect_to_modbus_client(client):
        logger.error("Cannot proceed without Modbus connection. Exiting...")
        return

    try:
        while True:
            station_data = fetch_station_data(client)
            logger.info(f"Fetched Data from PLC: {station_data}")

            for station in REGISTERS.keys():
                part_number = station_data.get(station, {}).get("qr", "").strip()
                if not part_number:
                    continue  # Skip stations where no QR was scanned

                result_value = station_data.get(station, {}).get("result", "UNKNOWN")
                logger.info(f"Storing {station}: Part {part_number} → Result {result_value}")

                try:
                    obj, created = TraceabilityData.objects.update_or_create(
                        part_number=part_number,
                        date=datetime.today().date(),
                        defaults={
                            "time": datetime.now().time(),
                            "shift": shift,
                            f"{station}_result": result_value,  # Store each station result in the correct field
                        },
                    )

                    logger.info(f"{'Created' if created else 'Updated'} record for {obj.part_number}")

                    reset_station_trigger(client, station)

                except Exception as e:
                    logger.error(f"Error updating traceability data for {station}: {e}")

            time.sleep(5)  # ✅ Corrected 'time.sleep' usage

    except Exception as e:
        logger.error(f"Critical error in traceability update: {e}")
    finally:
        client.close()
