from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QInputDialog, QDialog, QFormLayout, QPushButton, 
                             QLineEdit, QMessageBox, QApplication, QStatusBar, QFrame)
from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, pyqtSignal,QObject,QThread
from PyQt6.QtGui import (QImage, QPixmap, QPainter, QPen, QColor, QPolygon, 
                        QFont, QCursor, QAction, QKeyEvent,QMovie)
import cv2,multiprocessing, time
import numpy as np
import json
import os
from enum import Enum, auto
import logging
import sys
import yaml
from typing import Dict, List, Tuple, Optional, Union
from requestHIK_bin import HIKSERVER,RequestHIK
from logger_config import get_logger
from utils import random_string, resource_path,ensure_user_file,user_config_path
import utils
# Configure logging
logger = get_logger(__name__)

class ConfigLoader:
    @staticmethod
    def load_config(file_path=None):
        """Load configuration from YAML file"""
        if file_path is None:
            file_path = resource_path("config.yaml")
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.exception(f"Failed to load config: {e}")
            return {"rtc": {"ip_address": "192.168.5.16", "port": "8181"}}

class CameraManager:
    def __init__(self):
        self.cameras = []  # List of camera URLs/paths
        self.current_camera_index = 0

    def load_cameras_from_config(self, config_path="camera_configs.json"):
        """Load cameras from configuration file"""
        try:
            path=ensure_user_file(config_path)
            with path.open('r',encoding="utf-8") as f:
                configs = json.load(f)
            # with open(resource_path(config_path), 'r') as f:
            #     configs = json.load(f)
            
            self.cameras = []
            for config in configs:
                camera_url = config.get('camera_url', '')
                if camera_url:
                    self.cameras.append(camera_url)
            
            logger.info(f"Loaded {len(self.cameras)} cameras from config: {self.cameras}")
            return True
        except Exception as e:
            logger.exception(f"Failed to load camera configs: {e}")
            return False

    def add_camera(self, url):
        """Add a camera URL to the list"""
        if url not in self.cameras:
            self.cameras.append(url)

    def get_current_camera(self):
        """Get current camera URL"""
        if not self.cameras:
            return None
        return self.cameras[self.current_camera_index]

    def next_camera(self):
        """Switch to next camera"""
        logger.info(self.cameras, self.current_camera_index)
        if self.cameras and self.current_camera_index < len(self.cameras) - 1:
            self.current_camera_index += 1
            return True
        return False

    def prev_camera(self):
        """Switch to previous camera"""
        if self.cameras and self.current_camera_index > 0:
            self.current_camera_index -= 1
            return True
        return False

class PolygonPropertiesDialog(QDialog):
    """Dialog for editing polygon properties"""
    
    def __init__(self, parent=None, shape_name="",ctnr_type="", ctnr_code="", position_code="",stg_bin="",bind=""):
        super().__init__(parent)
        self.setWindowTitle("Edit Polygon Properties")
        self.setModal(True)
        self.resize(300, 200)
        
        layout = QFormLayout()
        
        # Name field
        self.name_edit = QLineEdit(shape_name)
        self.name_edit.setPlaceholderText("Enter shape name")
        layout.addRow("Name:", self.name_edit)
        
        # Container Code field
        self.ctnr_type_edit = QLineEdit(ctnr_type)
        self.ctnr_type_edit.setPlaceholderText("Enter container type")
        layout.addRow("Container Type:", self.ctnr_type_edit)
        
        self.ctnr_code_edit = QLineEdit(ctnr_code)
        self.ctnr_code_edit.setPlaceholderText("Enter container code")
        layout.addRow("Container Code:", self.ctnr_code_edit)
        # Position Code field
        self.position_code_edit = QLineEdit(position_code)
        self.position_code_edit.setPlaceholderText("Enter position code")
        layout.addRow("Position Code:", self.position_code_edit)
        #Storage Bin field
        self.stg_bin_edit = QLineEdit(stg_bin)
        self.stg_bin_edit.setPlaceholderText("Enter storage bin")
        layout.addRow("Storage bin:", self.stg_bin_edit)
        # Item available
        self.bind_code_edit = QLineEdit(bind)
        self.bind_code_edit.setPlaceholderText("Enter Bind Status")
        layout.addRow("Bind:", self.bind_code_edit)
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        save_button.setDefault(True)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addRow(button_layout)
        
        self.setLayout(layout)
        
        # Focus on name field
        self.name_edit.setFocus()
        self.name_edit.selectAll()
        main_win=self.parent()
        dev_enabled=getattr(main_win,"developer_mode",False) if main_win else False
        for widget in [self.ctnr_code_edit,self.bind_code_edit,self.name_edit]:
            widget.setDisabled(not dev_enabled)
            if not dev_enabled:
                widget.setStyleSheet("background-color: #f0f0f0;color:gray;")
            else:
                widget.setStyleSheet("")
    def get_values(self) -> Dict[str, str]:
        """Get the values from the form"""
        return {
            'name': self.name_edit.text().strip(),
            'ctnrCod': self.ctnr_code_edit.text().strip(),
            'positionCode': self.position_code_edit.text().strip(),
            'ctnrType': self.ctnr_type_edit.text().strip(),
            'bind':self.bind_code_edit.text().strip(),
            'stgBin':self.stg_bin_edit.text().strip()
        }
