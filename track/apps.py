from django.apps import AppConfig
from threading import Thread
import logging

logger = logging.getLogger(__name__)

class TrackConfig(AppConfig):
    name = 'track'

    def ready(self):
        from .plc_utils import update_traceability_data

        def run_task():
            try:
                logger.info("Starting Modbus data fetching task.")
                update_traceability_data()  # Assuming this function is designed to run indefinitely
            except Exception as e:
                logger.error(f"Error in Modbus data fetching task: {e}")

        thread = Thread(target=run_task, daemon=True)
        thread.start()
