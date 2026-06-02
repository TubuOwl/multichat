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

connected_clients: list[WebSocket] = []

async def broadcast(data: dict, exclude: WebSocket = None):
    msg = json.dumps(data)
    disconnected = []
    for ws in connected_clients:
        if ws == exclude:
            continue
        try:
            await ws.send_text(msg)
        except:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in connected_clients:
            connected_clients.remove(ws)

async def broadcast_viewers():
    await broadcast({"type": "viewers", "count": len(connected_clients)})

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    await broadcast_viewers()

    # Kirim state saat ini ke client baru
    await ws.send_text(json.dumps({"type": "sync", **yt_state, "viewers": len(connected_clients)}))

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            t = msg.get("type")

            if t == "play":
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
                await broadcast({"type": "load", **yt_state}, exclude=ws)

            elif t == "heartbeat":
                yt_state["current_time"] = msg.get("current_time", yt_state["current_time"])

    except WebSocketDisconnect:
        if ws in connected_clients:
            connected_clients.remove(ws)
        await broadcast_viewers()

# Serve static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    # Render inject PORT via env variable
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
