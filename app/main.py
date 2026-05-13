import json
import logging
import os
import sys
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn

# ── Path bootstrap ────────────────────────────────────────────────────────────
#  Allow running from `app/` while the package lives under `src/`
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from smart_house_agent.config import get_llm, get_settings          # noqa: E402
from smart_house_agent.graph.supervisor_graph import (               # noqa: E402
    build_supervisor_application,
)
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage  # noqa: E402

logger = logging.getLogger(__name__)

settings = get_settings()
DB_FILE = str(settings.home_status_path.resolve())

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="Smart House Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Lazy singleton agent graph ────────────────────────────────────────────────
_agent_graph = None

def get_agent_graph():
    """Build and cache the supervisor graph on first call."""
    global _agent_graph
    if _agent_graph is None:
        from smart_house_agent.clients.home_api import HomeApiClient
        llm = get_llm(settings)
        api = HomeApiClient(settings.smart_house_api_url)
        _agent_graph = build_supervisor_application(settings, llm, api_client=api)
        logger.info("Supervisor graph initialised.")
    return _agent_graph


# ── Home-status helpers ───────────────────────────────────────────────────────
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


# ── Request/Response schemas ──────────────────────────────────────────────────
class DeviceCommand(BaseModel):
    device_id: str = Field(..., description="The device to control")
    action: str = Field(..., description="The action to perform on the device")


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to the AI agent")


# ── SSE helpers ───────────────────────────────────────────────────────────────
def _sse(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _stream_agent(user_message: str) -> AsyncGenerator[str, None]:
    """
    Run the supervisor graph and yield SSE events describing every step.
    The stream stays inside the existing runner pattern (graph.stream) but
    converts log-level output into structured events for the UI.
    """
    graph = get_agent_graph()
    inputs = {"messages": [HumanMessage(content=user_message)]}

    final_answer: str | None = None

    try:
        async for step in graph.astream(inputs, config={"recursion_limit": 10}):
            for agent_name, output in step.items():

                # Skip internal context-refresh node from UI trace
                if agent_name == "refresh_context":
                    continue

                # ── Agent activation ──────────────────────────────────────
                yield _sse({"type": "agent", "name": agent_name, "status": "active"})

                if "next" in output:
                    next_node = output["next"]
                    if next_node and next_node != "__end__":
                        yield _sse({
                            "type": "route",
                            "from": agent_name,
                            "to": next_node,
                        })

                if "messages" in output:
                    for msg in output["messages"]:

                        # Skip system context injection messages
                        if isinstance(msg, SystemMessage):
                            continue

                        # ── Tool calls ────────────────────────────────────
                        if isinstance(msg, AIMessage) and msg.tool_calls:
                            for tc in msg.tool_calls:
                                yield _sse({
                                    "type": "tool_call",
                                    "name": tc.get("name", "unknown"),
                                    "args": tc.get("args", {}),
                                })

                        # ── Tool results ──────────────────────────────────
                        elif isinstance(msg, ToolMessage):
                            yield _sse({
                                "type": "tool_result",
                                "name": msg.name or "tool",
                                "result": str(msg.content)[:200],
                            })

                        # ── AI text message ───────────────────────────────
                        elif isinstance(msg, AIMessage) and msg.content:
                            # Only capture non-routing/handoff messages as final answer
                            if isinstance(msg.content, list):
                                text_parts = [
                                    p.get("text", "") if isinstance(p, dict) else str(p)
                                    for p in msg.content
                                ]
                                content_str = "".join(text_parts).strip()
                            else:
                                content_str = str(msg.content).strip()

                            if content_str and not content_str.startswith("[SYSTEM_REPORT]"):
                                final_answer = content_str

        # ── Emit the final reply ──────────────────────────────────────────
        if final_answer:
            yield _sse({"type": "message", "content": final_answer})
        else:
            yield _sse({
                "type": "message",
                "content": "I've processed your request. Check the device dashboard for updated states.",
            })

    except Exception as exc:
        logger.exception("Error during agent stream: %s", exc)
        yield _sse({"type": "error", "content": f"Agent error: {exc}"})

    finally:
        yield _sse({"type": "done"})


# ── Existing device endpoints (unchanged) ─────────────────────────────────────
@app.get("/status")
def get_status():
    return load_db()


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


# ── New: SSE chat endpoint ────────────────────────────────────────────────────
@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    Accepts a user message and streams SSE events as the agent processes it.
    Events: agent | route | tool_call | tool_result | message | error | done
    """
    return StreamingResponse(
        _stream_agent(req.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering if proxied
        },
    )


# ── Static files & HTML routes ────────────────────────────────────────────────
_STATIC_DIR = Path(__file__).resolve().parent / "static"

@app.get("/dashboard")
async def read_dashboard():
    f = _STATIC_DIR / "dashboard.html"
    if not f.exists():
        raise HTTPException(status_code=404, detail=f"Dashboard not found at {f}")
    return FileResponse(str(f))


@app.get("/")
async def read_index():
    f = _STATIC_DIR / "index.html"
    if not f.exists():
        return {"error": f"index.html not found in {_STATIC_DIR}"}
    return FileResponse(str(f))


# Mount static files LAST so explicit routes take precedence
app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

# ── Usage ─────────────────────────────────────────────────────────────────────
# Terminal A  →  cd app && python main.py
# Chat UI     →  http://localhost:8000/
# Dashboard   →  http://localhost:8000/dashboard
# Status API  →  http://localhost:8000/status
