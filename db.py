from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")

# Connect to MongoDB
client = AsyncIOMotorClient(MONGODB_URI)
db = client.krishi_dev
chats_collection = db.chats

# ---------------------- TEXT CHAT ----------------------

async def save_chat_to_db(user_id: str, question: str, response: str):
    """
    Save a text-based chat (question & response) to the database.
    """
    await chats_collection.insert_one({
        "user_id": user_id,
        "type": "text",
        "question": question,
        "response": response,
        "timestamp": datetime.utcnow()
    })

# ---------------------- IMAGE CHAT ----------------------

async def save_image_to_db(user_id: str, image_url: str, result: str):
    """
    Save an image message (with its analysis result) to the database.
    """
    await chats_collection.insert_one({
        "user_id": user_id,
        "type": "image",
        "image_url": image_url,
        "result": result,
        "timestamp": datetime.utcnow()
    })

# ---------------------- FETCH ALL CHATS ----------------------

async def get_chats_from_db(user_id: str):
    """
    Retrieve all chats for a user (text and image), sorted by time.
    """
    cursor = chats_collection.find({"user_id": user_id}).sort("timestamp", 1)
    chats = []
    async for chat in cursor:
        chat_type = chat.get("type")
        if chat_type == "text":
            chats.append({
                "type": "text",
                "question": chat.get("question"),
                "response": chat.get("response"),
                "timestamp": chat.get("timestamp")
            })
        elif chat_type == "image":
            chats.append({
                "type": "image",
                "image_url": chat.get("image_url"),
                "result": chat.get("result"),
                "timestamp": chat.get("timestamp")
            })
    return chats

