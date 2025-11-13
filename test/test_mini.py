# app.py
import time
import threading
import queue
import os

from logger_config import get_logger

logger = get_logger(__name__)


cmdq = queue.Queue()

def input_thread():
    """Đọc input blocking; đặt lệnh vào queue."""
    while True:
        try:
            s = input().strip().lower()
        except EOFError:
            # stdin đóng (ví dụ chạy dưới service) -> không làm gì
            break
        except Exception:
            break
        if s:
            cmdq.put(s)

def main():
    threading.Thread(target=input_thread, daemon=True).start()
    tick = 0
    logger.info("App started. Type 'crash' to raise exception, 'exit' to quit cleanly.")
    while True:
        tick += 1
        logger.info(f"heartbeat #{tick}")
        # check command non-blocking
        if os.path.exists("crash.flag"):
            logger.warning("Found crash.flag -> simulate crash now.")
            raise RuntimeError("Manual crash requested via crash.flag")


        # simulate work
        time.sleep(5)

if __name__ == "__main__":
    # if an exception escapes main, process will exit with non-zero and supervisor should restart
    main()
