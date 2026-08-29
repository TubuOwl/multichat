/* ══════════════════════════════
   CHESS vs MACHA (Hard Mode)
   Requires chess.js loaded BEFORE this file (CDN script tag).
══════════════════════════════ */

var CHESS_BOT_TIME_MS = 3000; // how long Macha "thinks" per move

var chessGame = null;
var chessMoveHistory = [];
var chessSelected = null;
var chessLegalTargets = [];
var chessCaptureTargets = [];
var chessPendingPromotions = {};
var chessPendingPromoMove = null;
var chessGameOver = false;
var chessBotThinking = false;
var chessWorker = null;

var PIECE_UNICODE = {
  w: { p: "♙", n: "♘", b: "♗", r: "♖", q: "♕", k: "♔" },
  b: { p: "♟", n: "♞", b: "♝", r: "♜", q: "♛", k: "♚" }
};

/* ── UI Construction ── */
function buildChessUI() {
  var style = document.createElement("style");
  style.id = "chessStyles";
  style.textContent =
    "#chessModal{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.65);" +
    "backdrop-filter:blur(4px);z-index:2100;align-items:center;justify-content:center;padding:16px;}" +
    "#chessCard{background:#1a1a2e;border:1px solid rgba(255,255,255,0.15);border-radius:16px;" +
    "padding:18px 20px;display:flex;flex-direction:column;gap:12px;align-items:center;" +
    "max-width:460px;width:100%;box-shadow:0 10px 40px rgba(0,0,0,0.6);}" +
    "#chessHeader{display:flex;align-items:center;justify-content:space-between;width:100%;}" +
    "#chessStatus{color:#fff;font-size:13px;min-height:18px;text-align:center;}" +
    ".chess-btn{padding:8px 14px;border-radius:8px;border:none;font-size:12px;font-weight:600;cursor:pointer;}" +
    "#chessBoard{display:grid;grid-template-columns:repeat(8,1fr);grid-template-rows:repeat(8,1fr);" +
    "width:min(88vw,420px);height:min(88vw,420px);border-radius:10px;overflow:hidden;" +
    "box-shadow:0 8px 30px rgba(0,0,0,0.5);transition:opacity 0.2s;}" +
    ".chess-square{position:relative;display:flex;align-items:center;justify-content:center;" +
    "cursor:pointer;user-select:none;}" +
    ".chess-square:hover{filter:brightness(1.15);}" +
    ".chess-light{background:#3a3a54;}" +
    ".chess-dark{background:#201f30;}" +
    ".chess-piece{font-size:min(7vw,32px);line-height:1;filter:drop-shadow(0 2px 3px rgba(0,0,0,0.6));" +
    "pointer-events:none;}" +
    ".chess-selected{box-shadow:inset 0 0 0 3px #ff6b9d;}" +
    ".chess-lastmove{background-color:rgba(96,165,250,0.35) !important;}" +
    ".chess-check{background-color:rgba(248,113,113,0.55) !important;}" +
    ".chess-legal::after{content:'';position:absolute;width:26%;height:26%;border-radius:50%;" +
    "background:rgba(192,132,252,0.85);pointer-events:none;}" +
    ".chess-legal-capture::after{content:'';position:absolute;inset:4px;border-radius:50%;" +
    "border:3px solid rgba(248,113,113,0.85);background:transparent;width:auto;height:auto;}" +
    "#chessPromoModal{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);" +
    "z-index:2200;align-items:center;justify-content:center;}" +
    "#chessPromoCard{background:#1a1a2e;border:1px solid rgba(255,255,255,0.2);border-radius:14px;" +
    "padding:20px;display:flex;flex-direction:column;gap:12px;align-items:center;}" +
    ".chess-promo-options{display:flex;gap:10px;}" +
    ".chess-promo-btn{font-size:28px;background:rgba(255,255,255,0.08);" +
    "border:1px solid rgba(255,255,255,0.2);border-radius:10px;padding:8px 14px;cursor:pointer;color:#fff;}";
  document.head.appendChild(style);

  var wrap = document.createElement("div");
  wrap.innerHTML =
    '<div id="chessModal">' +
      '<div id="chessCard">' +
        '<div id="chessHeader">' +
          '<span style="color:#fff;font-weight:bold;font-size:15px;">♞ Chess vs Macha</span>' +
          '<button class="chess-btn" style="background:rgba(255,255,255,0.1);color:#fff;" onclick="toggleChess()">✕</button>' +
        "</div>" +
        '<div style="color:#c084fc;font-size:11px;text-align:center;">🔥 Hard Mode — Macha mikir sampai ' +
          (CHESS_BOT_TIME_MS / 1000) + ' detik tiap langkah. Kamu main sebagai ⚪ Putih.</div>' +
        '<div id="chessStatus">Giliran kamu</div>' +
        '<div id="chessBoard"></div>' +
        '<div style="display:flex;gap:8px;">' +
          '<button class="chess-btn" style="background:linear-gradient(135deg,#ff6b9d,#c084fc);color:#fff;" onclick="newChessGame()">🔄 New Game</button>' +
          '<button class="chess-btn" style="background:rgba(255,255,255,0.1);color:#fff;" onclick="resignChess()">🏳️ Menyerah</button>' +
        "</div>" +
      "</div>" +
    "</div>" +
    '<div id="chessPromoModal">' +
      '<div id="chessPromoCard">' +
        '<span style="color:#fff;font-size:13px;">Promosi pion jadi:</span>' +
        '<div class="chess-promo-options">' +
          '<button class="chess-promo-btn" onclick="choosePromotion(\'q\')">♛</button>' +
          '<button class="chess-promo-btn" onclick="choosePromotion(\'r\')">♜</button>' +
          '<button class="chess-promo-btn" onclick="choosePromotion(\'b\')">♝</button>' +
          '<button class="chess-promo-btn" onclick="choosePromotion(\'n\')">♞</button>' +
        "</div>" +
      "</div>" +
    "</div>";
  document.body.appendChild(wrap);

  newChessGame();
}

