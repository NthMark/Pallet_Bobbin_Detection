# utils.py
import sys, os, json, shutil
from pathlib import Path

APP_NAME = "RTC_Viewer"   # đổi theo app của bạn

def app_base_dir() -> Path:
    if getattr(sys, 'frozen', False):
        # one-file: _MEIPASS, one-folder: dir chứa exe
        return Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
    # dev: thư mục chứa main.py
    return Path(sys.modules['__main__'].__file__).resolve().parent

def packaged_path(rel: str) -> Path:
    # đường dẫn tới bản đóng gói sẵn (read-only trong _MEIPASS)
    return app_base_dir() / rel

def user_config_dir() -> Path:
    # %APPDATA%\RTC_Viewer trên Windows, ~/.config/RTC_Viewer trên Linux
    if os.name == "nt":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
    d = base / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d

def user_config_path(filename: str) -> Path:
    return user_config_dir() / filename

def ensure_user_file(filename: str):
    """Nếu user chưa có file → copy từ packaged default."""
    u = user_config_path(filename)
    if not u.exists():
        p = packaged_path(filename)
        u.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            shutil.copy2(p, u)
        else:
            # nếu không có default, tạo rỗng
            u.write_text("{}", encoding="utf-8")
    return u
