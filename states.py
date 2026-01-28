from aiogram.fsm.state import StatesGroup, State

class ProfileForm(StatesGroup):
    weight = State()
    height = State()
    age = State()
    activity = State()
    city = State()

class FoodForm(StatesGroup):
    food_name = State()
    food_barcode = State()
    food_photo = State()
    food_weight = State()


class WaterForm(StatesGroup):
    water_amount = State()

class WorkoutForm(StatesGroup):
    location = State()
    type = State()
    duration = State()