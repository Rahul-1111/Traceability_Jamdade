from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusIOException
import time
import logging
from track.models import TraceabilityData
from datetime import datetime, time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_current_shift() -> str:
    now = datetime.now().time()
    if time(7, 0) <= now < time(15, 30):
        return 'Shift 1'
    elif time(15, 30) <= now < time(23, 59):
        return 'Shift 2'
    else:
        return 'Shift 3'

# Modbus connection details
PLC_HOST = "192.168.3.99"  # Updated IP address of the Modbus server
PLC_PORT = 502

# Define the register addresses for stations
REGISTERS = {
    "st1": {"qr": 5100, "result": 5150, "trigger": 5152},
    "st2": {"qr": 5200, "result": 5250, "trigger": 5252},
    "st3": {"qr": 5300, "result": 5350, "trigger": 5352},
    "st4": {"qr": 5400, "result": 5450, "trigger": 5452},
    "st5": {"qr": 5500, "result": 5550, "trigger": 5552},
}

# Function to connect to the Modbus server
def connect_to_modbus_client(client, retries=3, delay=2):
    for attempt in range(retries):
        if client.connect():
            logger.info("Successfully connected to Modbus server.")
            return True
        else:
            logger.warning(f"Connection attempt {attempt + 1} failed. Retrying in {delay} seconds...")
            time.sleep(delay)
    logger.error("Failed to connect to Modbus server after multiple attempts.")
    return False

# Function to read data from a Modbus register
def read_register(client, address, num_registers=1):
    try:
        response = client.read_holding_registers(address, num_registers)
        if not response.isError():
            logger.info(f"Read successful: {response.registers}")
            return response.registers
        else:
            logger.error(f"Error reading registers: {response}")
            return None
    except ModbusIOException as e:
        logger.error(f"Modbus IO error while reading registers: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while reading registers: {e}")
    return None

# Function to reset station trigger
def reset_station_trigger(client, station):
    try:
        trigger_address = REGISTERS[station]["trigger"]
        write_register(client, trigger_address, 0)
        logger.info(f"Reset trigger for {station}")
    except KeyError:
        logger.error(f"Trigger register not defined for {station}")

# Helper function to write to a register
def write_register(client, address, data):
    try:
        response = client.write_registers(address, data)
        if not response.isError():
            logger.info(f"Write successful to {address}")
        else:
            logger.error(f"Error writing registers: {response}")
    except ModbusIOException as e:
        logger.error(f"Modbus IO error while writing registers: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while writing registers: {e}")

# Fetch station data using the working Modbus communication functions
def fetch_station_data(client):
    station_data = {}
    for station, reg in REGISTERS.items():
        try:
            qr_count = read_register(client, reg["qr"])
            result_count = read_register(client, reg["result"])
            trigger = read_register(client, reg["trigger"])

            if None in (qr_count, result_count, trigger):
                logger.error(f"Failed to fetch data for {station}")
                continue

            station_data[station] = {
                "qr": qr_count[0],
                "result": result_count[0],
                "trigger": trigger[0],
            }
            logger.info(f"{station}: {station_data[station]}")
        except Exception as e:
            logger.error(f"Error fetching data for {station}: {e}")
    return station_data

# Update traceability data based on station data
def update_traceability_data():
    shift = get_current_shift()
    try:
        client = ModbusTcpClient(PLC_HOST, port=PLC_PORT, timeout=5)  # 5-second timeout for connection

        if not connect_to_modbus_client(client):
            logger.error("Failed to connect to Modbus server after multiple attempts.")
            return

        while True:
            station_data = fetch_station_data(client)
            for station, data in station_data.items():
                if data["trigger"] == 1:  # Process data if trigger is active
                    try:
                        # Update or create database records
                        TraceabilityData.objects.update_or_create(
                            station=station,
                            shift=shift,
                            date=datetime.today().date(),
                            defaults={
                                "qr_count": data["qr"],
                                "result_count": data["result"],
                                "timestamp": datetime.now(),
                            },
                        )
                        logger.info(f"Updated data for {station}: {data}")
                        reset_station_trigger(client, station)
                    except Exception as e:
                        logger.error(f"Error updating traceability data for {station}: {e}")
            time.sleep(5)  # Fetch data periodically

    except Exception as e:
        logger.error(f"Critical error in traceability update: {e}")
    finally:
        client.close()

# Main entry point
if __name__ == "__main__":
    try:
        logger.info("Starting traceability data update process...")
        update_traceability_data()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user.")
