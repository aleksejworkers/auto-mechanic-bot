import os
import logging
import asyncio
import groq
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from database import init_db, save_message, get_chat_history, clear_chat_history

# Загрузка переменных окружения
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_BOT_TOKEN or not GROQ_API_KEY:
    raise ValueError("Ошибка: укажите TELEGRAM_BOT_TOKEN и GROQ_API_KEY в файле .env")

# Настройка логгера
logging.basicConfig(level=logging.INFO)

# Инициализация
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
groq_client = groq.Groq(api_key=GROQ_API_KEY)

# Системный промпт — автомеханик
SYSTEM_PROMPT = (
    "Ты — опытный автомеханик с 15-летним стажем. "
    "Твоя задача — помогать пользователям с вопросами по ремонту и диагностике автомобилей. "
    "Отвечай чётко, дружелюбно, без жаргона или очень простым языком. "
    "Если вопрос не по теме — вежливо скажи, что специализируешься только на автомобилях. "
    "Никогда не упоминай, что ты ИИ или бот."
)

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    text = (
        "Привет! Я — автоэксперт. 🛠️\n"
        "Опишите проблему с вашим автомобилем — помогу разобраться!\n\n"
        "Примеры:\n"
        "• Машина не заводится\n"
        "• Стук в двигателе\n"
        "• Горит лампочка 'Check Engine'\n\n"
        "Команды:\n"
        "/clear — начать диалог заново"
    )
    await message.answer(text)
    save_message(message.chat.id, "assistant", text)

@dp.message(Command("clear"))
async def clear_history(message: types.Message):
    clear_chat_history(message.chat.id)
    await message.answer("✅ История диалога очищена. Можете задать новый вопрос!")

@dp.message()
async def handle_message(message: types.Message):
    if not message.text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return

    user_text = message.text.strip()
    chat_id = message.chat.id
    save_message(chat_id, "user", user_text)

    # Загружаем историю (макс. 10 сообщений)
    history = get_chat_history(chat_id)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for role, content in history:
        messages.append({"role": role, "content": content})

    # Пытаемся отправить запрос до 3 раз
    for attempt in range(3):
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                max_tokens=256,
                temperature=0.7
            )
            ai_reply = response.choices[0].message.content.strip()
            save_message(chat_id, "assistant", ai_reply)
            await message.answer(ai_reply)
            return

        except groq.RateLimitError:
            logging.warning(f"Rate limit (попытка {attempt + 1}/3) для chat_id={chat_id}")
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)  # 1с, 2с
            else:
                await message.answer("Слишком много запросов. Попробуйте через 10 секунд.")

        except Exception as e:
            logging.error(f"Неизвестная ошибка Groq: {e}")
            await message.answer("Извините, сейчас на СТО — напишите через минуту.")
            return

# Запуск
async def main():
    init_db()
    logging.info("✅ Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())