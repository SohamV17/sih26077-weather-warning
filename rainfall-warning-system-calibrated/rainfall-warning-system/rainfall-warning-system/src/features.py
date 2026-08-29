import math

BASE_MAP = {
    "temperature": "temperature_2m", "humidity": "relative_humidity_2m", "dew_point": "dew_point_2m",
    "precipitation": "precipitation", "rain": "rain", "snowfall": "snowfall", "snow_depth": "snow_depth",
    "weather_code": "weather_code", "pressure": "pressure_msl", "cloud_cover": "cloud_cover",
    "cloud_low": "cloud_cover_low", "cloud_mid": "cloud_cover_mid", "cloud_high": "cloud_cover_high",
    "wind_speed": "wind_speed_10m", "wind_direction": "wind_direction_10m", "wind_gusts": "wind_gusts_10m",
    "soil_temperature": "soil_temperature_0cm", "soil_moisture": "soil_moisture_0_to_1cm"
}

def v(arr, i, default=0.0):
    try:
        x = arr[i]
        return 0.0 if x is None else float(x)
    except (IndexError, TypeError, ValueError):
        return float(default)

def build_row(hourly, i, lat, lon, elevation):
    row = {}
    for feature, source in BASE_MAP.items():
        row[feature] = v(hourly.get(source, []), i)
    rain = hourly.get("rain", hourly.get("precipitation", []))
    temp = hourly.get("temperature_2m", [])
    hum = hourly.get("relative_humidity_2m", [])
    dew = hourly.get("dew_point_2m", [])
    pressure = hourly.get("pressure_msl", [])
    cloud = hourly.get("cloud_cover", [])
    wind = hourly.get("wind_speed_10m", [])
    for lag in [1,2,3,6,12,24]:
        row[f"rain_lag_{lag}h"] = v(rain, max(0, i-lag))
    for window in [3,6,12,24]:
        row[f"rain_sum_{window}h"] = sum(v(rain, j) for j in range(max(0, i-window+1), i+1))
    for name, arr in [("temperature", temp),("humidity",hum),("dew_point",dew),("pressure",pressure),("cloud_cover",cloud),("wind_speed",wind)]:
        for lag in [1,3]:
            row[f"{name}_change_{lag}h"] = v(arr,i) - v(arr,max(0,i-lag))
    # Time features are based on the API's local timestamp string.
    time_text = hourly.get("time", [""])[i]
    try:
        hour = int(time_text[11:13]); month = int(time_text[5:7])
    except Exception:
        hour, month = 0, 1
    row["hour_sin"] = math.sin(2*math.pi*hour/24)
    row["hour_cos"] = math.cos(2*math.pi*hour/24)
    row["month_sin"] = math.sin(2*math.pi*month/12)
    row["month_cos"] = math.cos(2*math.pi*month/12)
    row["latitude"] = float(lat); row["longitude"] = float(lon); row["elevation"] = float(elevation or 0)
    return row

def elevation_from_response(data):
    try: return float(data.get("elevation", 0))
    except Exception: return 0.0
