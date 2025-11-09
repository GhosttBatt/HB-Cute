from VIPMUSIC.core.mongo import mongodb

reaction_statusdb = mongodb.reactionstatus

# Cache in memory
reaction_enabled = {}


async def is_reaction_on(chat_id: int) -> bool:
    mode = reaction_enabled.get(chat_id)
    if mode is None:
        user = await reaction_statusdb.find_one({"chat_id": chat_id})
        if not user:
            reaction_enabled[chat_id] = True
            return True
        reaction_enabled[chat_id] = False
        return False
    return mode


async def reaction_on(chat_id: int):
    reaction_enabled[chat_id] = True
    user = await reaction_statusdb.find_one({"chat_id": chat_id})
    if user:
        await reaction_statusdb.delete_one({"chat_id": chat_id})


async def reaction_off(chat_id: int):
    reaction_enabled[chat_id] = False
    user = await reaction_statusdb.find_one({"chat_id": chat_id})
    if not user:
        await reaction_statusdb.insert_one({"chat_id": chat_id})
