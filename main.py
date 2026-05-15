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
    return [
        [None for _ in range(BOARD_SIZE)]
        for _ in range(BOARD_SIZE)
    ]


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


def cpu_move(board):
    cells = empty_cells(board)

    if not cells:
        return None

    return random.choice(cells)


def check_direction(board, player, x, y, dx, dy):
    count = 1

    nx = x + dx
    ny = y + dy

    while (
        0 <= nx < BOARD_SIZE and
        0 <= ny < BOARD_SIZE and
        board[ny][nx] == player
    ):
        count += 1
        nx += dx
        ny += dy

    nx = x - dx
    ny = y - dy

    while (
        0 <= nx < BOARD_SIZE and
        0 <= ny < BOARD_SIZE and
        board[ny][nx] == player
    ):
        count += 1
        nx -= dx
        ny -= dy

    return count


def check_winner(board, player, x, y, connect_n):
    directions = [
        (1, 0),
        (0, 1),
        (1, 1),
        (1, -1),
    ]

    for dx, dy in directions:
        if check_direction(board, player, x, y, dx, dy) >= connect_n:
            return True

    return False


def detect_threat(board, connect_n):
    # Simple MVP clue:
    # returns a row where a player may be building toward a win.
    for y in range(BOARD_SIZE):
        row_counts = {}

        for x in range(BOARD_SIZE):
            player = board[y][x]

            if player is None:
                continue

            row_counts[player] = row_counts.get(player, 0) + 1

            if row_counts[player] >= connect_n - 1:
                return {
                    "row": y + 1,
                    "player": player
                }

    return None


def run_cpu_cycle(game):
    cpu_moves = []

    while (
        game["winner"] is None and
        is_cpu(game["turn"])
    ):
        current = game["turn"]

        move = cpu_move(game["board"])

        if move is None:
            return cpu_moves

        x, y = move

        game["board"][y][x] = current

        cpu_moves.append({
            "player": current,
            "x": x,
            "y": y
        })

        if check_winner(
            game["board"],
            current,
            x,
            y,
            game["connect_n"]
        ):
            game["winner"] = current
            return cpu_moves

        game["turn"] = next_turn(
            game["players"],
            current
        )

    return cpu_moves


@app.get("/")
def serve_frontend():
    return FileResponse("epicstrategyfrontend.html")


@app.post("/games")
def create_game(players: list[str]):
    if len(players) not in [2, 3, 4]:
        raise HTTPException(
            status_code=400,
            detail="Supported player counts: 2, 3, or 4"
        )

    if players[0] != "p1":
        raise HTTPException(
            status_code=400,
            detail="Player 1 must be p1"
        )

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
        "threat": None,
        "cpu_moves": []
    }


@app.post("/move")
def make_move(move: Move):
    if move.game_id not in games:
        raise HTTPException(
            status_code=404,
            detail="Game not found"
        )

    game = games[move.game_id]

    if game["winner"] is not None:
        raise HTTPException(
            status_code=400,
            detail="Game finished"
        )

    if move.player != "p1":
        raise HTTPException(
            status_code=400,
            detail="Only p1 is human in this mode"
        )

    if game["turn"] != "p1":
        raise HTTPException(
            status_code=400,
            detail="Wait for CPU turns"
        )

    if (
        move.x < 0 or
        move.x >= BOARD_SIZE or
        move.y < 0 or
        move.y >= BOARD_SIZE
    ):
        raise HTTPException(
            status_code=400,
            detail="Out of bounds"
        )

    if game["board"][move.y][move.x] is not None:
        raise HTTPException(
            status_code=400,
            detail="Occupied"
        )

    # Human p1 move happens immediately.
    game["board"][move.y][move.x] = "p1"

    if check_winner(
        game["board"],
        "p1",
        move.x,
        move.y,
        game["connect_n"]
    ):
        game["winner"] = "p1"
        cpu_moves = []
    else:
        # Advance from p1 to cpu2/cpu3/cpu4.
        game["turn"] = next_turn(
            game["players"],
            "p1"
        )

        # Backend computes all CPU moves instantly.
        # Frontend animates them with 2-second fake thinking delays.
        cpu_moves = run_cpu_cycle(game)

    threat = detect_threat(
        game["board"],
        game["connect_n"]
    )

    return {
        "board": game["board"],
        "next_turn": game["turn"],
        "winner": game["winner"],
        "threat": threat,
        "cpu_moves": cpu_moves
    }


@app.get("/game/{game_id}")
def get_game(game_id: str):
    if game_id not in games:
        raise HTTPException(
            status_code=404,
            detail="Game not found"
        )

    game = games[game_id]

    threat = detect_threat(
        game["board"],
        game["connect_n"]
    )

    return {
        "board": game["board"],
        "next_turn": game["turn"],
        "winner": game["winner"],
        "threat": threat,
        "players": game["players"],
        "connect_n": game["connect_n"]
    }
