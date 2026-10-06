"""
Simulates an Azure Blob trigger (Azurite has no real event triggers).
Drop a CSV into ./incoming/ -> it is uploaded to Azurite -> the function runs automatically.

    python watcher.py
"""
import os
import time
from datetime import datetime

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import lambda_function

WATCH_DIR = os.getenv("WATCH_DIR", "incoming")


class CsvHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith(".csv"):
            return
        time.sleep(1)  # let the file finish copying
        print(f"\n[EVENT {datetime.now():%Y-%m-%d %H:%M:%S}] New file detected: {event.src_path}")
        lambda_function.upload_csv(event.src_path, blob_name=os.path.basename(event.src_path))
        lambda_function.main({"blob": os.path.basename(event.src_path)})


if __name__ == "__main__":
    os.makedirs(WATCH_DIR, exist_ok=True)
    observer = Observer()
    observer.schedule(CsvHandler(), WATCH_DIR, recursive=False)
    observer.start()
    print(f"[WATCHING] ./{WATCH_DIR}/ for new CSV files... (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
