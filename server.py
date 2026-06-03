
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import json, os, time, asyncio
import requests as http_requests

app = FastAPI()

# ── Groq / Macha ─────────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MACHA_SYSTEM = "Nama kamu adalah Macha. Balas kurang dari 30 kata, kepribadian tsundere, pakai bahasa Indonesia gaul dan kasual. Jangan tanya 'ada yang bisa dibantu' atau sejenisnya, langsung jawab aja dengan gaya tsundere. Enggak perlu sopan."
GROQ_HEADERS = {"Content-Type": "application/json", "Authorization": f"Bearer {GROQ_API_KEY}"}

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
        "temperature": 0.8, "max_tokens": 200, "stream": False
    }
    try:
        res = http_requests.post(GROQ_API_URL, json=payload, headers=GROQ_HEADERS, timeout=15)
        res.raise_for_status()
        text = res.json()["choices"][0]["message"]["content"].strip()
        return JSONResponse({"text": text})
    except Exception as e:
        return JSONResponse({"text": f"Hmph, error: {e}"}, status_code=500)

# ── YouTube State ─────────────────────────────────────────────────────
yt_state = {
    "videoId": "", "title": "", "is_playing": False,
    "current_time": 0, "thumbnail": ""
}

# ── Clients ───────────────────────────────────────────────────────────
clients: dict[WebSocket, dict] = {}
COLORS = ["#ff6b9d","#c084fc","#60a5fa","#34d399","#fbbf24","#f87171","#a78bfa","#38bdf8"]

def get_viewer_list():
    return [
        {"name": v["name"], "color": v["color"], "joined_at": v["joined_at"]}
        for v in clients.values() if v.get("name")
    ]

async def broadcast(data: dict, exclude: WebSocket = None):
    msg = json.dumps(data)
    dead = []
    for ws in list(clients):
        if ws == exclude:
            continue
        try:
            await ws.send_text(msg)
        except:
            dead.append(ws)
    for ws in dead:
        clients.pop(ws, None)
    if dead:
        # Ada yang mati saat broadcast — update viewer list
        await _broadcast_viewers_safe()

async def broadcast_bytes(data: bytes, exclude: WebSocket = None):
    dead = []
    for ws in list(clients):
        if ws == exclude:
            continue
        try:
            await ws.send_bytes(data)
        except:
            dead.append(ws)
    for ws in dead:
        clients.pop(ws, None)

async def broadcast_viewers():
    await broadcast({"type": "viewer_list", "viewers": get_viewer_list(), "count": len(clients)})

async def _broadcast_viewers_safe():
    """Broadcast viewer list tanpa trigger loop rekursif."""
    msg = json.dumps({"type": "viewer_list", "viewers": get_viewer_list(), "count": len(clients)})
    for ws in list(clients):
        try:
            await ws.send_text(msg)
        except:
            clients.pop(ws, None)

async def remove_client(ws: WebSocket):
    """Hapus client dan broadcast viewer list terbaru."""
    clients.pop(ws, None)
    await broadcast_viewers()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    color = COLORS[len(clients) % len(COLORS)]
    clients[ws] = {
        "name": "", "color": color,
        "joined_at": int(time.time() * 1000),
        "last_vn_duration": 0
    }

    # Kirim state saat ini ke client baru
    await ws.send_text(json.dumps({
        "type": "sync", **yt_state,
        "your_color": color,
        "viewers": get_viewer_list(),
        "count": len(clients)
    }))
    await broadcast_viewers()

    # ── Ping loop: deteksi disconnect dalam 10 detik ──────────────────
    async def ping_loop():
        while ws in clients:
            await asyncio.sleep(10)
            if ws not in clients:
                break
            try:
                await ws.send_text(json.dumps({"type": "ping"}))
            except:
                await remove_client(ws)
                return

    asyncio.create_task(ping_loop())

    try:
        while True:
            msg_data = await ws.receive()

            # ── Binary: audio voice note ──────────────────────────────
            if "bytes" in msg_data:
                audio = msg_data["bytes"]
                name = clients[ws].get("name", "")
                color = clients[ws].get("color", "#fff")
                duration = clients[ws].get("last_vn_duration", 0)
                await broadcast({
                    "type": "voice_note_incoming",
                    "name": name, "color": color, "duration": duration
                }, exclude=ws)
                await broadcast_bytes(audio, exclude=ws)
                continue

            # ── Text: JSON ────────────────────────────────────────────
            if "text" not in msg_data:
                continue

            msg = json.loads(msg_data["text"])
            t = msg.get("type")

            if t == "pong":
                pass  # client masih hidup

            elif t == "set_name":
                clients[ws]["name"] = msg.get("name", "").strip()[:20]
                await broadcast_viewers()

            elif t == "voice_note_incoming":
                # Simpan durasi untuk diteruskan saat binary tiba
                clients[ws]["last_vn_duration"] = msg.get("duration", 0)

            elif t == "bubble":
                text = " ".join(msg.get("text", "").strip().split()[:10])
                if text:
                    await broadcast({
                        "type": "bubble", "text": text,
                        "name": clients[ws].get("name", ""),
                        "color": clients[ws].get("color", "#fff")
                    }, exclude=ws)

            elif t == "reaction":
                await broadcast({
                    "type": "reaction",
                    "emoji": msg.get("emoji", ""),
                    "name": clients[ws].get("name", ""),
                    "color": clients[ws].get("color", "#fff")
                })

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
                yt_state.update(
                    videoId=msg.get("videoId", ""),
                    title=msg.get("title", ""),
                    thumbnail=msg.get("thumbnail", ""),
                    is_playing=True, current_time=0
                )
                await broadcast({
                    "type": "load", **yt_state,
                    "by": clients[ws].get("name", "")
                }, exclude=ws)

            elif t == "heartbeat":
                yt_state["current_time"] = msg.get("current_time", yt_state["current_time"])

    except WebSocketDisconnect:
        await remove_client(ws)
    except Exception:
        await remove_client(ws)

# ── Static files ──────────────────────────────────────────────────────
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
