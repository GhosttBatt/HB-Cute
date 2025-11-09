import json
import os
from typing import Dict

DB_PATH = "reaction_state.json"

def _load_db() -> Dict[str, bool]:
    if not os.path.exists(DB_PATH):
        return {}
    try:
        with open(DB_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_db(data: Dict[str, bool]):
    with open(DB_PATH, "w") as f:
        json.dump(data, f)

def get_reaction_status(chat_id: int) -> bool:
    data = _load_db()
    return data.get(str(chat_id), True)  # default ON

def set_reaction_status(chat_id: int, status: bool):
    data = _load_db()
    data[str(chat_id)] = status
    _save_db(data)
