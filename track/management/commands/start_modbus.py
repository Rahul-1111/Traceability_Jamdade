import time
import logging
from threading import Thread
from django.core.management.base import BaseCommand
from track.plc_utils import update_traceability_data

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Start Modbus data fetching task"

    def handle(self, *args, **kwargs):
        def run_task():
            try:
                logger.info("Starting Modbus data fetching task.")
                update_traceability_data()
            except Exception as e:
                logger.error(f"Error in Modbus data fetching task: {e}")

        thread = Thread(target=run_task, daemon=True)
        thread.start()

        while True:
            time.sleep(10)
