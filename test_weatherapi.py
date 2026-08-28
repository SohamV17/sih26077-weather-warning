import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("WEATHER_API_KEY")

url = "https://api.weatherapi.com/v1/forecast.json"

params = {
    "key": API_KEY,
    "q": "18.5204,73.8567",
    "days": 1,
    "alerts": "yes"
}

response = requests.get(
    url,
    params=params,
    timeout=10
)

print("Status:", response.status_code)

data = response.json()

print(data)