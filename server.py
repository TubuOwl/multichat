from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import json, os, time, asyncio, re
import requests as http_requests
from collections import defaultdict

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

@app.get("/favicon.ico")
async def favicon():
    return FileResponse("static/favicon.ico")

# ── Tenor GIF scraper ─────────────────────────────────────────────────
@app.get("/tenor")
async def tenor_search(q: str, page: int = 0):
    keyword = q.strip().replace(" ", "-")
    url = f"https://tenor.com/id/search/{keyword}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = http_requests.get(url, headers=headers, timeout=8)
        html = res.text
    except Exception as e:
        return JSONResponse({"results": [], "error": str(e)})
    results = re.findall(r'https://media\.tenor\.com/[^\s"\']+\.(?:gif|png|jpg)', html)
    results = list(dict.fromkeys(results))
    start = page * 5
    chunk = results[start:start + 5]
    return JSONResponse({
        "results": chunk, "page": page,
        "has_next": len(results) > start + 5,
        "has_prev": page > 0, "total": len(results)
    })

# ── YouTube State ─────────────────────────────────────────────────────
yt_state = {
    "videoId": "", "title": "", "is_playing": False,
    "current_time": 0, "thumbnail": ""
}

# ── Clients ───────────────────────────────────────────────────────────
clients: dict[WebSocket, dict] = {}
COLORS = ["#ff6b9d","#c084fc","#60a5fa","#34d399","#fbbf24","#f87171","#a78bfa","#38bdf8"]

# ── Anti-spam ─────────────────────────────────────────────────────────
# Tiap type punya limit dan window sendiri
RATE_LIMITS = {
    "reaction": {"limit": 2,  "window": 5},   # max 2 reaction per 5 detik
    "bubble":   {"limit": 2,  "window": 6},   # max 2 bubble per 6 detik
    "voice":    {"limit": 1,  "window": 15},  # max 1 voice note per 15 detik
}
spam_times:   dict[WebSocket, dict] = defaultdict(lambda: defaultdict(list))
spam_strikes: dict[WebSocket, int]  = defaultdict(int)
banned_names: set = set()
BAN_SECRET = os.environ.get("BAN_SECRET", "adminrahasia")

def check_rate_limit(ws: WebSocket, msg_type: str) -> bool:
    cfg = RATE_LIMITS.get(msg_type)
    if not cfg:
        return False
    now = time.time()
    times = spam_times[ws][msg_type]
    # Buang yang sudah lewat window
    spam_times[ws][msg_type] = [t for t in times if now - t < cfg["window"]]
    if len(spam_times[ws][msg_type]) >= cfg["limit"]:
        spam_strikes[ws] += 1
        return True
    spam_times[ws][msg_type].append(now)
    return False

def sanitize_emoji(raw: str) -> str:
    import unicodedata
    chars = list(raw.strip())
    if not chars:
        return ""
    result = chars[0]
    if len(chars) > 1 and unicodedata.category(chars[1]) in ("Mn", "Cf"):
        result += chars[1]
    return result

def sanitize_text(raw: str, max_words: int = 10, max_chars: int = 200) -> str:
    """Clamp teks ke max_words kata dan max_chars karakter."""
    if len(raw) > max_chars:
        return ""
    return " ".join(raw.strip().split()[:max_words])

# ── Broadcast helpers ─────────────────────────────────────────────────
def get_viewer_list():
    return [
        {"name": v["name"], "color": v["color"], "joined_at": v["joined_at"]}
        for v in clients.values() if v.get("name")
    ]

async def broadcast(data: dict, exclude: WebSocket = None):
    msg = json.dumps(data)
    dead = []
    for ws in list(clients):
        if ws == exclude: continue
        try:
            await ws.send_text(msg)
        except:
            dead.append(ws)
    for ws in dead:
        clients.pop(ws, None)
    if dead:
        await _broadcast_viewers_safe()

async def broadcast_bytes(data: bytes, exclude: WebSocket = None):
    dead = []
    for ws in list(clients):
        if ws == exclude: continue
        try:
            await ws.send_bytes(data)
        except:
            dead.append(ws)
    for ws in dead:
        clients.pop(ws, None)

async def broadcast_viewers():
    await broadcast({"type": "viewer_list", "viewers": get_viewer_list(), "count": len(clients)})

async def _broadcast_viewers_safe():
    msg = json.dumps({"type": "viewer_list", "viewers": get_viewer_list(), "count": len(clients)})
    for ws in list(clients):
        try:
            await ws.send_text(msg)
        except:
            clients.pop(ws, None)

async def remove_client(ws: WebSocket):
    clients.pop(ws, None)
    spam_times.pop(ws, None)
    spam_strikes.pop(ws, None)
    await broadcast_viewers()

async def kick_spammer(ws: WebSocket, reason: str = "Spam terdeteksi!"):
    name = clients.get(ws, {}).get("name", "anon")
    try:
        await ws.send_text(json.dumps({"type": "banned", "msg": reason}))
        await ws.close()
    except: pass
    await remove_client(ws)
    await broadcast({"type": "notif", "msg": f"⚠️ {name} dikick: {reason}"})

# ── Ban endpoints ─────────────────────────────────────────────────────
@app.get("/ban")
async def ban_user(name: str, secret: str):
    if secret != BAN_SECRET:
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    banned_names.add(name.lower())
    to_kick = [ws for ws, v in list(clients.items()) if v.get("name","").lower() == name.lower()]
    for ws in to_kick:
        await kick_spammer(ws, "Kamu dibanned oleh admin.")
    return JSONResponse({"banned": name})

