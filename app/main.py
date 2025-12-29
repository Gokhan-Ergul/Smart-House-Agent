from fastapi import FastAPI, Body,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn
from pydantic import BaseModel
from fastapi.responses import FileResponse
import os

HOME_DB = {
    "light": "off",
    "tv": "off",
    "curtain": "closed",
    "door_lock": "locked",
    "thermostat_mode": "off",
    "main_water_valve": "closed"
}

app = FastAPI()

# --- Configuration ---
# Allow interactions from your interface (CORS)

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
    "UI will use this endpoint to get the current status of all devices"
    return HOME_DB

@app.post("/update_device")
def update_device(command: DeviceCommand):
    device_id = command.device_id.lower()
    action = command.action.lower()
    
    if device_id in HOME_DB:
        HOME_DB[device_id] = action
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
    # Run on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)