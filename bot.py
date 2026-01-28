import asyncio
from datetime import datetime
from io import BytesIO
import sys
import logging
import json
import os
import atexit

import matplotlib.pyplot as plt
import numpy as np
from pyzxing import BarCodeReader

from aiogram import Bot, Dispatcher, F, BaseMiddleware
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter, CommandStart

from states import ProfileForm, FoodForm, WaterForm, WorkoutForm
from keyboards import (
    start_kb, profile_kb, main_menu, water_menu_kb, food_menu,
    workout_menu, workout_type_menu, goal_menu
)
from services.food import FoodAPI
from services.weather import get_temp_for_city, AVG_TEMP_RUSSIA

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден!")

bot = Bot(BOT_TOKEN)

dp = Dispatcher()

# Логирование
sys.stdout.reconfigure(line_buffering=True)
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, Message):
            logging.info(f"user={event.from_user.id} text={event.text}")
        return await handler(event, data)

dp.message.middleware(LoggingMiddleware())

# === ХРАНЕНИЕ ДАННЫХ ===

users = {}

def save_users():
    with open("users.json", "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_users():
    global users
    if os.path.exists("users.json"):
        with open("users.json", "r", encoding="utf-8") as f:
            users = json.load(f)
    else:
        users = {}



# ПОЛЯ ПРОФИЛЯ
FIELD_DESCRIPTIONS = {
    "weight": "⚖ Вес (кг)\nВведите ваш вес в килограммах.\nНапример: 75",
    "height": "📏 Рост (см)\nВведите ваш рост в сантиметрах.\nНапример: 180",
    "age": "🎂 Возраст\nВведите ваш возраст.\nНапример: 25",
    "activity": (
        "🏃 Уровень активности\n"
        "1 — минимальная\n"
        "2 — лёгкая\n"
        "3 — средняя\n"
        "4 — высокая\n"
        "5 — очень высокая"
    ),
    "city": "🌍 Город\nВведите название города (только буквы)"
}

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Привет! 👋\nНажми кнопку, чтобы начать:",
        reply_markup=start_kb()
    )

# АНКЕТА
@dp.callback_query(F.data == "start_form")
async def start_form(callback: CallbackQuery):
    user_id = callback.from_user.id
    users.setdefault(user_id, {
        "weight": None, "height": None, "age": None,
        "activity": None, "city": None, "profile_msg_id": None
    })
    msg = await callback.message.edit_text("📋 Анкета:", reply_markup=profile_kb(users[user_id]))
    users[user_id]["profile_msg_id"] = msg.message_id

# РЕДАКТИРОВАНИЕ ПОЛЯ
@dp.callback_query(F.data.startswith("edit_"))
async def edit_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.replace("edit_", "")
    await state.set_state(ProfileForm.weight)
    await state.update_data(edit_field=field)
    text = FIELD_DESCRIPTIONS.get(field, "Введите значение:")
    msg = await callback.message.answer(text)
    await state.update_data(last_prompt=msg.message_id)

# СОХРАНЕНИЕ ЗНАЧЕНИЯ
@dp.message(StateFilter(ProfileForm.weight))
async def save_value(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    field = data["edit_field"]

    value = message.text.strip()
    users.setdefault(user_id, {"weight": None, "height": None, "age": None,
                                "activity": None, "city": None,
                                "profile_msg_id": data.get("profile_msg_id")})
    error_messages = data.get("error_messages", [])
    error_user_messages = data.get("error_user_messages", [])

    try:
        if field in ["weight", "height", "age", "activity"]:
            value = int(value)
            if field == "weight" and not 30 <= value <= 300: raise ValueError
            if field == "height" and not 100 <= value <= 250: raise ValueError
            if field == "age" and not 5 <= value <= 120: raise ValueError
            if field == "activity" and not 1 <= value <= 5: raise ValueError
        elif field == "city":
            if not value.isalpha(): raise ValueError
    except ValueError:
        error_user_messages.append(message.message_id)
        msg = await message.answer("❌ Некорректное значение.\nПопробуйте ещё раз 👇")
        error_messages.append(msg.message_id)
        await state.update_data(error_messages=error_messages, error_user_messages=error_user_messages)
        return

    for msg_id in error_messages + error_user_messages + [data.get("last_prompt")]:
        if msg_id:
            try: await message.bot.delete_message(message.chat.id, msg_id)
            except: pass
    try: await message.delete()
    except: pass

    await state.update_data(error_messages=[], error_user_messages=[])
    users[user_id][field] = value
    save_users() 
    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=users[user_id]["profile_msg_id"],
        text="📋 Анкета:",
        reply_markup=profile_kb(users[user_id])
    )
    await state.clear()

