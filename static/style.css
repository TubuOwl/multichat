* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  width: 100%; min-height: 100vh;
  font-family: Arial, sans-serif;
  background-image: url("https://png.pngtree.com/background/20230616/original/pngtree-anime-tree-picture-image_3629955.jpg");
  background-size: cover; background-position: center;
  background-repeat: no-repeat; background-attachment: scroll;
}

#toolbar {
  width: 100%; display: flex; align-items: center; gap: 8px;
  padding: 10px 14px;
  background: rgba(255,255,255,0.25); backdrop-filter: blur(6px);
  border-bottom: 1px solid rgba(255,255,255,0.3); flex-wrap: wrap;
}
.tool-icon-btn {
  width: 38px; height: 38px; border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.5);
  background: rgba(255,255,255,0.35); font-size: 18px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  backdrop-filter: blur(2px); box-shadow: 0 2px 6px rgba(0,0,0,0.15);
  transition: background 0.2s; flex-shrink: 0;
}
.tool-icon-btn:hover { background: rgba(255,255,255,0.6); }
#chatInput {
  flex: 1; min-width: 120px; padding: 7px 10px; font-size: 13px;
  border-radius: 6px; border: 1px solid rgba(255,255,255,0.6);
  background: rgba(255,255,255,0.45); color: #000;
}
#addBtn {
  width: 34px; height: 34px; font-size: 20px; font-weight: bold;
  border-radius: 6px; border: none; background: rgba(0,150,255,0.8);
  color: white; cursor: pointer; flex-shrink: 0;
}

#bgBtn {
  position: fixed !important;
  left: 12px !important;
  bottom: 12px !important;
  display: flex !important;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  background: rgba(0,0,0,0.55);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  border: 1px solid rgba(255,255,255,.15);
  border-radius: 50%;
  font-size: 14px;
  cursor: pointer;
  z-index: 999 !important;
  transition: color 0.3s;
}
#bgBtn:hover { background: rgba(0,0,0,0.75); }
#bgMenu{position:fixed;left:12px;bottom:55px;width:min(260px,calc(100vw - 24px));display:none;flex-direction:column;gap:10px;padding:14px;background:rgba(20,20,20,.95);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.15);border-radius:14px;z-index:1001;box-sizing:border-box}
#bgMenu h3{color:#fff;margin:0;font-size:13px}
#bgUrl{width:100%;padding:9px;border:none;outline:none;border-radius:8px;background:rgba(255,255,255,.1);color:#fff;font-size:12px;box-sizing:border-box}
.bgButtons{display:flex;gap:8px}
.bgButtons button{flex:1;padding:9px;border:none;border-radius:8px;cursor:pointer;font-weight:bold;font-size:12px}
.bgButtons button:first-child{background:#ff6b9d;color:#fff}
.bgButtons button:last-child{background:#444;color:#fff}
#bgClose{position:absolute;top:8px;right:8px;width:24px;height:24px;border:none;border-radius:50%;background:rgba(255,255,255,.1);color:#fff;cursor:pointer;font-size:13px}

#ytWindow {
  position: fixed; top: 70px; left: 14px;
  width: 340px; height: 360px;
  border: 2px solid rgba(255,255,255,0.5); border-radius: 12px;
  background: rgba(0,0,0,0.85); backdrop-filter: blur(8px);
  z-index: 999; display: none; box-shadow: 0 6px 24px rgba(0,0,0,0.5);
  overflow: hidden; flex-direction: column;
}
#ytTitleBar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 6px 10px; background: rgba(255,255,255,0.1);
  border-bottom: 1px solid rgba(255,255,255,0.15);
  cursor: move; user-select: none; gap: 8px;
}
#ytTitleBar span { color: #fff; font-size: 12px; font-weight: bold; }
#ytCloseBtn {
  background: #ff4444; border: none; border-radius: 50%;
  width: 18px; height: 18px; color: #fff; font-size: 13px;
  cursor: pointer; line-height: 1;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}

#nowPlaying {
  display: none; align-items: center; gap: 6px; padding: 5px 10px;
  background: rgba(255,0,0,0.12); border-bottom: 1px solid rgba(255,255,255,0.08);
}
#nowPlayingThumb { width: 36px; height: 22px; object-fit: cover; border-radius: 3px; flex-shrink: 0; }
#nowPlayingTitle { color: #fff; font-size: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; }
#nowPlayingDot {
  width: 7px; height: 7px; border-radius: 50%; background: #ff4444;
  animation: pulse 1.2s infinite; flex-shrink: 0;
}
@keyframes pulse { 0%,100% { opacity:1; transform:scale(1); } 50% { opacity:0.4; transform:scale(0.7); } }

