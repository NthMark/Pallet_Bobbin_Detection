from socketio import Client
import logging

logging.basicConfig(level=logging.DEBUG)

sio = Client(logger=True)

@sio.event
def connect():
    print('Connected to server')

@sio.event
def connect_error(error):
    print('Connection failed:', error)

@sio.event
def disconnect():
    print('Disconnected from server')

@sio.on('detection_results')
def on_detection(data):
    print('Received detection results:', data)

try:
    sio.connect('http://localhost:4567')
    sio.wait()
except Exception as e:
    print('Error:', e)
