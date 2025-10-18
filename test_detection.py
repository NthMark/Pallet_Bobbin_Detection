import cv2
from ultralytics import YOLO

# 1) Load models
pallet_model = YOLO(r"C:\Users\Dell\Documents\RTC\Code\Pallet_Bobbin_Detection\model\best.pt")  # your 3-class model
person_model = YOLO("yolov5s.pt")  # COCO model (has 'person'); use 'yolov8n.pt' for faster

# 2) Read image
img_path = r"C:\Users\Dell\Documents\visionGUI\visionGUI\cam204_dataset\images\train\4f6020a5-frame_204_200307.png"
img = cv2.imread(img_path)
out = img.copy()

# 3) Inference
res_pallet = pallet_model(img, conf=0.5, iou=0.45, verbose=False)[0]
res_person = person_model(img, conf=0.2, iou=0.45, classes=[0], verbose=False)[0]  # classes=[0] -> 'person' in COCO

# 4) Draw pallets (from your model)
for b in res_pallet.boxes:
    cls = int(b.cls.item())
    name = res_pallet.names[cls]  # dict {0:'bobbin',1:'pallet',2:'empty'}
    if name != "pallet":
        continue
    x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())
    conf = float(b.conf.item())
    cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(out, f"pallet {conf:.2f}", (x1, max(20, y1-6)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

# 5) Draw persons (from COCO model)
for b in res_person.boxes:
    x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())
    conf = float(b.conf.item())
    cv2.rectangle(out, (x1, y1), (x2, y2), (255, 0, 0), 2)
    cv2.putText(out, f"person {conf:.2f}", (x1, max(20, y1-6)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

cv2.imwrite("out.jpg", out)
print("Saved: out.jpg")
