import aiohttp
from config import OPENWEATHER_API_KEY

async def get_weather(city: str) -> dict | None:
    if not OPENWEATHER_API_KEY:
        return None
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
        "lang": "ru",
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
    if "main" not in data:
        return None
    temp = int(data["main"]["temp"])
    description = data["weather"][0]["description"].capitalize()
    if temp >= 25:
        advice = "Не забудь надеть доспехи от жара!"
    elif temp <= 5:
        advice = "Лучше утеплиться и взять волшебный плащ."
    else:
        advice = "Погода спокойная, пора отправляться в странствие."
    return {
        "city": data.get("name", city),
        "temp": temp,
        "description": description,
        "advice": advice,
    }
