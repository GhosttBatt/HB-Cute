import os
import json

# JSON database file
REACTION_DB_PATH = "VIPMUSIC/utils/database/reaction_status.json"

# In-memory cache
reaction_status = {}

# ------------------------------
# 🔄 Load data from JSON on startup
# ------------------------------
def load_reaction_data():
    global reaction_status
    if os.path.exists(REACTION_DB_PATH):
        try:
            with open(REACTION_DB_PATH, "r") as f:
                reaction_status = json.load(f)
            print(f"[ReactionDB] Loaded {len(reaction_status)} chat statuses from JSON.")
        except Exception as e:
            print(f"[ReactionDB] Error loading DB: {e}")
            reaction_status = {}
    else:
        reaction_status = {}
        print("[ReactionDB] No saved data found, starting fresh.")

# ------------------------------
# 💾 Save to JSON
# ------------------------------
def save_reaction_data():
    try:
        os.makedirs(os.path.dirname(REACTION_DB_PATH), exist_ok=True)
        with open(REACTION_DB_PATH, "w") as f:
            json.dump(reaction_status, f)
    except Exception as e:
        print(f"[ReactionDB] Failed to save DB: {e}")

# ------------------------------
# ⚙️ Helpers for bot
# ------------------------------
async def get_reaction_status(chat_id: int) -> bool:
    """Return True if reactions are enabled for this chat."""
    return reaction_status.get(str(chat_id), False)

async def set_reaction_status(chat_id: int, status: bool):
    """Enable or disable reactions for a chat."""
    reaction_status[str(chat_id)] = status
    save_reaction_data()
    print(f"[ReactionDB] Chat {chat_id} set to {'ON' if status else 'OFF'}")

# Auto-load on import
load_reaction_data()
