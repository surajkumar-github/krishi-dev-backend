from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")

client = AsyncIOMotorClient(MONGODB_URI)
db = client.krishi_dev

async def save_chat_to_db(user_id: int, question: str, response: str):
    await db.chats.insert_one({
        "user_id": user_id,
        "question": question,
        "response": response,
        "timestamp": datetime.utcnow()
    })

async def get_chats_from_db(user_id: int):
    cursor = db.chats.find({"user_id": user_id}).sort("timestamp", 1)
    chats = []
    async for chat in cursor:
        chats.append({
            "question": chat["question"],
            "response": chat["response"],
            "timestamp": chat.get("timestamp")
        })
    return chats
