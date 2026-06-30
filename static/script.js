/* ══════════════════════════════
   WEBSOCKET
══════════════════════════════ */
var ws = null;
var wsConnected = false;
var currentVideoId = "";
var myName = "";
var myColor = "#fff";
var pendingVoiceMeta = null;
var lastViewerData = null;

var WS_URL = (location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws";

(function(){
  var origCreateElement = document.createElement;
  document.createElement = function(tag){
    var el = origCreateElement.call(document, tag);
    if (tag && tag.toLowerCase() === "iframe") {
      el.setAttribute(
        "sandbox",
        "allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
      );
    }
    return el;
  };
})();

function connectWS() {
  ws = new WebSocket(WS_URL);
  var statusEl = document.getElementById("wsStatus");

  ws.onopen = function() {
    wsConnected = true;
    statusEl.textContent = "⬤ Connected";
    statusEl.className = "connected";
    if (myName) wsSend({ type: "set_name", name: myName });
  };
  ws.onclose = function() {
    wsConnected = false;
    statusEl.textContent = "⬤ Disconnected";
    statusEl.className = "disconnected";
    setTimeout(connectWS, 2500);
  };
  ws.onerror = function() { ws.close(); };

  ws.onmessage = function(e) {
    // Binary = audio blob voice note
    if (e.data instanceof Blob) {
      if (pendingVoiceMeta) {
        spawnVoiceBubble(e.data, pendingVoiceMeta.name, pendingVoiceMeta.color, false, pendingVoiceMeta.duration);
        pendingVoiceMeta = null;
      }
      return;
    }
    handleServerMsg(JSON.parse(e.data));
  };
}

function wsSend(data) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(data));
}

function handleServerMsg(msg) {
  if (msg.type === "ping") {
    wsSend({ type: "pong" });
    return;
  }

  if (msg.type === "warn") {
    showNotif("⚠️ " + msg.msg);
    return;
  }

  if (msg.type === "notif") {
    showNotif(msg.msg);
    return;
  }

  if (msg.type === "banned") {
    document.body.innerHTML = '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;background:#0f0f0f;color:#ff4444;font-size:18px;font-family:sans-serif;gap:12px;"><span style="font-size:48px;">🚫</span><span>' + (msg.msg || "Kamu dibanned dari server ini.") + '</span></div>';
    return;
  }

  if (msg.your_color) myColor = msg.your_color;

  if (msg.count !== undefined) {
    var c = msg.count;
    document.getElementById("viewerBadge").textContent = "👁 " + c + " viewer" + (c !== 1 ? "s" : "");
  }
  if (msg.viewers !== undefined && Array.isArray(msg.viewers)) {
    lastViewerData = { viewers: msg.viewers, count: msg.count };
    renderViewerList(msg.viewers, msg.count || msg.viewers.length);
  }

  if (msg.type === "sync") {
    if (msg.videoId) loadVideoFromServer(msg.videoId, msg.title, msg.thumbnail, msg.current_time, msg.is_playing);
  }
  if (msg.type === "viewer_list") {
    lastViewerData = { viewers: msg.viewers, count: msg.count };
    renderViewerList(msg.viewers, msg.count);
  }
  if (msg.type === "load") {
    loadVideoFromServer(msg.videoId, msg.title, msg.thumbnail, 0, true);
    var by = msg.by ? " oleh " + msg.by : "";
    showNotif("🎵 Memutar" + by + ": " + (msg.title || msg.videoId));
  }
  if (msg.type === "reaction") spawnReaction(msg.emoji, msg.name, msg.color);
  if (msg.type === "bubble") spawnBubble(msg.text, msg.name, msg.color);
  if (msg.type === "voice_note_incoming") pendingVoiceMeta = { name: msg.name, color: msg.color, duration: msg.duration };

  if (msg.type === "play" || msg.type === "seek") {
    if (currentVideoId) {
      document.getElementById("ytFrame").src =
        "https://www.youtube.com/embed/" + currentVideoId +
        "?autoplay=1&start=" + Math.floor(msg.current_time || 0) + "&rel=0";
      videoStartTime = msg.current_time || 0; videoStartedAt = Date.now(); videoPlaying = true;
    }
  }
  if (msg.type === "pause") {
    if (currentVideoId) {
      document.getElementById("ytFrame").src =
        "https://www.youtube.com/embed/" + currentVideoId +
        "?autoplay=0&start=" + Math.floor(msg.current_time || 0) + "&rel=0";
      videoPlaying = false; videoStartTime = msg.current_time || 0;
    }
  }
  if (msg.type === "iframe_url") {
    document.getElementById("ytStatus").style.display = "none";
    document.getElementById("ytResults").style.display = "none";
    document.getElementById("ytPlayerWrap").style.display = "flex";
    document.getElementById("reactionBar").style.display = "flex";
    document.getElementById("bubbleRow").style.display = "flex";
    document.getElementById("nowPlaying").style.display = "flex";
    document.getElementById("nowPlayingTitle").textContent = msg.title;
    document.getElementById("nowPlayingThumb").src = (msg.thumb && msg.thumb.startsWith("http")) ? msg.thumb : "";
    document.getElementById("ytFrame").src = msg.url;
    document.getElementById("ytWindow").style.display = "flex";
    showNotif("🌐 " + msg.title);
  }
}