function injectChessToolbarButton() {
  var toolbar = document.getElementById("toolbar");
  if (!toolbar) return;
  var btn = document.createElement("button");
  btn.className = "tool-icon-btn";
  btn.title = "Chess vs Macha (Hard Mode)";
  btn.textContent = "♟️";
  btn.onclick = toggleChess;
  var chatInput = document.getElementById("chatInput");
  if (chatInput) toolbar.insertBefore(btn, chatInput);
  else toolbar.appendChild(btn);
}

document.addEventListener("DOMContentLoaded", function() {
  injectChessToolbarButton();
  buildChessUI();
});

/* ── Modal toggle ── */
function toggleChess() {
  if (typeof Chess === "undefined") {
    alert("Gagal memuat modul catur. Cek koneksi internet kamu lalu reload halaman.");
    return;
  }
  var modal = document.getElementById("chessModal");
  if (!modal) return;
  modal.style.display = modal.style.display === "flex" ? "none" : "flex";
}

/* ── Game lifecycle ── */
function newChessGame() {
  if (typeof Chess === "undefined") return;
  chessGame = new Chess();
  chessMoveHistory = [];
  chessSelected = null;
  chessLegalTargets = [];
  chessCaptureTargets = [];
  chessPendingPromotions = {};
  chessPendingPromoMove = null;
  chessGameOver = false;
  chessBotThinking = false;
  setChessThinkingUI(false);
  renderBoard();
  updateChessStatus();
}

function resignChess() {
  if (!chessGame || chessGameOver) return;
  chessGameOver = true;
  var statusEl = document.getElementById("chessStatus");
  if (statusEl) statusEl.textContent = "🏳️ Kamu menyerah. Macha menang.";
  maybeMachaTaunt("resign");
}

/* ── Rendering ── */
function findKingSquare(boardState, color) {
  for (var row = 0; row < 8; row++) {
    for (var col = 0; col < 8; col++) {
      var p = boardState[row][col];
      if (p && p.type === "k" && p.color === color) {
        return String.fromCharCode(97 + col) + (8 - row);
      }
    }
  }
  return null;
}

