from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json, os, time, asyncio, re, sqlite3, hashlib, secrets
import requests as http_requests
from collections import defaultdict

app = FastAPI()

# ── Database ──────────────────────────────────────────────────────────
DB_PATH = "data.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            joined_at INTEGER NOT NULL,
            left_at INTEGER,
            duration INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS leaderboard (
            username TEXT PRIMARY KEY,
            total_seconds INTEGER DEFAULT 0,
            visit_count INTEGER DEFAULT 0
        );
    """)
    # Buat admin default kalau belum ada
    admin_pass = hash_password(os.environ.get("ADMIN_PASSWORD", "admin123"))
    c.execute("INSERT OR IGNORE INTO users (username, password, role, created_at) VALUES (?, ?, 'admin', ?)",
              ("admin", admin_pass, int(time.time())))
    conn.commit()
    conn.close()

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def verify_user(username: str, password: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    if not row:
        return None
    if row["password"] != hash_password(password):
        return None
    return dict(row)

def create_user(username: str, password: str, role: str = "user"):
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)",
                     (username, hash_password(password), role, int(time.time())))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def delete_user(username: str):
    conn = get_db()
    conn.execute("DELETE FROM users WHERE username=?", (username,))
    conn.commit()
    conn.close()

def start_session(username: str) -> int:
    conn = get_db()
    c = conn.cursor()
    now = int(time.time() * 1000)
    c.execute("INSERT INTO sessions (username, joined_at) VALUES (?, ?)", (username, now))
    session_id = c.lastrowid
    conn.commit()
    conn.close()
    return session_id

def end_session(session_id: int, username: str):
    conn = get_db()
    now = int(time.time() * 1000)
    row = conn.execute("SELECT joined_at FROM sessions WHERE id=?", (session_id,)).fetchone()
    if row:
        duration_sec = max(0, (now - row["joined_at"]) // 1000)
        conn.execute("UPDATE sessions SET left_at=?, duration=? WHERE id=?",
                     (now, duration_sec, session_id))
        # Update leaderboard
        conn.execute("""
            INSERT INTO leaderboard (username, total_seconds, visit_count)
            VALUES (?, ?, 1)
            ON CONFLICT(username) DO UPDATE SET
                total_seconds = total_seconds + ?,
                visit_count = visit_count + 1
        """, (username, duration_sec, duration_sec))
        conn.commit()
    conn.close()

def get_leaderboard(limit: int = 20):
    conn = get_db()
    rows = conn.execute("""
        SELECT username, total_seconds, visit_count
        FROM leaderboard
        ORDER BY total_seconds DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_users():
    conn = get_db()
    rows = conn.execute("SELECT username, role, created_at FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

init_db()

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
        "messages": [{"role": "system", "content": MACHA_SYSTEM}, {"role": "user", "content": prompt}],
        "temperature": 0.8, "max_tokens": 200, "stream": False
    }
    try:
        res = http_requests.post(GROQ_API_URL, json=payload, headers=GROQ_HEADERS, timeout=15)
        res.raise_for_status()
        return JSONResponse({"text": res.json()["choices"][0]["message"]["content"].strip()})
    except Exception as e:
        return JSONResponse({"text": f"Hmph, error: {e}"}, status_code=500)

# ── Tenor ─────────────────────────────────────────────────────────────
@app.get("/tenor")
async def tenor_search(q: str, page: int = 0):
    keyword = q.strip().replace(" ", "-")
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = http_requests.get(f"https://tenor.com/id/search/{keyword}", headers=headers, timeout=8)
        results = re.findall(r'https://media\.tenor\.com/[^\s"\']+\.(?:gif|png|jpg)', res.text)
        results = list(dict.fromkeys(results))
    except:
        return JSONResponse({"results": []})
    start = page * 5
    return JSONResponse({
        "results": results[start:start+5], "page": page,
        "has_next": len(results) > start+5, "has_prev": page > 0
    })

# ── Auth endpoints ────────────────────────────────────────────────────
BAN_SECRET = os.environ.get("BAN_SECRET", "adminrahasia")

@app.post("/auth/login")
async def login(request: Request):
    body = await request.json()
    username = re.sub(r'[^a-zA-Z0-9]', '', body.get("username", ""))[:20]
    password = body.get("password", "")
    user = verify_user(username, password)
    if not user:
        return JSONResponse({"error": "Username atau password salah"}, status_code=401)
    token = secrets.token_hex(16)
    # Simpan token sementara di memory
    auth_tokens[token] = {"username": username, "role": user["role"]}
    return JSONResponse({"token": token, "username": username, "role": user["role"]})

