import random
import sys
import os
import shutil
from pathlib import Path
CONTAINER_CODE_OUTSIDE="99"
APP_NAME="RTC_Viewer"
def random_string(length=6):
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        return ''.join(random.choice(letters) for i in range(length))
# def resource_path(rel_path: str) -> str:
#     base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
#     return os.path.join(os.path.dirname(base), rel_path)
def resource_path(rel:str):
    if getattr(sys,'frozen',False):
         base=Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
         base=Path(sys.modules['__main__'].__name__).resolve().parent
    return str(base/rel)

def app_base_dir():
      if getattr(sys,'frozen',False):
            return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
      return Path(sys.modules['__main__'].__name__).resolve().parent
def packaged_path(rel:str):
      return app_base_dir()/rel
def user_config_dir():
     if os.name=="nt":
           base=Path(os.getenv("APPDATA",Path.home()/"AppData"/"Roaming"))
     else:
           base=Path(os.getenv("XDG_CONFIG_HOME",Path.home()/ ".config"))
     d=base/APP_NAME
     d.mkdir(parents=True,exist_ok=True)
     return d
def user_config_path(filename:str):
      return user_config_dir()/filename
def ensure_user_file(filename:str):
     u=user_config_path(filename)
     if not u.exists():
          p=packaged_path(filename)
          u.parent.mkdir(parents=True,exist_ok=True)
          if p.exists():
               shutil.copy2(p,u)
          else:
                u.write_text("{}",encoding="utf-8")
     return u