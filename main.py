from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import os
from dotenv import load_dotenv
import re

# === Load environment variables ===
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# === Configure Gemini ===
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="gemini-2.0-flash")

# === FastAPI setup ===
app = FastAPI()

# === CORS setup ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Chat history per user ===
user_chat_history = {}

# === Keywords to filter personal/non-agriculture questions ===
PERSONAL_QUESTIONS = {
    "who made you": "Suraj",
    "who created you": "Suraj",
    "your name": "Krishi Dev",
    "what is your name": "Krishi Dev",
}

# === Helper: Check if question is related to agriculture ===
def is_agriculture_question(text: str) -> bool:
    ag_keywords = [
        "crop", "soil", "fertilizer", "plant", "harvest", "irrigation",
        "pesticide", "weather", "farm", "agriculture", "farming", "disease",
        "yield", "manure", "spray", "weed", "insect", "seed", "land"
    ]
    return any(word in text.lower() for word in ag_keywords)

# === Helper: Clean Gemini output ===
def format_response(text: str) -> str:
    lines = text.strip().split("\n")
    short_answer = lines[0].strip() if lines else text.strip()
    return f"{short_answer}\n\n🌿 Need more info? Ask your next question."

# === Gemini-based Q&A ===
def ask_gemini_with_context(user_id: int, question: str) -> str:
    question_lower = question.lower()

    # Personal / identity-based custom answers
    for key, value in PERSONAL_QUESTIONS.items():
        if key in question_lower:
            return value

    # Restrict to agriculture questions only
    if not is_agriculture_question(question):
        return "❌ I can only answer questions related to agriculture. Please ask something about farming, crops, or soil."

    try:
        if user_id not in user_chat_history:
            user_chat_history[user_id] = [
                {
                    "role": "user",
                    "parts": [{"text": "You are an agriculture expert. Give short, clear answers only about Indian farming. Never say you are an AI or Gemini. Ask if the user wants more details after each reply."}]
                },
                {
                    "role": "model",
                    "parts": [{"text": "Understood. I will give short, agriculture-only replies and suggest follow-up."}]
                }
            ]
        user_chat_history[user_id].append({"role": "user", "parts": [{"text": question}]})
        chat = model.start_chat(history=user_chat_history[user_id])
        response = chat.send_message(question)
        user_chat_history[user_id].append({"role": "model", "parts": [{"text": response.text}]})
        user_chat_history[user_id] = user_chat_history[user_id][-20:]

        return format_response(response.text)

    except Exception as e:
        return f"❌ Error: {e}"

# === Request Schema ===
class AskRequest(BaseModel):
    user_id: int
    question: str

# === Endpoints ===

@app.post("/ask")
async def ask_question(req: AskRequest):
    answer = ask_gemini_with_context(req.user_id, req.question)
    return {"answer": answer}

@app.get("/")
def root():
    return {"status": "✅ Krishi Dev backend is running."}