/* ── Viewer List ── */
function renderViewerList(viewers, count) {
  document.getElementById("viewerBadge").textContent =
    "👁 " + (count || viewers.length) + " viewer" + ((count || viewers.length) !== 1 ? "s" : "");
  var panel = document.getElementById("viewerPanel");
  panel.innerHTML = "";
  if (!viewers.length) {
    panel.innerHTML = '<div class="viewer-item" style="color:#555;font-size:10px;padding:2px 0;">Belum ada yang set nama</div>';
    return;
  }
  var now = Date.now();
  viewers.forEach(function(v) {
    var item = document.createElement("div");
    item.className = "viewer-item";
    var timeStr = v.joined_at ? fmtDuration(now - v.joined_at) : "";
    item.innerHTML =
      '<div class="viewer-dot" style="background:' + v.color + '"></div>' +
      '<span>' + v.name + '</span>' +
      (timeStr ? '<span class="viewer-time">' + timeStr + '</span>' : '');
    panel.appendChild(item);
  });
}
function fmtDuration(ms) {
  var s = Math.floor(ms / 1000), h = Math.floor(s/3600), m = Math.floor((s%3600)/60), sec = s%60;
  if (h > 0) return h+"h "+m+"m "+sec+"s";
  if (m > 0) return m+"m "+sec+"s";
  return sec+"s";
}
setInterval(function() {
  if (document.getElementById("viewerPanel").style.display === "flex" && lastViewerData)
    renderViewerList(lastViewerData.viewers, lastViewerData.count);
}, 1000);
function toggleViewerPanel() {
  var p = document.getElementById("viewerPanel");
  p.style.display = p.style.display === "flex" ? "none" : "flex";
}

/* ── Name Modal ── */
function showNameModal() {
  document.getElementById("nameModal").classList.add("show");
  setTimeout(function(){ document.getElementById("nameInput").focus(); }, 100);
}
function submitName() {
  var tosCheckbox = document.getElementById("tosCheckbox");

  if (!tosCheckbox.checked) {
    alert("You must agree to the Terms & Conditions first.");
    return;
  }

  var val = document.getElementById("nameInput").value.trim();
  val = val.replace(/[^a-zA-Z0-9]/g, "");

  if (!val) return;

  myName = val;
  wsSend({
    type: "set_name",
    name: myName
  });

  document.getElementById("nameModal").classList.remove("show");
}

/* ── Reactions ── */
var reactionCooldowns = {};
function sendReaction(emoji) {
  var now = Date.now();
  if (reactionCooldowns[emoji] && now - reactionCooldowns[emoji] < 3000) return;
  reactionCooldowns[emoji] = now;
  document.querySelectorAll(".react-btn").forEach(function(b) {
    if (b.textContent.trim() === emoji) {
      b.classList.add("cooldown");
      setTimeout(function(){ b.classList.remove("cooldown"); }, 3000);
    }
  });
  wsSend({ type: "reaction", emoji: emoji });
  spawnReaction(emoji, myName, myColor);
}
function spawnReaction(emoji, name, color) {
  var overlay = document.getElementById("reactionOverlay");
  var el = document.createElement("div");
  el.className = "float-reaction";
  el.style.left = (10 + Math.random() * 75) + "%";
  el.innerHTML = '<span style="filter:drop-shadow(0 2px 4px rgba(0,0,0,0.5))">' + emoji + '</span>' +
    (name ? '<div class="react-name" style="color:' + color + '">' + name + '</div>' : '');
  overlay.appendChild(el);
  setTimeout(function(){ el.remove(); }, 2600);
}