function renderBoard() {
  var boardEl = document.getElementById("chessBoard");
  if (!boardEl || !chessGame) return;
  boardEl.innerHTML = "";

  var boardState = chessGame.board();
  var lastMove = chessMoveHistory.length ? chessMoveHistory[chessMoveHistory.length - 1] : null;
  var inCheckColor = chessGame.in_check() ? chessGame.turn() : null;
  var kingSquare = inCheckColor ? findKingSquare(boardState, inCheckColor) : null;

  for (var row = 0; row < 8; row++) {
    for (var col = 0; col < 8; col++) {
      var file = String.fromCharCode(97 + col);
      var rank = 8 - row;
      var sqName = file + rank;

      var sq = document.createElement("div");
      sq.className = "chess-square " + ((row + col) % 2 === 0 ? "chess-light" : "chess-dark");
      sq.dataset.square = sqName;

      if (chessSelected === sqName) sq.classList.add("chess-selected");
      if (lastMove && (lastMove.from === sqName || lastMove.to === sqName)) sq.classList.add("chess-lastmove");
      if (kingSquare === sqName) sq.classList.add("chess-check");
      if (chessLegalTargets.indexOf(sqName) !== -1) {
        sq.classList.add(chessCaptureTargets.indexOf(sqName) !== -1 ? "chess-legal-capture" : "chess-legal");
      }

      var piece = boardState[row][col];
      if (piece) {
        var span = document.createElement("span");
        span.className = "chess-piece";
        span.textContent = PIECE_UNICODE[piece.color][piece.type];
        sq.appendChild(span);
      }

      sq.addEventListener("click", onSquareClick);
      boardEl.appendChild(sq);
    }
  }
}

function setChessThinkingUI(thinking) {
  var boardEl = document.getElementById("chessBoard");
  if (boardEl) {
    boardEl.style.pointerEvents = thinking ? "none" : "auto";
    boardEl.style.opacity = thinking ? "0.7" : "1";
  }
  if (thinking) {
    var statusEl = document.getElementById("chessStatus");
    if (statusEl) statusEl.textContent = "🤔 Macha lagi mikir...";
  }
}

function updateChessStatus() {
  var statusEl = document.getElementById("chessStatus");
  if (!statusEl || !chessGame) return;

  if (chessGame.in_checkmate()) {
    statusEl.textContent = chessGame.turn() === "w"
      ? "💀 Skakmat! Macha menang."
      : "🎉 Skakmat! Kamu menang lawan Macha!";
    return;
  }
  if (chessGame.in_stalemate()) { statusEl.textContent = "🤝 Stalemate. Seri."; return; }
  if (chessGame.in_threefold_repetition()) { statusEl.textContent = "🤝 Seri (repetisi 3x)."; return; }
  if (chessGame.insufficient_material()) { statusEl.textContent = "🤝 Seri (materi tidak cukup)."; return; }
  if (chessGame.in_draw()) { statusEl.textContent = "🤝 Seri."; return; }

  var turnText = chessGame.turn() === "w" ? "Giliran kamu" : "Giliran Macha";
  var checkText = chessGame.in_check() ? " — Skak!" : "";
  statusEl.textContent = turnText + checkText;
}

function checkChessGameOver() {
  if (chessGame && chessGame.game_over()) {
    chessGameOver = true;
    setChessThinkingUI(false);
    maybeMachaTaunt("gameover");
    return true;
  }
  return false;
}

/* ── Human input ── */
function onSquareClick() {
  if (!chessGame || chessBotThinking || chessGameOver) return;
  if (chessGame.turn() !== "w") return; // human plays white

  var sqName = this.dataset.square;

  if (chessSelected) {
    if (chessLegalTargets.indexOf(sqName) !== -1) {
      attemptHumanMove(chessSelected, sqName);
      return;
    }
    var reclick = chessGame.get(sqName);
    if (reclick && reclick.color === "w") {
      selectSquare(sqName);
    } else {
      clearSelection();
    }
    return;
  }

  var piece = chessGame.get(sqName);
  if (piece && piece.color === "w") selectSquare(sqName);
}

