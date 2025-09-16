# from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QMessageBox, QVBoxLayout
# import sys

# class MainWindown(QWidget):
#     def __init__(self):
#         super().__init__()

#         self.setWindowTitle("RTC")
#         self.setGeometry(100, 100, 300, 150)
         
#         self.button = QPushButton("click me")
#         self.button.clicked.connect(self.on_click)

#         layout = QVBoxLayout()
#         layout.addWidget(self.button)
#         self.setLayout(layout)

#     def on_click(self):
#         QMessageBox.information(self, "hello", "clicked button")
# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     windown = MainWindown()
#     windown.show()
#     sys.exit(app.exec())

import cv2 

rtsp = "rtsp://admin:RTC@1122@172.24.24.201:554/Streaming/Channels/101"
cap = cv2.VideoCapture(rtsp)
if not cap.isOpened():
    print("false")
    exit()
while True:
    ret, frame = cap.read()
    if not ret:
        print("false to grab frame")
        break
    cv2.imshow("RTSP", frame)
    if cv2.waitKey(1)&0xff == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()