@app.post("/auth/logout")
async def logout(request: Request):
    body = await request.json()
    token = body.get("token", "")
    auth_tokens.pop(token, None)
    return JSONResponse({"ok": True})

# ── Admin endpoints ───────────────────────────────────────────────────
def verify_admin(secret: str) -> bool:
    return secret == BAN_SECRET

@app.post("/admin/create-user")
async def admin_create_user(request: Request):
    body = await request.json()
    if not verify_admin(body.get("secret", "")):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    username = re.sub(r'[^a-zA-Z0-9]', '', body.get("username", ""))[:20]
    password = body.get("password", "")
    role     = body.get("role", "user")
    if not username or not password:
        return JSONResponse({"error": "Username dan password wajib diisi"}, status_code=400)
    ok = create_user(username, password, role)
    if not ok:
        return JSONResponse({"error": "Username sudah ada"}, status_code=409)
    return JSONResponse({"created": username})

@app.post("/admin/delete-user")
async def admin_delete_user(request: Request):
    body = await request.json()
    if not verify_admin(body.get("secret", "")):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    username = body.get("username", "")
    if username == "admin":
        return JSONResponse({"error": "Tidak bisa hapus admin"}, status_code=400)
    delete_user(username)
    return JSONResponse({"deleted": username})

@app.post("/admin/reset-password")
async def admin_reset_password(request: Request):
    body = await request.json()
    if not verify_admin(body.get("secret", "")):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    username = body.get("username", "")
    new_pass = body.get("password", "")
    conn = get_db()
    conn.execute("UPDATE users SET password=? WHERE username=?",
                 (hash_password(new_pass), username))
    conn.commit()
    conn.close()
    return JSONResponse({"reset": username})

@app.get("/admin/users")
async def admin_users(secret: str):
    if not verify_admin(secret):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    return JSONResponse({"users": get_all_users()})

@app.get("/leaderboard")
async def leaderboard():
    return JSONResponse({"leaderboard": get_leaderboard()})

@app.get("/ban")
async def ban_user(name: str, secret: str):
    if not verify_admin(secret):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    banned_names.add(name.lower())
    to_kick = [ws for ws, v in list(clients.items()) if v.get("name","").lower() == name.lower()]
    for ws in to_kick:
        await kick_spammer(ws, "Kamu dibanned oleh admin.")
    return JSONResponse({"banned": name})

@app.get("/unban")
async def unban_user(name: str, secret: str):
    if not verify_admin(secret):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    banned_names.discard(name.lower())
    return JSONResponse({"unbanned": name})

@app.get("/banned")
async def list_banned(secret: str):
    if not verify_admin(secret):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    return JSONResponse({"banned": list(banned_names)})

@app.get("/favicon.ico")
async def favicon():
    return JSONResponse({}, status_code=204)

# ── State ─────────────────────────────────────────────────────────────
yt_state = {"videoId": "", "title": "", "is_playing": False, "current_time": 0, "thumbnail": ""}
iframe_state = {"url": "", "title": "", "thumb": "", "active": False}

clients:     dict[WebSocket, dict] = {}
auth_tokens: dict[str, dict]       = {}
banned_names: set                  = set()
COLORS = ["#ff6b9d","#c084fc","#60a5fa","#34d399","#fbbf24","#f87171","#a78bfa","#38bdf8"]

# ── Anti-spam ─────────────────────────────────────────────────────────
RATE_LIMITS = {
    "reaction": {"limit": 2, "window": 5},
    "bubble":   {"limit": 2, "window": 6},
    "voice":    {"limit": 1, "window": 15},
    "load":     {"limit": 1, "window": 30},
}
spam_times:   dict = defaultdict(lambda: defaultdict(list))
spam_strikes: dict = defaultdict(int)

def check_rate_limit(ws: WebSocket, msg_type: str) -> bool:
    cfg = RATE_LIMITS.get(msg_type)
    if not cfg: return False
    now = time.time()
    spam_times[ws][msg_type] = [t for t in spam_times[ws][msg_type] if now - t < cfg["window"]]
    if len(spam_times[ws][msg_type]) >= cfg["limit"]:
        spam_strikes[ws] += 1
        return True
    spam_times[ws][msg_type].append(now)
    return False

