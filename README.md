# Pallet & Bobbin Detection System

## Overview
This project provides an automated system for detecting pallets and bobbins in a warehouse using AI models and camera streams. The system informs a server about the availability of pallets and bobbins, enabling automated warehouse management without human intervention.

## Key Features
- **Automated Detection:** Uses AI (YOLO) models to detect pallets and bobbins from camera streams and images.
- **Multi-Camera Support:** View and manage multiple camera streams simultaneously.
- **Interactive GUI:** Built with PyQt6 for easy configuration, visualization, and management.
- **Server Communication:** Automatically sends detection results to a server for further processing.
- **Configurable:** Easily update camera and model configurations via GUI dialogs and config files.

## Technologies Used
- Python 3 (recommended: use Conda environment)
- PyQt6
- OpenCV
- Ultralytics YOLO
- NumPy
- PyYAML

## Installation
1. **Clone the repository:**
	```
	git clone <your-repo-url>
	cd Pallet_Bobbin_Detection
	```
2. **Create and activate a Conda environment (recommended):**
	```
	conda create -n pallet_bobbin python=3.10
	conda activate pallet_bobbin
	```
3. **Install dependencies:**
	```
	pip install -r requirements.txt
	```

## Usage
1. **Configure cameras and models:**
	- Edit `camera_configs.json` and `config.yaml` as needed.
	- Place your YOLO model weights (e.g., `best.pt`) in the `model/` directory.
2. **Run the application:**
	```
	python main.py
	```
3. **Interact with the GUI:**
	- View live camera streams, run detection, and manage settings.
	- Use the menu to configure RTSP streams, draw/edit detection zones, and view multi-camera displays.

## Example Configuration

## Configuration Guide

## Server Request Status & Response Messages
When editing a shape (polygon) in the app, a request is sent to the server to bind or unbind a pod and berth. The server responds with a message indicating the result. These messages are shown in the app to inform the user of the operation status.

**Possible Response Messages:**

```
'message': 'successful'
'message': 'Fail to bind or unbind:  Berth does not exist:LH5' -> Wrong positionCode
'message': 'Fail to bind or unbind: Storage rack does not exist asdf' -> Wrong podCode
'message': 'Fail to bind or unbind: Rack serial number may not be empty'
'message': 'Fail to bind or unbind: Berth name cannot be blank'
'message': 'Fail to bind or unbind: Berth already linked to rack, cannot link, berth:LH4' -> set bind=1 when there is a bind
'message': 'Fail to bind or unbind: Berth linked to selected rack not found, rack100267' -> set bind=0 when there is no bind
```

**Role in the App:**
- These messages are displayed in the status bar or as popups when you edit a shape in the video display.
- They help you quickly identify issues with your configuration or server data (e.g., wrong codes, missing fields, or already linked items).
- The app uses these responses to update the UI and guide the user to correct any problems.

### 1. `config.yaml`
This file contains the server connection settings:
```yaml
rtc:
	ip_address: "172.24.24.201"  # Server IP address
	port: "8182"                 # Server port
```

### 2. `camera_configs.json`
Defines the list of cameras and their associated detection models. Each entry should have:
- `camera_url`: RTSP stream URL of the camera
- `model_path`: Path to the YOLO model weights (e.g., `./model/best.pt`)
- `id_class`: Class ID for detection (as string)

Example:
```json
[
	{
		"camera_url": "rtsp://admin:hao14072003@192.168.1.64:554/Streaming/Channels/101",
		"model_path": "./model/best.pt",
		"id_class": "1"
	}
]
```

You can add, edit, or remove cameras using the application's configuration dialog or by editing this file directly.

### 3. `camera_polygons.json`
Stores the detection zones (polygons) for each camera. Each camera URL maps to one or more shapes, each with:
- `points`: List of normalized (x, y) coordinates for the polygon
- `podCode`: Identifier for the detected pod
- `positionCode`: Location code in the warehouse
- `status`: Detection status

Example:
```json
{
	"rtsp://admin:rtc@1234@192.168.5.240:554/Streaming/Channels/101": {
		"shape_0": {
			"points": [[0.85, 0.16], [0.97, 0.16], [0.97, 0.40], [0.85, 0.40]],
			"podCode": "100267",
			"positionCode": "LH4",
			"status": "SUCCESSFUL"
		}
	}
}
```
You can draw and edit these polygons in the application's GUI.

## Authors
- Nguyen Thien Hao, Robotics R&D Engineer, RTC Technology
- Nguyen Quang Phuc, Robotics R&D Engineer, RTC Technology

## License
See [LICENSE](LICENSE) for details.