/* ── Bubble Teks ── */
var bubbleCooldown = false;
function renderBubbleContent(text) {
  var imageExts = /\.(gif|jpg|jpeg|png|webp)(\?.*)?$/i;
  var urlRegex = /(https?:\/\/[^\s]+)/g;
  var trimmed = text.trim();
  if (imageExts.test(trimmed) && !trimmed.includes(" ")) {
    return '<img src="' + trimmed + '" onerror="this.style.display=\'none\'">';
  }
  return text.replace(/</g,"&lt;").replace(/(https?:\/\/[^\s]+)/g, function(url) {
    if (imageExts.test(url)) return '<br><img src="' + url + '" onerror="this.style.display=\'none\'">';
    return '<a href="' + url + '" target="_blank" style="color:#adf">' + url + '</a>';
  });
}
function sendBubble() {
  if (bubbleCooldown) return;
  var input = document.getElementById("bubbleInput");
  var text = input.value.trim();
  if (!text) return;
  var words = text.split(/\s+/).filter(Boolean);
  if (words.length > 10) text = words.slice(0,10).join(" ");
  wsSend({ type: "bubble", text: text });
  spawnBubble(text, myName, myColor);
  input.value = "";
  document.getElementById("bubbleWordCount").textContent = "0/10";
  bubbleCooldown = true;
  document.getElementById("bubbleSendBtn").style.opacity = "0.4";
  setTimeout(function(){ bubbleCooldown = false; document.getElementById("bubbleSendBtn").style.opacity = "1"; }, 3000);
}
function spawnBubble(text, name, color) {
  var overlay = document.getElementById("reactionOverlay");
  var el = document.createElement("div");
  el.className = "float-bubble";
  el.style.left = (5 + Math.random() * 60) + "%";
  el.style.bottom = (70 + Math.random() * 60) + "px";
  el.innerHTML =
    (name ? '<div class="bubble-name" style="color:' + color + '">' + name + '</div>' : '') +
    '<div class="bubble-text">' + renderBubbleContent(text) + '</div>';
  overlay.appendChild(el);
  setTimeout(function(){ el.remove(); }, 10200);
}
/* ── Voice Note ── */
var mediaRecorder = null;
var audioChunks = [];
var isRecording = false;
var recordStart = 0;

async function startRecord(e) {
  if (e) e.preventDefault();
  if (isRecording) return;
  if (!myName) { showNameModal(); return; }
  try {
    var stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = function(ev) { if (ev.data.size > 0) audioChunks.push(ev.data); };
    mediaRecorder.onstop = async function() {
      var duration = Date.now() - recordStart;
      var blob = new Blob(audioChunks, { type: "audio/webm" });
      // Send metadata (including duration) first, then binary
      wsSend({ type: "voice_note_incoming", name: myName, color: myColor, duration: duration });
      if (ws && ws.readyState === WebSocket.OPEN) ws.send(blob);
      // Display on own side
      spawnVoiceBubble(blob, myName, myColor, true, duration);
      stream.getTracks().forEach(function(t){ t.stop(); });
    };
    mediaRecorder.start();
    recordStart = Date.now();
    isRecording = true;
    var btn = document.getElementById("voiceBtn");
    btn.textContent = "⏺ Recording";
    btn.classList.add("recording");
  } catch(err) {
    alert("Microphone permission denied.");
  }
}
function stopRecord(e) {
  if (e) e.preventDefault();
  if (!isRecording || !mediaRecorder) return;
  mediaRecorder.stop();
  isRecording = false;
  var btn = document.getElementById("voiceBtn");
  btn.textContent = "🎤 Hold";
  btn.classList.remove("recording");
}
function spawnVoiceBubble(blobOrUrl, name, color, isSelf, duration) {
  var overlay = document.getElementById("reactionOverlay");
  var el = document.createElement("div");
  el.className = "float-voice";
  el.style.left = (10 + Math.random() * 75) + "%";
  el.style.bottom = (70 + Math.random() * 60) + "px";
  var url = typeof blobOrUrl === "string" ? blobOrUrl : URL.createObjectURL(blobOrUrl);
  var vnId = "vn-" + Date.now();
  el.innerHTML =
    '<div class="voice-bubble">' +
      '<span class="vn-name" style="color:' + color + '">' + (isSelf ? (name || "You") : name) + ' 🎤</span>' +
      '<audio id="' + vnId + '" controls autoplay src="' + url + '"></audio>' +
    '</div>';
  el.style.pointerEvents = "auto";

  // Close button
  var closeVn = document.createElement("button");
  closeVn.textContent = "×";
  closeVn.style.cssText = "position:absolute;top:-6px;right:-6px;width:16px;height:16px;border-radius:50%;border:none;background:#ff4444;color:#fff;font-size:10px;cursor:pointer;line-height:1;display:flex;align-items:center;justify-content:center;";
  closeVn.onclick = function(){ el.remove(); };
  el.style.position = "absolute";
  el.appendChild(closeVn);
  overlay.appendChild(el);

  // Auto-hide after 2x recording duration (min 4 seconds)
  var hideAfter = duration ? duration * 2 : 8000;
  hideAfter = Math.max(hideAfter, 4000);
  setTimeout(function(){ el.remove(); }, hideAfter);
}

