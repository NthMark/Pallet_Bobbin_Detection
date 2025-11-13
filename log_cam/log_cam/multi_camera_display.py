from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QScrollArea, QCheckBox
from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, pyqtSignal, QThread
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QPolygon, QFont
import cv2
import numpy as np
import json
import os
import torch
import torch.cuda
from ultralytics import YOLO
import datetime
import threading
from queue import Queue
from typing import Dict, List
import gc
import sys
import datetime
from logger_config import get_logger
from requestHIK_bin import HIKSERVER, RequestHIK
from PyQt6.QtWidgets import QMessageBox
from utils import random_string, resource_path,ensure_user_file,user_config_path
import utils
NUMBER_OF_CAMERA=4
MAX_ROWS=2
MAX_COLUMNS=2
CONTAINER_CODE_OUTSIDE="99"
MAX_FRAME_LOG=5000
ERROR="99999"
logger = get_logger(__name__)
import yaml
# Load camera configurations from YAML file
yaml_file = os.path.join(os.path.dirname(__file__), 'config.yaml')
if not os.path.exists(resource_path(yaml_file)):
    logger.error(f"Camera configuration file {yaml_file} not found.")
    sys.exit(1)
config = {}
"""rtc:
  ip_address: "192.168.5.16"
  port: "8182"
"""
with open(resource_path(yaml_file), 'r') as file:
    try:
        config = yaml.safe_load(file)
    except yaml.YAMLError as e:
        logger.exception(f"Error loading YAML file: {e}")
        sys.exit(1)
hikserver = HIKSERVER(ip_address=config['rtc']['ip_address'], port=config['rtc']['port'])