def sanitize_emoji(raw: str) -> str:
    import unicodedata
    chars = list(raw.strip())
    if not chars: return ""
    result = chars[0]
    if len(chars) > 1 and unicodedata.category(chars[1]) in ("Mn", "Cf"):
        result += chars[1]
    return result

def sanitize_text(raw: str, max_words: int = 10, max_chars: int = 200) -> str:
    if len(raw) > max_chars: return ""
    return " ".join(raw.strip().split()[:max_words])

# ── Broadcast ─────────────────────────────────────────────────────────
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
        try: await ws.send_text(msg)
        except: dead.append(ws)
    for ws in dead: clients.pop(ws, None)
    if dead: await _broadcast_viewers_safe()

async def broadcast_bytes(data: bytes, exclude: WebSocket = None):
    dead = []
    for ws in list(clients):
        if ws == exclude: continue
        try: await ws.send_bytes(data)
        except: dead.append(ws)
    for ws in dead: clients.pop(ws, None)

async def broadcast_viewers():
    await broadcast({"type": "viewer_list", "viewers": get_viewer_list(), "count": len(clients)})

async def _broadcast_viewers_safe():
    msg = json.dumps({"type": "viewer_list", "viewers": get_viewer_list(), "count": len(clients)})
    for ws in list(clients):
        try: await ws.send_text(msg)
        except: clients.pop(ws, None)

async def remove_client(ws: WebSocket):
    data = clients.pop(ws, None)
    spam_times.pop(ws, None)
    spam_strikes.pop(ws, None)
    # Akhiri session
    if data and data.get("session_id") and data.get("name"):
        end_session(data["session_id"], data["name"])
    await broadcast_viewers()

async def kick_spammer(ws: WebSocket, reason: str = "Spam terdeteksi!"):
    name = clients.get(ws, {}).get("name", "anon")
    try:
        await ws.send_text(json.dumps({"type": "banned", "msg": reason}))
        await ws.close()
    except: pass
    await remove_client(ws)
    await broadcast({"type": "notif", "msg": f"⚠️ {name} dikick: {reason}"})

