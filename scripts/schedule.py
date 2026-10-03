"""Container-owned recurring crawl. Failed runs are logged; never closes a failed board."""

import logging
import subprocess
import sys
import time

logging.basicConfig(level=logging.INFO)
while True:
    result = subprocess.run([sys.executable, "-m", "rolefit.run_crawl"], check=False)
    logging.info("Crawl exited with status %s", result.returncode)
    time.sleep(6 * 60 * 60)
