# VIPMUSIC/utils/database/__init__.py
# Unified import layer for all database functions (legacy + new)

# -----------------------------
# Safe imports with fallbacks
# -----------------------------

# --- Admin / Auth DB helpers ---
try:
    from VIPMUSIC.utils.database.auth import (
        get_authuser_names,
        get_authuser_id,
        is_auth,
        add_authuser,
        remove_authuser,
    )
except ImportError:
    # fallback stubs
    def get_authuser_names(chat_id: int):
        return []

    def get_authuser_id(chat_id: int, name: str):
        return None

    def is_auth(chat_id: int, user_id: int):
        return False

    def add_authuser(chat_id: int, user_id: int, name: str):
        pass

    def remove_authuser(chat_id: int, user_id: int):
        pass


# --- Sudo & Core ---
try:
    from VIPMUSIC.utils.database.sudo import get_sudoers
except ImportError:
    def get_sudoers():
        return []


# --- Channel Mode / Play Mode ---
try:
    from VIPMUSIC.utils.database.cmode import get_cmode
except ImportError:
    def get_cmode(chat_id: int):
        return None


# --- MongoDB wrapper (if exists) ---
try:
    from VIPMUSIC.utils.database.mongo import mongodb
except ImportError:
    mongodb = None


# --- Reaction System (JSON / Mongo-based) ---
try:
    from VIPMUSIC.utils.database.reactiondb import (
        get_reaction_status,
        set_reaction_status,
    )
except ImportError:
    def get_reaction_status(chat_id: int) -> bool:
        return True

    def set_reaction_status(chat_id: int, status: bool):
        pass


# -----------------------------
# Export everything cleanly
# -----------------------------
__all__ = [
    # Auth
    "get_authuser_names",
    "get_authuser_id",
    "is_auth",
    "add_authuser",
    "remove_authuser",

    # Core
    "get_sudoers",
    "get_cmode",
    "mongodb",

    # Reaction
    "get_reaction_status",
    "set_reaction_status",
]
