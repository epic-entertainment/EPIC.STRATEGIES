from pydantic import BaseModel
from typing import List, Optional

BOARD_SIZE = 30

class Game(BaseModel):
    id: str
    players: List[str]
    board: List[List[Optional[str]]]
    current_turn: str
    winner: Optional[str] = None
def check_win(board, x, y, player, target):
    directions = [(1,0),(0,1),(1,1),(1,-1)]
    for dx, dy in directions:
        count = 1
        for d in [1, -1]:
            nx, ny = x, y
            while True:
                nx += dx * d
                ny += dy * d
                if 0 <= nx < len(board) and 0 <= ny < len(board[0]) and board[nx][ny] == player:
                    count += 1
                else:
                    break
        if count >= target:
            return True
    return False


def find_threat(board, target):
    for x in range(len(board)):
        for y in range(len(board[0])):
            if board[x][y] is None:
                for player in ["X", "O", "A", "B"]:
                    board[x][y] = player
                    if check_win(board, x, y, player, target):
                        board[x][y] = None
                        return player
                    board[x][y] = None
    return None
