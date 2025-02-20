from zebra import Zebra
import qrcode
import datetime
import logging
import os

# Logging Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Get Current Project Directory (Django `BASE_DIR`)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get current script's directory
OUTPUT_DIR = os.path.join(BASE_DIR, "Qr")  # ✅ Save in "Qr" folder inside project

# ✅ Create directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

def clear_old_qr_codes():
    """Deletes QR codes older than 2 days."""
    today_str = datetime.datetime.now().strftime("%d%m%y")       # Format: DDMMYY
    yesterday_str = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d%m%y")  # Keep Yesterday's QR too

    for filename in os.listdir(OUTPUT_DIR):
        if today_str not in filename and yesterday_str not in filename:  # ✅ Delete files older than 2 days
            file_path = os.path.join(OUTPUT_DIR, filename)
            try:
                os.remove(file_path)
                logger.info(f"🗑️ Deleted old QR: {filename}")
            except Exception as e:
                logger.error(f"❌ Error deleting file {filename}: {e}")

def generate_zpl_qrcode(qr_data):
    """Generates ZPL code for printing a QR code on a Zebra printer."""
    zpl = f"""
    ^XA
    ^PW160
    ^LL100
    ^FT30,120^BQN,2,3
    ^FH\\^FDLA,{qr_data}^FS
    ^PQ1,0,1,Y
    ^XZ
    """
    return zpl

def print_zpl(zpl_command):
    """Sends ZPL command to the Zebra printer."""
    try:
        z = Zebra()
        z.setqueue("ZDesigner GC420t (copy 1)")  
        z.output(zpl_command)
        logger.info("✅ ZPL command sent successfully.")
    except Exception as e:
        logger.error(f"❌ Error sending ZPL to printer: {e}")

def generate_qrcode_image(qr_data):
    """Generates and saves a QR code image."""
    filename = f"qrcode_{qr_data}.png"
    filepath = os.path.join(OUTPUT_DIR, filename)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    img.save(filepath)
    
    logger.info(f"🖼️ QR saved: {filepath}")

def generate_qr_code(prefix, serial_number):
    """Generates QR Code with format: [PREFIX]-DDMMYY-[SERIAL]"""

    clear_old_qr_codes()  # ✅ Delete old QR codes before generating a new one

    now = datetime.datetime.now()
    date_part = now.strftime("%d%m%y")  # ddmmyy (last two digits of year)
    unique_serial = str(serial_number).zfill(5)  # Ensure 5-digit serial number

    qr_data = f"{prefix}-{date_part}-{unique_serial}"  # ✅ Removed time

    zpl_qrcode = generate_zpl_qrcode(qr_data)
    print_zpl(zpl_qrcode)

    generate_qrcode_image(qr_data)

    logger.info(f"🖨️ Printed QR: {qr_data}")

    return f"✅ QR Code Generated: {qr_data}"

# Example usage:
if __name__ == "__main__":
    sample_prefix = "PDU-S-10594-1"
    sample_serial = 12345
    print(generate_qr_code(sample_prefix, sample_serial))