# ── WebSocket ─────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    color = COLORS[len(clients) % len(COLORS)]
    clients[ws] = {
        "name": "", "color": color,
        "joined_at": int(time.time() * 1000),
        "last_vn_duration": 0,
        "session_id": None,
        "role": "user"
    }

    await ws.send_text(json.dumps({
        "type": "sync", **yt_state,
        "your_color": color,
        "viewers": get_viewer_list(),
        "count": len(clients)
    }))

    if iframe_state.get("active"):
        await ws.send_text(json.dumps({
            "type": "iframe_url",
            "url": iframe_state["url"],
            "title": iframe_state["title"],
            "thumb": iframe_state["thumb"]
        }))

    await broadcast_viewers()

    async def ping_loop():
        while ws in clients:
            await asyncio.sleep(10)
            if ws not in clients: break
            try: await ws.send_text(json.dumps({"type": "ping"}))
            except:
                await remove_client(ws)
                return

    asyncio.create_task(ping_loop())

    try:
        while True:
            msg_data = await ws.receive()

            # ── Binary: voice note ────────────────────────────────────
            if "bytes" in msg_data:
                if not clients[ws].get("name"): continue
                if check_rate_limit(ws, "voice"):
                    if spam_strikes[ws] >= 3:
                        await kick_spammer(ws, "Spam voice note!")
                        break
                    continue
                audio = msg_data["bytes"]
                if len(audio) > 2 * 1024 * 1024: continue
                name  = clients[ws].get("name", "")
                color = clients[ws].get("color", "#fff")
                duration = clients[ws].get("last_vn_duration", 0)
                await broadcast({"type": "voice_note_incoming", "name": name, "color": color, "duration": duration}, exclude=ws)
                await broadcast_bytes(audio, exclude=ws)
                continue

            if "text" not in msg_data: continue
            msg = json.loads(msg_data["text"])
            t = msg.get("type")

            # Cek banned
            name = clients[ws].get("name", "")
            if name and name.lower() in banned_names:
                await kick_spammer(ws, "Kamu dibanned.")
                break

            if t == "pong":
                pass

            elif t == "auth":
                # Login via WebSocket
                token = msg.get("token", "")
                user_data = auth_tokens.get(token)
                if not user_data:
                    await ws.send_text(json.dumps({"type": "auth_fail", "msg": "Token tidak valid"}))
                    continue
                uname = user_data["username"]
                if uname.lower() in banned_names:
                    await kick_spammer(ws, "Kamu dibanned.")
                    break
                clients[ws]["name"]  = uname
                clients[ws]["role"]  = user_data["role"]
                clients[ws]["session_id"] = start_session(uname)
                await ws.send_text(json.dumps({"type": "auth_ok", "username": uname, "role": user_data["role"]}))
                await broadcast_viewers()

            elif t == "set_name":
                # Hanya boleh kalau belum auth
                if clients[ws].get("session_id"):
                    continue
                new_name = re.sub(r'[^a-zA-Z0-9]', '', msg.get("name", ""))[:20]
                if new_name.lower() in banned_names:
                    await kick_spammer(ws, "Nama ini dibanned.")
                    break
                clients[ws]["name"] = new_name
                await broadcast_viewers()

            elif t == "voice_note_incoming":
                clients[ws]["last_vn_duration"] = msg.get("duration", 0)

            elif t == "bubble":
                if not clients[ws].get("name"): continue
                if check_rate_limit(ws, "bubble"):
                    if spam_strikes[ws] >= 3:
                        await kick_spammer(ws, "Spam bubble!")
                        break
                    continue
                text = sanitize_text(msg.get("text", ""), max_words=10, max_chars=200)
                if not text: continue
                await broadcast({
                    "type": "bubble", "text": text,
                    "name": clients[ws].get("name", ""),
                    "color": clients[ws].get("color", "#fff")
                })

            elif t == "reaction":
                if not clients[ws].get("name"): continue
                if check_rate_limit(ws, "reaction"):
                    if spam_strikes[ws] >= 3:
                        await kick_spammer(ws, "Spam reaction!")
                        break
                    continue
                emoji = sanitize_emoji(msg.get("emoji", ""))
                if not emoji: continue
                await broadcast({
                    "type": "reaction", "emoji": emoji,
                    "name": clients[ws].get("name", ""),
                    "color": clients[ws].get("color", "#fff")
                })

            elif t == "load":
                if not clients[ws].get("name"): continue
                if check_rate_limit(ws, "load"):
                    if spam_strikes[ws] >= 3:
                        await kick_spammer(ws, "Spam load video!")
                        break
                    continue
                video_id = re.sub(r'[^a-zA-Z0-9_-]', '', msg.get("videoId", ""))[:11]
                if len(video_id) < 5: continue
                try:
                    oembed = http_requests.get(
                        f"https://www.youtube.com/oembed?url=https://youtu.be/{video_id}", timeout=5)
                    if oembed.status_code != 200: continue
                    data = oembed.json()
                except: continue
                yt_state.update(videoId=video_id, title=data["title"],
                    thumbnail=data["thumbnail_url"], is_playing=True, current_time=0)
                iframe_state.update(url="", title="", thumb="", active=False)
                await broadcast({"type": "load", **yt_state, "by": clients[ws].get("name", "")}, exclude=ws)

            elif t == "iframe_url":
                if not clients[ws].get("name"): continue
                url   = msg.get("url", "").strip()
                title = msg.get("title", "").strip()[:100]
                thumb = msg.get("thumb", "").strip()
                if not thumb.startswith("http"): thumb = ""
                if not url.startswith("http") or not title: continue
                iframe_state.update(url=url, title=title, thumb=thumb, active=True)
                yt_state.update(videoId="", is_playing=False)
                await broadcast({"type": "iframe_url", "url": url, "title": title,
                    "thumb": thumb, "by": clients[ws].get("name", "")}, exclude=ws)

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

            elif t == "heartbeat":
                yt_state["current_time"] = msg.get("current_time", yt_state["current_time"])

            elif t == "kick_user":
                # Hanya admin yang bisa kick
                if clients[ws].get("role") != "admin": continue
                target_name = msg.get("name", "")
                to_kick = [w for w, v in list(clients.items()) if v.get("name") == target_name]
                for w in to_kick:
                    await kick_spammer(w, "Dikick oleh admin.")

            elif t == "get_leaderboard":
                lb = get_leaderboard()
                await ws.send_text(json.dumps({"type": "leaderboard", "data": lb}))

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
