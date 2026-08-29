/* ══════════════════════════════
   CHESS AI WORKER (Hard Mode)
   Minimax + alpha-beta pruning + quiescence search + iterative deepening
══════════════════════════════ */

importScripts("https://cdnjs.cloudflare.com/ajax/libs/chess.js/0.10.3/chess.min.js");

var PIECE_VALUES = { p: 100, n: 320, b: 330, r: 500, q: 900, k: 20000 };

var PAWN_TABLE = [
  0,  0,  0,  0,  0,  0,  0,  0,
  50, 50, 50, 50, 50, 50, 50, 50,
  10, 10, 20, 30, 30, 20, 10, 10,
  5,  5, 10, 25, 25, 10,  5,  5,
  0,  0,  0, 20, 20,  0,  0,  0,
  5, -5,-10,  0,  0,-10, -5,  5,
  5, 10, 10,-20,-20, 10, 10,  5,
  0,  0,  0,  0,  0,  0,  0,  0
];
var KNIGHT_TABLE = [
  -50,-40,-30,-30,-30,-30,-40,-50,
  -40,-20,  0,  0,  0,  0,-20,-40,
  -30,  0, 10, 15, 15, 10,  0,-30,
  -30,  5, 15, 20, 20, 15,  5,-30,
  -30,  0, 15, 20, 20, 15,  0,-30,
  -30,  5, 10, 15, 15, 10,  5,-30,
  -40,-20,  0,  5,  5,  0,-20,-40,
  -50,-40,-30,-30,-30,-30,-40,-50
];
var BISHOP_TABLE = [
  -20,-10,-10,-10,-10,-10,-10,-20,
  -10,  0,  0,  0,  0,  0,  0,-10,
  -10,  0,  5, 10, 10,  5,  0,-10,
  -10,  5,  5, 10, 10,  5,  5,-10,
  -10,  0, 10, 10, 10, 10,  0,-10,
  -10, 10, 10, 10, 10, 10, 10,-10,
  -10,  5,  0,  0,  0,  0,  5,-10,
  -20,-10,-10,-10,-10,-10,-10,-20
];
var ROOK_TABLE = [
  0,  0,  0,  0,  0,  0,  0,  0,
  5, 10, 10, 10, 10, 10, 10,  5,
 -5,  0,  0,  0,  0,  0,  0, -5,
 -5,  0,  0,  0,  0,  0,  0, -5,
 -5,  0,  0,  0,  0,  0,  0, -5,
 -5,  0,  0,  0,  0,  0,  0, -5,
 -5,  0,  0,  0,  0,  0,  0, -5,
  0,  0,  0,  5,  5,  0,  0,  0
];
var QUEEN_TABLE = [
  -20,-10,-10, -5, -5,-10,-10,-20,
  -10,  0,  0,  0,  0,  0,  0,-10,
  -10,  0,  5,  5,  5,  5,  0,-10,
  -5,  0,  5,  5,  5,  5,  0, -5,
  0,  0,  5,  5,  5,  5,  0, -5,
  -10,  5,  5,  5,  5,  5,  0,-10,
  -10,  0,  5,  0,  0,  0,  0,-10,
  -20,-10,-10, -5, -5,-10,-10,-20
];
var KING_MIDDLE_TABLE = [
  -30,-40,-40,-50,-50,-40,-40,-30,
  -30,-40,-40,-50,-50,-40,-40,-30,
  -30,-40,-40,-50,-50,-40,-40,-30,
  -30,-40,-40,-50,-50,-40,-40,-30,
  -20,-30,-30,-40,-40,-30,-30,-20,
  -10,-20,-20,-20,-20,-20,-20,-10,
   20, 20,  0,  0,  0,  0, 20, 20,
   20, 30, 10,  0,  0, 10, 30, 20
];
var KING_END_TABLE = [
  -50,-40,-30,-20,-20,-30,-40,-50,
  -30,-20,-10,  0,  0,-10,-20,-30,
  -30,-10, 20, 30, 30, 20,-10,-30,
  -30,-10, 30, 40, 40, 30,-10,-30,
  -30,-10, 30, 40, 40, 30,-10,-30,
  -30,-10, 20, 30, 30, 20,-10,-30,
  -30,-30,  0,  0,  0,  0,-30,-30,
  -50,-30,-30,-30,-30,-30,-30,-50
];

var PST = { p: PAWN_TABLE, n: KNIGHT_TABLE, b: BISHOP_TABLE, r: ROOK_TABLE, q: QUEEN_TABLE };

function squareIndex(square) {
  var file = square.charCodeAt(0) - 97;
  var rank = parseInt(square[1], 10);
  var row = 8 - rank;
  return row * 8 + file;
}

function pstValue(piece, square, endgame) {
  var idx = squareIndex(square);
  var table = piece.type === 'k' ? (endgame ? KING_END_TABLE : KING_MIDDLE_TABLE) : PST[piece.type];
  if (!table) return 0;
  var i = piece.color === 'w' ? idx : (63 - idx);
  return table[i];
}

function isEndgame(game) {
  var board = game.board();
  var queens = 0, minorsAndRooks = 0;
  for (var r = 0; r < 8; r++) {
    for (var c = 0; c < 8; c++) {
      var sq = board[r][c];
      if (!sq) continue;
      if (sq.type === 'q') queens++;
      else if (sq.type === 'r' || sq.type === 'b' || sq.type === 'n') minorsAndRooks++;
    }
  }
  return queens === 0 || minorsAndRooks <= 2;
}

