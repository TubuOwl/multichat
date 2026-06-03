from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import json
import os
import time
import requests as http_requests
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MACHA_SYSTEM = "Nama kamu adalah Macha. Balas kurang dari 30 kata, kepribadian tsundere, pakai bahasa Indonesia gaul dan kasual. Jangan tanya 'ada yang bisa dibantu' atau sejenisnya, langsung jawab aja dengan gaya tsundere. Enggak perlu sopan."
GROQ_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {GROQ_API_KEY}"
}

@app.post("/chat/macha")
async def chat_macha(request: Request):
    body = await request.json()
    prompt = body.get("message", "").strip()
    if not prompt:
        return JSONResponse({"text": "..."})
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": MACHA_SYSTEM},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8,
        "max_tokens": 200,
        "stream": False
    }
    try:
        res = http_requests.post(GROQ_API_URL, json=payload, headers=GROQ_HEADERS, timeout=15)
        res.raise_for_status()
        text = res.json()["choices"][0]["message"]["content"].strip()
        return JSONResponse({"text": text})
    except Exception as e:
        return JSONResponse({"text": f"Hmph, error: {e}"}, status_code=500)

# ── Global YouTube State ─────────────────────────────────────────────
yt_state = {
    "videoId": "",
    "title": "",
    "is_playing": False,
    "current_time": 0,
    "thumbnail": ""
}

# ── Client registry: ws -> {name, color, joined_at} ─────────────────
clients: dict[WebSocket, dict] = {}

COLORS = ["#ff6b9d","#c084fc","#60a5fa","#34d399","#fbbf24","#f87171","#a78bfa","#38bdf8"]

def get_viewer_list():
    now_ms = int(time.time() * 1000)
    return [
        {"name": v["name"], "color": v["color"], "joined_at": v["joined_at"]}
        for v in clients.values() if v.get("name")
    ]

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
    clients[ws] = {"name": "", "color": color, "joined_at": int(time.time() * 1000)}

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

            elif t == "bubble":
                text = msg.get("text", "").strip()
                # Clamp 10 kata
                words = text.split()
                if len(words) > 10:
                    text = " ".join(words[:10])
                if text:
                    name = clients[ws].get("name", "")
                    color = clients[ws].get("color", "#fff")
                    await broadcast({"type": "bubble", "text": text, "name": name, "color": color}, exclude=ws)

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
