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


def check_direction(
    board,
    player,
    x,
    y,
    dx,
    dy
):
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


def check_winner(
    board,
    player,
    x,
    y,
    connect_n
):

    directions = [

        (1, 0),
        (0, 1),
        (1, 1),
        (1, -1)
    ]

    for dx, dy in directions:

        if check_direction(
            board,
            player,
            x,
            y,
            dx,
            dy
        ) >= connect_n:

            return True

    return False


def get_empty_cells(board):

    cells = []

    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):

            if board[y][x] is None:
                cells.append((x, y))

    return cells


def cpu_move(board):

    empty = get_empty_cells(board)

    if not empty:
        return None

    return random.choice(empty)


def next_turn(players, current):

    index = players.index(current)

    return players[
        (index + 1) % len(players)
    ]


def detect_threat(board, connect_n):

    for y in range(BOARD_SIZE):

        row_count = 0

        for x in range(BOARD_SIZE):

            if board[y][x] is not None:
                row_count += 1

        if row_count >= connect_n - 1:

            return {
                "row": y + 1
            }

    return None


def run_cpu_turns(game):

    while (
        game["winner"] is None and
        is_cpu(game["turn"])
    ):

        cpu = game["turn"]

        thinking_time = random.uniform(
            1.0,
            10.0
        )

        import time
        time.sleep(thinking_time)

        move = cpu_move(game["board"])

        if move is None:
            return

        x, y = move

        game["board"][y][x] = cpu

        if check_winner(
            game["board"],
            cpu,
            x,
            y,
            game["connect_n"]
        ):

            game["winner"] = cpu

            return

        game["turn"] = next_turn(
            game["players"],
            game["turn"]
        )


@app.get("/")
def serve_frontend():

    return FileResponse(
        "epicstrategyfrontend.html"
    )


@app.post("/games")
def create_game(players: list[str]):

    game_id = str(uuid.uuid4())

    board = create_board()

    connect_n = connect_rule(
        len(players)
    )

    game = {

        "id": game_id,

        "board": board,

        "players": players,

        "turn": players[0],

        "winner": None,

        "connect_n": connect_n
    }

    games[game_id] = game

    run_cpu_turns(game)

    threat = detect_threat(
        board,
        connect_n
    )

    return {

        "game_id": game_id,

        "board": board,

        "next_turn": game["turn"],

        "winner": game["winner"],

        "threat": threat
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

    if game["turn"] != move.player:

        raise HTTPException(
            status_code=400,
            detail="Not your turn"
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

    game["board"][move.y][move.x] = move.player

    if check_winner(
        game["board"],
        move.player,
        move.x,
        move.y,
        game["connect_n"]
    ):

        game["winner"] = move.player

    else:

        game["turn"] = next_turn(
            game["players"],
            game["turn"]
        )

        run_cpu_turns(game)

    threat = detect_threat(
        game["board"],
        game["connect_n"]
    )

    return {

        "board": game["board"],

        "next_turn": game["turn"],

        "winner": game["winner"],

        "threat": threat
    }
