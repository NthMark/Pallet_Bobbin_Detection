import random
import sys
import os
from pathlib import Path
def random_string(length=6):
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        return ''.join(random.choice(letters) for i in range(length))
def resource_path(rel_path: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
    return os.path.join(base, rel_path)
def user_data_path(filename: str) -> str:
    from pathlib import Path
    base = Path.home() / ".rtc_viewer"
    base.mkdir(parents=True, exist_ok=True)
    return str(base / filename)
def _camera_configs_path_for_read() -> str:
    user = user_data_path("camera_configs.json")
    if os.path.exists(user):
        return user
    return resource_path("camera_configs.json")  # packaged default

def _camera_configs_path_for_write() -> str:
    return user_data_path("camera_configs.json")
if __name__ == "__main__":
        print(random_string(10))
        print(resource_path("camera_configs.json"))
        print(user_data_path("camera_configs.json"))
        print(_camera_configs_path_for_read())
        print(_camera_configs_path_for_write())