from zebra import Zebra
import qrcode
import datetime
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OUTPUT_DIR = r"D:\Shubham\Fourfront\Traceability_python\traceability\qrcodes"
lot_serial_tracker = {}

def generate_zpl_qrcode(data):
    """Generates ZPL code for printing a QR code on a Zebra printer."""
    zpl = f"""
    ^XA
    ^PW160
    ^LL100
    ^FT30,120^BQN,2,3
    ^FH\\^FDLA,{data}^FS
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

def generate_qrcode_image(data, filename="qrcode.png"):
    """Generates and saves a QR code image."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    img.save(filepath)
    logger.info(f"🖼️ QR saved: {filepath}")

def generate_qr_code(serial_number):
    """Generates QR codes in the ddmmyyhhmm12345 format."""
    
    now = datetime.datetime.now()
    date_part = now.strftime("%d%m%y")  # ddmmyy
    time_part = now.strftime("%H%M")  # hhmm
    unique_serial = str(serial_number).zfill(5)  # Ensure 5-digit format

    qr_data = f"{date_part}{time_part}{unique_serial}"
    
    zpl_qrcode = generate_zpl_qrcode(qr_data)
    print_zpl(zpl_qrcode)

    generate_qrcode_image(qr_data, f"qrcode_{unique_serial}.png")

    logger.info(f"🖨️ Printed QR: {qr_data}")

    return f"✅ QR Code Generated: {qr_data}"

# Example usage:
if __name__ == "__main__":
    serial_number = 12345  # Example unique serial number
    print(generate_qr_code(serial_number))
