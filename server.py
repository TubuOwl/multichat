from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json
import os

app = FastAPI()

# ── Global YouTube State ─────────────────────────────────────────────
yt_state = {
    "videoId": "",
    "title": "",
    "is_playing": False,
    "current_time": 0,
    "thumbnail": ""
}

# ── Client registry: ws -> {name, color} ────────────────────────────
clients: dict[WebSocket, dict] = {}

COLORS = ["#ff6b9d","#c084fc","#60a5fa","#34d399","#fbbf24","#f87171","#a78bfa","#38bdf8"]

def get_viewer_list():
    return [{"name": v["name"], "color": v["color"]} for v in clients.values() if v.get("name")]

async def broadcast(data: dict, exclude: WebSocket = None):
    msg = json.dumps(data)
    disconnected = []
    for ws in clients:
        if ws == exclude:
            continue
        try:
            await ws.send_text(msg)
        except:
            disconnected.append(ws)
    for ws in disconnected:
        clients.pop(ws, None)

async def broadcast_viewer_list():
    await broadcast({"type": "viewer_list", "viewers": get_viewer_list(), "count": len(clients)})

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    color = COLORS[len(clients) % len(COLORS)]
    clients[ws] = {"name": "", "color": color}

    # Kirim state + viewer list ke client baru
    await ws.send_text(json.dumps({
        "type": "sync",
        **yt_state,
        "your_color": color,
        "viewers": get_viewer_list(),
        "count": len(clients)
    }))

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            t = msg.get("type")

            if t == "set_name":
                name = msg.get("name", "").strip()[:20]
                clients[ws]["name"] = name
                await broadcast_viewer_list()

            elif t == "reaction":
                emoji = msg.get("emoji", "")
                name = clients[ws].get("name", "")
                color = clients[ws].get("color", "#fff")
                await broadcast({"type": "reaction", "emoji": emoji, "name": name, "color": color})

            elif t == "play":
                yt_state["is_playing"] = True
                yt_state["current_time"] = msg.get("current_time", 0)
                await broadcast({"type": "play", "current_time": yt_state["current_time"]}, exclude=ws)

            elif t == "pause":
                yt_state["is_playing"] = False
                yt_state["current_time"] = msg.get("current_time", 0)
                await broadcast({"type": "pause", "current_time": yt_state["current_time"]}, exclude=ws)

            elif t == "seek":
                yt_state["current_time"] = msg.get("current_time", 0)
                await broadcast({"type": "seek", "current_time": yt_state["current_time"]}, exclude=ws)

            elif t == "load":
                yt_state["videoId"] = msg.get("videoId", "")
                yt_state["title"] = msg.get("title", "")
                yt_state["thumbnail"] = msg.get("thumbnail", "")
                yt_state["is_playing"] = True
                yt_state["current_time"] = 0
                name = clients[ws].get("name", "")
                await broadcast({"type": "load", **yt_state, "by": name}, exclude=ws)

            elif t == "heartbeat":
                yt_state["current_time"] = msg.get("current_time", yt_state["current_time"])

    except WebSocketDisconnect:
        clients.pop(ws, None)
        await broadcast_viewer_list()

# Serve static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
