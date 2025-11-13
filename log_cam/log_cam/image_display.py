from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton,
                         QFileDialog, QComboBox, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap
import cv2
from pathlib import Path
from ultralytics import YOLO
import os

class ImageDisplay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_files = []  # Đảm bảo luôn khởi tạo trước
        self.current_index = 0
        self.current_folder = None
        self.model = None
        self.detection_timer = QTimer()
        self.detection_timer.timeout.connect(self.run_detection)
        self.detection_timer.setInterval(100)  # Run detection every 100ms
        self.init_ui()

    def init_ui(self):
        # Main layout
        layout = QVBoxLayout(self)
        
        # Controls layout
        controls_layout = QHBoxLayout()
        
        # Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model File:"))
        
        # Model path input and browse button
        self.model_path = QLabel("No model selected")
        model_layout.addWidget(self.model_path)
        
        self.browse_model_button = QPushButton("Browse Model")
        self.browse_model_button.clicked.connect(self.browse_model)
        model_layout.addWidget(self.browse_model_button)
        
        controls_layout.addLayout(model_layout)
        layout.addLayout(controls_layout)
        
        # Image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label)
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("Previous")
        self.prev_button.clicked.connect(self.show_previous)
        nav_layout.addWidget(self.prev_button)
        
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.show_next)
        nav_layout.addWidget(self.next_button)
        
        layout.addLayout(nav_layout)
        
        # Status label
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.update_nav_buttons()

    def browse_model(self):
        """Open file dialog to select YOLO model file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select YOLO Model",
            "",
            "YOLO Models (*.pt);;All Files (*.*)"
        )
        
        if file_path:
            self.model_path.setText(file_path)
            self.model = None  # Reset model so it will be reloaded with new weights
            if self.image_files:  # Start detection if we have images
                self.detection_timer.start()
            
    def run_detection(self):
        """Run object detection on current image"""
        if not self.image_files or self.current_index >= len(self.image_files):
            self.detection_timer.stop()
            return

        try:
            # Get model path from label
            model_path = self.model_path.text()
            if model_path == "No model selected" or not os.path.exists(model_path):
                self.detection_timer.stop()
                return

            # Load model if not loaded or model path changed
            if self.model is None or getattr(self.model, 'model_path', None) != model_path:
                self.model = YOLO(model_path)
                self.model.model_path = model_path  # Save path for future checks

            # Load and process image
            img_path = str(self.image_files[self.current_index])
            
            # Run detection without saving
            results = self.model.predict(img_path)
            
            # Get the plotted image directly from results
            if len(results) > 0:
                # Plot results on image
                plotted_img = results[0].plot()  # Returns numpy array in BGR format
                
                # Convert BGR to RGB
                rgb_img = cv2.cvtColor(plotted_img, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_img.shape
                
                # Convert to QImage and display
                bytes_per_line = ch * w
                qt_image = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image)
                
                # Scale pixmap to fit label
                scaled_pixmap = pixmap.scaled(
                    self.image_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation
                )
                
                self.image_label.setPixmap(scaled_pixmap)
                self.status_label.setText(f"Detection running on: {Path(img_path).name}")

        except Exception as e:
            self.status_label.setText(f"Detection error: {str(e)}")
            self.detection_timer.stop()

    def display_image(self, image_path):
        """Display image from path"""
        try:
            # Read and convert image
            image = cv2.imread(str(image_path))
            if image is None:
                raise ValueError("Failed to load image")
                
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            h, w, ch = image.shape
            
            # Convert to QImage and display
            bytes_per_line = ch * w
            qt_image = QImage(image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            
            # Scale pixmap to fit label while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.image_label.setPixmap(scaled_pixmap)
            self.detect_button.setEnabled(True)
            
        except Exception as e:
            self.status_label.setText(f"Error loading image: {str(e)}")
            self.detect_button.setEnabled(False)

    def load_folder(self, folder_path):
        """Load all images from a folder"""
        self.current_folder = Path(folder_path)
        self.image_files = []
        
        # Get all image files
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp']:
            self.image_files.extend(list(self.current_folder.glob(ext)))
        
        self.image_files.sort()
        self.current_index = 0
        
        if self.image_files:
            if self.model is not None:
                self.detection_timer.start()
                self.run_detection()
            else:
                self.show_current_image()
            self.update_nav_buttons()
            self.status_label.setText(f"Image 1 of {len(self.image_files)}")
        else:
            self.status_label.setText("No images found in folder")
            self.detection_timer.stop()

    def show_current_image(self):
        """Display the current image"""
        if not self.image_files:
            self.image_label.clear()
            self.status_label.clear()
            return
            
        try:
            # Read image
            img_path = str(self.image_files[self.current_index])
            img = cv2.imread(img_path)
            if img is None:
                self.image_label.setText(f"Failed to load image: {img_path}")
                return
            
            # Convert to RGB for display
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_img.shape
            
            # Convert to QImage
            qt_img = QImage(rgb_img.data, w, h, ch * w, QImage.Format.Format_RGB888)
            
            # Scale to fit label while maintaining aspect ratio
            pixmap = QPixmap.fromImage(qt_img)
            # Nếu label chưa có kích thước, dùng kích thước ảnh
            label_size = self.image_label.size()
            if label_size.width() < 10 or label_size.height() < 10:
                self.image_label.resize(w, h)
                label_size = self.image_label.size()
            scaled_pixmap = pixmap.scaled(
                label_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Show image
            self.image_label.setPixmap(scaled_pixmap)
            
            # Update status
            self.status_label.setText(
                f"Image {self.current_index + 1} of {len(self.image_files)}: "
                f"{self.image_files[self.current_index].name}"
            )
            
        except Exception as e:
            self.image_label.setText(f"Error displaying image: {str(e)}")

    def show_previous(self):
        """Show previous image"""
        if self.image_files:
            self.current_index = (self.current_index - 1) % len(self.image_files)
            if self.model is not None:  # If we have a model, detection will update the display
                self.run_detection()
            else:
                self.show_current_image()
            self.update_nav_buttons()

    def show_next(self):
        """Show next image"""
        if self.image_files:
            self.current_index = (self.current_index + 1) % len(self.image_files)
            if self.model is not None:  # If we have a model, detection will update the display
                self.run_detection()
            else:
                self.show_current_image()
            self.update_nav_buttons()

    def update_nav_buttons(self):
        """Enable/disable navigation buttons"""
        has_images = len(self.image_files) > 0
        self.prev_button.setEnabled(has_images and len(self.image_files) > 1)
        self.next_button.setEnabled(has_images and len(self.image_files) > 1)

    def resizeEvent(self, event):
        """Handle resize events to scale image"""
        super().resizeEvent(event)
        if self.image_files:
            self.show_current_image()