// Absolute (white-positive) material + positional score. Does NOT handle
// checkmate/draw — that's handled by evaluateRelative before this is called.
function evaluateMaterial(game) {
  var endgame = isEndgame(game);
  var board = game.board();
  var score = 0;
  for (var r = 0; r < 8; r++) {
    for (var c = 0; c < 8; c++) {
      var sq = board[r][c];
      if (!sq) continue;
      var value = PIECE_VALUES[sq.type];
      var file = String.fromCharCode(97 + c);
      var rank = 8 - r;
      var pst = pstValue(sq, file + rank, endgame);
      var total = value + pst;
      score += sq.color === 'w' ? total : -total;
    }
  }
  if (game.in_check()) {
    score += game.turn() === 'w' ? -30 : 30;
  }
  return score;
}

// Score relative to the side to move (negamax convention: positive = good
// for the player whose turn it is right now).
function evaluateRelative(game) {
  if (game.in_checkmate()) return -100000;
  if (game.in_stalemate() || game.in_threefold_repetition() ||
      game.insufficient_material() || game.in_draw()) return 0;
  var abs = evaluateMaterial(game);
  return game.turn() === 'w' ? abs : -abs;
}

function orderMoves(moves) {
  return moves.slice().sort(function(a, b) { return moveScore(b) - moveScore(a); });
  function moveScore(m) {
    var score = 0;
    if (m.flags.indexOf('c') !== -1 || m.flags.indexOf('e') !== -1) {
      var capturedVal = PIECE_VALUES[m.captured] || 0;
      var attackerVal = PIECE_VALUES[m.piece] || 0;
      score += 1000 + capturedVal - attackerVal / 10;
    }
    if (m.promotion) score += 800;
    if (m.flags.indexOf('k') !== -1 || m.flags.indexOf('q') !== -1) score += 50;
    return score;
  }
}

function TimeUp() {}
TimeUp.prototype = Object.create(Error.prototype);

function quiescence(game, alpha, beta, deadline) {
  if (Date.now() > deadline) throw new TimeUp();

  var standPat = evaluateRelative(game);
  if (standPat >= beta) return beta;
  if (standPat > alpha) alpha = standPat;
  if (game.game_over()) return standPat;

  var captures = orderMoves(
    game.moves({ verbose: true }).filter(function(m) {
      return m.flags.indexOf('c') !== -1 || m.flags.indexOf('e') !== -1;
    })
  );

  for (var i = 0; i < captures.length; i++) {
    var m = captures[i];
    game.move({ from: m.from, to: m.to, promotion: m.promotion });
    var score = -quiescence(game, -beta, -alpha, deadline);
    game.undo();
    if (score >= beta) return beta;
    if (score > alpha) alpha = score;
  }
  return alpha;
}

function negamax(game, depth, alpha, beta, deadline) {
  if (Date.now() > deadline) throw new TimeUp();
  if (game.game_over()) return evaluateRelative(game);
  if (depth === 0) return quiescence(game, alpha, beta, deadline);

  var moves = orderMoves(game.moves({ verbose: true }));
  var best = -Infinity;
  for (var i = 0; i < moves.length; i++) {
    var m = moves[i];
    game.move({ from: m.from, to: m.to, promotion: m.promotion });
    var score = -negamax(game, depth - 1, -beta, -alpha, deadline);
    game.undo();
    if (score > best) best = score;
    if (best > alpha) alpha = best;
    if (alpha >= beta) break;
  }
  return best;
}

function findBestMove(fen, timeLimitMs) {
  var game = new Chess(fen);
  var deadline = Date.now() + timeLimitMs;
  var bestMove = null;
  var bestScore = -Infinity;
  var depth = 1;
  var maxDepth = 12;

  while (depth <= maxDepth && Date.now() < deadline) {
    var rootMoves = orderMoves(game.moves({ verbose: true }));
    if (!rootMoves.length) break;

    var currentBestMove = null;
    var currentBestScore = -Infinity;
    var alpha = -Infinity, beta = Infinity;
    var timedOut = false;

    try {
      for (var i = 0; i < rootMoves.length; i++) {
        var m = rootMoves[i];
        game.move({ from: m.from, to: m.to, promotion: m.promotion });
        var score = -negamax(game, depth - 1, -beta, -alpha, deadline);
        game.undo();
        if (score > currentBestScore) {
          currentBestScore = score;
          currentBestMove = m;
        }
        if (score > alpha) alpha = score;
      }
    } catch (e) {
      timedOut = true;
    }

    if (!timedOut && currentBestMove) {
      bestMove = currentBestMove;
      bestScore = currentBestScore;
    }
    if (timedOut) break;
    depth++;
  }

  if (!bestMove) {
    var fallback = game.moves({ verbose: true });
    if (fallback.length) bestMove = fallback[Math.floor(Math.random() * fallback.length)];
  }

  return { move: bestMove, score: bestScore, depth: depth - 1 };
}

self.onmessage = function(e) {
  var data = e.data || {};
  try {
    var result = findBestMove(data.fen, data.timeLimit || 3000);
    self.postMessage({
      ok: !!result.move,
      move: result.move ? { from: result.move.from, to: result.move.to, promotion: result.move.promotion } : null,
      depth: result.depth,
      score: result.score
    });
  } catch (err) {
    self.postMessage({ ok: false, error: String(err) });
  }
};
