# server.py
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import requests
import uuid
import os
from typing import Dict
from fastapi.responses import JSONResponse
import dotenv
import json

dotenv.load_dotenv()

# Путь к файлу хранения учеников
STORAGE_API_URL = os.getenv("STORAGE_API_URL")
# Загрузка или создание базы
def load_students_from_api() -> Dict[str, str]:
    print(STORAGE_API_URL)
    
    try:
        response = requests.get(f"{STORAGE_API_URL}/students", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"[load_students] Ошибка ответа API: {response.status_code}")
    except Exception as e:
        print(f"[load_students] Не удалось загрузить студентов: {e}")
    return {}  # Возврат пустого словаря при ошибке


def save_students_to_api():
    try:
        response = requests.post(
           f"{STORAGE_API_URL}/students",
            json=user_tokens,
            timeout=5
        )
        if response.status_code != 200:
            print(f"[save_students] Ошибка при сохранении студентов: {response.status_code}")
    except Exception as e:
        print(f"[save_students] Сервис сохранения недоступен: {e}")

app = FastAPI()

# Хранилище зарегистрированных "ключей"
  # token: name
user_tokens: Dict[str, str] = load_students_from_api()

# Настройки API внешнего сервиса (DeepSeek / Intelligence.io)
API_KEY = os.getenv("API_KEY")  # 🔐 Настоящий ключ
API_URL = "https://api.intelligence.io.solutions/api/v1"

# Модель запроса от ученика
class RegisterRequest(BaseModel):
    name: str
    surname: str

from typing import List, Dict

class AskRequest(BaseModel):
    token: str
    model: str
    messages: List[Dict]  # Пример: [{"role": "user", "content": "Привет!"}]

class AskModel(BaseModel):
    token: str
  
@app.post("/register")
def register_student(data: RegisterRequest):
    # Генерация уникального токена
    if data.name is None or data.surname is None:
        raise HTTPException(status_code=400, detail="Имя и фамилия должны быть указаны")
    # Генерация уникального токена
    token = str(uuid.uuid4())
    full_name = f"{data.name} {data.surname}"
    user_tokens[token] = full_name
    save_students_to_api()# 💾 Сохраняем в файл
    return {"token": token, "message": f"Добро пожаловать, {full_name}!"}

@app.post("/models")
def fetch_models_from_deepseek(data:AskModel):
    if data.token not in user_tokens:
        raise HTTPException(status_code=403, detail="Неверный или просроченный токен доступа")
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    response = requests.get(f"{API_URL}/models", headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=response.text)

@app.post("/ask")
def ask_ai(data: AskRequest):
    # Проверка токена
    if data.token not in user_tokens:
        raise HTTPException(status_code=403, detail="Неверный или просроченный токен доступа")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": data.model,
        "messages": data.messages  # ← теперь весь массив передаёт ученик
    }

    response = requests.post(f"{API_URL}/chat/completions", headers=headers, json=payload)

    if response.status_code == 200:
        ai_response = response.json()
        return {
            "student": user_tokens[data.token],
            "response": ai_response
        }
    else:
        raise HTTPException(status_code=response.status_code, detail=response.text)
TEACHER_SECRET = "teacher123"  # Придумай пароль
#GET https://<адрес_ngrok>/students?secret=teacher123
@app.get("/students")
def list_students(secret: str):
    if secret != TEACHER_SECRET:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    return {"registered_students": [{"name": name, "token": token} for token, name in user_tokens.items()]}

#ЗАПУСК СЕРВЕР
#uvicorn server:app --host 0.0.0.0 --port 8000
#ngrok http 8000
