import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)

def log_file_upload(filename, url):
    logger.info(f"File uploaded: {filename} → {url}")

def log_file_deletion(filename):
    logger.info(f"File deleted: {filename}")
