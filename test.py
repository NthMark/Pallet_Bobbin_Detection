# leak_test_show.py
import cv2
import time
from collections import deque

# Choose your leak mode
#  "list"  -> keeps all frames (RAM explodes very fast)
#  "queue" -> keeps last N frames (safe)
MODE = "list"   # change to "queue" for controlled version
MAX_KEEP = 50   # only used when MODE="queue"

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise RuntimeError("Cannot open camera!")

print("Press 'q' to quit.")
frames = []       # for list mode
queue  = deque()  # for queue mode
frame_count = 0
start_time = time.time()

while True:
    ok, frame = cap.read()
    if not ok:
        break
    frame_count += 1

    # -- 1) Cause memory growth ----------------------------------------------
    if MODE == "list":
        frames.append(frame)           # ❌ keeps every frame forever
    elif MODE == "queue":
        queue.append(frame)
        if len(queue) > MAX_KEEP:
            queue.popleft()            # ✅ keep only latest N frames

    # -- 2) Display -----------------------------------------------------------
    cv2.putText(frame, f"Frame: {frame_count}", (30,50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 2)
    cv2.imshow("Leak test", frame)

    # -- 3) Break condition ---------------------------------------------------
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    # -- Optional: show FPS every 100 frames ---------------------------------
    if frame_count % 100 == 0:
        elapsed = time.time() - start_time
        print(f"{frame_count} frames in {elapsed:.1f}s "
              f"({frame_count/elapsed:.1f} FPS)")

cap.release()
cv2.destroyAllWindows()
# main.py
import sys
from PyQt6 import QtWidgets

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = QtWidgets.QWidget()
    w.setWindowTitle("Hello")
    w.resize(300, 120)
    w.show()
    sys.exit(app.exec())