#ytSearchRow { display: flex; gap: 6px; padding: 8px 10px; background: rgba(255,255,255,0.07); }
#ytInput {
  flex: 1; padding: 5px 8px; border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.3);
  background: rgba(255,255,255,0.15); color: #fff; font-size: 12px;
}
#ytInput::placeholder { color: #aaa; }
#ytSearchBtn { padding: 5px 10px; border-radius: 6px; border: none; background: #ff0000; color: #fff; font-size: 12px; cursor: pointer; }

#ytResults { flex: 1; overflow-y: auto; padding: 6px 8px; display: flex; flex-direction: column; gap: 6px; }
#ytResults::-webkit-scrollbar { width: 4px; }
#ytResults::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 2px; }
.yt-item {
  display: flex; gap: 8px; align-items: center;
  background: rgba(255,255,255,0.08); border-radius: 6px; padding: 5px 7px;
  cursor: pointer; transition: background 0.15s;
}
.yt-item:hover { background: rgba(255,255,255,0.18); }
.yt-item img { width: 72px; height: 44px; object-fit: cover; border-radius: 4px; flex-shrink: 0; }
.yt-item-info { flex: 1; overflow: hidden; }
.yt-item-title { color: #fff; font-size: 11px; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.yt-item-meta { color: #aaa; font-size: 10px; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

#ytPlayerWrap { display: none; flex-direction: column; flex: 1; overflow: hidden; min-height: 0; }
#ytBackBtn {
  padding: 4px 10px; background: rgba(255,255,255,0.1); border: none;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  color: #ccc; font-size: 11px; cursor: pointer; text-align: left;
}
#ytBackBtn:hover { background: rgba(255,255,255,0.2); }
#ytFrame { width: 100%; border: none; flex: 1; min-height: 0; max-height: 200px; }
#ytStatus { color: #aaa; font-size: 11px; text-align: center; padding: 16px 10px; }

#reactionBar {
  display: none; gap: 2px; padding: 4px 8px;
  background: rgba(255,255,255,0.06);
  border-top: 1px solid rgba(255,255,255,0.08);
  align-items: center;
}
.react-btn {
  font-size: 16px; background: none; border: none;
  cursor: pointer; padding: 3px 5px; border-radius: 6px;
  transition: transform 0.15s, background 0.15s; line-height: 1; position: relative;
}
.react-btn:hover { background: rgba(255,255,255,0.15); transform: scale(1.25); }
.react-btn.cooldown { opacity: 0.35; pointer-events: none; }

#voiceBtn {
  font-size: 14px; background: rgba(255,255,255,0.1); border: none;
  cursor: pointer; padding: 3px 8px; border-radius: 6px;
  color: #fff; transition: background 0.15s; line-height: 1;
  margin-left: auto; white-space: nowrap; flex-shrink: 0;
  user-select: none; -webkit-user-select: none;
}
#voiceBtn:hover { background: rgba(255,255,255,0.2); }
#voiceBtn.recording { background: rgba(255,50,50,0.8); animation: recPulse 1s infinite; }
@keyframes recPulse { 0%,100% { opacity:1; } 50% { opacity:0.6; } }

#bubbleRow {
  display: none; gap: 4px; padding: 4px 8px;
  background: rgba(255,255,255,0.04);
  border-top: 1px solid rgba(255,255,255,0.06); align-items: center;
}
#bubbleInput {
  flex: 1; padding: 4px 8px; border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.2);
  background: rgba(255,255,255,0.1); color: #fff; font-size: 11px; outline: none;
}
#bubbleInput::placeholder { color: #777; }
#bubbleInput:focus { border-color: rgba(255,255,255,0.4); }
#bubbleSendBtn {
  padding: 4px 10px; border-radius: 12px; border: none;
  background: rgba(255,107,157,0.8); color: #fff;
  font-size: 11px; cursor: pointer; white-space: nowrap; flex-shrink: 0;
}
#bubbleSendBtn:hover { background: rgba(255,107,157,1); }
#bubbleWordCount { color: #666; font-size: 9px; flex-shrink: 0; }

