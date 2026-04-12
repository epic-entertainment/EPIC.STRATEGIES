import uuid
from sqlalchemy import Column, String, Integer
from sqlalchemy.dialects.sqlite import BLOB
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    clue_balance = Column(Integer, default=3)


class Game(Base):
    __tablename__ = "games"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String, default="waiting")
    max_players = Column(Integer)
    current_turn_player_id = Column(String, nullable=True)
    winner_player_id = Column(String, nullable=True)


class Move(Base):
    __tablename__ = "moves"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    game_id = Column(String)
    player_id = Column(String)
    x_position = Column(Integer)
    y_position = Column(Integer)
    move_number = Column(Integer)
