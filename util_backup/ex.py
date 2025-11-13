# video_display.py (hoặc nơi bạn load/save polygons)
import json, logging
from utils import ensure_user_file, user_config_path

logger = logging.getLogger(__name__)

_POLYGONS_FILE = "camera_polygons.json"

def load_polygons(self):
    try:
        path = ensure_user_file(_POLYGONS_FILE)   # đảm bảo tồn tại ở thư mục user
        with path.open("r", encoding="utf-8") as f:
            self.polygons = json.load(f)
        logger.info("Loaded polygons from %s", path)
    except Exception as e:
        self.polygons = {}
        logger.exception("Failed to load polygons: %s", e)

def save_polygons(self):
    try:
        path = user_config_path(_POLYGONS_FILE)   # LUÔN ghi vào thư mục user
        tmp = path.with_suffix(".json.tmp")
        # ghi an toàn (atomic-ish)
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(self.polygons, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
        logger.info("Saved polygons to %s", path)
    except Exception as e:
        logger.exception("Failed to save polygons: %s", e)
