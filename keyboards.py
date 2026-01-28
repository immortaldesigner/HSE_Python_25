from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from storage import users

# =======================
# START KB
# =======================
def start_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Старт", callback_data="start_form")]
        ]
    )

# =======================
# PROFILE KB
# =======================
def profile_kb(filled: dict):
    buttons = [
        InlineKeyboardButton(
            text=f"⚖ Вес: {filled.get('weight', '—')}",
            callback_data="edit_weight"
        ),
        InlineKeyboardButton(
            text=f"📏 Рост: {filled.get('height', '—')}",
            callback_data="edit_height"
        ),
        InlineKeyboardButton(
            text=f"🎂 Возраст: {filled.get('age', '—')}",
            callback_data="edit_age"
        ),
        InlineKeyboardButton(
            text=f"🏃 Активность: {filled.get('activity', '—')}",
            callback_data="edit_activity"
        ),
        InlineKeyboardButton(
            text=f"🌍 Город: {filled.get('city', '—')}",
            callback_data="edit_city"
        ),
    ]

    keyboard = [[b] for b in buttons]

    # Добавляем кнопку "Готово", если все поля заполнены
    if all([
        filled.get("weight"),
        filled.get("height"),
        filled.get("age"),
        filled.get("activity"),
        filled.get("city"),
    ]):
        keyboard.append(
            [InlineKeyboardButton(text="✅ Готово", callback_data="done")]
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# =======================
# MAIN MENU
# =======================
def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧾 Анкета", callback_data="menu_profile")],
            [InlineKeyboardButton(text="🏋️ Тренировка", callback_data="menu_workout")],
            [InlineKeyboardButton(text="💧 Вода", callback_data="menu_water")],
            [InlineKeyboardButton(text="🍽 Еда", callback_data="menu_food")],
            [InlineKeyboardButton(text="🎯 Цель", callback_data="menu_goal")],
            [InlineKeyboardButton(text="📊 Визуализация", callback_data="menu_visualization")],  # исправлено
        ]
    )

# =======================
# FOOD MENU
# =======================
def food_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔎 По названию", callback_data="food_by_name")],
            [InlineKeyboardButton(text="📦 По штрих-коду", callback_data="food_by_barcode")],
            [InlineKeyboardButton(text="📷 По фото", callback_data="food_by_photo")],  # новая кнопка
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
        ]
    )

# =======================
# WATER MENU
# =======================
def water_menu_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💧 Добавить воды", callback_data="water_add")],
            [InlineKeyboardButton(text="📜 История", callback_data="water_history")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ]
    )

# =======================
# WORKOUT MENU
# =======================
def workout_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Дома", callback_data="workout_indoor")],
            [InlineKeyboardButton(text="🌳 На улице", callback_data="workout_outdoor")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ]
    )

def workout_type_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏃 Бег", callback_data="workout_run")],
            [InlineKeyboardButton(text="🚶 Ходьба", callback_data="workout_walk")],
            [InlineKeyboardButton(text="🦵 Приседания", callback_data="workout_squat")],
            [InlineKeyboardButton(text="📏 Планка", callback_data="workout_plank")],
            [InlineKeyboardButton(text="💪 Подтягивания", callback_data="workout_pullups")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="workout_back")]
        ]
    )

# =======================
# GOAL MENU
# =======================
def goal_menu(user_id):
    reminder = users.get(user_id, {}).get("reminder", {"enabled": False, "time": "08:00"})
    toggle_text = "✅ Вкл" if reminder["enabled"] else "❌ Выкл"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⏰ Время: {reminder['time']}",
                    callback_data="goal_time"
                ),
                InlineKeyboardButton(
                    text=toggle_text,
                    callback_data="goal_toggle"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="back_to_menu"
                )
            ]
        ]
    )