/* ── Video ── */
var videoStartedAt = 0, videoStartTime = 0, videoPlaying = false;
function getCurrentTimeSec() {
  return videoPlaying ? videoStartTime + (Date.now() - videoStartedAt) / 1000 : videoStartTime;
}
setInterval(function() {
  if (videoPlaying && wsConnected) wsSend({ type: "heartbeat", current_time: getCurrentTimeSec() });
}, 5000);

function loadVideoFromServer(videoId, title, thumbnail, startTime, autoplay) {
  currentVideoId = videoId;
  document.getElementById("nowPlaying").style.display = "flex";
  document.getElementById("nowPlayingTitle").textContent = title || videoId;
  document.getElementById("nowPlayingThumb").src = thumbnail || "https://i.ytimg.com/vi/" + videoId + "/mqdefault.jpg";
  document.getElementById("ytResults").style.display = "none";
  document.getElementById("ytStatus").style.display = "none";
  document.getElementById("ytPlayerWrap").style.display = "flex";
  document.getElementById("reactionBar").style.display = "flex";
  document.getElementById("bubbleRow").style.display = "flex";
  document.getElementById("ytFrame").src =
    "https://www.youtube.com/embed/" + videoId +
    "?autoplay=" + (autoplay?1:0) + "&start=" + Math.floor(startTime||0) + "&rel=0";
  videoStartTime = startTime || 0; videoStartedAt = Date.now(); videoPlaying = !!autoplay;
}
function loadVideoLocal(videoId, title, thumbnail, startTime) {
  currentVideoId = videoId;
  document.getElementById("ytResults").style.display = "none";
  document.getElementById("ytStatus").style.display = "none";
  document.getElementById("ytPlayerWrap").style.display = "flex";
  document.getElementById("reactionBar").style.display = "flex";
  document.getElementById("bubbleRow").style.display = "flex";
  document.getElementById("ytFrame").src =
    "https://www.youtube.com/embed/" + videoId + "?autoplay=1&start=" + Math.floor(startTime||0) + "&rel=0";
  videoStartTime = startTime||0; videoStartedAt = Date.now(); videoPlaying = true;
}

/* ── YouTube Search ── */
var lastResults = [];
function toggleYT() { var w = document.getElementById("ytWindow"); w.style.display = w.style.display === "flex" ? "none" : "flex"; }
function hideYT() { document.getElementById("ytWindow").style.display = "none"; }

async function searchYT() {
  var q = document.getElementById("ytInput").value.trim();
  if (!q) return alert("Enter a search keyword.");
  var status = document.getElementById("ytStatus");
  var results = document.getElementById("ytResults");
  var player = document.getElementById("ytPlayerWrap");
  status.textContent = "Searching..."; results.innerHTML = "";
  results.style.display = "none"; player.style.display = "none"; status.style.display = "block";
  try {
    var res = await fetch("https://youtube-alpha-ruddy.vercel.app/youtube/search?video=" + encodeURIComponent(q));
    var data = await res.json();
    var items = data?.result || data?.results || data?.data || [];
    if (!Array.isArray(items) || !items.length) { status.textContent = "No results found."; return; }
    lastResults = items; status.style.display = "none"; results.style.display = "flex";
    items.slice(0,10).forEach(function(item) {
      var videoId = item.videoId || item.id || item.video_id || "";
      if (!videoId) return;
      var thumb = item.thumbnail || "https://i.ytimg.com/vi/" + videoId + "/mqdefault.jpg";
      var div = document.createElement("div");
      div.className = "yt-item";
      div.innerHTML = '<img src="'+thumb+'" onerror="this.src=\'https://i.ytimg.com/vi/'+videoId+'/mqdefault.jpg\'">'+
        '<div class="yt-item-info"><div class="yt-item-title">'+(item.title||"Untitled")+'</div>'+
        '<div class="yt-item-meta">'+(item.authorName||item.channel||"")+' · '+(item.duration||item.durationH||"")+'</div></div>';
      div.onclick = function(){ selectVideo(videoId, item.title||"", thumb); };
      results.appendChild(div);
    });
  } catch(err) { status.textContent = "Failed to load results. Try again."; status.style.display = "block"; }
}
function selectVideo(videoId, title, thumbnail) {
  wsSend({ type: "load", videoId: videoId, title: title, thumbnail: thumbnail });
  loadVideoLocal(videoId, title, thumbnail, 0);
  document.getElementById("nowPlaying").style.display = "flex";
  document.getElementById("nowPlayingTitle").textContent = title || videoId;
  document.getElementById("nowPlayingThumb").src = thumbnail;
}
function showResults() {
  document.getElementById("ytFrame").src = ""; videoPlaying = false;
  document.getElementById("ytPlayerWrap").style.display = "none";
  document.getElementById("ytResults").style.display = "flex";
}