class CameraThread(QThread):
    frame_ready = pyqtSignal(str, np.ndarray, dict)  # Signal to emit frame and detections

    def __init__(self, camera_config: dict, polygons: dict):
        super().__init__()
        self.url = camera_config["camera_url"]
        self.model_path = camera_config["model_path"]
        self.class_id = int(camera_config["id_class"])
        self.model = None
        self.polygons = polygons
        self.running = True
        self.yolo_enabled = False  # Mặc định tắt YOLO
        self.cap = None
        self.skip_frames=10
        self.frame_count=0
        self.last_shape_states = {}  # Store last detection results
        self.no_empty_states={}
        if self.url in self.polygons:
            for shape_name in self.polygons[self.url].keys():
                self.no_empty_states[shape_name] = 0
    def dispose(self):
        """Cleanup resources properly"""
        self.running = False
        
        # Release camera
        if self.cap:
            self.cap.release()
            self.cap = None

        # Cleanup YOLO model
        if self.model:
            try:
                # Unload model from GPU
                if hasattr(self.model, 'cpu'):
                    self.model.cpu()
                if hasattr(self.model, 'model') and self.model.model is not None:
                    if hasattr(self.model.model, 'cpu'):
                        self.model.model.cpu()
                
                # Clear model
                self.model.model = None
                del self.model
                self.model = None

                # Clear CUDA cache
                if torch.cuda.is_available():
                    with torch.cuda.device('cuda'):
                        torch.cuda.empty_cache()
                        torch.cuda.ipc_collect()

            except Exception as e:
                logger.exception(f"Error disposing YOLO model: {e}")

        # Force garbage collection
        gc.collect()

    def run(self):
        try:
            self.cap = cv2.VideoCapture(self.url,cv2.CAP_FFMPEG)
            logger.info(f"Started camera thread for {self.url}")
            
            while self.running and self.cap and self.cap.isOpened():
                if not self.running:  # Double check running state
                    break
                    
                ret, frame = self.cap.read()
                if not ret:
                    break
                self.frame_count+=1
                do_detect=self.yolo_enabled and (self.frame_count%self.skip_frames==0)
                
                # Initialize shape_states with all shapes set to 0 (CLEAR)
                shape_states = {}
                if self.url in self.polygons:
                    for shape_name in self.polygons[self.url].keys():
                        shape_states[shape_name] = 0
                
                if do_detect:  # Chỉ chạy YOLO khi được bật
                    if self.model is None:  # Load model khi cần
                        self.model = YOLO(self.model_path, verbose=False)
                        self.model.fuse()
                    if self.model and self.running:
                        results = self.model(frame, verbose=False)[0]
                        h, w = frame.shape[:2]
                        # no_bobbin=0
                        # confidences=[]
                        for r in results.boxes.data:
                            if not self.running:
                                break

                            x1, y1, x2, y2, score, class_id = r
                            # confidences.append((score.item(),class_id)) 
                            if class_id == self.class_id:  # Bobbin class or Pallet class
                                # no_bobbin+=1
                                if self.url in self.polygons:
                                    for shape_name, points in self.polygons[self.url].items():
                                        abs_points = [(int(x * w), int(y * h)) for x, y in points['points']]
                                        polygon = np.array(abs_points, np.int32)
                                        person_center = ((int(x1) + int(x2)) // 2, (int(y1) + int(y2)) // 2)
                                        if cv2.pointPolygonTest(polygon, person_center, False) >= 0:
                                            shape_states[shape_name] = 1
                                        

                                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
                        # logger.info(f"Number of bobbin: {no_bobbin} with probs {confidences}")
                    # Store the detection results for use in skipped frames
                    self.last_shape_states = shape_states.copy()
                    
                else:
                    # Use last detection results when skipping frames
                    if self.yolo_enabled and self.last_shape_states:
                        shape_states = self.last_shape_states.copy()
                    # If YOLO is disabled, keep all shapes as 0 (CLEAR)
                if self.running:
                    # Emit frame and shape_states, using last_shape_states to fill missing shapes
                    self.frame_ready.emit(self.url, frame, {**self.last_shape_states, **shape_states})
                    # Update last_shape_states
                    self.last_shape_states = shape_states

        except Exception as e:
            logger.exception(f"Error in camera thread: {e}")
        # finally:
        #     self.dispose()
        #     logger.info(f"Camera thread finished for {self.url}")

    def stop(self):
        """Stop thread and cleanup resources"""
        logger.info(f"Stopping camera thread for {self.url}")
        self.running = False
        self.dispose()
        self.wait()
        logger.info(f"Camera thread stopped for {self.url}")

class CameraWidget(QWidget):
    def __init__(self, camera_config: dict, polygons: dict, have_camera: bool):
        super().__init__()
        self.url = camera_config.get("camera_url","")
        self.camera_config = camera_config
        self.polygons = polygons
        self.camera_thread = None
        self.yolo_enabled = False  # Default YOLO state
        self.have_camera=have_camera
        self.previous_states = {}  # Track previous states for change detection
        self.no_empty_state_thresh=1000
        self.is_start=True
        self.init_ui()
        self.busy=False
        self.is_change=False
        self.count=0
        self.change_count=0
        if have_camera:
            self.start_camera()
        else:
            self.camera_not_connected()
    def dispose(self):
        """Cleanup resources"""
        if self.camera_thread:
            logger.info(f"Disposing camera widget for {self.url}")
            self.camera_thread.stop()
            self.camera_thread.wait()
            self.camera_thread.deleteLater()
            self.camera_thread = None
            
    def closeEvent(self, event):
        self.dispose()
        super().closeEvent(event)
    def closeEvent(self, event):
        if hasattr(self, 'camera_thread') and self.camera_thread is not None:
            logger.info(f"Stopping camera thread for {self.url}")
            self.camera_thread.stop()
            self.camera_thread.wait()  # Wait for thread to finish
            self.camera_thread.deleteLater()
            del self.camera_thread  # Explicitly delete the thread
        super().closeEvent(event)
    def init_ui(self):
        self.layout = QVBoxLayout(self)
        
        # Add checkbox to enable/disable YOLO
        self.yolo_checkbox = QCheckBox("Enable Detection")
        self.yolo_checkbox.setChecked(False)
        self.yolo_checkbox.stateChanged.connect(self.toggle_yolo)
        self.yolo_checkbox.setEnabled(self.have_camera)
        # Create container for checkbox with right alignment
        checkbox_container = QHBoxLayout()
        checkbox_container.addStretch()
        checkbox_container.addWidget(self.yolo_checkbox)
        self.layout.addLayout(checkbox_container)
        if self.have_camera:
            self.video_label = QLabel()
            self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout.addWidget(self.video_label)
        else:
            self.status_label = QLabel()
            self.status_label.setStyleSheet("QLabel { background-color: rgba(0, 0, 0, 128); color: white; padding: 5px; }")
            self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout.addWidget(self.status_label)
    def warn(self,msg:str):
        try:
            if hasattr(self,"status_label"):
                self.status_label.setText(f"{msg}")
            # logger.info(msg)
            logger.info(f"[WARN] {msg}")
        except Exception:
            pass
    def error(self,msg:str):
        try:
            if hasattr(self,"status_label"):
                self.status_label.setText(f"{msg}")
                logger.info(msg)
                # logger.critical(f"[ERROR] {msg}")
        except Exception:
            pass
    def camera_not_connected(self):
        self.status_label.setText("No camera")
    def toggle_yolo(self, state):
        """Toggle YOLO detection on/off"""
        requested=bool(state)
        if requested:
            if not self.is_polygon_valid():
                self.yolo_checkbox.setChecked(False)
                self.yolo_checkbox.setEnabled(False)
                if hasattr(self,"status_label"):
                    self.status_label.setText("Detection disabled")

                try:
                    QMessageBox.warning(self,"Detection Disabled",
                                        "Information not fullfilled or wrong. Check information!")
                except Exception:
                    pass
                return

        self.yolo_enabled = requested
        # Update the state of the camera thread
        if self.camera_thread:
            self.camera_thread.yolo_enabled = self.yolo_enabled
        if not self.yolo_checkbox.isEnabled():
            if self.is_polygon_valid():
                self.yolo_checkbox.setEnabled(True)
    def start_camera(self):
        self.camera_thread = CameraThread(self.camera_config, self.polygons)
        self.camera_thread.frame_ready.connect(self.update_frame)
        self.camera_thread.start()
    def is_polygon_valid(self):
        try:
            if self.url not in self.polygons:
                return False
            for _, data in self.polygons[self.url].items():
                # ctnrType=str(data.get('ctnrType','')).strip()
                ctnrCod=str(data.get('ctnrCod','')).strip()
                # positionCode=str(data.get('positionCode','')).strip()
                # stgBin=str(data.get('stgBin','')).strip()
                status=str(data.get('status','')).strip()
                bind=str(data.get('bind','')).strip()
                if status !='SUCCESSFUL':
                    return False
                if bind=='1' and ctnrCod=='':
                    return False
            return True
        except Exception:
            self.error(f"is polygon valid error: {e}")
            return False
    def get_info_shape_ctnrcode_bind(self,ctnrType,positionCode,stgBin,ctnrCod=utils.CONTAINER_CODE_OUTSIDE):
        hikreq = RequestHIK(random_string(8),ctnrType, ctnrCod, \
                                positionCode, '1',stgBinCode=stgBin)
        try:
            result = hikserver.bind_ctnr_and_bin(hikreq=hikreq)
            if result is not None:
                    if result.status_code == 200:
                        logger.info(f"Request successful")
                    else:
                        logger.error(f"Request failed")
        except Exception as e:
            logger.warning(f"Request raised exception: {e}")
            return None
        logger.info(result.json())
        if result.json()["code"]=='0':
            hikreq = RequestHIK(random_string(8),ctnrType, ctnrCod, \
                                positionCode, '0',stgBinCode=stgBin)
            response = hikserver.bind_ctnr_and_bin(hikreq=hikreq)
            if response is not None:
                    if response.status_code == 200:
                        logger.info(f"Request successful")
                    else:
                        logger.error(f"Request failed")
            return ('','0')
        elif 'has bind container code' in result.json()['message']:
            return (result.json()['message'][-1:],'1')
        else:
            return ('','')
    def on_state_changed(self, camera_url: str, shape_name: str, old_state: int, new_state: int):
        """Xử lý khi có thay đổi state"""
        if camera_url == self.url:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            state_text = "DETECTED" if new_state == 1 else "CLEAR"
            old_state_text = "DETECTED" if old_state == 1 else "CLEAR"
            self.polygons[self.url][shape_name]["bind"]=str(new_state)
            # In thông báo ra console
            logger.info(f"[{timestamp}] CAMERA: {camera_url} | ZONE: {shape_name} | CHANGED: {old_state_text} → {state_text}")
            
            # Gửi yêu cầu đến HIKSERVER,  ctnrCod, indBing, positionCode lấy trong file camera_polygons.json theo shape_name
            if self.url not in self.polygons or shape_name not in self.polygons[self.url]:
                logger.info(f"Polygon for {shape_name} not found in {self.url}")
                return
            camera_polygon = self.polygons[self.url][shape_name]
            if not camera_url:
                logger.warning(f"Camera URL is empty for {shape_name} in {self.url}")
                return
            indBind='1' if state_text == "DETECTED" else '0'
            info=self.get_info_shape_ctnrcode_bind(camera_polygon['ctnrType'],camera_polygon['positionCode'],camera_polygon['stgBin'])
            if info is None and info[1]=='':
                try:
                    QMessageBox.critical(self,"Detection Status",
                                        "Error while getting container code!!!")
                except Exception:
                    return
            if info[1]=='1':
                self.polygons[self.url][shape_name]["ctnrCod"]=''if new_state==0 else info[0]
                hikreq = RequestHIK(hikserver.random_string(8),
                                        camera_polygon['ctnrType'],
                                    info[0],
                                    camera_polygon['positionCode'],
                                    indBind,
                                    stgBinCode=camera_polygon['stgBin']
                    )
                response = hikserver.bind_ctnr_and_bin(hikreq=hikreq)
                if response is not None:
                    if response.status_code == 200:
                        logger.info(f"Request successful ({camera_polygon['ctnrCod']},{camera_polygon['positionCode']}): {response.json()} with bind {indBind}")
                    else:
                        logger.error(f"Request failed ({camera_polygon['ctnrCod']},{camera_polygon['positionCode']}) with status code {response.status_code}: {response.text}")
            self.save_polygons()
            
    def check_changed_state(self,previous_state,current_state,shape_name):
        if current_state ==0 :
            if previous_state==1 and self.camera_thread.no_empty_states[shape_name] <self.no_empty_state_thresh:
                self.camera_thread.no_empty_states[shape_name]+=1
                return 1
            return 0
        else:
            self.camera_thread.no_empty_states[shape_name]=0
            return 1
            
    def update_frame(self, url: str, frame: np.ndarray, shape_states: dict):
        if url != self.url:
            return
        if self.busy:
            return
        self.busy=True
        if self.is_start:
            logger.info(self.previous_states)
            self.is_start=False
        # Check for state changes and call on_state_changed
        for shape_name, current_state in shape_states.items():
            previous_state = self.previous_states.get(shape_name, 0)
            current_state=self.check_changed_state(previous_state,current_state,shape_name)
            shape_states[shape_name]=current_state
            if current_state != previous_state:
                # logger.info(f"on_state_changed {url}-{shape_name}-{previous_state}-{current_state}")
                if self.yolo_enabled:
                    self.is_change=True
                    # logger.info(f"on_state_changed {url}-{shape_name}-{previous_state}-{current_state}")
                    self.on_state_changed(url, shape_name, previous_state, current_state)
        if self.count >=MAX_FRAME_LOG and self.is_change:
            self.count=0
        if self.is_change:
            self.is_change=False
            self.change_count+=1
        if self.count <MAX_FRAME_LOG  :
            self.count+=1
            if self.count % 200==0:
                cv2.imwrite(os.path.join("./log_cam",f"frame_{url[22:35]}_{self.change_count}_{self.count}.png"),frame)
        # Update previous states
        self.previous_states = shape_states.copy()

        # Convert frame to RGB for Qt
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        
        # Convert to QImage
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
        
        # Create pixmap and painter
        pixmap = QPixmap.fromImage(qt_image)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw polygons and their states
        if self.url in self.polygons:
            status_text = []
            for shape_name, points in self.polygons[self.url].items():
                # Set color based on state
                state = shape_states.get(shape_name, 0)
                color = QColor(0, 255, 0) if state == 1 else QColor(255, 0, 0)
                
                # Draw polygon
                pen = QPen(color)
                pen.setWidth(2)
                painter.setPen(pen)
                
                # Fill polygon with semi-transparent color
                fill_color = QColor(color)
                fill_color.setAlpha(50)
                painter.setBrush(fill_color)
                
                # Convert points to pixel coordinates
                pixel_points = []
                for x, y in points['points']:
                    pixel_x = int(x * w)
                    pixel_y = int(y * h)
                    pixel_points.append(QPoint(pixel_x, pixel_y))
                
                # Draw polygon
                painter.drawPolygon(QPolygon(pixel_points))
                
                # Add status text với màu sắc rõ ràng hơn
                state_text = "DETECTED" if state == 1 else "CLEAR"
                status_text.append(f"{shape_name}: {state_text}")


        painter.end()

        # Scale image to fit label
        scaled_pixmap = pixmap.scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)
        self.busy=False
    def save_polygons(self):
        """Save polygons to JSON file"""
        try:
            path=user_config_path('camera_polygons.json')
            tmp=path.with_suffix(".json.tmp")
            with tmp.open('w',encoding="utf-8") as f:
                json.dump(self.polygons, f, ensure_ascii=False,indent=2)
            tmp.replace(path)
            # with open(resource_path('camera_polygons.json'), 'w') as f:
            #     json.dump(self.polygons, f, indent=2)
            logger.info("Polygons saved successfully")
        except Exception as e:
            logger.exception(f"Error saving polygons: {e}")
