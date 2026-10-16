import os
import requests
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, Router, html
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

# Завантажуємо змінні середовища з файлу .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")

bot = Bot(token=TOKEN)
router = Router()

# Визначаємо старти для машини станів (FSM)
class TripState(StatesGroup):
    waiting_for_city = State()
    waiting_for_date = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await message.answer("Привіт! Введіть назву міста, куди плануєте подорож:")
    await state.set_state(TripState.waiting_for_city)

@router.message(TripState.waiting_for_city)
async def process_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Введіть дату подорожі (наприклад, у форматі ДД.ММ або просто текстом):")
    await state.set_state(TripState.waiting_for_date)

@router.message(TripState.waiting_for_date)
async def process_date(message: Message, state: FSMContext):
    user_data = await state.get_data()
    city = user_data["city"]
    travel_date = message.text

    # Запит до OpenWeatherMap API
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_KEY}&units=metric&lang=ua"
    response = requests.get(url)

    if response.status_code != 200:
        await message.answer(f"Не вдалося знайти погоду для міста '{city}'. Перевірте назву.")
        await state.clear()
        return

    data = response.json()
    temp = data["main"]["temp"]
    weather_desc = data["weather"][0]["description"]
    rain_expected = "дощ" in weather_desc.lower() or "опади" in weather_desc.lower()

    # Алгоритм генерації чек-листа
    checklist = ["📋 <b>Чек-лист речей у подорож:</b>", "• Документи та квитки", "• Зарядний пристрій / Powerbank"]
    
    if temp < 10:
        checklist.append("🧥 Теплий одяг (куртка, светр)")
        checklist.append("🧣 Шапка та рукавички")
    elif temp < 20:
        checklist.append("👕 Легка куртка або світшот")
    else:
        checklist.append("🕶 Сонцезахисні окуляри та крем")
        checklist.append("🧢 Головний убір від сонця")

    if rain_expected or temp < 15:
        checklist.append("☔ Парасолька або дощовик")

    result_text = (
        f"🌆 Місто: <b>{city}</b>\n"
        f"📅 Дата: <b>{travel_date}</b>\n"
        f"🌡 Погода: <b>{temp}°C, {weather_desc}</b>\n\n"
        + "\n".join(checklist)
    )

    await message.answer(result_text, parse_mode="HTML")
    await state.clear()

async def main():
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())