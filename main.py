from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import os
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# === Configure Gemini ===
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="gemini-2.0-flash")

# === FastAPI setup ===
app = FastAPI()

# === Enable CORS (for mobile / frontend) ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set specific domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Store chat sessions ===
user_chat_sessions = {}

# === Data model for /ask ===
class AskRequest(BaseModel):
    user_id: int
    question: str

# === Main logic ===
def ask_gemini_with_context(user_id: int, question: str) -> str:
    question_lower = question.lower()

    # === Handle identity Qs ===
    if "who made you" in question_lower or "who created you" in question_lower:
        return "Suraj"
    if "what is your name" in question_lower or "your name" in question_lower:
        return "Krishi Dev"

    # === Start new chat if needed ===
    if user_id not in user_chat_sessions:
        system_instruction = (
            "You are Krishi Dev, an agriculture expert for Indian farmers.\n"
            "Only answer agriculture-related questions like farming, crops, soil, fertilizers, irrigation, and pest control.\n"
            "Do NOT answer non-agriculture topics like politics, celebrities, math, science, coding, GK, or English.\n"
            "If the question is unrelated, respond with: '❌ I can only answer agriculture-related questions.'\n"
            "Never say you're AI, Gemini, or Google.\n"
            "Keep replies short, clear, and end with: '🌿 Need more info? Ask your next question.'"
        )
        chat = model.start_chat(history=[
            {"role": "user", "parts": [{"text": system_instruction}]},
            {"role": "model", "parts": [{"text": "Understood. I will follow these rules."}]}
        ])
        user_chat_sessions[user_id] = chat

    # === Continue chat with memory ===
    try:
        chat = user_chat_sessions[user_id]
        response = chat.send_message(question)
        return response.text.strip()
    except Exception as e:
        return f"❌ Error: {e}"

# === API endpoints ===
@app.post("/ask")
async def ask_question(req: AskRequest):
    answer = ask_gemini_with_context(req.user_id, req.question)
    return {"answer": answer}

@app.get("/")
def root():
    return {"status": "✅ Krishi Dev backend is running."}