function selectSquare(sqName) {
  chessSelected = sqName;
  var moves = chessGame.moves({ square: sqName, verbose: true });
  chessLegalTargets = moves.map(function(m) { return m.to; });
  chessCaptureTargets = moves
    .filter(function(m) { return m.flags.indexOf("c") !== -1 || m.flags.indexOf("e") !== -1; })
    .map(function(m) { return m.to; });
  chessPendingPromotions = {};
  moves.forEach(function(m) { if (m.promotion) chessPendingPromotions[m.to] = true; });
  renderBoard();
}

function clearSelection() {
  chessSelected = null;
  chessLegalTargets = [];
  chessCaptureTargets = [];
  renderBoard();
}

function attemptHumanMove(from, to) {
  if (chessPendingPromotions[to]) {
    chessPendingPromoMove = { from: from, to: to };
    var promoModal = document.getElementById("chessPromoModal");
    if (promoModal) promoModal.style.display = "flex";
    return;
  }
  finalizeMove(from, to, undefined);
}

function choosePromotion(piece) {
  var promoModal = document.getElementById("chessPromoModal");
  if (promoModal) promoModal.style.display = "none";
  if (!chessPendingPromoMove) return;
  finalizeMove(chessPendingPromoMove.from, chessPendingPromoMove.to, piece);
  chessPendingPromoMove = null;
}

function finalizeMove(from, to, promotion) {
  var moveObj = { from: from, to: to };
  if (promotion) moveObj.promotion = promotion;
  var result = chessGame.move(moveObj);
  if (!result) { clearSelection(); return; }

  chessMoveHistory.push(result);
  chessSelected = null;
  chessLegalTargets = [];
  chessCaptureTargets = [];
  renderBoard();
  updateChessStatus();

  if (checkChessGameOver()) return;
  scheduleBotMove();
}

/* ── Bot move via Web Worker ── */
function getChessWorker() {
  if (chessWorker) return chessWorker;
  chessWorker = new Worker("static/chess-worker.js");
  chessWorker.onmessage = function(e) {
    chessBotThinking = false;
    setChessThinkingUI(false);
    var data = e.data || {};
    if (data.ok && data.move) {
      applyBotMove(data.move.from, data.move.to, data.move.promotion);
      return;
    }
    // Fallback so the game never gets stuck
    var moves = chessGame ? chessGame.moves({ verbose: true }) : [];
    if (moves.length) {
      var m = moves[Math.floor(Math.random() * moves.length)];
      applyBotMove(m.from, m.to, m.promotion);
    }
  };
  chessWorker.onerror = function() {
    chessBotThinking = false;
    setChessThinkingUI(false);
    showNotif("⚠️ Macha error mikir jalan catur, coba New Game.");
  };
  return chessWorker;
}

function scheduleBotMove() {
  if (!chessGame || chessGameOver) return;
  chessBotThinking = true;
  setChessThinkingUI(true);
  var worker = getChessWorker();
  worker.postMessage({ fen: chessGame.fen(), timeLimit: CHESS_BOT_TIME_MS });
}

function applyBotMove(from, to, promotion) {
  if (!chessGame) return;
  var moveObj = { from: from, to: to };
  if (promotion) moveObj.promotion = promotion;
  var result = chessGame.move(moveObj);
  if (!result) return;

  chessMoveHistory.push(result);
  renderBoard();
  updateChessStatus();
  checkChessGameOver();
}

/* ── Optional Macha flavor reaction via existing /chat/macha endpoint ── */
function maybeMachaTaunt(context) {
  if (typeof showNotif !== "function") return; // script.js not loaded, skip silently
  var prompt;
  if (context === "resign") {
    prompt = "aku baru menyerah main catur lawan kamu";
  } else if (chessGame && chessGame.in_checkmate()) {
    prompt = chessGame.turn() === "w"
      ? "kamu baru menang catur lawan aku, skakmat"
      : "aku baru menang catur lawan kamu, skakmat";
  } else {
    prompt = "permainan catur kita baru aja berakhir seri";
  }

  fetch("/chat/macha", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: prompt })
  })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data && data.text) showNotif("💬 Macha: " + data.text);
    })
    .catch(function() {});
}