@app.get("/unban")
async def unban_user(name: str, secret: str):
    if secret != BAN_SECRET:
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    banned_names.discard(name.lower())
    return JSONResponse({"unbanned": name})

@app.get("/banned")
async def list_banned(secret: str):
    if secret != BAN_SECRET:
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    return JSONResponse({"banned": list(banned_names)})

# ── WebSocket ─────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    color = COLORS[len(clients) % len(COLORS)]
    clients[ws] = {
        "name": "", "color": color,
        "joined_at": int(time.time() * 1000),
        "last_vn_duration": 0
    }

    await ws.send_text(json.dumps({
        "type": "sync", **yt_state,
        "your_color": color,
        "viewers": get_viewer_list(),
        "count": len(clients)
    }))
    await broadcast_viewers()

    async def ping_loop():
        while ws in clients:
            await asyncio.sleep(10)
            if ws not in clients: break
            try:
                await ws.send_text(json.dumps({"type": "ping"}))
            except:
                await remove_client(ws)
                return

    asyncio.create_task(ping_loop())

    try:
        while True:
            msg_data = await ws.receive()

            # ── Binary: voice note ────────────────────────────────────
            if "bytes" in msg_data:
                # Cek rate limit voice
                if check_rate_limit(ws, "voice"):
                    if spam_strikes[ws] >= 3:
                        await kick_spammer(ws, "Spam voice note!")
                        break
                    await ws.send_text(json.dumps({"type": "warn", "msg": "Pelan-pelan dong! Cooldown voice note."}))
                    continue
                audio = msg_data["bytes"]
                # Batasi ukuran audio max 2MB
                if len(audio) > 2 * 1024 * 1024:
                    await ws.send_text(json.dumps({"type": "warn", "msg": "Voice note terlalu panjang!"}))
                    continue
                name  = clients[ws].get("name", "")
                color = clients[ws].get("color", "#fff")
                duration = clients[ws].get("last_vn_duration", 0)
                await broadcast({"type": "voice_note_incoming", "name": name, "color": color, "duration": duration}, exclude=ws)
                await broadcast_bytes(audio, exclude=ws)
                continue

            if "text" not in msg_data:
                continue

            msg = json.loads(msg_data["text"])
            t = msg.get("type")

            # Cek banned
            name = clients[ws].get("name", "")
            if name and name.lower() in banned_names:
                await kick_spammer(ws, "Kamu dibanned.")
                break

            if t == "pong":
                pass

            elif t == "set_name":
                new_name = re.sub(r'[^a-zA-Z0-9]', '', msg.get("name", ""))[:20]
                if new_name.lower() in banned_names:
                    await kick_spammer(ws, "Nama ini dibanned.")
                    break
                clients[ws]["name"] = new_name
                await broadcast_viewers()

            elif t == "voice_note_incoming":
                clients[ws]["last_vn_duration"] = msg.get("duration", 0)

            elif t == "bubble":
                if not clients[ws].get("name"):
                    continue
                if check_rate_limit(ws, "bubble"):
                    if spam_strikes[ws] >= 3:
                        await kick_spammer(ws, "Spam bubble!")
                        break
                    await ws.send_text(json.dumps({"type": "warn", "msg": "Slow down! Jangan spam bubble!"}))
                    continue
                text = sanitize_text(msg.get("text", ""), max_words=10, max_chars=200)
                if not text:
                    continue
                await broadcast({
                    "type": "bubble", "text": text,
                    "name": clients[ws].get("name", ""),
                    "color": clients[ws].get("color", "#fff")
                }, exclude=ws)

            elif t == "reaction":
                if not clients[ws].get("name"):
                    continue
                if check_rate_limit(ws, "reaction"):
                    if spam_strikes[ws] >= 3:
                        await kick_spammer(ws, "Spam reaction!")
                        break
                    await ws.send_text(json.dumps({"type": "warn", "msg": "Slow down! Jangan spam emoji."}))
                    continue
                # Sanitize: ambil 1 emoji saja, buang repeat
                emoji = sanitize_emoji(msg.get("emoji", ""))
                if not emoji:
                    continue
                await broadcast({
                    "type": "reaction", "emoji": emoji,
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
                if check_rate_limit(ws, "load"):
                    if spam_strikes[ws] >= 3:
                        await kick_spammer(ws, "Spam load video!")
                        break
                    continue
            
                if not clients[ws].get("name"):
                    continue
            
                video_id = re.sub(r'[^a-zA-Z0-9_-]', '', msg.get("videoId", ""))[:11]
                if len(video_id) < 5:
                    continue
            
                try:
                    oembed = http_requests.get(
                        f"https://www.youtube.com/oembed?url=https://youtu.be/{video_id}",
                        timeout=5
                    )
                    if oembed.status_code != 200:
                        continue
                    data = oembed.json()
                except:
                    continue
            
                yt_state.update(
                    videoId=video_id,
                    title=data["title"],
                    thumbnail=data["thumbnail_url"],
                    is_playing=True,
                    current_time=0
                )
                await broadcast({
                    "type": "load", **yt_state,
                    "by": clients[ws].get("name", "")
                }, exclude=ws)

            elif t == "iframe_url":
                if not clients[ws].get("name"):
                    continue
                url   = msg.get("url", "").strip()
                title = msg.get("title", "").strip()[:100]
                if not url.startswith("http") or not title:
                    continue
                await broadcast({
                    "type": "iframe_url",
                    "url": url,
                    "title": title,
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