# АНКЕТА ЗАВЕРШЕНА
@dp.callback_query(F.data == "done")
async def done(callback: CallbackQuery):
    await callback.message.edit_text("✅ Анкета заполнена!\n\nВыберите действие:", reply_markup=main_menu())

# ПРОФИЛЬ
@dp.callback_query(F.data == "menu_profile")
async def menu_profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    # Создаём словарь пользователя, если ещё нет
    users.setdefault(user_id, {
        "weight": None, "height": None, "age": None,
        "activity": None, "city": None, "profile_msg_id": None
    })

    profile_msg_id = users[user_id].get("profile_msg_id")

    if profile_msg_id:
        try:
            # Пытаемся отредактировать старое сообщение
            await callback.message.bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=profile_msg_id,
                text="📋 Ваш профиль:",
                reply_markup=profile_kb(users[user_id])
            )
        except Exception as e:
            # Если не удалось — отправляем новое сообщение и обновляем ID
            logging.warning(f"Cannot edit message {profile_msg_id}: {e}")
            msg = await callback.message.answer(
                "📋 Ваш профиль:",
                reply_markup=profile_kb(users[user_id])
            )
            users[user_id]["profile_msg_id"] = msg.message_id
    else:
        # Если старого сообщения нет — отправляем новое
        msg = await callback.message.answer(
            "📋 Ваш профиль:",
            reply_markup=profile_kb(users[user_id])
        )
        users[user_id]["profile_msg_id"] = msg.message_id

# ЕДА
@dp.callback_query(F.data == "menu_food")
async def menu_food(callback: CallbackQuery):
    await callback.message.edit_text("🍽 Добавление еды:", reply_markup=food_menu())