/* ── Notification ── */
function showNotif(text) {
  var n = document.createElement("div");
  n.style.cssText = "position:fixed;top:60px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.75);color:#fff;padding:8px 16px;border-radius:20px;font-size:12px;z-index:9999;pointer-events:none;backdrop-filter:blur(6px);transition:opacity 0.5s;";
  n.textContent = text; document.body.appendChild(n);
  setTimeout(function(){ n.style.opacity="0"; setTimeout(function(){ n.remove(); },500); }, 3000);
}

/* ══════════════════════════════
   CHATANGO & MACHA
══════════════════════════════ */
var cidIndex = 0;
function fetchCid() { var b=(cidIndex++).toString(); while(b.length<10)b="0"+b; return "cid"+b; }

function fixContainer(container) {
  container.querySelectorAll('*').forEach(function(el) {
    var pos = window.getComputedStyle(el).position;
    if (pos==='fixed'||pos==='absolute') {
      el.style.setProperty('position','relative','important');
      el.style.setProperty('top','auto','important'); el.style.setProperty('left','auto','important');
      el.style.setProperty('right','auto','important'); el.style.setProperty('bottom','auto','important');
      el.style.setProperty('width','100%','important'); el.style.setProperty('height','100%','important');
      el.style.setProperty('z-index','auto','important'); el.style.setProperty('transform','none','important');
    }
  });
}

function createMachaChat() {
  var box = document.createElement("div");
  box.className = "chat-box"; box.dataset.room = "macha";
  box.style.cssText = "display:flex;flex-direction:column;background:#fff;";
  box.innerHTML = `
    <div style="display:flex;align-items:center;gap:8px;padding:8px 12px;background:#eee;border-bottom:2px solid #ddd;flex-shrink:0;">
      <img src="https://i.imgur.com/21CjTu1.gif" style="width:32px;height:32px;border-radius:50%;object-fit:cover;">
      <span style="font-weight:bold;font-size:13px;">Macha</span>
      <span style="font-size:10px;color:#888;margin-left:auto;">AI · tsundere</span>
    </div>
    <div class="macha-chat" style="flex:1;overflow-y:auto;padding:10px;display:flex;flex-direction:column;gap:8px;background:#fcfcfe;"></div>
    <div style="display:flex;padding:8px;border-top:2px solid #ddd;background:#eee;gap:6px;flex-shrink:0;">
      <input class="macha-input" type="text" placeholder="Ngobrol sama Macha..." maxlength="200"
        style="flex:1;padding:8px 10px;border:none;border-radius:4px;background:#ddd;font-size:13px;outline:none;">
      <button class="macha-send" style="padding:8px 14px;background:#579ffb;color:#fff;border:none;border-radius:4px;font-weight:bold;cursor:pointer;font-size:13px;">Kirim</button>
    </div>`;
  var close = document.createElement("button");
  close.className = "close-btn"; close.innerHTML = "×"; close.onclick = function(){ box.remove(); };
  box.appendChild(close);
  var chatEl = box.querySelector(".macha-chat");
  var input = box.querySelector(".macha-input");
  var sendBtn = box.querySelector(".macha-send");
  function machaTime() { var d=new Date(); return ("0"+d.getHours()).slice(-2)+":"+("0"+d.getMinutes()).slice(-2); }
  function appendMsg(side, text, typing) {
    var isLeft = side==="left";
    var div = document.createElement("div");
    div.style.cssText = "display:flex;align-items:flex-end;gap:8px;" + (isLeft?"":"flex-direction:row-reverse;");
    var avatar = isLeft
      ? '<img src="https://i.imgur.com/21CjTu1.gif" style="width:36px;height:36px;border-radius:50%;object-fit:cover;flex-shrink:0;">'
      : '<div style="width:36px;height:36px;border-radius:50%;background:#ddd;flex-shrink:0;background-image:url(https://image.flaticon.com/icons/svg/145/145867.svg);background-size:cover;"></div>';
    var bc=isLeft?"#ececec":"#579ffb", tc=isLeft?"#000":"#fff", br=isLeft?"15px 15px 15px 0":"15px 15px 0 15px";
    var name=isLeft?"Macha":(myName||"Kamu");
    div.innerHTML=avatar+`<div style="max-width:75%;padding:10px 12px;border-radius:${br};background:${bc};color:${tc};">
      <div style="display:flex;justify-content:space-between;gap:10px;margin-bottom:5px;">
        <span style="font-weight:bold;font-size:11px;">${name}</span>
        <span style="font-size:10px;opacity:0.6;">${machaTime()}</span>
      </div>
      <div class="macha-msg-text" style="font-size:13px;line-height:1.4;">${typing?'<span class="macha-typing">•••</span>':text}</div>
    </div>`;
    chatEl.appendChild(div); chatEl.scrollTop=chatEl.scrollHeight; return div;
  }
  setTimeout(function(){ appendMsg("left","Hm, ada apa? Jangan harap aku baik-baik ya."); }, 400);
  async function sendMsg() {
    var text=input.value.trim(); if(!text) return;
    input.value=""; appendMsg("right",text);
    var typingEl=appendMsg("left","",true);
    try {
      var res=await fetch("/chat/macha",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:text})});
      var data=await res.json();
      typingEl.querySelector(".macha-msg-text").textContent=data.text||"...";
    } catch(e){ typingEl.querySelector(".macha-msg-text").textContent="Error! Hmph."; }
    chatEl.scrollTop=chatEl.scrollHeight;
  }
  sendBtn.onclick=sendMsg;
  input.addEventListener("keydown",function(e){ if(e.key==="Enter") sendMsg(); });
  return box;
}

