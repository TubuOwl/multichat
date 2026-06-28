from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import json, os, time, asyncio, re, html, secrets
from urllib.parse import quote, urlparse

import requests as http_requests
from collections import defaultdict
import psycopg

REQUIRED_ENV = ["DATABASE_URL", "GROQ_API_KEY", "BAN_SECRET"]
missing_env = [name for name in REQUIRED_ENV if not os.environ.get(name)]
if missing_env:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing_env)}")

DATABASE_URL = os.environ["DATABASE_URL"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
BAN_SECRET = os.environ["BAN_SECRET"]

conn = psycopg.connect(DATABASE_URL)
with conn.cursor() as cur:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS room_stats (
            id INTEGER PRIMARY KEY,
            total_joins BIGINT DEFAULT 0,
            total_messages BIGINT DEFAULT 0,
            total_songs BIGINT DEFAULT 0
        )
    """)
    cur.execute("""
        INSERT INTO room_stats (id)
        VALUES (1)
        ON CONFLICT (id) DO NOTHING
    """)
    conn.commit()

app = FastAPI()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MACHA_SYSTEM = (
    "Your name is Macha. Reply in under 30 words, tsundere personality, "
    "casual English slang. Never ask things like 'how can I help', just answer "
    "directly in a tsundere style. No need to be polite."
)
GROQ_HEADERS = {"Content-Type": "application/json", "Authorization": f"Bearer {GROQ_API_KEY}"}

MAX_CLIENTS = 300
MAX_WS_TEXT_BYTES = 4000
MAX_CHAT_MESSAGE_LEN = 500
MAX_TENOR_QUERY_LEN = 60
MAX_TENOR_PAGE = 50
MAX_IFRAME_URL_LEN = 1000
MAX_IFRAME_TITLE_LEN = 100
MAX_BUBBLE_WORDS = 10
MAX_BUBBLE_CHARS = 200
ALLOWED_URL_SCHEMES = {"http", "https"}
DEFAULT_THUMB = "https://i.imgur.com/21CjTu1.gif"

def safe_equal(a: str, b: str) -> bool:
    return secrets.compare_digest(a.encode("utf-8"), b.encode("utf-8"))

def call_groq(prompt: str) -> str:
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": MACHA_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.8,
        "max_tokens": 200,
        "stream": False,
    }
    res = http_requests.post(GROQ_API_URL, json=payload, headers=GROQ_HEADERS, timeout=15)
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"].strip()

@app.post("/chat/macha")
async def chat_macha(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"text": "Invalid request."}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({"text": "Invalid request."}, status_code=400)
    prompt = str(body.get("message", "")).strip()
    if not prompt:
        return JSONResponse({"text": "..."})
    if len(prompt) > MAX_CHAT_MESSAGE_LEN:
        return JSONResponse({"text": "Message too long."}, status_code=400)
    try:
        text = call_groq(prompt)
        return JSONResponse({"text": text})
    except Exception:
        return JSONResponse({"text": "Something went wrong, try again later."}, status_code=500)

@app.get("/favicon.ico")
async def favicon():
    return FileResponse("static/favicon.ico")

@app.get("/stats")
async def stats():
    with conn.cursor() as cur:
        cur.execute("""
            SELECT total_joins, total_messages, total_songs
            FROM room_stats
            WHERE id = 1
        """)
        joins, messages, songs = cur.fetchone()
    return {"joins": joins, "messages": messages, "songs": songs}

_TENOR_QUERY_RE = re.compile(r"^[a-zA-Z0-9 _-]+$")

@app.get("/tenor")
async def tenor_search(q: str, page: int = 0):
    q = q.strip()
    if not q or len(q) > MAX_TENOR_QUERY_LEN or not _TENOR_QUERY_RE.match(q):
        return JSONResponse({"results": [], "error": "Invalid query."}, status_code=400)
    if page < 0 or page > MAX_TENOR_PAGE:
        return JSONResponse({"results": [], "error": "Invalid page."}, status_code=400)
    keyword = quote(q.replace(" ", "-"), safe="-")
    url = f"https://tenor.com/id/search/{keyword}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = http_requests.get(url, headers=headers, timeout=8)
        page_html = res.text
    except Exception:
        return JSONResponse({"results": [], "error": "Search failed."}, status_code=502)
    results = re.findall(r'https://media\.tenor\.com/[^\s"\']+\.(?:gif|png|jpg)', page_html)
    results = list(dict.fromkeys(results))
    start = page * 5
    chunk = results[start:start + 5]
    return JSONResponse({
        "results": chunk,
        "page": page,
        "has_next": len(results) > start + 5,
        "has_prev": page > 0,
        "total": len(results),
    })

yt_state = {
    "videoId": "", "title": "", "is_playing": False,
    "current_time": 0, "thumbnail": "",
}

iframe_state = {
    "url": "", "title": "", "thumb": "", "active": False,
}

clients: dict[WebSocket, dict] = {}
COLORS = ["#ff6b9d", "#c084fc", "#60a5fa", "#34d399", "#fbbf24", "#f87171", "#a78bfa", "#38bdf8"]

RATE_LIMITS = {
    "global":     {"limit": 20, "window": 5},
    "reaction":   {"limit": 2,  "window": 5},
    "bubble":     {"limit": 2,  "window": 6},
    "voice":      {"limit": 1,  "window": 15},
    "load":       {"limit": 3,  "window": 10},
    "iframe_url": {"limit": 3,  "window": 10},
}

spam_times: dict[WebSocket, dict] = defaultdict(lambda: defaultdict(list))
spam_strikes: dict[WebSocket, int] = defaultdict(int)
banned_names: set = set()

def check_rate_limit(ws: WebSocket, msg_type: str) -> bool:
    cfg = RATE_LIMITS.get(msg_type)
    if not cfg:
        return False
    now = time.time()
    times = spam_times[ws][msg_type]
    spam_times[ws][msg_type] = [t for t in times if now - t < cfg["window"]]
    if len(spam_times[ws][msg_type]) >= cfg["limit"]:
        spam_strikes[ws] += 1
        return True
    spam_times[ws][msg_type].append(now)
    return False

def sanitize_emoji(raw: str) -> str:
    import unicodedata
    chars = list(str(raw).strip())
    if not chars:
        return ""
    result = chars[0]
    if len(chars) > 1 and unicodedata.category(chars[1]) in ("Mn", "Cf"):
        result += chars[1]
    return html.escape(result)

def sanitize_text(raw: str, max_words: int = 10, max_chars: int = 200) -> str:
    raw = str(raw)
    if len(raw) > max_chars:
        return ""
    cleaned = " ".join(raw.strip().split()[:max_words])
    return html.escape(cleaned)

def is_safe_url(url: str) -> bool:
    if not url or len(url) > MAX_IFRAME_URL_LEN:
        return False
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    return parsed.scheme in ALLOWED_URL_SCHEMES and bool(parsed.netloc)

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
        except Exception:
            dead.append(ws)
    for ws in dead:
        clients.pop(ws, None)
    if dead:
        await _broadcast_viewers_safe()

async def broadcast_bytes(data: bytes, exclude: WebSocket = None):
    dead = []
    for ws in list(clients):
        if ws == exclude:
            continue
        try:
            await ws.send_bytes(data)
        except Exception:
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
        except Exception:
            clients.pop(ws, None)

async def remove_client(ws: WebSocket):
    clients.pop(ws, None)
    spam_times.pop(ws, None)
    spam_strikes.pop(ws, None)
    await broadcast_viewers()

async def kick_spammer(ws: WebSocket, reason: str = "Spam detected!"):
    name = clients.get(ws, {}).get("name", "anon")
    try:
        await ws.send_text(json.dumps({"type": "banned", "msg": reason}))
        await ws.close()
    except Exception:
        pass
    await remove_client(ws)
    await broadcast({"type": "notif", "msg": f"⚠️ {name} was kicked: {reason}"})

@app.get("/ban")
async def ban_user(name: str, secret: str):
    if not safe_equal(secret, BAN_SECRET):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    banned_names.add(name.lower())
    to_kick = [ws for ws, v in list(clients.items()) if v.get("name", "").lower() == name.lower()]
    for ws in to_kick:
        await kick_spammer(ws, "You have been banned by an admin.")
    return JSONResponse({"banned": name})

@app.get("/unban")
async def unban_user(name: str, secret: str):
    if not safe_equal(secret, BAN_SECRET):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    banned_names.discard(name.lower())
    return JSONResponse({"unbanned": name})

@app.get("/banned")
async def list_banned(secret: str):
    if not safe_equal(secret, BAN_SECRET):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    return JSONResponse({"banned": list(banned_names)})

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    if len(clients) >= MAX_CLIENTS:
        await ws.close(code=1013)
        return

    await ws.accept()
    color = COLORS[len(clients) % len(COLORS)]
    clients[ws] = {
        "name": "", "color": color,
        "joined_at": int(time.time() * 1000),
        "last_vn_duration": 0,
    }
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE room_stats
            SET total_joins = total_joins + 1
            WHERE id = 1
        """)
        conn.commit()

    await ws.send_text(json.dumps({
        "type": "sync", **yt_state,
        "your_color": color,
        "viewers": get_viewer_list(),
        "count": len(clients),
    }))

    if iframe_state.get("active"):
        await ws.send_text(json.dumps({
            "type": "iframe_url",
            "url": iframe_state["url"],
            "title": iframe_state["title"],
            "thumb": iframe_state["thumb"],
        }))

    await broadcast_viewers()

    async def ping_loop():
        while ws in clients:
            await asyncio.sleep(10)
            if ws not in clients:
                break
            try:
                await ws.send_text(json.dumps({"type": "ping"}))
            except Exception:
                await remove_client(ws)
                return

    asyncio.create_task(ping_loop())

    try:
        while True:
            msg_data = await ws.receive()

            if "bytes" in msg_data:
                if not clients[ws]["name"]:
                    continue
                if check_rate_limit(ws, "voice"):
                    if spam_strikes[ws] >= 3:
                        await kick_spammer(ws, "Spamming voice notes!")
                        break
                    await ws.send_text(json.dumps({"type": "warn", "msg": "Slow down! Voice note cooldown."}))
                    continue
                audio = msg_data["bytes"]
                if len(audio) > 2 * 1024 * 1024:
                    await ws.send_text(json.dumps({"type": "warn", "msg": "Voice note is too long!"}))
                    continue
                name = clients[ws].get("name", "")
                color = clients[ws].get("color", "#fff")
                duration = clients[ws].get("last_vn_duration", 0)
                await broadcast({"type": "voice_note_incoming", "name": name, "color": color, "duration": duration}, exclude=ws)
                await broadcast_bytes(audio, exclude=ws)
                continue

            if "text" not in msg_data:
                continue

            raw_text = msg_data["text"]
            if len(raw_text.encode("utf-8")) > MAX_WS_TEXT_BYTES:
                await ws.send_text(json.dumps({"type": "warn", "msg": "Message too large."}))
                continue

            try:
                msg = json.loads(raw_text)
            except Exception:
                await ws.send_text(json.dumps({"type": "warn", "msg": "Invalid message format."}))
                continue
            if not isinstance(msg, dict):
                continue

            t = msg.get("type")
            if not isinstance(t, str):
                continue

            if check_rate_limit(ws, "global"):
                if spam_strikes[ws] >= 5:
                    await kick_spammer(ws, "Flooding the connection!")
                    break
                await ws.send_text(json.dumps({"type": "warn", "msg": "Slow down!"}))
                continue

            if not clients[ws]["name"] and t not in ("set_name", "pong"):
                await ws.send_text(json.dumps({"type": "warn", "msg": "Please enter your name first."}))
                continue

            name = clients[ws].get("name", "")
            if name and name.lower() in banned_names:
                await kick_spammer(ws, "You are banned.")
                break

            if t == "pong":
                pass

            elif t == "set_name":
                new_name = re.sub(r"[^a-zA-Z0-9]", "", str(msg.get("name", "")))[:20]
                if not new_name:
                    await ws.send_text(json.dumps({"type": "warn", "msg": "Invalid name."}))
                    continue
                if any(
                    c["name"].lower() == new_name.lower()
                    for c in clients.values()
                    if c is not clients[ws]
                ):
                    await ws.send_text(json.dumps({"type": "warn", "msg": "Name already in use."}))
                    continue
                if new_name.lower() in banned_names:
                    await kick_spammer(ws, "This name is banned.")
                    break
                clients[ws]["name"] = new_name
                await broadcast_viewers()

            elif t == "voice_note_incoming":
                duration = msg.get("duration", 0)
                if not isinstance(duration, (int, float)) or duration < 0 or duration > 600:
                    duration = 0
                clients[ws]["last_vn_duration"] = duration

            elif t == "bubble":
                if not clients[ws].get("name"):
                    continue
                if check_rate_limit(ws, "bubble"):
                    if spam_strikes[ws] >= 3:
                        await kick_spammer(ws, "Spamming bubbles!")
                        break
                    await ws.send_text(json.dumps({"type": "warn", "msg": "Slow down! No bubble spam."}))
                    continue
                text = sanitize_text(msg.get("text", ""), max_words=MAX_BUBBLE_WORDS, max_chars=MAX_BUBBLE_CHARS)
                if not text:
                    continue
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE room_stats
                        SET total_messages = total_messages + 1
                        WHERE id = 1
                    """)
                    conn.commit()
                await broadcast({
                    "type": "bubble", "text": text,
                    "name": clients[ws].get("name", ""),
                    "color": clients[ws].get("color", "#fff"),
                }, exclude=ws)
                if "@macha" in text.lower():
                    prompt = text.lower().replace("@macha", "").strip()
                    if prompt and len(prompt) <= MAX_CHAT_MESSAGE_LEN:
                        try:
                            answer = call_groq(prompt)
                            await broadcast({
                                "type": "bubble",
                                "text": html.escape(answer),
                                "name": "Macha",
                                "color": "#ff69b4",
                            })
                        except Exception:
                            pass

            elif t == "reaction":
                if not clients[ws].get("name"):
                    continue
                if check_rate_limit(ws, "reaction"):
                    if spam_strikes[ws] >= 3:
                        await kick_spammer(ws, "Spamming reactions!")
                        break
                    await ws.send_text(json.dumps({"type": "warn", "msg": "Slow down! No emoji spam."}))
                    continue
                emoji = sanitize_emoji(msg.get("emoji", ""))
                if not emoji:
                    continue
                await broadcast({
                    "type": "reaction", "emoji": emoji,
                    "name": clients[ws].get("name", ""),
                    "color": clients[ws].get("color", "#fff"),
                })

            elif t == "play":
                ct = msg.get("current_time", 0)
                yt_state["is_playing"] = True
                yt_state["current_time"] = ct if isinstance(ct, (int, float)) else 0
                await broadcast({"type": "play", "current_time": yt_state["current_time"]}, exclude=ws)

            elif t == "pause":
                ct = msg.get("current_time", 0)
                yt_state["is_playing"] = False
                yt_state["current_time"] = ct if isinstance(ct, (int, float)) else 0
                await broadcast({"type": "pause", "current_time": yt_state["current_time"]}, exclude=ws)

            elif t == "seek":
                ct = msg.get("current_time", 0)
                yt_state["current_time"] = ct if isinstance(ct, (int, float)) else 0
                await broadcast({"type": "seek", "current_time": yt_state["current_time"]}, exclude=ws)

            elif t == "load":
                if check_rate_limit(ws, "load"):
                    if spam_strikes[ws] >= 3:
                        await kick_spammer(ws, "Spamming video loads!")
                        break
                    continue
                if not clients[ws].get("name"):
                    continue
                video_id = re.sub(r"[^a-zA-Z0-9_-]", "", str(msg.get("videoId", "")))[:11]
                if len(video_id) < 5:
                    continue
                try:
                    oembed = http_requests.get(
                        f"https://www.youtube.com/oembed?url=https://youtu.be/{video_id}",
                        timeout=5,
                    )
                    if oembed.status_code != 200:
                        continue
                    data = oembed.json()
                except Exception:
                    continue
                if not isinstance(data, dict) or "title" not in data or "thumbnail_url" not in data:
                    continue
                yt_state.update(
                    videoId=video_id,
                    title=html.escape(str(data["title"]))[:200],
                    thumbnail=str(data["thumbnail_url"])[:500],
                    is_playing=True,
                    current_time=0,
                )
                iframe_state.update(url="", title="", thumb="", active=False)
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE room_stats
                        SET total_songs = total_songs + 1
                        WHERE id = 1
                    """)
                    conn.commit()
                await broadcast({
                    "type": "load", **yt_state,
                    "by": clients[ws].get("name", ""),
                }, exclude=ws)

            elif t == "iframe_url":
                if not clients[ws].get("name"):
                    continue
                if check_rate_limit(ws, "iframe_url"):
                    if spam_strikes[ws] >= 3:
                        await kick_spammer(ws, "Spamming embed links!")
                        break
                    await ws.send_text(json.dumps({"type": "warn", "msg": "Slow down!"}))
                    continue
                url = str(msg.get("url", "")).strip()
                title = html.escape(str(msg.get("title", "")).strip()[:MAX_IFRAME_TITLE_LEN])
                thumb = str(msg.get("thumb", "")).strip()
                if not is_safe_url(thumb):
                    thumb = DEFAULT_THUMB
                if not is_safe_url(url) or not title:
                    continue

                iframe_state.update(url=url, title=title, thumb=thumb, active=True)
                yt_state.update(videoId="", is_playing=False)

                await broadcast({
                    "type": "iframe_url",
                    "url": url,
                    "title": title,
                    "thumb": thumb,
                    "by": clients[ws].get("name", ""),
                }, exclude=ws)

            elif t == "heartbeat":
                ct = msg.get("current_time", yt_state["current_time"])
                yt_state["current_time"] = ct if isinstance(ct, (int, float)) else yt_state["current_time"]

    except WebSocketDisconnect:
        await remove_client(ws)
    except Exception:
        await remove_client(ws)

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