def _probe_process(url: str, result_queue: multiprocessing.Queue):
    """
    Runs in a separate process. Attempts one open+read
    and reports back via the queue.
    """
    cap = cv2.VideoCapture()
    try:
        # Force FFMPEG backend
        if not cap.open(url,cv2.CAP_FFMPEG):
            result_queue.put(("error", "could not open stream"))
            return

        ret, _ = cap.read()
        if not ret:
            result_queue.put(("error", "could not read first frame"))
            return

        result_queue.put(("ok", ""))

    except Exception as e:
        result_queue.put(("error", str(e)))
    finally:
        cap.release()


class StreamOpener(QObject):
    finished = pyqtSignal(str, bool, str)

    def __init__(self, url: str, timeout_s: float = 60.0):
        super().__init__()
        self.url       = url
        self.timeout_s = timeout_s

    def run(self):
        # 1) Create a queue and a process
        queue = multiprocessing.Queue(1)
        proc  = multiprocessing.Process(
            target=_probe_process,
            args=(self.url, queue),
            daemon=True,
        )
        proc.start()

        # 2) Wait for result or timeout
        start = time.time()
        while True:
            if not proc.is_alive():
                # process finished—grab the result
                try:
                    status, msg = queue.get_nowait()
                except:
                    status, msg = "error", "no response"
                proc.join()
                break

            if time.time() - start > self.timeout_s:
                # timed out—kill the process
                proc.terminate()
                proc.join()
                status, msg = "timeout", f"Timed out after {self.timeout_s:.1f}s"
                break

            time.sleep(0.01)

        # 3) Emit the appropriate signal
        if status == "ok":
            self.finished.emit(self.url, True, "")
        else:
            self.finished.emit(self.url, False, msg)

class ShapeStatus(Enum):
    NO_INFORMATION = auto()
    SUCCESSFUL = auto()
    WRONG_PODCODE = auto()
    WRONG_POSITIONCODE=auto()
    EMPTY_PODCODE=auto()
    EMPTY_POSITIONCODE=auto()
    ALREADY_BINDED=auto()
    NOT_BINDED=auto()
    FAILED=auto()