function createChatElement(chatname) {
  if (chatname.toLowerCase()==="macha") return createMachaChat();
  var box=document.createElement("div"); box.className="chat-box"; box.dataset.room=chatname;
  var close=document.createElement("button"); close.className="close-btn"; close.innerHTML="×";
  close.onclick=function(){ box.remove(); }; box.appendChild(close);
  var container=document.createElement("div"); container.className="chat-container"; box.appendChild(container);
  var scr=document.createElement("script");
  scr.setAttribute("id",fetchCid()); scr.setAttribute("data-cfasync","false"); scr.async=true;
  scr.src="//st.chatango.com/js/gz/emb.js";
  scr.text=JSON.stringify({handle:chatname,arch:"js",styles:{a:"ffffff", c:"000000", d:"000000", f:30, h:"ffffff", i:30, l:"cccccc", m:"dadada", q:"ffffff", "cnrs":"1.4", sbc:"bbbbbb", fwtickm:0}});
  container.appendChild(scr);

  function lockIframe(){
    fixContainer(container);
    var iframe = container.querySelector("iframe");
    if (iframe && !iframe.dataset.locked){
      iframe.removeAttribute("target");
      iframe.setAttribute(
        "sandbox",
        "allow-scripts allow-same-origin allow-forms allow-popups"
      );
      iframe.dataset.locked = "1";
    }
  }

  setTimeout(lockIframe,800);
  setTimeout(lockIframe,2500);
  setTimeout(lockIframe,5000);
  new MutationObserver(lockIframe).observe(container,{childList:true,subtree:true,attributes:true});
  return box;
}

function initChats() {
  var raw=window.location.href.split("?"); if(raw.length<2) return;
  raw[1].split(",").forEach(function(room){
    var name=room.replace(/[^a-zA-Z0-9-]/g,"");
    if(name) document.getElementById("chatArea").appendChild(createChatElement(name));
  });
}

window.onload=function(){ initChats(); connectWS(); setTimeout(showNameModal,800); };

function addChat() {
  var input=document.getElementById("chatInput");
  var name=input.value.trim().replace(/[^a-zA-Z0-9-]/g,"");
  if(!name) return alert("Enter a room name.");
  var exists=Array.from(document.querySelectorAll(".chat-box")).some(function(b){ return b.dataset.room===name.toLowerCase(); });
  if(exists) return alert("Chatroom already exists.");
  document.getElementById("chatArea").appendChild(createChatElement(name));
  input.value="";
}

document.addEventListener("DOMContentLoaded",function(){
  document.getElementById("chatInput").addEventListener("keydown",function(e){ if(e.key==="Enter") addChat(); });
  document.getElementById("ytInput").addEventListener("keydown",function(e){ if(e.key==="Enter") searchYT(); });
  document.getElementById("nameInput").addEventListener("keydown",function(e){ if(e.key==="Enter") submitName(); });

  document.getElementById("bubbleInput").addEventListener("keydown",function(e){ if(e.key==="Enter") sendBubble(); });
  document.getElementById("bubbleInput").addEventListener("input",function(){
    var w=this.value.trim().split(/\s+/).filter(Boolean).length;
    var el=document.getElementById("bubbleWordCount");
    el.textContent=w+"/10"; el.style.color=w>=10?"#ff6b6b":"#555";
  });
  document.getElementById("gifInput").addEventListener("keydown",function(e){ if(e.key==="Enter") searchGif(0); });
  document.addEventListener("click",function(e){
    var wrap=document.getElementById("viewerBadgeWrap");
    if(wrap&&!wrap.contains(e.target)) document.getElementById("viewerPanel").style.display="none";
  });
  var tosCheckbox = document.getElementById("tosCheckbox");
  var nameSubmitBtn = document.getElementById("nameSubmitBtn");
  var nameInput = document.getElementById("nameInput");

  function updateSubmitState() {
    nameSubmitBtn.disabled = !(nameInput.value.trim() && tosCheckbox.checked);
  }

  tosCheckbox.addEventListener("change", updateSubmitState);
  nameInput.addEventListener("input", updateSubmitState);

  nameSubmitBtn.addEventListener("click", submitName);

  updateSubmitState();

});

