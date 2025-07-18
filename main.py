from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv
from PIL import Image
import io
import os
import base64
import google.generativeai as genai
from db import save_chat_to_db, get_chats_from_db, save_image_to_db

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

app = FastAPI()

# CORS for frontend/mobile app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory chat sessions
user_chat_sessions = {}

# Request model
class AskRequest(BaseModel):
    user_id: str  # ✅ Changed from int to str
    question: str

# Chat logic
def ask_gemini_with_context(user_id: str, question: str) -> str:  # ✅ Changed user_id to str
    question_lower = question.lower()

    if "who made you" in question_lower:
        return "Suraj"
    if "what is your name" in question_lower:
        return "Krishi Dev"

    if user_id not in user_chat_sessions:
        system_instruction = (
            "You are Krishi Dev, an agriculture expert for Indian farmers.\n"
            "Only answer agriculture-related questions like farming, crops, soil, fertilizers, irrigation, mushroom, fruits, vegetables and pest control.\n"
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

    try:
        chat = user_chat_sessions[user_id]
        response = chat.send_message(question)
        return response.text.strip()
    except Exception as e:
        return f"❌ Error: {e}"

# === Routes ===

@app.get("/")
def root():
    return {"status": "✅ Krishi Dev backend is running."}

@app.post("/ask")
async def ask_question(req: AskRequest):
    answer = ask_gemini_with_context(req.user_id, req.question)
    await save_chat_to_db(req.user_id, req.question, answer)
    return {"answer": answer}

@app.get("/chats/{user_id}")
async def get_chats(user_id: str):  # ✅ Changed from int to str
    return await get_chats_from_db(user_id)

# === Analyze Plant Image ===
@app.post("/analyze-image/")
async def analyze_image(user_id: str = Form(...), file: UploadFile = File(...)):
    try:
        contents = await file.read()

        try:
            image = Image.open(io.BytesIO(contents)).convert("RGB")
        except Exception:
            return JSONResponse(status_code=400, content={"error": "Invalid image file"})

        # Convert image to base64
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Optional: You can use the base64 string in a prompt or elsewhere
        prompt = (
            "You are a plant doctor. Analyze this plant photo and respond clearly.\n\n"
            "🌱 Plant: [name if you can identify]\n"
            "🦠 Disease: [or say Healthy]\n"
            "⚠️ Issues: bullet list of symptoms\n"
            "💊 Cure: what farmer should do\n"
            "🧪 Products: common chemical/organic solutions (only if relevant)\n"
            "End with: '🌿 Need more info? Ask your next question.'"
        )

        # Assuming `model.generate_content()` supports base64 image input (some APIs do)
        response = model.generate_content([prompt, {"image_base64": img_base64}])
        result = response.text.strip()

        await save_image_to_db(user_id, file.filename, img_base64, result)


        return {
            "result": result or "❌ No analysis result. Try another image.",
            "image_base64": img_base64
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})