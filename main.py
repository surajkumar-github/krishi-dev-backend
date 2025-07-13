from fastapi import FastAPI, UploadFile, File, Form
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

# === CORS for React Native / Expo ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can change this to specific frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Memory store for chat history ===
user_chat_history = {}

# === Helper: Gemini Q&A with chat context ===
def ask_gemini_with_context(user_id: int, question: str) -> str:
    try:
        if user_id not in user_chat_history:
            user_chat_history[user_id] = [
                {
                    "role": "user",
                    "parts": [{"text": "You are an agriculture expert. Help Indian farmers with short, clear advice."}]
                },
                {
                    "role": "model",
                    "parts": [{"text": "Understood. I will assist with agriculture-related help."}]
                }
            ]
        user_chat_history[user_id].append({"role": "user", "parts": [{"text": question}]})
        chat = model.start_chat(history=user_chat_history[user_id])
        response = chat.send_message(question)
        user_chat_history[user_id].append({"role": "model", "parts": [{"text": response.text}]})
        user_chat_history[user_id] = user_chat_history[user_id][-20:]  # Trim to last 20 messages
        return response.text.strip()
    except Exception as e:
        return f"❌ Error: {e}"

# === Helper: Analyze plant image with Gemini ===
def analyze_image_with_gemini(image_path: str) -> str:
    try:
        with open(image_path, "rb") as img_file:
            image_data = img_file.read()

        prompt = (
            "You are an agriculture expert helping Indian farmers.\n"
            "Analyze the attached image of a plant. Detect any disease or nutrient deficiency.\n"
            "Format the response like this:\n\n"
            "🌱 Plant: [Plant Name or Unknown]\n"
            "🦠 Disease: [Disease Name or 'Healthy']\n"
            "⚠️ Precautions:\n- Bullet 1\n- Bullet 2\n"
            "💊 Cure: [Steps to take]\n"
            "🧪 Recommended Products: [Affordable Options]\n"
        )

        response = model.generate_content([
            {"role": "user", "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": image_data}}
            ]}
        ])
        return response.text.strip()
    except Exception as e:
        return f"❌ Image analysis error: {e}"

# === API Schemas ===
class AskRequest(BaseModel):
    user_id: int
    question: str

# === Endpoints ===

@app.post("/ask")
async def ask_question(req: AskRequest):
    answer = ask_gemini_with_context(req.user_id, req.question)
    return {"answer": answer}

@app.post("/analyze")
async def analyze_image(
    user_id: int = Form(...),  # Important: Accept user_id as form field
    file: UploadFile = File(...)
):
    try:
        save_path = f"/tmp/{user_id}_uploaded.jpg"
        with open(save_path, "wb") as f:
            f.write(await file.read())

        result = analyze_image_with_gemini(save_path)
        return {"result": result}
    except Exception as e:
        return {"result": f"❌ Server error: {e}"}

@app.get("/")
def root():
    return {"status": "✅ Krishi Dev backend is running."}
