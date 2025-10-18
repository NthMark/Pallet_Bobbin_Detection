import ultralytics
from ultralytics import YOLO
person_model = YOLO("yolov5s.pt")  # COCO model (has 'person'); use 'yolov8n.pt' for faster