import requests

OPEN_METEO = "https://api.open-meteo.com/v1/forecast"

HOURLY = ",".join([
    "temperature_2m", "relative_humidity_2m", "dew_point_2m", "precipitation",
    "rain", "snowfall", "snow_depth", "weather_code", "pressure_msl",
    "cloud_cover", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high",
    "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "soil_temperature_0cm",
    "soil_moisture_0_to_1cm"
])

CURRENT = ",".join([
    "temperature_2m", "relative_humidity_2m", "dew_point_2m", "precipitation",
    "rain", "snowfall", "snow_depth", "weather_code", "pressure_msl", "cloud_cover",
    "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"
])

def fetch_weather(lat, lon):
    params = {
        "latitude": lat, "longitude": lon,
        "current": CURRENT,
        "hourly": HOURLY,
        "past_hours": 24,
        "forecast_hours": 4,
        "timezone": "auto"
    }
    r = requests.get(OPEN_METEO, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    return data

def fetch_weatherapi(lat, lon, api_key):
    if not api_key:
        return {}, None
    try:
        r = requests.get("https://api.weatherapi.com/v1/forecast.json", params={
            "key": api_key, "q": f"{lat},{lon}", "days": 1, "alerts": "yes"
        }, timeout=12)
        r.raise_for_status()
        return r.json(), None
    except requests.RequestException as e:
        return {}, str(e)
