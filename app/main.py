import json
import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn

# Allow running from `app/` while package lives under `src/`
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from smart_house_agent.config import get_settings  # noqa: E402

logger = logging.getLogger(__name__)

settings = get_settings()
DB_FILE = str(settings.home_status_path.resolve())

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

app = FastAPI()


def load_db():
    """Reads the latest state from the JSON file."""
    if not os.path.exists(DB_FILE):
        return {
            "light": "off",
            "tv": "off",
            "curtain": "closed",
            "door_lock": "locked",
            "thermostat_mode": "off",
            "main_water_valve": "closed",
        }
    try:
        with open(DB_FILE, encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {}


def save_db_from_api(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class DeviceCommand(BaseModel):
    device_id: str = Field(..., description="The device to control")
    action: str = Field(..., description="The action to perform on the device")


@app.get("/status")
def get_status():
    current_db = load_db()
    return current_db


@app.post("/update_device")
def update_device(command: DeviceCommand):
    device_id = command.device_id.lower()
    action = command.action.lower()

    current_db = load_db()

    if device_id in current_db:
        current_db[device_id] = action
        save_db_from_api(current_db)
        logger.info("Updated %s -> %s", device_id, action)
        return {"status": "success", "device_id": device_id, "new_state": action}
    raise HTTPException(status_code=404, detail=f"Device {device_id} not found")


@app.get("/")
async def read_index():
    file_path = "static/index.html"
    if not os.path.exists(file_path):
        return {"error": f"File not found at: {os.getcwd()}\\{file_path}"}
    return FileResponse(file_path)

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=242)

# http://localhost:242/ please use this URL to acccess the dashboard after running the server.

#Terminal A: cd app → python main.py → dashboard  
#Terminal B (repo root): python -m smart_house_agent.main "your question" (after pip install -r requirements.txt, pip install -e ., and .env with GOOGLE_API_KEY)
