import pymcprotocol
import time
import logging
from track.models import TraceabilityData
from datetime import datetime
import struct
import re
import threading
import socket

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define PLCs for each station
PLC_MAPPING = {
    "st1": {"ip": "192.168.1.100"},
    "st2": {"ip": "192.168.1.130"},
    "st3": {"ip": "192.168.1.20"},
    "st4": {"ip": "192.168.1.20"},
    "st5": {"ip": "192.168.1.40"},
    "st6": {"ip": "192.168.1.40"},
    "st7": {"ip": "192.168.1.60"},
    "st8": {"ip": "192.168.1.60"},
}

# Define Registers for each station
REGISTERS = {
    "st1": {"qr": 5100, "result": 5154, "scan_trigger": 5156, "write_signal": 5158},
    "st2": {"qr": 5200, "result": 5254, "scan_trigger": 5256, "write_signal": 5258},
    "st3": {"qr": 5300, "result": 5354, "scan_trigger": 5356, "write_signal": 5358},
    "st4": {"qr": 5400, "result": 5454, "scan_trigger": 5456, "write_signal": 5458},
    "st5": {"qr": 5500, "result": 5554, "scan_trigger": 5556, "write_signal": 5558},
    "st6": {"qr": 5600, "result": 5654, "scan_trigger": 5656, "write_signal": 5658},
    "st7": {"qr": 5700, "result": 5764, "scan_trigger": 5760, "write_signal": 5762},
    "st8": {"qr": 5800, "result": 5854, "scan_trigger": 5856, "write_signal": 5858},
}

QR_PATTERN = re.compile(r"^[A-Z]+-S-\d+-\d+-\d{11}$")


def connect_to_plc(plc_ip, timeout=3, retry_delay=5):
    while True:
        mc = pymcprotocol.Type3E()
        try:
            socket.setdefaulttimeout(timeout)
            mc.connect(plc_ip, 5007)
            logger.info(f"✅ Connected to PLC {plc_ip}")
            return mc
        except Exception as e:
            logger.error(f"❌ Connection failed to PLC {plc_ip}: {e}. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)


def read_register(mc, address, num_registers=1):
    try:
        return mc.batchread_wordunits(headdevice=f"D{address}", readsize=num_registers)
    except Exception as e:
        logger.error(f"❌ Error reading register {address}: {e}")
        return None


def write_register(mc, address, value):
    try:
        mc.batchwrite_wordunits(headdevice=f"D{address}", values=[value])
        logger.info(f"✅ Wrote {value} to register {address}")
    except Exception as e:
        logger.error(f"❌ Error writing to register {address}: {e}")


def convert_registers_to_string(registers):
    try:
        byte_array = b"".join(struct.pack("<H", reg) for reg in registers)
        return byte_array.decode("ascii", errors="ignore").replace("\x00", "").strip()
    except Exception as e:
        logger.error(f"❌ Error converting register data: {e}")
        return ""


def get_current_shift():
    now = datetime.now().time()
    if datetime.strptime("07:00", "%H:%M").time() <= now < datetime.strptime("15:30", "%H:%M").time():
        return 'Shift 1'
    elif datetime.strptime("15:30", "%H:%M").time() <= now < datetime.strptime("23:59", "%H:%M").time():
        return 'Shift 2'
    else:
        return 'Shift 3'


def process_station(station):
    plc = PLC_MAPPING[station]
    reg = REGISTERS[station]

    while True:
        mc = None
        try:
            mc = connect_to_plc(plc["ip"])
            if not mc:
                continue

            scan_trigger = read_register(mc, reg["scan_trigger"], 1)
            if not scan_trigger or scan_trigger[0] != 1:
                logger.info(f"⏸️ {station}: No scan trigger")
                mc.close()
                time.sleep(1)
                continue

            qr_registers = read_register(mc, reg["qr"], 30)
            result = read_register(mc, reg["result"], 1)
            if not qr_registers or not result:
                logger.warning(f"⚠️ {station}: Failed to read QR/result")
                write_register(mc, reg["scan_trigger"], 0)
                mc.close()
                continue

            qr_string = convert_registers_to_string(qr_registers).strip()
            part_number = qr_string
            result_value = "OK" if result[0] == 1 else "NOT OK"

            if not QR_PATTERN.match(part_number):
                logger.warning(f"🚫 {station}: Invalid QR format - '{part_number}'")
                write_register(mc, reg["write_signal"], 3)
                write_register(mc, reg["scan_trigger"], 0)
                mc.close()
                continue

            obj = TraceabilityData.objects.filter(part_number=part_number).first()
            if not obj:
                obj = TraceabilityData.objects.create(
                    part_number=part_number,
                    date=datetime.today().date(),
                    time=datetime.now().time(),
                    shift=get_current_shift()
                )
                logger.info(f"🟢 {station}: Created record for {part_number}")
            else:
                logger.info(f"🟡 {station}: Updating record for {part_number}")

            station_num = int(station[2:])
            prev_station = f"st{station_num - 1}" if station_num > 1 else None
            prev_result = getattr(obj, f"{prev_station}_result", None) if prev_station else None

            if prev_station and prev_result in [None, "NOT OK"]:
                logger.warning(f"🚨 {station}: Previous station '{prev_station}' result: {prev_result}")
                write_register(mc, reg["write_signal"], 5)
                write_register(mc, reg["scan_trigger"], 0)
                mc.close()
                continue

            existing_ok = getattr(obj, f"{station}_result", None) == "OK"
            if existing_ok:
                write_register(mc, reg["write_signal"], 2)
                logger.info(f"✅ {station}: Part already OK. Sending 2.")
                write_register(mc, reg["scan_trigger"], 0)
                mc.close()
                continue

            setattr(obj, f"{station}_result", result_value)
            setattr(obj, f"{station}_time", datetime.now().time())  # ✅ Save the current time for the station
            obj.save()
            logger.info(f"✅ {station}: Updated DB with result '{result_value}'")

            signal = 4 if result_value == "OK" else 1
            write_register(mc, reg["write_signal"], signal)
            write_register(mc, reg["scan_trigger"], 0)

        except Exception as e:
            logger.error(f"❌ Error in {station}: {e}")
        finally:
            if mc:
                mc.close()
            time.sleep(2)


# Function to start PLC monitoring in a separate thread
def start_plc_monitoring():
    for station in PLC_MAPPING.keys():
        t = threading.Thread(target=process_station, args=(station,), daemon=True)
        t.start()
    logger.info("🚀 PLC Monitoring started in background threads.")

# Start Django server first
if __name__ == "__main__":
    start_plc_monitoring()  # Run PLC handling in background threads