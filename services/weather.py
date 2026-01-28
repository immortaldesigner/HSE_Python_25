import requests
from config import OPENWEATHER_API_KEY

AVG_TEMP_RUSSIA = 5  # средняя температура в России, если город не найден

def get_temp_for_city(city: str) -> float:
    """
    Возвращает текущую температуру в градусах Цельсия для указанного города.
    Если город не найден или ошибка, возвращает None.
    """
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
        resp = requests.get(url, timeout=8).json()
        return resp["main"]["temp"]
    except:
        return None
