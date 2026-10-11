"""Configuration shared by the local application."""
import os
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((ROOT / "config.yaml").read_text())
OFFLINE_SECONDS = CONFIG["device_health"]["offline_after_seconds"]
API_KEY = os.environ.get("STOREWATCH_API_KEY", "")
