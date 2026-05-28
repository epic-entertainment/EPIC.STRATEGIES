from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import uuid
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BOARD_SIZE = 30
games = {}


class Move(BaseModel):
    game_id: str
    player: str
    x: int
    y: int


def create_board():
    return [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]


def connect_rule(player_count):
    if player_count == 2:
        return 5
    if player_count == 3:
        return 4
    return 3


def is_cpu(player):
    return player.startswith("cpu")


def next_turn(players, current):
    index = players.index(current)
    return players[(index + 1) % len(players)]


def empty_cells(board):
    cells = []
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            if board[y][x] is None:
                cells.append((x, y))
    return cells


def check_direction(board, player, x, y, dx, dy):
    count = 1

    nx = x + dx
    ny = y + dy

    while 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE and board[ny][nx] == player:
        count += 1
        nx += dx
        ny += dy

    nx = x - dx
    ny = y - dy

    while 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE and board[ny][nx] == player:
        count += 1
        nx -= dx
        ny -= dy

    return count


def line_score(board, player, x, y, dx, dy):
    total = 1
    open_ends = 0

    nx = x + dx
    ny = y + dy

    while 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE and board[ny][nx] == player:
        total += 1
        nx += dx
        ny += dy

    if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE and board[ny][nx] is None:
        open_ends += 1

    nx = x - dx
    ny = y - dy

    while 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE and board[ny][nx] == player:
        total += 1
        nx -= dx
        ny -= dy

    if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE and board[ny][nx] is None:
        open_ends += 1

    return total, open_ends


def check_winner(board, player, x, y, connect_n):
    for dx, dy in [(1, 0), (0, 1), (1, 1), (1, -1)]:
        if check_direction(board, player, x, y, dx, dy) >= connect_n:
            return True
    return False


def winning_move(board, player, connect_n):
    for x, y in empty_cells(board):
        board[y][x] = player

        if check_winner(board, player, x, y, connect_n):
            board[y][x] = None
            return (x, y)

        board[y][x] = None

    return None


def move_strength(board, player, x, y, connect_n):
    score = 0
    fork_lines = 0

    board[y][x] = player

    for dx, dy in [(1, 0), (0, 1), (1, 1), (1, -1)]:
        length, open_ends = line_score(board, player, x, y, dx, dy)

        if length >= connect_n:
            score += 100000

        if length == connect_n - 1 and open_ends >= 1:
            score += 5000
            fork_lines += 1

        if length == connect_n - 2 and open_ends == 2:
            score += 900
            fork_lines += 1

        score += length * length * 20
        score += open_ends * 25

    if fork_lines >= 2:
        score += 3000

    board[y][x] = None

    return score


def cluster_score(board, player, x, y):
    score = 0

    for yy in range(max(0, y - 3), min(BOARD_SIZE, y + 4)):
        for xx in range(max(0, x - 3), min(BOARD_SIZE, x + 4)):
            cell = board[yy][xx]

            if cell is None:
                continue

            distance = max(abs(xx - x), abs(yy - y))
            weight = max(1, 4 - distance)

            if cell == player:
                score += 12 * weight
            else:
                score += 8 * weight

    center = BOARD_SIZE // 2
    score += max(0, 20 - abs(x - center) - abs(y - center))

    return score


def cpu_move(board, player, players, connect_n):
    own_win = winning_move(board, player, connect_n)
    if own_win:
        return own_win

    for enemy in players:
        if enemy == player:
            continue

        block = winning_move(board, enemy, connect_n)
        if block:
            return block

    best_move = None
    best_score = -1

    for x, y in empty_cells(board):
        score = 0

        score += move_strength(board, player, x, y, connect_n) * 3

        for enemy in players:
            if enemy == player:
                continue
            score += move_strength(board, enemy, x, y, connect_n) * 2

        score += cluster_score(board, player, x, y)

        if score > best_score:
            best_score = score
            best_move = (x, y)

    if best_move:
        return best_move

    cells = empty_cells(board)
    return random.choice(cells) if cells else None


def detect_threat(board, players, connect_n):
    best = None
    best_score = 0

    for player in players:
        for x, y in empty_cells(board):
            score = move_strength(board, player, x, y, connect_n)

            if score > best_score:
                best_score = score
                best = {
                    "player": player,
                    "row": y + 1,
                    "col": x + 1,
                    "type": "threat"
                }

    if best_score >= 900:
        return best

    return None


def run_cpu_cycle(game):
    cpu_moves = []

    while game["winner"] is None and is_cpu(game["turn"]):
        current = game["turn"]

        move = cpu_move(
            game["board"],
            current,
            game["players"],
            game["connect_n"]
        )

        if move is None:
            return cpu_moves

        x, y = move

        game["board"][y][x] = current

        cpu_moves.append({
            "player": current,
            "x": x,
            "y": y
        })

        if check_winner(game["board"], current, x, y, game["connect_n"]):
            game["winner"] = current
            return cpu_moves

        game["turn"] = next_turn(game["players"], current)

    return cpu_moves


@app.get("/")
def serve_frontend():
    return FileResponse("epicstrategyfrontend.html")


@app.post("/games")
def create_game(players: list[str]):
    if len(players) not in [2, 3, 4]:
        raise HTTPException(status_code=400, detail="Supported: 2, 3, 4")

    if players[0] != "p1":
        raise HTTPException(status_code=400, detail="First player must be p1")

    game_id = str(uuid.uuid4())

    game = {
        "id": game_id,
        "board": create_board(),
        "players": players,
        "turn": "p1",
        "winner": None,
        "connect_n": connect_rule(len(players))
    }

    games[game_id] = game

    return {
        "game_id": game_id,
        "board": game["board"],
        "next_turn": game["turn"],
        "winner": game["winner"],
        "threat": detect_threat(game["board"], game["players"], game["connect_n"]),
        "cpu_moves": []
    }


@app.post("/move")
def make_move(move: Move):
    if move.game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[move.game_id]

    if game["winner"] is not None:
        raise HTTPException(status_code=400, detail="Game finished")

    if move.player != "p1":
        raise HTTPException(status_code=400, detail="Only p1 is human")

    if game["turn"] != "p1":
        raise HTTPException(status_code=400, detail="Wait for CPU turns")

    if not (0 <= move.x < BOARD_SIZE and 0 <= move.y < BOARD_SIZE):
        raise HTTPException(status_code=400, detail="Out of bounds")

    if game["board"][move.y][move.x] is not None:
        raise HTTPException(status_code=400, detail="Occupied")

    game["board"][move.y][move.x] = "p1"

    if check_winner(game["board"], "p1", move.x, move.y, game["connect_n"]):
        game["winner"] = "p1"
        cpu_moves = []
    else:
        game["turn"] = next_turn(game["players"], "p1")
        cpu_moves = run_cpu_cycle(game)

    return {
        "board": game["board"],
        "next_turn": game["turn"],
        "winner": game["winner"],
        "threat": detect_threat(game["board"], game["players"], game["connect_n"]),
        "cpu_moves": cpu_moves
    }


@app.get("/game/{game_id}")
def get_game(game_id: str):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[game_id]

    return {
        "board": game["board"],
        "next_turn": game["turn"],
        "winner": game["winner"],
        "threat": detect_threat(game["board"], game["players"], game["connect_n"]),
        "players": game["players"],
        "connect_n": game["connect_n"]
    }
