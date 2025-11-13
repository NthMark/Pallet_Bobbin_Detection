from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QMenuBar, QMenu, QDialog, QPushButton, 
                             QInputDialog, QMessageBox, QListWidget, QFileDialog,
                             QProgressDialog, QTabWidget,QLineEdit)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap, QIcon
from pathlib import Path
import cv2
from video_display import VideoDisplay
from config_dialog import ConfigDialog

from image_display import ImageDisplay
import sys
import json
import os
import yaml
import argparse
from utils import resource_path, ensure_user_file,user_config_path
from logger_config import get_logger
logger = get_logger(__name__)
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"]=(
    "rtsp_transport;tcp|"
    "stimeout;7000000|"
    "max_delay;3000000|"
    "buffer_size;1048576"
)
def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--auto-multicam",action="store_true",default=None)
    p.add_argument("--auto-detect",action="store_true")
    return p.parse_args()
class ConfigLoader:
    @staticmethod
    def load_config(file_path="config.yaml"):
        with open(resource_path(file_path), 'r') as f:
            return yaml.safe_load(f)
class MultiCamWindow(QMainWindow):
    def closeEvent(self,e):
        cw=self.centralWidget()
        try:
            if cw and hasattr(cw,"dispose"):
                cw.dispose()
        finally:
            super().closeEvent(e)
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RTC CCTV & Image Viewer")
        self.setWindowIcon(QIcon(resource_path("rtc.png")))  # Set the window icon
        # Đặt cửa sổ ở chế độ toàn màn hình
        self.showMaximized()
        self.setWindowFlags(Qt.WindowType.WindowMaximizeButtonHint | Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowCloseButtonHint)
        config = ConfigLoader.load_config()
        logger.info(f"Loaded configuration: {config}")
        # Create central widget with tab widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create video display tab
        self.video_display = VideoDisplay()
        
        # Thêm layout chứa nút Previous/Next vào video_display
        video_tab_layout = QVBoxLayout(self.video_display)
        nav_layout = QHBoxLayout()
        self.prev_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.next_button)
        video_tab_layout.addStretch()
        video_tab_layout.addLayout(nav_layout)
        self.prev_button.clicked.connect(self.show_previous)
        self.next_button.clicked.connect(self.show_next)
        self.tab_widget.addTab(self.video_display, "Video Stream")
        
        # Create image display tab
        self.image_display = ImageDisplay()
        self.tab_widget.addTab(self.image_display, "Image Viewer")
        
        # Load initial URLs
        self.current_url_index = 0
        self.urls = []
        self.load_urls()
        
        #Debounce
        self._debouncing=False
        if self.urls:
            self.video_display.set_source(self.urls[0]["camera_url"])
        
        # Create menus
        self.dev_mode=None
        self.create_menus()
        if hasattr(self,"video_display") and hasattr(self.video_display,"set_developer_mode"):
            self.video_display.set_developer_mode(self.dev_mode)
    def create_menus(self):
        menubar = self.menuBar()
        path=ensure_user_file('dev_mode.json')
        print(path)
        with path.open('r',encoding="utf-8") as f:
            self.dev_mode = bool(int(json.load(f)["dev_mode"]))
        print(f"Dev mode: {self.dev_mode}")
        # File menu
        file_menu = menubar.addMenu('&File')
        file_menu.setDisabled(not self.dev_mode)
        # Add 'Open Images' action to File menu
        open_images_action = file_menu.addAction('Open Images Folder')
        open_images_action.triggered.connect(self.open_images_folder)
        
        # Settings menu
        config_menu = menubar.addMenu('&Settings')
        config_action = config_menu.addAction('&Configure RTSP')
        config_action.triggered.connect(self.show_config_dialog)
        config_menu.setDisabled(not self.dev_mode)
        # MultiCamera Display menu
        multicam_menu = menubar.addMenu('&MultiCamDisplay')
        show_multicam_action = multicam_menu.addAction('Show All Cameras')
        show_multicam_action.triggered.connect(self.on_open_multicam_clicked)
        
        # BoundingBox menu
        bbox_menu = menubar.addMenu('&BoundingBox')
        
        # Draw polygon submenu
        draw_menu = QMenu('Draw', self)
        bbox_menu.addMenu(draw_menu)
        
        # Add polygon and rectangle actions
        draw_polygon_action = draw_menu.addAction('Free Polygon')
        draw_polygon_action.triggered.connect(lambda: self.start_drawing_shape(False))
        
        draw_rectangle_action = draw_menu.addAction('Rectangle')
        draw_rectangle_action.triggered.connect(lambda: self.start_drawing_shape(True))
        
        # Edit polygons submenu
        self.edit_menu = QMenu('Edit', self)
        bbox_menu.addMenu(self.edit_menu)
        self.edit_menu.setDisabled(not self.dev_mode)
        # Add edit actions
        edit_action = self.edit_menu.addAction('Edit Shape')
        edit_action.triggered.connect(self.edit_shape)
        
        delete_action = self.edit_menu.addAction('Delete Shape')
        delete_action.triggered.connect(self.delete_shape)
        
        # Cancel drawing action
        cancel_action = bbox_menu.addAction('&Cancel Drawing')
        cancel_action.triggered.connect(self.cancel_drawing_shape)

        dev_menu=menubar.addMenu('&Developer')
        self.toggle_dev_action=dev_menu.addAction('Toggle Developer Mode')
        self.toggle_dev_action.setChecked(self.dev_mode)
        self.toggle_dev_action.setCheckable(True)
        self.toggle_dev_action.triggered.connect(self.toggle_developer_mode)
    def on_open_multicam_clicked(self):
        if self._debouncing:
            return
        self._debouncing=True
        QTimer.singleShot(800,lambda: setattr(self,"_debouncing",False))
        self.show_multicam_display()
    def show_multicam_display(self):
        try:
            from multi_camera_display import MultiCameraDisplay
            # Load camera configurations
            path=ensure_user_file('camera_configs.json')
            with path.open('r',encoding="utf-8") as f:
                camera_configs = json.load(f)
            # with open(resource_path('camera_configs.json'), 'r') as f:
            #     camera_configs = json.load(f)
            
            # Create new window for multi-camera display
            self.multicam_window = MultiCamWindow(self)
            self.multicam_window.setWindowTitle("Multi-Camera Display")
            self.multicam_window.resize(1200, 800)
            self.multicam_window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose,True)
            # Create multi-camera display widget
            multicam_display = MultiCameraDisplay(camera_configs)
            multicam_display.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose,True)
            multicam_display.destroyed.connect(multicam_display.dispose)
            self.multicam_window.setCentralWidget(multicam_display)
            self.multicam_window.destroyed.connect(lambda:setattr(self,"multicam_window",None))
            # Show the window
            self.multicam_window.show()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load camera configurations: {str(e)}")
    def _on_connecting(self,url:str):
        self.prev_button.setEnabled(False)
        self.next_button.setEnabled(False)
        self.statusBar().showMessage(f"Connecting to {url}...")
    def _on_connection_result(self,url:str,success:bool,error:str):
        self.update_nav_buttons()
        if success:
            self.statusBar().showMessage(f"Connected to {url}...")
        else:
            self.statusBar().showMessage(f"Connection failed: {error}")
    def load_urls(self):
        # Load camera URLs from a configuration file
        try:
            path=ensure_user_file('camera_configs.json')
            with path.open('r',encoding="utf-8") as f:
                camera_configs = json.load(f)
                self.urls = [{"camera_url": config["camera_url"]} for config in camera_configs]
            # with open(resource_path('camera_configs.json'), 'r') as f:
            #     camera_configs = json.load(f)
            #     self.urls = [{"camera_url": config["camera_url"]} for config in camera_configs]
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load camera configurations: {str(e)}")
            self.urls = []

    def show_previous(self):
        # Show the previous camera stream
        if self.urls:
            self.current_url_index = (self.current_url_index - 1) % len(self.urls)
            self.video_display.set_source(self.urls[self.current_url_index]["camera_url"])
            self.update_nav_buttons()

    def show_next(self):
        # Show the next camera stream
        if self.urls:
            self.current_url_index = (self.current_url_index + 1) % len(self.urls)
            self.video_display.set_source(self.urls[self.current_url_index]["camera_url"])
            self.update_nav_buttons()

    def update_nav_buttons(self):
        if not self.urls or len(self.urls)==1:
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
            return
        self.prev_button.setEnabled(self.current_url_index>0)
        self.next_button.setEnabled(self.current_url_index<len(self.urls)-1)

    def show_config_dialog(self):
        dialog = ConfigDialog(self)
        if dialog.exec():
            self.camera_config=dialog.camera_configs
            logger.info(self.camera_config)
            try:
                path=user_config_path('camera_configs.json')
                tmp=path.with_suffix(".json.tmp")
                with tmp.open('w',encoding="utf-8") as f:
                    json.dump(self.camera_config, f, ensure_ascii=False,indent=2)
                tmp.replace(path)
                # with open(resource_path('camera_configs.json'), 'w') as f:
                #     json.dump(self.camera_config, f, indent=2)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save camera configs: {str(e)}")
            # Reload the application with new configuration
            # QApplication.quit()
            # status = QApplication.exec()
            # sys.exit(status)

    def start_drawing_shape(self, rectangle_mode=False):
        """Start drawing a shape (rectangle or polygon)"""
        if self.video_display.current_url:
            self.video_display.start_drawing(rectangle_mode)
        else:
            QMessageBox.warning(self, "Warning", "Please connect to a camera first!")

    def cancel_drawing_shape(self):
        """Cancel the current drawing operation"""
        self.video_display.cancel_drawing()

    def edit_shape(self):
        """Edit an existing shape"""
        if not self.video_display.current_url:
            QMessageBox.warning(self, "Warning", "Please connect to a camera first!")
            return

        shape_names = self.video_display.get_shape_names()
        if not shape_names:
            QMessageBox.warning(self, "Warning", "No shapes to edit!")
            return

        shape_name, ok = QInputDialog.getItem(
            self, "Select Shape", "Choose a shape to edit:", shape_names, 0, False
        )
        if ok and shape_name:
            self.video_display.edit_shape_properties(shape_name)

    def delete_shape(self):
        """Delete an existing shape"""
        if not self.video_display.current_url:
            QMessageBox.warning(self, "Warning", "Please connect to a camera first!")
            return

        shape_names = self.video_display.get_shape_names()
        if not shape_names:
            QMessageBox.warning(self, "Warning", "No shapes to delete!")
            return

        shape_name, ok = QInputDialog.getItem(
            self, "Select Shape", "Choose a shape to delete:", shape_names, 0, False
        )
        if ok and shape_name:
            self.video_display.delete_shape(shape_name)

    def open_images_folder(self):
        """Open a folder of images in the image display tab"""
        folder = QFileDialog.getExistingDirectory(self, "Select Images Folder")
        if folder:
            self.image_display.load_folder(folder)
            self.tab_widget.setCurrentWidget(self.image_display)  # Switch to image viewer tab
    def toggle_developer_mode(self,checked):
        if checked:
            password,ok=QInputDialog.getText(
                self,
                "Developer Mode",
                "Password to turn on Dev Mode:",
                QLineEdit.EchoMode.Password,
            )
            if not ok or password!="rtc@admin":
                QMessageBox.warning(self,"Wrong Password","Password not incorrect!")
                self.toggle_dev_action.setChecked(False)
                return
        self.dev_mode=checked
        state="ENABLED" if checked else "DISABLED"
        QMessageBox.information(self,"Developer Mode",f"Developer mode {state}")

        if hasattr(self,"video_display") and hasattr(self.video_display,"set_developer_mode"):
            self.video_display.set_developer_mode( checked)
        menubar=self.menuBar()
        for name in ["&File","&Settings"]:
            for menu in menubar.findChildren(QMenu):
                if menu.title()==name:
                    menu.setDisabled( not checked)
        for menu in menubar.findChildren(QMenu):
                if menu.title()=="&BoundingBox":
                    for action in menu.actions():
                        sub=action.menu()
                        if sub and sub.title().replace("&","")=="Edit":
                            sub.setDisabled(not checked)
                            break
    def closeEvent(self, event):
        try:
            if hasattr(self,"video_display") and self.video_display is not None:
                try:
                    self.video_display.close()
                except Exception as e:
                    logger.exception(f"Error closing video_display: {e}")
            if getattr(self,"multicam_window",None):
                try:
                    self.multicam_window.close()
                except Exception as e:
                    logger.exception(f"Error closing multicam_window: {e}")
        finally:
            return super().closeEvent(event)
def main():
    args=parse_args()
    if args.auto_multicam is None:
        args.auto_multicam=True
    if not args.auto_detect:
        args.auto_detect=True
    app = QApplication(sys.argv)
    window = MainWindow()
    if not window.video_display.connect:
        sys.exit(app.exec())
    window.show()
    if args.auto_multicam:
        window.show_multicam_display()
        def enable_detect_later():
            try:
                if args.auto_detect and hasattr(window,"multicam_window"):
                    multicam=window.multicam_window.centralWidget()
                    for w in multicam.camera_widgets:
                        if hasattr(w,"yolo_checkbox") and w.yolo_checkbox.isEnabled():
                            w.yolo_checkbox.setChecked(True)
            except Exception as e:
                print("error")
        QTimer.singleShot(2000,enable_detect_later)
    sys.exit(app.exec())

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()
    main()
