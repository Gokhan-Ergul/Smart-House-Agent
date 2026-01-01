from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse
import uvicorn
import os
import json

app = FastAPI()

# File path (Make sure this matches where your notebook saves it!)

# 1. Get the folder where 'main.py' lives (i.e., .../TEZ/app)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
DB_FILE = os.path.join(parent_dir, "home_status.json")

# --- HELPER: Load DB from file ---
def load_db():
    """Reads the latest state from the JSON file."""
    if not os.path.exists(DB_FILE):
        # Default state if file doesn't exist yet
        return {
            "light": "off", "tv": "off", "curtain": "closed",
            "door_lock": "locked", "thermostat_mode": "off",
            "main_water_valve": "closed"
        }
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {} # Handle empty/corrupt file errors

# --- HELPER: Save DB to file (if API also updates it) ---
def save_db_from_api(data):
    with open(DB_FILE, "w") as f:
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
    # ALWAYS load from file to get the Notebook's latest changes
    current_db = load_db()
    return current_db

@app.post("/update_device")
def update_device(command: DeviceCommand):
    device_id = command.device_id.lower()
    action = command.action.lower()
    
    # 1. Load current state
    current_db = load_db()
    
    if device_id in current_db:
        # 2. Update state
        current_db[device_id] = action
        
        # 3. Save back to file so Notebook sees it too
        save_db_from_api(current_db)
        
        print(f"Updated {device_id} -> {action}")
        return {'status': 'success', 'device_id': device_id, 'new_state': action}
    else:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

@app.get("/") 
async def read_index():
    file_path = "static/index.html"
    if not os.path.exists(file_path):
        return {"error": f"File not found at: {os.getcwd()}\\{file_path}"}
    return FileResponse(file_path)

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)