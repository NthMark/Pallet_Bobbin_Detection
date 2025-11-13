from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QLabel, QListWidget, QMessageBox,
                             QFileDialog, QGridLayout, QGroupBox)
from PyQt6.QtCore import Qt
import json
import os
from logger_config import get_logger
from utils import resource_path,ensure_user_file,user_config_path
logger = get_logger(__name__)
class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.camera_configs = {}  # Dict to store {url: model_path}
        self.load_configs()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('Camera Configuration')
        self.setMinimumWidth(700)
        layout = QVBoxLayout(self)
        
        # Camera list
        list_group = QGroupBox("Cameras")
        list_layout = QVBoxLayout()
        self.url_list = QListWidget()
        self.url_list.addItems([cfg["camera_url"] for cfg in self.camera_configs])        
        list_layout.addWidget(self.url_list)
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        # Input fields group
        input_group = QGroupBox("Camera Settings")
        grid_layout = QGridLayout()
        
        # URL input
        url_label = QLabel('RTSP URL:')
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText('rtsp://username:password@ip:port/path')
        grid_layout.addWidget(url_label, 0, 0)
        grid_layout.addWidget(self.url_edit, 0, 1, 1, 2)
        
        # Model path input
        model_label = QLabel('YOLO Model:')
        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText('Path to YOLO model file')
        browse_button = QPushButton('Browse')
        grid_layout.addWidget(model_label, 1, 0)
        grid_layout.addWidget(self.model_edit, 1, 1)
        grid_layout.addWidget(browse_button, 1, 2)
        
        input_group.setLayout(grid_layout)
        layout.addWidget(input_group)

        # Class input
        class_label = QLabel('YOLO class:')
        self.class_edit = QLineEdit()
        self.class_edit.setPlaceholderText('Input id class name of model')
        grid_layout.addWidget(class_label, 2, 0)
        grid_layout.addWidget(self.class_edit, 2, 1)
        
        input_group.setLayout(grid_layout)
        layout.addWidget(input_group)
        
        # Action buttons
        action_layout = QHBoxLayout()
        add_button = QPushButton('Add')
        edit_button = QPushButton('Edit')
        delete_button = QPushButton('Delete')
        action_layout.addWidget(add_button)
        action_layout.addWidget(edit_button)
        action_layout.addWidget(delete_button)
        layout.addLayout(action_layout)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton('OK')
        cancel_button = QPushButton('Cancel')
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # Connect buttons
        add_button.clicked.connect(self.add_camera)
        edit_button.clicked.connect(self.edit_camera)
        delete_button.clicked.connect(self.delete_camera)
        browse_button.clicked.connect(self.browse_model)
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        self.url_list.itemClicked.connect(self.on_item_selected)
        
    def browse_model(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select YOLO Model",
            "",
            "Model Files (*.pt *.pth *.weights);;All Files (*.*)"
        )
        if file_path:
            self.model_edit.setText(file_path)
            
    def add_camera(self):
        url = self.url_edit.text().strip()
        model_path = self.model_edit.text().strip()
        id_cls = self.class_edit.text().strip()
        
        if url:
            if not any(cam['camera_url'] == url for cam in self.camera_configs):
                camera = {
                    "camera_url": url,
                    "model_path": model_path,
                    "id_class": id_cls
                }
                self.camera_configs.append(camera)
                
                self.url_list.addItem(camera["camera_url"])
                self.url_edit.clear()
                self.model_edit.clear()
                self.class_edit.clear()
                self.save_configs()
            else:
                QMessageBox.warning(self, "Warning", "This URL already exists!")
        else:
            QMessageBox.warning(self, "Warning", "RTSP URL cannot be empty!")
            self.url_edit.clear()
            self.model_edit.clear()
            self.class_edit.clear()
            self.save_configs()
    def edit_camera(self):
        current_row = self.url_list.currentRow()
        if current_row >= 0:
            old_url = self.url_list.item(current_row).text()
            new_url = self.url_edit.text().strip()
            new_model = self.model_edit.text().strip()
            new_id = self.class_edit.text().strip()

            if not new_url:
                return  # không làm gì nếu URL mới trống

            # Tìm đúng config cần sửa
            for cfg in self.camera_configs:
                if cfg["camera_url"] == old_url:
                    # Cập nhật nếu URL hoặc model_path có thay đổi
                    if new_url != old_url:
                        cfg["camera_url"] = new_url
                        self.url_list.item(current_row).setText(new_url)
                    if new_model != cfg["model_path"]:
                        cfg["model_path"] = new_model
                    if new_id != cfg["id_class"]:
                        cfg["id_class"] = new_id
                    break

            self.save_configs()

                
    def delete_camera(self):
        current_row = self.url_list.currentRow()
        if current_row >= 0:
            url = self.url_list.item(current_row).text()
            
            # Find and remove the matching dict by camera_url
            self.camera_configs = [
                config for config in self.camera_configs
                if config.get("camera_url") != url
            ]
            
            self.url_list.takeItem(current_row)
            self.save_configs()

            
    def on_item_selected(self, item):
        url = item.text()
        self.url_edit.setText(url)

        # Tìm model_path tương ứng với camera_url
        model_path = ""
        id_class = ""
        for cfg in self.camera_configs:
            if cfg["camera_url"] == url:
                model_path = cfg["model_path"]
                id_class = cfg["id_class"]
                break

        self.model_edit.setText(model_path)
        self.class_edit.setText(id_class)

        
    def get_configs(self):
        return self.camera_configs
        
    def save_configs(self):
        path=user_config_path('camera_configs.json')
        tmp=path.with_suffix(".json.tmp")
        with tmp.open('w',encoding="utf-8") as f:
            json.dump(self.camera_configs, f, ensure_ascii=False,indent=2)
        tmp.replace(path)
        # with open(resource_path('camera_configs.json'), 'w') as f:
        #     json.dump(self.camera_configs, f, indent=4)
            
    def load_configs(self):
        try:
            if os.path.exists(resource_path('camera_configs.json')):
                path=ensure_user_file('camera_configs.json')
                with path.open('r',encoding="utf-8") as f:
                    self.camera_configs = json.load(f)
                # with open(resource_path('camera_configs.json'), 'r') as f:
                #     self.camera_configs = json.load(f)
        except Exception as e:
            logger.error(f"Error loading configs: {e}")
            self.camera_configs = {}