#viewerBadgeWrap { position: relative; }
#viewerBadge {
  background: rgba(255,60,60,0.85); color: #fff; font-size: 10px; font-weight: bold;
  padding: 2px 7px; border-radius: 20px; white-space: nowrap;
  cursor: pointer; user-select: none; display: block;
}
#viewerBadge:hover { background: rgba(255,60,60,1); }
#viewerPanel {
  display: none; position: absolute; top: 100%; right: 0; z-index: 100;
  flex-direction: column; background: rgba(15,15,25,0.96);
  border: 1px solid rgba(255,255,255,0.12); border-radius: 10px;
  min-width: 180px; max-width: 220px; max-height: 200px; overflow-y: auto;
  padding: 8px 10px; gap: 5px; box-shadow: 0 6px 20px rgba(0,0,0,0.6);
}
#viewerPanel::-webkit-scrollbar { width: 3px; }
#viewerPanel::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); }
.viewer-item { display: flex; align-items: center; gap: 7px; font-size: 11px; color: #ddd; }
.viewer-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.viewer-time { color: #555; font-size: 9px; margin-left: auto; white-space: nowrap; }

#nameModal {
  display: none; position: fixed; inset: 0;
  background: rgba(0,0,0,0.6); backdrop-filter: blur(4px);
  z-index: 2000; align-items: center; justify-content: center;
}
#nameModal.show { display: flex; }
#nameBox {
  background: #1a1a2e; border: 1px solid rgba(255,255,255,0.2);
  border-radius: 14px; padding: 24px 28px;
  display: flex; flex-direction: column; gap: 14px; width: 280px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5);
}
#nameBox h3 { color: #fff; font-size: 15px; text-align: center; }
#nameBox p { color: #aaa; font-size: 11px; text-align: center; margin-top: -8px; }
#nameInput {
  padding: 9px 12px; border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.25);
  background: rgba(255,255,255,0.1); color: #fff; font-size: 13px; outline: none;
}
#nameInput:focus { border-color: #ff6b9d; }
#nameSubmitBtn {
  padding: 9px; border-radius: 8px; border: none;
  background: linear-gradient(135deg, #ff6b9d, #c084fc);
  color: #fff; font-size: 13px; font-weight: bold; cursor: pointer;
}
#nameSubmitBtn:hover { opacity: 0.9; }
#nameSubmitBtn:disabled { opacity: 0.4; cursor: not-allowed; }
#nameSubmitBtn:disabled:hover { opacity: 0.4; }

#reactionOverlay {
  position: fixed; inset: 0; pointer-events: none; z-index: 1500; overflow: hidden;
}

.float-reaction {
  position: absolute; bottom: 80px; font-size: 28px;
  animation: floatUp 2.5s ease-out forwards; pointer-events: none;
  display: flex; flex-direction: column; align-items: center; gap: 2px;
}
.float-reaction .react-name {
  font-size: 9px; color: #fff; background: rgba(0,0,0,0.5);
  padding: 1px 5px; border-radius: 10px; white-space: nowrap;
}
@keyframes floatUp {
  0%   { opacity: 1; transform: translateY(0) scale(1); }
  80%  { opacity: 0.8; }
  100% { opacity: 0; transform: translateY(-220px) scale(0.7); }
}

.float-bubble {
  position: absolute; pointer-events: none;
  display: flex; flex-direction: column; align-items: flex-start; gap: 2px;
  animation: floatBubble 4s ease-out forwards; max-width: 180px;
}
.float-bubble .bubble-name { font-size: 9px; font-weight: bold; padding: 0 6px; margin-bottom: 1px; }
.float-bubble .bubble-text {
  background: rgba(30,30,40,0.88); border: 1px solid rgba(255,255,255,0.15);
  border-radius: 14px 14px 14px 4px; padding: 5px 10px;
  font-size: 12px; color: #fff; backdrop-filter: blur(4px);
  word-break: break-word; box-shadow: 0 2px 8px rgba(0,0,0,0.4);
  white-space: pre-wrap; max-width: 180px;
}
.float-bubble .bubble-text img {
  max-width: 140px; max-height: 120px; border-radius: 8px;
  display: block; margin-top: 4px;
}
@keyframes floatBubble {
  0%   { opacity: 0; transform: translateY(0) scale(0.8); }
  10%  { opacity: 1; transform: translateY(-10px) scale(1); }
  85%  { opacity: 1; transform: translateY(-80px); }
  100% { opacity: 0; transform: translateY(-110px); }
}