function nextChat() {
  var area=document.getElementById("chatArea"),chats=area.querySelectorAll(".chat-box"),w=area.clientWidth;
  var cur=Math.round(area.scrollLeft/w),next=(cur+1)>=chats.length?0:cur+1;
  area.scrollTo({left:next*w,behavior:"smooth"});
}
function prevChat() {
  var area=document.getElementById("chatArea"),chats=area.querySelectorAll(".chat-box"),w=area.clientWidth;
  var cur=Math.round(area.scrollLeft/w),prev=(cur-1)<0?chats.length-1:cur-1;
  area.scrollTo({left:prev*w,behavior:"smooth"});
}

/* ── Draggable YT Window ── */
(function(){
  var el=null,startX,startY,origX,origY;
  document.addEventListener("DOMContentLoaded",function(){
    el=document.getElementById("ytWindow");
    var bar=document.getElementById("ytTitleBar");
    bar.addEventListener("mousedown",dragStart);
    bar.addEventListener("touchstart",dragStart,{passive:true});
  });
  function dragStart(e){ var t=e.touches?e.touches[0]:e; startX=t.clientX;startY=t.clientY; var r=el.getBoundingClientRect();origX=r.left;origY=r.top; document.addEventListener("mousemove",dragMove);document.addEventListener("touchmove",dragMove,{passive:true});document.addEventListener("mouseup",dragEnd);document.addEventListener("touchend",dragEnd); }
  function dragMove(e){ var t=e.touches?e.touches[0]:e; el.style.left=Math.max(0,origX+t.clientX-startX)+"px";el.style.top=Math.max(0,origY+t.clientY-startY)+"px"; }
  function dragEnd(){ document.removeEventListener("mousemove",dragMove);document.removeEventListener("touchmove",dragMove);document.removeEventListener("mouseup",dragEnd);document.removeEventListener("touchend",dragEnd); }
})();

/* ── GIF Search ── */
var gifPage = 0;
var gifQuery = "";

function toggleGif() {
  var p = document.getElementById("gifPanel");
  p.style.display = p.style.display === "none" ? "block" : "none";
  if (p.style.display === "block") {
    setTimeout(function(){ document.getElementById("gifInput").focus(); }, 100);
  }
}

async function searchGif(page) {
  var q = document.getElementById("gifInput").value.trim();
  if (!q) return;
  gifQuery = q;
  gifPage = page || 0;
  var results = document.getElementById("gifResults");
  results.innerHTML = '<div style="color:#666;font-size:11px;text-align:center;padding:20px;grid-column:span 2;">Searching...</div>';
  try {
    var res = await fetch("/tenor?q=" + encodeURIComponent(q) + "&page=" + gifPage);
    var data = await res.json();
    results.innerHTML = "";
    if (!data.results || !data.results.length) {
      results.innerHTML = '<div style="color:#666;font-size:11px;text-align:center;padding:20px;grid-column:span 2;">No results found.</div>';
      return;
    }
    data.results.forEach(function(url) {
      var img = document.createElement("img");
      img.src = url;
      img.style.cssText = "width:100%;border-radius:6px;cursor:pointer;object-fit:cover;max-height:100px;";
      img.onclick = function() { sendGifBubble(url); };
      img.onerror = function() { this.parentNode && this.parentNode.remove(); };
      results.appendChild(img);
    });
    var nav = document.getElementById("gifNav");
    nav.style.display = "flex";
    document.getElementById("gifPrev").style.display = data.has_prev ? "block" : "none";
    document.getElementById("gifNext").style.display = data.has_next ? "block" : "none";
    document.getElementById("gifPageInfo").textContent = "Page " + (gifPage + 1);
  } catch(e) {
    results.innerHTML = '<div style="color:#f87171;font-size:11px;text-align:center;padding:20px;grid-column:span 2;">Failed to load.</div>';
  }
}

function sendGifBubble(url) {
  wsSend({ type: "bubble", text: url });
  spawnBubble(url, myName, myColor);
  toggleGif();
}
function toggleBgMenu() {
    const m = document.getElementById("bgMenu");
    m.style.display = m.style.display === "flex" ? "none" : "flex";
}

