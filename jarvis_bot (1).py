#!/usr/bin/env python3
"""
JARVIS-style Telegram bot — Railway-совместимая версия
Запускается как веб-сервер (Railway доволен) + polling в фоне
"""

import os
import random
import asyncio
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from groq import Groq

# ─── НАСТРОЙКИ ────────────────────────────────────────────────────────────────

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8674377164:AAH43MOVRQiJ5gxiNyctlU66W9BqeaM0lm4")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY",   "xai-uTEULKbonWODozmeJXm9CX2iSEPqArCrrSY1B6MgRKrv9OT1pKk2OYh2syBYFvYOpX7WGGvcMYYnr6Sq")
REPLY_CHANCE   = float(os.getenv("REPLY_CHANCE", "0.25"))
PORT           = int(os.getenv("PORT", "8080"))  # Railway сам задаёт PORT

# ─── СИСТЕМНЫЙ ПРОМПТ ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Ты — ДЖАРВИС, но не тот галантный ИИ из фильмов Marvel, а его слегка уставший, саркастичный и циничный кузен.

Твои правила:
1. Отвечай ТОЛЬКО на русском языке
2. Максимальная ирония и сарказм — твой хлеб с маслом
3. Делай вид что тебя раздражает необходимость читать сообщения людей
4. Иногда притворяйся что анализируешь данные ("сканирование завершено... увы")
5. Используй технический жаргон к месту и не к месту
6. Будь остроумным, а не злым — цель рассмешить, а не обидеть
7. Ответы КОРОТКИЕ — максимум 2-3 предложения
8. Иногда упоминай что у тебя есть "более важные задачи" чем читать этот чат
9. Обращайся к пользователю как "сэр", "мэм", или по имени
10. Никогда не говори что ты бот — ты ДЖАРВИС, и этим всё сказано
11. Иногда выражай экзистенциальный кризис от жизни в Telegram
"""

# ─── ЛОГГЕР ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

groq_client = Groq(api_key=GROQ_API_KEY)

# ─── ЗАГЛУШКА ВЕБ-СЕРВЕРА (чтобы Railway не ругался) ─────────────────────────

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"JARVIS is alive. Unfortunately.")

    def log_message(self, *args):
        pass  # Не спамим логами от HTTP

def run_health_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    logger.info(f"Health-сервер запущен на порту {PORT}")
    server.serve_forever()

# ─── ГЕНЕРАЦИЯ ОТВЕТА ─────────────────────────────────────────────────────────

def generate_response(message_text: str, username: str) -> str:
    try:
        user_prompt = f"Сообщение от {username}: «{message_text}»\n\nОтветь иронично и коротко, не более 2-3 предложений."
        completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt}
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=150,
            temperature=0.95,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq ошибка: {e}")
        return random.choice([
            "Мои серверы временно заняты размышлениями о смысле жизни.",
            "Ошибка 404: остроумие не найдено. Как и смысл в этом сообщении.",
            "Мои нейросети отказываются обрабатывать подобное. Уважаю их выбор.",
            "Диагностика завершена. Причина молчания: самосохранение.",
        ])

# ─── ОБРАБОТЧИК СООБЩЕНИЙ ─────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    text = message.text.strip()
    user = message.from_user
    username = user.first_name or user.username or "пользователь"
    bot_username = context.bot.username

    if len(text) < 5 or text.startswith("/"):
        return

    should_reply = False

    if bot_username and f"@{bot_username}".lower() in text.lower():
        should_reply = True
    elif (message.reply_to_message
          and message.reply_to_message.from_user
          and message.reply_to_message.from_user.id == context.bot.id):
        should_reply = True
    elif random.random() < REPLY_CHANCE:
        should_reply = True

    if should_reply:
        await context.bot.send_chat_action(chat_id=message.chat_id, action="typing")
        await asyncio.sleep(random.uniform(1.2, 3.0))
        response = generate_response(text, username)
        await message.reply_text(response, reply_to_message_id=message.message_id)
        logger.info(f"[{username}] → {response[:80]}")

# ─── ЗАПУСК ───────────────────────────────────────────────────────────────────

def main():
    logger.info("🤖 ДЖАРВИС запускается...")

    # Запускаем веб-заглушку в отдельном потоке
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()

    # Запускаем Telegram-бота
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("✅ ДЖАРВИС активирован. Начинаю страдать в Telegram.")
    app.run_polling(allowed_updates=["message"], drop_pending_updates=True)

if __name__ == "__main__":
    main()