class VideoDisplay(QWidget):
    """Enhanced video display widget with polygon drawing capabilities"""
    
    # Signals
    shape_selected = pyqtSignal(str)  # Emitted when a shape is selected
    shape_created = pyqtSignal(str)   # Emitted when a new shape is created
    shape_deleted = pyqtSignal(str)   # Emitted when a shape is deleted
    connecting = pyqtSignal(str)
    connection_result = pyqtSignal(str,bool,str)
    hik_error = pyqtSignal(str)
    fatalError = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Load configuration
        config = ConfigLoader.load_config()
        
        # Initialize camera manager and load cameras from config
        self.camera_manager = CameraManager()
        if not self.camera_manager.load_cameras_from_config():
            # Fallback to default camera if config loading fails
            logger.info("Failed to load camera configs, using default camera")
            self.camera_manager.add_camera("rtsp://admin:RTC@1122@172.24.24.201:554/Streaming/Channels/101")
        
        # Get HIK server IP and port from config.yaml
        self.ip_address = config["rtc"].get("ip_address", "192.168.5.16")
        self.port = int(config["rtc"].get("port", "8181"))
        logger.info(f"Using HIK server: {self.ip_address}:{self.port}")
        
        self.drawing_mode = False
        self.draw_rectangle_mode = False
        self.start_point: Optional[Tuple[float, float]] = None
        self.points: List[Tuple[float, float]] = []
        self.polygons: Dict[str, Dict[str, Union[Dict, List]]] = {}
        self.current_shape_id: int = 0
        self.selected_shape: Optional[str] = None
        self.current_mouse_pos: Optional[QPoint] = None
        self.current_video_coords: Optional[Tuple[float, float]] = None
        self._openers: List[QThread] = []
        self._opener_thread=None
        
        # Video capture objects
        self.cap: Optional[cv2.VideoCapture] = None
        self.timer: QTimer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.fatalError.connect(QApplication.quit)
        self.hik_error.connect(self.on_hik_error)
        
        # Initialize HIK server
        self.hikserver = HIKSERVER(ip_address=self.ip_address, port=self.port)
        self.connect = True
        self.dev_mode=dict()
        # Initialize UI and load saved data
        self.init_ui()
        self._connect_spinners()
        self.load_polygons()
        self.init_shape_info()
        logger.info(f"VideoDisplay widget initialized with {len(self.camera_manager.cameras)} cameras")
    def on_hik_error(self, msg: str):
        QMessageBox.critical(self, "HIK Server Error", msg)
        self.cleanup_thread()
        self.cleanup_capture()
        QApplication.quit()
        sys.exit(0)
    def init_ui(self):
        """Initialize the user interface"""
        self.layout = QVBoxLayout(self)
        # Create video display label
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        
        # Create camera info label
        self.camera_info_label = QLabel("Camera: Not connected")
        self.camera_info_label.setStyleSheet("""
            QLabel {
                min-height: 20px;
                max-height: 20px;
                padding: 5px;
                border: 1px solid #ccc;
                background-color: #e8f4fd;
                font-weight: bold;
            }
        """)
        
        # Create navigation buttons
        nav_layout = QHBoxLayout()
        self.prev_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")
        self.prev_button.clicked.connect(self.prev_camera)
        self.next_button.clicked.connect(self.next_camera)
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.next_button)
        
        self.layout.addWidget(self.camera_info_label)
        self.layout.addWidget(self.video_label)
        self.layout.addLayout(nav_layout)
        
        # Update navigation buttons state
        self.update_nav_buttons()
        self.update_camera_info()
        
        #Spinner Overlay
        self.spinner_label=QLabel(self.video_label)
        self.spinner_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.spinner_movie=QMovie(resource_path("spinner.gif"))
        self.spinner_label.setMovie(self.spinner_movie)
        self.spinner_label.hide()
        # Create status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                min-height: 20px;
                max-height:20px;
                padding: 5px;
                border: 1px solid #ccc;
                background-color: #f0f0f0;
            }
        """)
        self.layout.addWidget(self.status_label)
        
        # Configure mouse and keyboard events
        self.setup_event_handlers()
        
        logger.info("UI initialized")
    
    def setup_event_handlers(self):
        """Set up event handlers for mouse and keyboard interactions"""
        self.video_label.setMouseTracking(True)
        self.video_label.mousePressEvent = self.mouse_press_event
        self.video_label.mouseDoubleClickEvent = self.mouse_double_click_event
        self.video_label.mouseMoveEvent = self.mouse_move_event
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def get_scaled_video_rect(self) -> QRect:
        """Get the actual rectangle where the video is displayed in the label"""
        if not self.video_label.pixmap():
            return QRect(0, 0, self.video_label.width(), self.video_label.height())
        
        # Get the scaled size of the video
        scaled_size = self.video_label.pixmap().size()
        scaled_size.scale(self.video_label.size(), Qt.AspectRatioMode.KeepAspectRatio)
        
        # Calculate position to center the video in the label
        x = (self.video_label.width() - scaled_size.width()) / 2
        y = (self.video_label.height() - scaled_size.height()) / 2
        
        return QRect(int(x), int(y), scaled_size.width(), scaled_size.height())
    
    def convert_to_video_coordinates(self, pos: QPoint) -> Optional[Tuple[float, float]]:
        """Convert mouse position to relative video coordinates (0-1 range)"""
        video_rect = self.get_scaled_video_rect()
        
        # Check if click is inside video area
        if not video_rect.contains(pos):
            return None
        
        # Convert to relative coordinates within the video
        x = (pos.x() - video_rect.x()) / video_rect.width()
        y = (pos.y() - video_rect.y()) / video_rect.height()
        
        return (max(0, min(1, x)), max(0, min(1, y)))
    
    def mouse_press_event(self, event):
        """Handle mouse press events"""
        if not self.current_url:
            return
        
        # Get relative coordinates in video space
        video_coords = self.convert_to_video_coordinates(event.pos())
        if video_coords is None:
            return
        
        x, y = video_coords
        
        if not self.drawing_mode:
            # Handle selection when not in drawing mode
            self.handle_selection(x, y)
            return
        
        # Handle drawing mode
        self.handle_drawing(event, video_coords)
    
    def handle_selection(self, x: float, y: float):
        """Handle polygon selection"""
        click_point = (x, y)
        clicked_shape = None
        
        # Find clicked polygon
        if self.current_url in self.polygons:
            for shape_name, polygon_data in self.polygons[self.current_url].items():
                points = self.get_polygon_points(polygon_data)
                if self.point_in_polygon(click_point, np.array(points)):
                    clicked_shape = shape_name
                    break
        
        # Update selection
        if self.selected_shape != clicked_shape:
            self.selected_shape = clicked_shape
            if clicked_shape:
                self.shape_selected.emit(clicked_shape)
                self.update_status(f"Selected shape: {clicked_shape}")
            else:
                self.update_status("No shape selected")
    
    def handle_drawing(self, event, video_coords: Tuple[float, float]):
        """Handle drawing operations"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.draw_rectangle_mode:
                self.handle_rectangle_drawing(video_coords)
            else:
                self.handle_polygon_drawing(video_coords)
        elif event.button() == Qt.MouseButton.RightButton and len(self.points) >= 3:
            self.complete_polygon()
    
    def handle_rectangle_drawing(self, video_coords: Tuple[float, float]):
        """Handle rectangle drawing"""
        if self.start_point is None:
            self.start_point = video_coords
            self.update_status("Click to complete rectangle")
        else:
            x1, y1 = self.start_point
            x, y = video_coords
            self.points = [(x1, y1), (x, y1), (x, y), (x1, y)]
            self.complete_shape()
    
    def handle_polygon_drawing(self, video_coords: Tuple[float, float]):
        """Handle polygon drawing"""
        self.points.append(video_coords)
        self.update_status(f"Added point {len(self.points)}. Right-click to complete.")
    
    def complete_polygon(self):
        """Complete polygon drawing"""
        if len(self.points) >= 3:
            self.complete_shape()
    
    def complete_shape(self):
        """Complete shape creation"""
        self.get_shape_id()
        shape_name = f"shape_{self.current_shape_id}"
        
        # Initialize dictionary for current URL if it doesn't exist
        if self.current_url not in self.polygons:
            self.polygons[self.current_url] = {}
        ctnrtype=None
        if '172.24.24.202' in self.current_url:
            ctnrtype='2'
        else:
            ctnrtype='1'
        if ctnrtype is None:
            try:
                QMessageBox.warning(self,"Wrong url",
                                        "Check url!")
            except Exception:
                pass
            return
        # Create new shape
        self.polygons[self.current_url][shape_name] = {
            'points': self.points.copy(),
            'ctnrType':ctnrtype,
            'ctnrCod': '',
            'positionCode': '',
            'stgBin':'',
            'status':ShapeStatus.NO_INFORMATION.name,
            'bind':"0"
        }
        
        self.current_shape_id += 1
        self.points.clear()
        self.start_point = None
        
        # Save and emit signal
        self.save_polygons()
        self.shape_created.emit(shape_name)
        self.update_status(f"Created shape: {shape_name}")
        
        logger.info(f"Shape created: {shape_name}")
    def get_shape_id(self):
        if self.current_url not in self.polygons:
            self.current_shape_id=0
            return
        shape_names=list(self.polygons[self.current_url].keys())
        shape_names=[int(x[len("shape_"):]) for x in shape_names]
        # logger.info(shape_names)
        max_shape_id=max(shape_names)
        for i in range(max_shape_id+1):
            if i not in shape_names:
                self.current_shape_id=i
                return
        self.current_shape_id=max_shape_id+1
    def mouse_double_click_event(self, event):
        """Handle double click events for polygon property editing"""
        if self.drawing_mode or not self.current_url:
            return
        
        shape_name = self.find_clicked_polygon(event.pos())
        if shape_name:
            status_id=self.polygons[self.current_url][shape_name]['status']
            if status_id==ShapeStatus.WRONG_POSITIONCODE.name:
                self.update_status("Fail to bind or unbind:  Berth does not exist")
            elif status_id==ShapeStatus.WRONG_PODCODE.name:
                self.update_status("Fail to bind or unbind: Storage rack does not exist")
            elif status_id==ShapeStatus.EMPTY_POSITIONCODE.name:
                self.update_status("Fail to bind or unbind: Berth name cannot be blank")
            elif status_id==ShapeStatus.EMPTY_PODCODE.name:
                self.update_status("Fail to bind or unbind: Rack serial number may not be empty")
            elif status_id==ShapeStatus.NO_INFORMATION.name:
                self.update_status("No information")
            elif status_id==ShapeStatus.SUCCESSFUL.name:
                self.update_status("Correct information")
            self.edit_shape_properties(shape_name)
            
    
    def mouse_move_event(self, event):
        """Handle mouse move events"""
        if not self.cap:
            return
        
        # Convert mouse position to frame coordinates
        mouse_pos = event.pos()
        current_coords = self.convert_to_video_coordinates(mouse_pos)
        
        # Store current mouse position for use in update_frame
        self.current_mouse_pos = mouse_pos
        self.current_video_coords = current_coords
        
        # Update status with coordinates
        if current_coords:
            status_text = f"Mouse: ({mouse_pos.x()}, {mouse_pos.y()}) "
            status_text += f"Normalized: ({current_coords[0]:.3f}, {current_coords[1]:.3f})"
            self.update_status(status_text)
    # Initialize current container code and bind status at start-up
    def init_shape_info(self):
        for url in self.polygons.keys():
            for shape in self.polygons[url].keys():
                if self.polygons[url][shape]["status"]==ShapeStatus.SUCCESSFUL.name:
                    shape_info=self.polygons[url][shape]
                    print(f"url {url} with {shape_info['stgBin']}")
                    shape_ctnr_code_bind=self.get_info_shape_ctnrcode_bind(shape_info["ctnrType"],
                                                      shape_info["positionCode"],
                                                      shape_info["stgBin"])
                    logger.info(f"Get shape {shape_ctnr_code_bind}")
                    if shape_ctnr_code_bind is not None and shape_ctnr_code_bind[1]!='':
                        self.polygons[url][shape]["ctnrCod"]=shape_ctnr_code_bind[0]
                        self.polygons[url][shape]["bind"]=shape_ctnr_code_bind[1]
        self.save_polygons()
    #Automatically get container code and bind status
    def get_info_shape_ctnrcode_bind(self,ctnrType,positionCode,stgBin,ctnrCod=utils.CONTAINER_CODE_OUTSIDE):
        hikreq = RequestHIK(random_string(8),ctnrType, ctnrCod, \
                                positionCode, '1',stgBinCode=stgBin)
        try:
            result = self.hikserver.bind_ctnr_and_bin(hikreq=hikreq)
            if result is not None:
                    if result.status_code == 200:
                        logger.info(f"Request successful")
                    else:
                        logger.error(f"Request failed")
        except Exception as e:
            logger.warning(f"Request raised exception: {e}")
            return None
        print(result.json())
        if result.json()["code"]=='0':
            hikreq = RequestHIK(random_string(8),ctnrType, ctnrCod, \
                                positionCode, '0',stgBinCode=stgBin)
            response = self.hikserver.bind_ctnr_and_bin(hikreq=hikreq)
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
    def edit_shape_properties(self, shape_name: str):
        """Edit properties of a shape"""
        try: 
            self.load_polygons()
        except Exception as e:
            logger.exception(f"Fail to load polygon")
        if self.current_url not in self.polygons or shape_name not in self.polygons[self.current_url]:
            logger.exception(f"Fail to get information to load")
            return
        ctnrtype=None
        if '172.24.24.202' in self.current_url:
            ctnrtype='2'
        else:
            ctnrtype='1'
        if ctnrtype is None:
            try:
                QMessageBox.warning(self,"Wrong url",
                                        "Check url!")
            except Exception:
                pass
            return
        status=None
        polygon_data = self.polygons[self.current_url][shape_name]
        if self.polygons[self.current_url][shape_name]['ctnrType'] !=ctnrtype:
            self.polygons[self.current_url][shape_name]['ctnrType']=ctnrtype
        dialog = PolygonPropertiesDialog(
            self,
            shape_name,
            polygon_data.get('ctnrType',''),
            polygon_data.get('ctnrCod', ''),
            polygon_data.get('positionCode', ''),
            polygon_data.get('stgBin', ''),
            polygon_data.get('bind', ''),
            
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.get_values()
            new_name = values['name']
            
            if not new_name:
                QMessageBox.warning(self, "Warning", "Shape name cannot be empty!")
                return
            
            # Check if new name already exists (and is different from current)
            if new_name != shape_name and new_name in self.polygons[self.current_url]:
                QMessageBox.warning(self, "Warning", f"Shape name '{new_name}' already exists!")
                return
            
            # Update polygon properties
            points = self.get_polygon_points(polygon_data)
            
            # Remove old entry if name changed
            if new_name != shape_name:
                del self.polygons[self.current_url][shape_name]
            #BKeep bind in all situations
            # hikreq = RequestHIK(random_string(8),values['ctnrType'], values['ctnrCod'], \
            #                     values['positionCode'], values['bind'],stgBinCode=values['stgBin'])
            # response = self.hikserver.bind_ctnr_and_bin(hikreq=hikreq)
            # result=response.json()
            # logger.info(result)
            is_successful=False
            if values['ctnrType'] and values['positionCode'] and values['stgBin']:
                info=self.get_info_shape_ctnrcode_bind(values['ctnrType'],values['positionCode'],values['stgBin'])
                if info is not None and info[1] != '':
                    values['ctnrCod']=info[0]
                    values['bind']=info[1]
                    status=ShapeStatus.SUCCESSFUL.name
                    logger.info(f"Updated shape {new_name}: Successful")
                    self.update_status(f"Updated shape {new_name}: Successful")
                    is_successful=True
            # if (values['ctnrType'] and values['positionCode'] and values['bind']=='1' and values['stgBin'] and values['ctnrCod']) or \
            # (values['ctnrType'] and values['positionCode'] and values['bind']=='0' and values['stgBin'] and values['ctnrCod']==''):
            #     if values['bind']=='1' and values['ctnrCod']:
            #         info=self.get_info_shape_ctnrcode_bind(values['ctnrType'],values['positionCode'],values['stgBin'])
            #         if info is not None:
            #             if info[1]=='1':
            #                 if info[0] != 
            #     status=ShapeStatus.SUCCESSFUL.name
            #     logger.info(f"Updated shape {new_name}: Successful")
            #     self.update_status(f"Updated shape {new_name}: Successful")
            if not is_successful:
                status=ShapeStatus.NO_INFORMATION.name
                logger.info(f"Updated shape {new_name}: No information filled")
                self.update_status(f"Updated shape {new_name}: No information filled")     
            self.polygons[self.current_url][new_name] = {
                'points': points,
                'ctnrType':values['ctnrType'],
                'ctnrCod': values['ctnrCod'],
                'positionCode': values['positionCode'],
                'stgBin': values['stgBin'],
                'status': status,
                'bind':values['bind']
            }
            self.save_polygons()
            logger.info(f"Shape updated: {shape_name} -> {new_name}")
    def _connect_spinners(self):
        self.connecting.connect(self._on_connecting_spinner)
        self.connection_result.connect(self._on_connection_spinner_result)
    def _on_connecting_spinner(self,url:str):
        self.spinner_label.resize(self.video_label.size())
        self.spinner_movie.start()
        self.spinner_label.show()
    def _on_connection_spinner_result(self,url:str,success:bool,error:str):
        self.spinner_movie.stop()
        self.spinner_label.hide()
    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        self.spinner_label.resize(self.video_label.size())
    def set_source(self, url: str) -> None:
        if getattr(self, '_opener_thread', None):
            # logger.info("thread existed")
            self.cleanup_thread()

        self.cleanup_capture()
        self._pending_url = url
        self.video_label.clear()
        self.video_label.setText("Connecting…")
        self.connecting.emit(url)

        self._opener_thread = QThread(self)
        self._opener        = StreamOpener(url)
        self._opener.moveToThread(self._opener_thread)

        self._opener_thread.started.connect(self._opener.run)
        self._opener.finished .connect(self.on_stream_opened)
        self._opener.finished .connect(self._opener_thread.quit)
        self._opener.finished .connect(self._opener.deleteLater)

        self._opener_thread.start()
        self._openers.append(self._opener_thread)
    def on_stream_opened(self,url:str,success:bool,error_message:str):
        if url != self._pending_url:
            return
        self._pending_url = None
        self.connection_result.emit(url,success,error_message)

        if success:
            self.cap=cv2.VideoCapture(url,cv2.CAP_FFMPEG)
            self.current_url=url
            self.timer.start(30)
            self.update_status(f"Connected to: {url}")
        else:
            # logger.info("I get error ")
            self.video_label.setText(f"Error: {error_message}\nURL: {url}")
            self.current_url=None
            self.update_status("Connection failed")
    
    
    def cleanup_capture(self):
        if hasattr(self,'timer') and self.timer.isActive():
            self.timer.stop()
        if hasattr(self,'cap') and self.cap:
            self.cap.release()
            self.cap=None
        self.current_url = None
    def cleanup_thread(self):
        """
    Stop & wait any in-flight StreamOpener thread before we overwrite it.
    """
        if self._opener_thread in self._openers:
            self._openers.remove(self._opener_thread)
        thr = getattr(self, '_opener_thread', None)
        if not thr:
            return
        thr.quit()
        thr.finished.connect(thr.deleteLater)
        self._opener_thread = None
        self._opener        = None
    def update_frame(self):
        """Update video frame display"""
        if self.cap is None or not self.cap.isOpened():
            return
        
        ret, frame = self.cap.read()
        if not ret:
            logger.warning("Failed to read frame")
            return
        
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            
            # Convert to QImage
            bytes_per_line = ch * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
            
            # Create pixmap and draw overlays
            pixmap = QPixmap.fromImage(qt_image)
            self.draw_overlays(pixmap)
            
            # Scale and display
            scaled_pixmap = pixmap.scaled(
                self.video_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation
            )
            
            self.video_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            logger.exception(f"Error updating frame: {e}")
    
    def draw_overlays(self, pixmap: QPixmap):
        """Draw polygon overlays on the video frame"""
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        try:
            # Draw saved polygons
            if self.current_url in self.polygons:
                for shape_name, polygon_data in self.polygons[self.current_url].items():
                    color = QColor(125, 0, 200) if shape_name == self.selected_shape else QColor(255, 125, 125)
                    self.draw_polygon(painter, polygon_data, color, shape_name)
            
            # Draw polygon being created
            if self.drawing_mode and self.points:
                temp_data = {'points': self.points}
                self.draw_polygon(painter, temp_data, QColor(125, 236, 0))
            
            # Draw rectangle preview
            if self.drawing_mode and self.draw_rectangle_mode and self.start_point and self.current_video_coords:
                self.draw_rectangle_preview(painter)
            
            # Draw coordinate info
            self.draw_coordinate_info(painter, pixmap.size())
            
        except Exception as e:
            logger.exception(f"Error drawing overlays: {e}")
        finally:
            painter.end()
    
    def draw_rectangle_preview(self, painter: QPainter):
        """Draw rectangle preview while drawing"""
        if not self.start_point or not self.current_video_coords:
            return
        
        x1, y1 = self.start_point
        x2, y2 = self.current_video_coords
        preview_points = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        temp_data = {'points': preview_points}
        self.draw_polygon(painter, temp_data, QColor(255, 255, 0))
    
    def draw_coordinate_info(self, painter: QPainter, pixmap_size):
        """Draw coordinate information overlay"""
        if not (self.current_mouse_pos and self.current_video_coords):
            return
        
        # Prepare coordinate text
        mouse_info = f"Mouse: ({self.current_mouse_pos.x()}, {self.current_mouse_pos.y()})"
        x, y = self.current_video_coords
        coord_info = f"Normalized: ({x:.3f}, {y:.3f})"
        
        # Draw background rectangle
        painter.setPen(QPen(Qt.GlobalColor.white))
        painter.setFont(QFont("Arial", 10))
        
        text = f"{mouse_info} | {coord_info}"
        text_rect = painter.boundingRect(QRect(10, 10, pixmap_size.width() - 20, 30), 
                                       Qt.TextFlag.TextWordWrap, text)
        
        # Draw semi-transparent background
        painter.fillRect(text_rect.adjusted(-5, -2, 5, 2), QColor(0, 0, 0, 128))
        painter.drawText(15, 22, text)
    
    def draw_polygon(self, painter: QPainter, polygon_data: Dict, color: QColor, shape_name: str = None):
        """Draw a polygon with the given color and optional label"""
        points = self.get_polygon_points(polygon_data)
        if not points:
            return
        
        # Get frame dimensions
        if not self.cap:
            return
        
        frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        
        # Set pen style based on selection
        pen = QPen(color)
        if shape_name == self.selected_shape:
            pen.setWidth(4)
            pen.setStyle(Qt.PenStyle.DashLine)
        else:
            pen.setWidth(2)
            pen.setStyle(Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        
        # Set fill brush
        fill_color = QColor(color)
        fill_color.setAlpha(50 if shape_name != self.selected_shape else 80)
        painter.setBrush(fill_color)
        
        # Convert normalized coordinates to pixel coordinates
        pixel_points = []
        for x, y in points:
            pixel_x = int(x * frame_width)
            pixel_y = int(y * frame_height)
            pixel_points.append(QPoint(pixel_x, pixel_y))
        
        # Draw polygon
        if len(pixel_points) >= 2:
            polygon = QPolygon(pixel_points)
            painter.drawPolygon(polygon)
            
            # Draw vertices
            for point in pixel_points:
                painter.drawEllipse(point, 4, 4)
        
        # Draw label
        if shape_name:
            self.draw_polygon_label(painter, pixel_points, shape_name, polygon_data)
    
    def draw_polygon_label(self, painter: QPainter, pixel_points: List[QPoint], 
                          shape_name: str, polygon_data: Dict):
        """Draw polygon label with properties"""
        if not pixel_points:
            return
        
        # Position label above the polygon
        min_x = min(p.x() for p in pixel_points)
        min_y = min(p.y() for p in pixel_points)
        text_point = QPoint(min_x, max(min_y - 10, 15))
        
        # Format display text
        pod_code = polygon_data.get('ctnrCod', '')
        position_code = polygon_data.get('positionCode', '')
        
        display_text = shape_name
        if pod_code or position_code:
            display_text += f" (Pod:{pod_code}, Pos:{position_code})"
        
        # Draw text with background
        painter.setFont(QFont("Arial", 10))
        text_rect = painter.boundingRect(text_point.x(), text_point.y() - 15, 200, 20, 
                                       Qt.AlignmentFlag.AlignLeft, display_text)
        painter.fillRect(text_rect.adjusted(-2, -1, 2, 1), QColor(0, 0, 0, 128))
        painter.setPen(QPen(Qt.GlobalColor.white))
        painter.drawText(text_point, display_text)
    
    def get_polygon_points(self, polygon_data: Union[Dict, List]) -> List[Tuple[float, float]]:
        """Extract points from polygon data (handles both old and new formats)"""
        if isinstance(polygon_data, list):
            return polygon_data
        elif isinstance(polygon_data, dict):
            return polygon_data.get('points', [])
        return []
    
    def start_drawing(self, rectangle_mode: bool = False):
        """Start drawing mode"""
        self.drawing_mode = True
        self.draw_rectangle_mode = rectangle_mode
        self.points.clear()
        self.start_point = None
        
        # Update UI
        self.video_label.setCursor(Qt.CursorShape.CrossCursor)
        mode_text = "Rectangle" if rectangle_mode else "Polygon"
        instruction = "Click and drag to draw rectangle" if rectangle_mode else "Click to add points, right-click to complete"
        self.update_status(f"{mode_text} mode: {instruction}")
        logger.info(f"Started drawing mode: {mode_text}")
    
    def cancel_drawing(self):
        """Cancel drawing mode"""
        self.drawing_mode = False
        self.draw_rectangle_mode = False
        self.points.clear()
        self.start_point = None
        
        # Reset UI
        self.video_label.setCursor(Qt.CursorShape.ArrowCursor)
        self.update_status("Drawing cancelled")
        logger.info("Drawing mode cancelled")
    
    def delete_selected_shape(self):
        """Delete the currently selected shape"""
        if self.selected_shape:
            self.delete_shape(self.selected_shape)
    
    def delete_shape(self, shape_name: str):
        """Delete a specific shape"""
        if not self.current_url or self.current_url not in self.polygons:
            return
        
        if shape_name in self.polygons[self.current_url]:
            del self.polygons[self.current_url][shape_name]
            
            # Clean up empty URL entry
            if not self.polygons[self.current_url]:
                del self.polygons[self.current_url]
            
            # Clear selection if deleted shape was selected
            if self.selected_shape == shape_name:
                self.selected_shape = None
            
            self.save_polygons()
            self.shape_deleted.emit(shape_name)
            self.update_status(f"Deleted shape: {shape_name}")
            logger.info(f"Shape deleted: {shape_name}")
    
    def find_clicked_polygon(self, click_pos: QPoint) -> Optional[str]:
        """Find which polygon was clicked at the given position"""
        if not self.current_url or self.current_url not in self.polygons:
            return None
        
        video_coords = self.convert_to_video_coordinates(click_pos)
        if not video_coords:
            return None
        
        for shape_name, polygon_data in self.polygons[self.current_url].items():
            points = self.get_polygon_points(polygon_data)
            if self.point_in_polygon(video_coords, np.array(points)):
                return shape_name
        
        return None
    
    def point_in_polygon(self, point: Tuple[float, float], polygon: np.ndarray) -> bool:
        """Check if a point is inside a polygon using ray casting algorithm"""
        if len(polygon) < 3:
            return False
        
        x, y = point
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard events"""
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if not self.drawing_mode and self.selected_shape:
                self.delete_selected_shape()
        elif event.key() == Qt.Key.Key_Escape:
            if self.drawing_mode:
                self.cancel_drawing()
            else:
                self.selected_shape = None
                self.update_status("Selection cleared")
        else:
            super().keyPressEvent(event)
    
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
            QMessageBox.critical(self, "Error", f"Failed to save polygons: {str(e)}")
    
    def load_polygons(self):
        """Load polygons from JSON file"""
        try:
            if os.path.exists(resource_path('camera_polygons.json')):
                path=ensure_user_file('camera_polygons.json')
                with path.open('r',encoding="utf-8") as f:
                    self.polygons = json.load(f)
                # with open(resource_path('camera_polygons.json'), 'r') as f:
                #     self.polygons = json.load(f)
                logger.info("Polygons loaded successfully")
            else:
                logger.info(resource_path('camera_polygons.json'))
                self.polygons = {}
                logger.info("No saved polygons found")
        except Exception as e:
            logger.exception(f"Error loading polygons: {e}")
            self.polygons = {}
            QMessageBox.warning(self, "Warning", f"Failed to load saved polygons: {str(e)}")
    
    def update_status(self, message: str):
        """Update status bar message"""
        if hasattr(self, 'status_label'):
            self.status_label.setText(message)
    
    def get_shape_names(self) -> List[str]:
        """Get list of shape names for current URL"""
        if self.current_url and self.current_url in self.polygons:
            return list(self.polygons[self.current_url].keys())
        return []
    
    def get_shape_data(self, shape_name: str) -> Optional[Dict]:
        """Get data for a specific shape"""
        if self.current_url and self.current_url in self.polygons:
            return self.polygons[self.current_url].get(shape_name)
        return None
    
    def closeEvent(self, event):
        """Handle widget close event"""
        self.cleanup_capture()
        self.cleanup_thread()
        path=user_config_path('dev_mode.json')
        tmp=path.with_suffix(".json.tmp")
        with tmp.open('w',encoding="utf-8") as f:
            json.dump(self.dev_mode, f, ensure_ascii=False,indent=2)
        tmp.replace(path)
        logger.info("VideoDisplay widget closed")
        super().closeEvent(event)
    
    def update_nav_buttons(self):
        """Update navigation button states"""
        if not hasattr(self, 'prev_button') or not hasattr(self, 'next_button'):
            return
            
        self.prev_button.setEnabled(self.camera_manager.current_camera_index > 0)
        self.next_button.setEnabled(self.camera_manager.current_camera_index < len(self.camera_manager.cameras) - 1)
        logger.info(f"Nav buttons updated: prev={self.prev_button.isEnabled()}, next={self.next_button.isEnabled()}")

    def update_camera_info(self):
        """Update camera info label"""
        if not hasattr(self, 'camera_info_label'):
            return
            
        if self.camera_manager.cameras:
            current_index = self.camera_manager.current_camera_index + 1
            total_cameras = len(self.camera_manager.cameras)
            current_camera = self.camera_manager.get_current_camera()
            # Truncate long URLs for display
            display_url = current_camera[:50] + "..." if len(current_camera) > 50 else current_camera
            self.camera_info_label.setText(f"Camera {current_index}/{total_cameras}: {display_url}")
        else:
            self.camera_info_label.setText("No cameras available")

    def prev_camera(self):
        """Switch to previous camera"""
        logger.info("Attempting to switch to previous camera")
        if self.camera_manager.prev_camera():
            logger.info(f"Switching to camera index {self.camera_manager.current_camera_index}")
            self.stop_video()
            self.start_video()
            self.update_nav_buttons()
            self.update_camera_info()
        else:
            logger.info("Cannot switch to previous camera")

    def next_camera(self):
        """Switch to next camera"""
        logger.info("Attempting to switch to next camera")
        if self.camera_manager.next_camera():
            logger.info(f"Switching to camera index {self.camera_manager.current_camera_index}")
            self.stop_video()
            self.start_video()
            self.update_nav_buttons()
            self.update_camera_info()
        else:
            logger.info("Cannot switch to next camera")

    def start_video(self):
        """Start video stream"""
        if self.camera_manager:
            current_camera = self.camera_manager.get_current_camera()
            if current_camera:
                logger.info(f"Starting video stream from: {current_camera}")
                self.set_source(current_camera)
                self.update_nav_buttons()
                self.update_camera_info()
            else:
                logger.info("No camera URL available")
    def stop_video(self):
        """Stop video stream"""
        logger.info("Stopping video stream")
        self.cleanup_capture()
        self.video_label.clear()
        self.video_label.setText("Video stopped")
        self.update_status("Video stopped")
        self.current_url = None
        self.update_nav_buttons()
    def set_developer_mode(self,enabled):
        self.developer_mode=enabled
        self.dev_mode["dev_mode"]=int(enabled)