class MultiCameraDisplay(QWidget):
    def __init__(self, camera_configs: List[dict], parent=None):
        super().__init__(parent)
        self.camera_configs = camera_configs
        self.camera_widgets = []
        self.polygons_config=os.path.join(os.path.dirname(__file__), 'camera_polygons.json')
        self.init_ui()
        
    def dispose(self):
        """Cleanup all resources"""
        logger.info("Starting MultiCameraDisplay cleanup")
        
        # Stop and cleanup all camera widgets
        for widget in self.camera_widgets:
            try:
                logger.info(f"Cleaning up widget for {widget.url}")
                widget.dispose()  # Stop thread and cleanup YOLO
                widget.deleteLater()
            except Exception as e:
                logger.exception(f"Error cleaning up widget: {e}")

        self.camera_widgets.clear()
        
        # Force cleanup
        gc.collect()
        if torch.cuda.is_available():
            with torch.cuda.device('cuda'):
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
        
        logger.info("MultiCameraDisplay cleanup completed")

    def closeEvent(self, event):
        logger.info("MultiCameraDisplay closing...")
        self.dispose()
        super().closeEvent(event)
        self.deleteLater()
        logger.info("MultiCameraDisplay closed")

    def init_ui(self):
        # Create main layout
        self.layout = QVBoxLayout(self)
        
        # Create scroll area for camera grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.layout.addWidget(scroll)
        
        # Create widget for grid
        grid_widget = QWidget()
        self.grid_layout = QGridLayout(grid_widget)
        scroll.setWidget(grid_widget)
        
        # Load polygons
        try:
            path=ensure_user_file(self.polygons_config)
            with path.open('r',encoding="utf-8") as f:
            # with open(resource_path(self.polygons_config), 'r') as f:
                self.polygons = json.load(f)
        except:
            self.polygons = {}
        
        # Create camera widgets
        column_idx = 0
        row_idx=0
        for i, config in enumerate(self.camera_configs):
            logger.info(i)
            camera_widget = CameraWidget(config, self.polygons,True)
            self.camera_widgets.append(camera_widget)  # Store reference
            row_idx=i//MAX_ROWS
            column_idx=i%MAX_COLUMNS
            self.grid_layout.addWidget(camera_widget, row_idx, column_idx)
        for i in range(len(self.camera_configs),NUMBER_OF_CAMERA):
            camera_widget = CameraWidget({}, {},False)
            self.camera_widgets.append(camera_widget)  # Store reference
            row_idx=i//MAX_ROWS
            column_idx=i%MAX_COLUMNS
            self.grid_layout.addWidget(camera_widget, row_idx, column_idx)
