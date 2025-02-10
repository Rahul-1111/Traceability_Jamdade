from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class TrackConfig(AppConfig):
    name = 'track'

    def ready(self):
        logger.info("Track app is ready. Use 'python manage.py start_modbus' to run the Modbus task.")
