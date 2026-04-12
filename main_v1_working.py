from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import Base, engine
from models import User
from auth import get_db, hash_password, verify_password, create_token, get_current_user

import uuid
from typing import List
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
BOARD_SIZE = 30


# ---------------------------
# GAME RULES
# ---------------------------
def get_connect_rule(num_players):
    if num_players == 2:
        return 5
    elif num_players == 3:
        return 4
    elif num_players == 4:
        return 3
    elif num_players == 9:
        return 2
    else:
        raise HTTPException(
            status_code=400,
            detail="Supported player counts: 2, 3, 4, or 9"
        )


def create_board():
    return [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]


games = {}

Base.metadata.create_all(bind=engine)


# ---------------------------
# ROOT
# ---------------------------
@app.get("/")
def root():
    return {"status": "Gomoku backend running"}


# ---------------------------
# AUTH
# ---------------------------
@app.post("/register")
def register(username: str, email: str, password: str, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token(user.id)
    return {"token": token}


@app.post("/login")
def login(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_token(user.id)
    return {"token": token}


@app.get("/me")
def read_me(current_user=Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "clue_balance": current_user.clue_balance
    }


# ---------------------------
# GAME MODELS
# ---------------------------
class Move(BaseModel):
    game_id: str
    player: str
    x: int
    y: int


# ---------------------------
# CREATE GAME
# ---------------------------
@app.post("/games")
def create_game(players: List[str]):
    if len(players) not in [2, 3, 4, 9]:
        raise HTTPException(
            status_code=400,
            detail="Supported player counts: 2, 3, 4, or 9"
        )

    game_id = str(uuid.uuid4())
    board = create_board()
    connect_n = get_connect_rule(len(players))

    games[game_id] = {
        "players": players,
        "board": board,
        "turn": players[0],
        "winner": None,
        "connect_n": connect_n
    }

    return {
        "game_id": game_id,
        "board": board,
        "connect_n": connect_n
    }


# ---------------------------
# WIN CHECK
# ---------------------------
def check_winner(board, player, x, y, connect_n):
    directions = [
        (1, 0),   # horizontal
        (0, 1),   # vertical
        (1, 1),   # diagonal \
        (1, -1),  # diagonal /
    ]

    size = len(board)

    for dx, dy in directions:
        count = 1  # include current move

        # forward
        i = 1
        while True:
            nx = x + dx * i
            ny = y + dy * i
            if 0 <= nx < size and 0 <= ny < size and board[ny][nx] == player:
                count += 1
                i += 1
            else:
                break

        # backward
        i = 1
        while True:
            nx = x - dx * i
            ny = y - dy * i
            if 0 <= nx < size and 0 <= ny < size and board[ny][nx] == player:
                count += 1
                i += 1
            else:
                break

        if count >= connect_n:
            return True

    return False


# ---------------------------
# MAKE MOVE
# ---------------------------
@app.post("/move")
def make_move(move: Move):
    if move.game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[move.game_id]

    if game["winner"] is not None:
        raise HTTPException(status_code=400, detail="Game already finished")

    if game["turn"] != move.player:
        raise HTTPException(status_code=400, detail="Not your turn")

    if game["board"][move.y][move.x] is not None:
        raise HTTPException(status_code=400, detail="Cell already occupied")

    # place move
    game["board"][move.y][move.x] = move.player

    # check win
    if check_winner(game["board"], move.player, move.x, move.y, game["connect_n"]):
        game["winner"] = move.player
        return {
            "board": game["board"],
            "winner": game["winner"]
        }

    # next turn
    players = game["players"]
    next_index = (players.index(move.player) + 1) % len(players)
    game["turn"] = players[next_index]

    return {
        "board": game["board"],
        "next_turn": game["turn"]
    }


# ---------------------------
# GET GAME
# ---------------------------
@app.get("/game/{game_id}")
def get_game(game_id: str):
    game = games.get(game_id)

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    return game
