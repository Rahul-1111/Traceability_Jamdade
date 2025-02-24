import pymcprotocol
import time
import logging
from track.models import TraceabilityData
from datetime import datetime
import struct

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
    "st7": {"qr": 5700, "result": 5754, "scan_trigger": 5756, "write_signal": 5758},
    "st8": {"qr": 5800, "result": 5854, "scan_trigger": 5856, "write_signal": 5858},
}

def connect_to_plc(plc_ip):
    """Connect to PLC using pymcprotocol."""
    mc = pymcprotocol.Type3E()
    try:
        mc.connect(plc_ip, 5007)  # Default Mitsubishi MELSEC port
        logger.info(f"✅ Connected to PLC {plc_ip}")
        return mc
    except Exception as e:
        logger.error(f"❌ Failed to connect to PLC {plc_ip}: {e}")
        return None

def read_register(mc, address, num_registers=1):
    """Read registers from Mitsubishi PLC using pymcprotocol."""
    try:
        response = mc.batchread_wordunits(headdevice=f"D{address}", readsize=num_registers)
        return response if response else None
    except Exception as e:
        logger.error(f"❌ Error reading register {address}: {e}")
        return None

def write_register(mc, address, value):
    """Write to Mitsubishi PLC register."""
    try:
        mc.batchwrite_wordunits(headdevice=f"D{address}", values=[value])
        logger.info(f"✅ Wrote {value} to register {address}")
    except Exception as e:
        logger.error(f"❌ Error writing to register {address}: {e}")

def fetch_station_data():
    """Fetch data from all stations."""
    station_data = {}
    for station, plc in PLC_MAPPING.items():
        mc = connect_to_plc(plc["ip"])
        if not mc:
            continue  # Skip if PLC is not connected
        
        reg = REGISTERS[station]
        scan_trigger = read_register(mc, reg["scan_trigger"], 1)
        if not scan_trigger or scan_trigger[0] != 1:
            logger.info(f"🚫 {station}: No scan trigger")
            mc.close()
            continue
        
        qr_registers = read_register(mc, reg["qr"], 30)
        result = read_register(mc, reg["result"], 1)
        mc.close()
        
        if qr_registers and result:
            qr_string = convert_registers_to_string(qr_registers)
            result_value = "OK" if result[0] == 1 else "NOT OK"
            station_data[station] = {"qr": qr_string, "result": result_value}
    
    return station_data

def convert_registers_to_string(registers):
    """Convert PLC register data to a string."""
    try:
        byte_array = b"".join(struct.pack("<H", reg) for reg in registers)
        return byte_array.decode("ascii", errors="ignore").replace("\x00", "").strip()
    except Exception as e:
        logger.error(f"❌ Error converting register data: {e}")
        return ""

def update_traceability_data():
    """Update traceability database and PLC signals."""
    while True:
        station_data = fetch_station_data()
        for station, data in station_data.items():
            part_number = data["qr"].strip()
            plc = PLC_MAPPING[station]
            reg = REGISTERS[station]

            mc = connect_to_plc(plc["ip"])
            if not mc:
                continue
            
            # Fetch existing traceability record
            obj, created = TraceabilityData.objects.get_or_create(
                part_number=part_number,
                date=datetime.today().date(),
                defaults={"time": datetime.now().time(), "shift": get_current_shift()},
            )
            
            last_status = getattr(obj, f"{station}_result", None)
            
            if last_status == "OK":
                logger.info(f"✅ {station}: Part {part_number} is already OK. Sending signal directly.")
                write_register(mc, reg["write_signal"], 2)  # Directly send signal
                mc.close()
                continue  # Skip reading result
            
            # Read result only if not already OK
            result = read_register(mc, reg["result"], 1)
            result_value = "OK" if result and result[0] == 1 else "NOT OK"

            # Determine signal
            if result_value == "OK":
                write_signal = 4 if last_status != "OK" else 2
            else:
                write_signal = 1  # Not OK

            # Save new result
            setattr(obj, f"{station}_result", result_value)
            obj.save()

            # Write signal to PLC
            write_register(mc, reg["write_signal"], write_signal)
            if write_signal == 4:
                write_register(mc, reg["scan_trigger"], 0)

            mc.close()
        time.sleep(2)

def get_current_shift():
    """Determine the current production shift."""
    now = datetime.now().time()
    if datetime.strptime("07:00", "%H:%M").time() <= now < datetime.strptime("15:30", "%H:%M").time():
        return 'Shift 1'
    elif datetime.strptime("15:30", "%H:%M").time() <= now < datetime.strptime("23:59", "%H:%M").time():
        return 'Shift 2'
    else:
        return 'Shift 3'