.float-voice {
  position: absolute; pointer-events: auto;
  display: flex; flex-direction: column; align-items: flex-start; gap: 2px;
  animation: floatBubble 10s ease-out forwards;
  animation-fill-mode: both;
}
.float-voice .voice-bubble {
  background: rgba(30,30,40,0.92); border: 1px solid rgba(255,255,255,0.15);
  border-radius: 14px 14px 14px 4px; padding: 7px 10px;
  backdrop-filter: blur(4px); box-shadow: 0 2px 8px rgba(0,0,0,0.4);
  display: flex; flex-direction: column; gap: 4px;
}
.float-voice .vn-name { font-size: 9px; font-weight: bold; }
.float-voice audio { width: 160px; height: 30px; outline: none; }
@keyframes floatVoice {
  0% { opacity:0; transform: translateY(10px) scale(0.9); }
  100% { opacity:1; transform: translateY(0) scale(1); }
}

.macha-typing { display: inline-block; font-size: 18px; letter-spacing: 2px; animation: machaTyping 1s infinite; }
@keyframes machaTyping { 0%,100% { opacity: 0.2; } 50% { opacity: 1; } }

#wsStatus {
  position: fixed; bottom: 12px; right: 12px;
  font-size: 10px; padding: 4px 10px; border-radius: 20px;
  background: rgba(0,0,0,0.55); color: #aaa; backdrop-filter: blur(4px);
  z-index: 1000; pointer-events: none; transition: color 0.3s;
}
#wsStatus.connected { color: #4cff91; }
#wsStatus.disconnected { color: #ff5555; }

#chatArea {
  width: 100%; display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px,1fr));
  gap: 12px; padding: 32px 12px 40px;
  justify-items: center;
  scroll-behavior: smooth;
}
.chat-box {
  position: relative; width: 250px; height: 350px;
  background: transparent; border-radius: 8px; overflow: hidden;
  box-shadow: 0 3px 8px rgba(0,0,0,0.3);
  will-change: transform;
}
.chat-container { width: 100%; height: 100%; }
.chat-container iframe { width: 100%; height: 100%; border: none; }
.close-btn {
  position: absolute; top: 6px; right: 6px;
  width: 28px; height: 28px; background: #ff0000; color: white;
  border: none; border-radius: 50%; font-size: 18px; cursor: pointer; z-index: 10;
}

.nav-btn { display: none; }
@media (max-width: 480px) {
  html, body {
    overflow: hidden;
    height: 100%;
    position: fixed;
    width: 100%;
  }
  #toolbar {
    padding: 6px 8px;
    gap: 5px;
    flex-wrap: nowrap;
    overflow-x: auto;
  }
  .tool-icon-btn {
    width: 34px;
    height: 34px;
    font-size: 16px;
    flex-shrink: 0;
  }
  #addBtn {
    flex-shrink: 0;
  }
  #bgBtn {
    display: flex !important;
    left: 12px;
    bottom: 12px;
  }
  #chatArea {
    display: flex;
    overflow-x: auto;
    gap: 12px;
    padding: 32px 12px 12px;
    scroll-snap-type: x mandatory;
    -webkit-overflow-scrolling: touch;
    scroll-behavior: smooth;
  }
  .chat-box {
    flex: 0 0 100%;
    width: 100%;
    height: 75vh;
    scroll-snap-align: center;
  }
  #ytWindow {
    width: calc(100vw - 28px);
    left: 14px;
    right: 14px;
  }
  .nav-btn {
    display: flex;
    position: fixed;
    top: 50%;
    transform: translateY(-50%);
    width: 46px;
    height: 46px;
    background: rgba(255,255,255,0.45);
    backdrop-filter: blur(6px);
    border: 1px solid rgba(255,255,255,0.5);
    border-radius: 50%;
    align-items: center;
    justify-content: center;
    font-size: 26px;
    color: #333;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    cursor: pointer;
    z-index: 998;
    transition: 0.25s ease;
  }
  .nav-btn:hover {
    background: rgba(255,255,255,0.7);
    transform: translateY(-50%) scale(1.05);
  }
  #prevBtn { left: 12px; }
  #nextBtn { right: 12px; }
}