# 1) По названию
@dp.callback_query(F.data == "food_by_name")
async def food_by_name(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("🍎 Введите название продукта:")
    await state.set_state(FoodForm.food_name)

# 2) По штрихкоду
@dp.callback_query(F.data == "food_by_barcode")
async def food_by_barcode(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("📦 Введите штрих-код:")
    await state.set_state(FoodForm.food_barcode)

# 3) По фото
@dp.callback_query(F.data == "food_by_photo")
async def food_by_photo(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("📷 Отправьте фото продукта с видимым штрихкодом:")
    await state.set_state(FoodForm.food_photo)

# ОБРАБОТКА НАЗВАНИЯ
@dp.message(StateFilter(FoodForm.food_name))
async def process_food_name(message: Message, state: FSMContext):
    api = FoodAPI()
    result = api.search_food(message.text)
    foods = result.get("foods", {}).get("food", [])
    if not foods:
        await message.answer("❌ Продукт не найден.")
        await state.clear()
        return
    food = foods[0]
    await state.update_data(
        food_name=food.get("name"),
        calories_per_portion=food.get("calories") or 0,
        serving_weight=food.get("serving_weight") or 100
    )
    await message.answer(f"🍎 Найден продукт: {food.get('name')}\nВведите массу в граммах:")
    await state.set_state(FoodForm.food_weight)

# ОБРАБОТКА ШТРИХКОДА
@dp.message(StateFilter(FoodForm.food_barcode))
async def process_food_barcode(message: Message, state: FSMContext):
    api = FoodAPI()
    result = api.get_by_barcode(message.text.strip())
    food = result.get("food", {})
    name = food.get("name")
    if name == "Unknown":
        await message.answer("❌ Продукт не найден.")
        await state.clear()
        return
    await state.update_data(
        food_name=name,
        calories_per_portion=food.get("calories") or 0,
        serving_weight=food.get("serving_weight") or 100
    )
    await message.answer(f"🍎 Найден продукт: {name}\nВведите массу в граммах:")
    await state.set_state(FoodForm.food_weight)

# ОБРАБОТКА ФОТО
@dp.message(
    StateFilter(FoodForm.food_photo),
    F.content_type == ContentType.PHOTO
)
async def process_food_photo(message: Message, state: FSMContext):
    # 1. Получаем фото и сохраняем временно
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    path = f"temp_{photo.file_id}.jpg"
    await bot.download_file(file.file_path, destination=path)

    # 2. Распознаём штрихкод через pyzxing
    result = reader.decode(path)

    if not result or result[0].get("parsed") is None:
        await message.answer("❌ Штрихкод не найден на фото.")
        return

    barcode_data = result[0]["parsed"]

    # 3. Получаем продукт через API
    api = FoodAPI()
    result = api.get_by_barcode(barcode_data)
    food = result.get("food", {})
    name = food.get("name")
    if name == "Unknown":
        await message.answer("❌ Продукт не найден.")
        await state.clear()
        return

    await state.update_data(
        food_name=name,
        calories_per_portion=food.get("calories") or 0,
        serving_weight=food.get("serving_weight") or 100
    )
    await message.answer(f"🍎 Найден продукт: {name}\nВведите массу в граммах:")
    await state.set_state(FoodForm.food_weight)


# ВВОД МАССЫ
@dp.message(StateFilter(FoodForm.food_weight))
async def process_food_weight(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        weight = float(message.text)
        if weight <= 0: raise ValueError
    except:
        await message.answer("❌ Введите корректное число граммов.")
        return
    calories = data["calories_per_portion"] * weight / data["serving_weight"]
    user_id = message.from_user.id
    users.setdefault(user_id, {}).setdefault("logged_calories", 0)
    users[user_id]["logged_calories"] += calories
    await message.answer(f"🍽 {data['food_name']} — {calories:.1f} ккал для {weight} г.")
    await state.clear()


# WATER
@dp.callback_query(F.data == "menu_water")
async def menu_water(callback: CallbackQuery):
    users.setdefault(callback.from_user.id, {}).setdefault("water_log", [])
    await callback.message.edit_text("💧 Вода — выберите действие:", reply_markup=water_menu_kb())

@dp.callback_query(F.data == "water_add")
async def water_add(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("💧 Введите количество воды (мл):")
    await state.set_state(WaterForm.water_amount)

@dp.message(StateFilter(WaterForm.water_amount))
async def process_water_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0: raise ValueError
    except:
        await message.answer("❌ Введите корректное число")
        return
    user_id = message.from_user.id
    users.setdefault(user_id, {}).setdefault("water_log", [])
    users[user_id]["water_log"].append({"amount": amount, "timestamp": message.date.strftime("%d.%m %H:%M")})
    total = sum(x["amount"] for x in users[user_id]["water_log"])
    remaining = max(2000 - total, 0)
    await message.answer(f"💧 Добавлено: {amount} мл\nВсего: {total} мл\nОсталось: {remaining} мл")
    await state.clear()

# WATER HISTORY
@dp.callback_query(F.data == "water_history")
async def water_history(callback: CallbackQuery):
    user_id = callback.from_user.id
    water_log = users.get(user_id, {}).get("water_log", [])
    if not water_log:
        await callback.message.answer("💧 История воды пуста")
        return

    text_lines = []
    total = 0
    for entry in water_log:
        text_lines.append(f"{entry['timestamp']}: {entry['amount']} мл")
        total += entry["amount"]

    remaining = max(2000 - total, 0)  # стандартная цель воды, пока без расчета
    text_lines.append(f"\nВсего выпито: {total} мл\nОсталось: {remaining} мл")
    await callback.message.answer("\n".join(text_lines))

# WORKOUT
@dp.callback_query(F.data == "menu_workout")
async def workout_menu_handler(callback: CallbackQuery):
    await callback.message.edit_text("Где вы хотите тренироваться?", reply_markup=workout_menu())

@dp.callback_query(F.data == "workout_indoor")
async def workout_indoor(callback: CallbackQuery, state: FSMContext):
    await state.set_state(WorkoutForm.location)
    await state.update_data(location="indoor")
    await callback.message.edit_text("Вы выбрали *Дома*. 🏠\nВыберите вид тренировки:", reply_markup=workout_type_menu())

@dp.callback_query(F.data == "workout_outdoor")
async def workout_outdoor(callback: CallbackQuery, state: FSMContext):
    await state.set_state(WorkoutForm.location)
    await state.update_data(location="outdoor")
    await callback.message.edit_text("Вы выбрали *На улице*. 🌳\nПолучаем температуру...")
    city = users.get(callback.from_user.id, {}).get("city")
    temp = get_temp_for_city(city) if city else AVG_TEMP_RUSSIA
    await state.update_data(temp=temp)
    await callback.message.answer(f"Температура: {temp}°C\nВыберите вид тренировки:", reply_markup=workout_type_menu())

@dp.callback_query(lambda c: c.data.startswith("workout_") and c.data not in ["workout_indoor","workout_outdoor","workout_back"])
async def workout_type(callback: CallbackQuery, state: FSMContext):
    workout = callback.data.replace("workout_","")
    await state.update_data(type=workout)
    await callback.message.edit_text(f"Вы выбрали: {workout.replace('_',' ').title()}\nВведите длительность в минутах:")
    await state.set_state(WorkoutForm.duration)

@dp.message(StateFilter(WorkoutForm.duration))
async def process_duration(message: Message, state: FSMContext):
    data = await state.get_data()
    wtype = data.get("type")
    temp = data.get("temp", 20)
    try:
        duration = int(message.text)
        if duration <= 0: raise ValueError
    except:
        await message.answer("❌ Введите корректное число минут.")
        return
    weight = users.get(message.from_user.id, {}).get("weight") or 70
    kcal = {"run":0.12, "walk":0.05, "squat":0.1, "plank":0.08, "pullups":0.11}.get(wtype,0)*weight*duration
    water_loss = duration * (0.5 + max(temp-20,0)*0.02)
    await message.answer(f"🏋️ Тренировка: {wtype.title()}\n⏱ Длительность: {duration} мин\n🔥 Потрачено калорий: {kcal:.1f} ккал\n💧 Потеря воды: {water_loss:.1f} мл")

    user_id = message.from_user.id
    users.setdefault(user_id, {}).setdefault("workouts", [])
    users[user_id]["workouts"].append({
        "type": wtype,
        "duration": duration,
        "kcal": kcal,
        "date": message.date.strftime("%d.%m")
    })

    await state.clear()
    await message.answer("Выберите действие:", reply_markup=main_menu())

@dp.callback_query(F.data == "workout_back")
async def workout_back(callback: CallbackQuery):
    await callback.message.edit_text("Выберите действие:", reply_markup=main_menu())

# GOALS
@dp.callback_query(F.data == "menu_goal")
async def menu_goal_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    goals = calculate_daily_goal(user_id)

    text = (
        f"🎯 Ежедневная цель:\n\n"
        f"🔥 Калории: {goals['calories_done']} / {goals['calories_goal']} ккал\n"
        f"💧 Вода: {goals['water_done']} / {goals['water_goal']} мл\n\n"
        f"⏰ Напоминания о цели:"
    )

    await callback.message.edit_text(text, reply_markup=goal_menu(user_id))

@dp.callback_query(F.data == "goal_toggle")
async def goal_toggle(callback: CallbackQuery):
    reminder = users.setdefault(callback.from_user.id, {}).setdefault("reminder", {"enabled": False, "time":"08:00"})
    reminder["enabled"] = not reminder["enabled"]
    await callback.message.edit_text("🎯 Цели и напоминания:", reply_markup=goal_menu(callback.from_user.id))

@dp.callback_query(F.data == "goal_time")
async def goal_time(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите время напоминания в формате ЧЧ:ММ (например, 08:30):")
    await state.set_state("set_goal_time")

@dp.message(StateFilter("set_goal_time"))
async def process_goal_time(message: Message, state: FSMContext):
    text = message.text.strip()
    try:
        hh, mm = map(int, text.split(":"))
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            raise ValueError
    except:
        await message.answer("❌ Неверный формат. Введите ЧЧ:ММ")
        return
    reminder = users.setdefault(message.from_user.id, {}).setdefault("reminder", {"enabled": False, "time": "08:00"})
    reminder["time"] = text
    await message.answer(f"⏰ Время напоминания установлено на {text}", reply_markup=main_menu())
    await state.clear()

# GOAL CALCULATION
def calculate_daily_goal(user_id):
    user = users.get(user_id, {})
    weight = user.get("weight", 70)
    height = user.get("height", 170)
    age = user.get("age", 25)
    activity = user.get("activity", 1)

    # Калории по формуле Миффлина-Сан Жеора
    bmr = 10 * weight + 6.25 * height - 5 * age + 5  # для мужчин, для женщин -161
    # Коэффициент активности
    activity_multiplier = {1: 1.2, 2: 1.375, 3: 1.55, 4: 1.725, 5: 1.9}.get(activity, 1.2)
    calories_goal = int(bmr * activity_multiplier)

    # Вода 30 мл на кг веса
    water_goal = int(weight * 30)

    # Текущий прогресс
    water_done = sum(x["amount"] for x in user.get("water_log", []))
    calories_done = sum(x.get("kcal", 0) for x in user.get("workouts", []))  # расход калорий

    return {
        "calories_goal": calories_goal,
        "calories_done": calories_done,
        "water_goal": water_goal,
        "water_done": water_done
    }

# VISUALIZATION
async def send_workout_chart(message: Message):
    user_id = message.from_user.id
    workouts = users.get(user_id, {}).get("workouts", [])
    if not workouts:
        await message.answer("📊 Нет данных для графика")
        return
    dates = [w["date"] for w in workouts]
    calories = [w["kcal"] for w in workouts]
    plt.figure(figsize=(6,4))
    plt.plot(dates, calories, marker='o')
    plt.title("Потраченные калории")
    plt.xlabel("Дата")
    plt.ylabel("Ккал")
    plt.grid(True)
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()
    await message.answer_photo(buf)

@dp.callback_query(F.data == "menu_visualization")
async def menu_visualization(callback: CallbackQuery):
    await send_workout_chart(callback.message)

# BACK STUB
@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text("Выберите действие:", reply_markup=main_menu())

@dp.callback_query(F.data.startswith("menu_"))
async def menu_stub(callback: CallbackQuery):
    await callback.message.answer(f"👉 {callback.data.replace('menu_','').upper()} (в разработке)")

reader = None

async def main():
    global reader
    reader = BarCodeReader()
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