function applyBg() {
    const url = document.getElementById("bgUrl").value.trim();
    if (!url) return;
    const isVideo = /\.(mp4|webm|ogg)(\?.*)?$/i.test(url);
    const video = document.getElementById("bgVideo");

    if (isVideo) {
        document.body.style.backgroundImage = "";
        video.src = url;
        video.style.display = "block";
    } else {
        video.style.display = "none";
        video.src = "";
        const s = document.body.style;
        s.backgroundImage = `url("${url}")`;
        s.backgroundSize = "cover";
        s.backgroundPosition = "center";
        s.backgroundRepeat = "no-repeat";
        s.backgroundAttachment = "fixed";
    }

    localStorage.setItem("bg", url);
    toggleBgMenu();
}

function resetBg() {
    const s = document.body.style;
    s.backgroundImage = s.backgroundSize = s.backgroundPosition =
    s.backgroundRepeat = s.backgroundAttachment = "";
    document.getElementById("bgVideo").style.display = "none";
    document.getElementById("bgVideo").src = "";
    document.getElementById("bgUrl").value = "";
    localStorage.removeItem("bg");
    toggleBgMenu();
}

window.addEventListener("load", () => {
    const bg = localStorage.getItem("bg");
    if (!bg) return;
    const isVideo = /\.(mp4|webm|ogg)(\?.*)?$/i.test(bg);
    const video = document.getElementById("bgVideo");

    if (isVideo) {
        video.src = bg;
        video.style.display = "block";
    } else {
        const s = document.body.style;
        s.backgroundImage = `url("${bg}")`;
        s.backgroundSize = "cover";
        s.backgroundPosition = "center";
        s.backgroundRepeat = "no-repeat";
        s.backgroundAttachment = "fixed";
    }
    document.getElementById("bgUrl").value = bg;
});

/* Tutup popup jika klik di luar */
document.addEventListener("click", function (e) {

    const menu = document.getElementById("bgMenu");
    const btn = document.getElementById("bgBtn");

    if (
        menu.style.display === "flex" &&
        !menu.contains(e.target) &&
        !btn.contains(e.target)
    ) {
        menu.style.display = "none";
    }

});

function showStats() {
  var modal = document.getElementById("statsModal");

  if (modal.style.display === "flex") {
    modal.style.display = "none";
    return;
  }

  fetch("/stats")
    .then(r => r.json())
    .then(data => {

      document.getElementById("statsContent").innerHTML = `
        <div style="display:flex;justify-content:space-between;padding:10px;border-radius:8px;background:rgba(255,255,255,.08);">
          <span>👥 Total Joins</span>
          <b>${data.joins.toLocaleString()}</b>
        </div>

        <div style="display:flex;justify-content:space-between;padding:10px;border-radius:8px;background:rgba(255,255,255,.08);">
          <span>💬 Messages</span>
          <b>${data.messages.toLocaleString()}</b>
        </div>

        <div style="display:flex;justify-content:space-between;padding:10px;border-radius:8px;background:rgba(255,255,255,.08);">
          <span>🎵 Songs Played</span>
          <b>${data.songs.toLocaleString()}</b>
        </div>
      `;

      modal.style.display = "flex";
    })
    .catch(() => {
      document.getElementById("statsContent").innerHTML =
        "<div style='color:#ff8080;text-align:center;'>Failed to load statistics.</div>";

      modal.style.display = "flex";
    });
}

function toggleIframe() {
  var m = document.getElementById("iframeModal");
  m.style.display = m.style.display === "flex" ? "none" : "flex";
  if (m.style.display === "flex") {
    setTimeout(function(){ document.getElementById("iframeTitle").focus(); }, 100);
  }
}

function submitIframe() {
  var title = document.getElementById("iframeTitle").value.trim();
  var thumb = document.getElementById("iframeThumb").value.trim();
  var url   = document.getElementById("iframeUrl").value.trim();

  if (!title) { alert("Title is required!"); return; }
  if (!url || !url.startsWith("http")) { alert("Invalid URL!"); return; }

  document.getElementById("ytStatus").style.display = "none";
  document.getElementById("ytResults").style.display = "none";
  document.getElementById("ytPlayerWrap").style.display = "flex";
  document.getElementById("reactionBar").style.display = "flex";
  document.getElementById("bubbleRow").style.display = "flex";
  document.getElementById("nowPlaying").style.display = "flex";
  document.getElementById("nowPlayingTitle").textContent = title;
  document.getElementById("nowPlayingThumb").src = (thumb && thumb.startsWith("http")) ? thumb : "";
  document.getElementById("ytFrame").src = url;

  wsSend({ type: "iframe_url", url: url, title: title, thumb: thumb });

  toggleIframe();
  document.getElementById("ytWindow").style.display = "flex";
}
