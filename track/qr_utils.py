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
    zpl = f"""
    ^XA
    ^PW160  ; Wider label width (was 160)
    ^LL100  ; Taller label height (was 100)
    ^FT30,120^BQN,2,3  ; Larger QR size (was 2,3)
    ^FH\\^FDLA,{data}^FS
    ^PQ1,0,1,Y
    ^XZ
    """
    return zpl

def print_zpl(zpl_command):
    try:
        z = Zebra()
        z.setqueue("ZDesigner GC420t (copy 1)")  
        z.output(zpl_command)
        logger.info("✅ ZPL command sent successfully.")
    except Exception as e:
        logger.error(f"❌ Error sending ZPL to printer: {e}")

def generate_qrcode_image(data, filename="qrcode.png"):
    os.makedirs(OUTPUT_DIR, exist_ok=True)  
    filepath = os.path.join(OUTPUT_DIR, filename)

    qr = qrcode.QRCode(
        version=None,  
        error_correction=qrcode.constants.ERROR_CORRECT_M,  
        box_size=8,  # Increase QR size (was 5)
        border=2,  # Reduce empty space (was 3)
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    img.save(filepath)
    logger.info(f"🖼️ QR saved: {filepath}")

def generate_qr_codes_batch(lot_number):
    if lot_number not in lot_serial_tracker:
        lot_serial_tracker[lot_number] = 1  

    serial_number = lot_serial_tracker[lot_number]

    if serial_number > lot_number:
        logger.info(f"✅ Lot {lot_number} completed. Resetting...")
        del lot_serial_tracker[lot_number]
        return f"✅ Lot {lot_number} completed. Enter a new lot number."

    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.datetime.now().strftime("%H:%M:%S")

    qr_data = f"{serial_number},{lot_number},{current_date},{current_time}"

    zpl_qrcode = generate_zpl_qrcode(qr_data)
    print_zpl(zpl_qrcode)

    generate_qrcode_image(qr_data, f"qrcode_{serial_number}.png")

    logger.info(f"🖨️ Printed QR: SN {serial_number}, Lot {lot_number}")

    lot_serial_tracker[lot_number] += 1
    return f"✅ QR Code for SN {serial_number} in Lot {lot_number} printed!"
