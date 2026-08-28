def clamp(value, minimum=0, maximum=100):
    try:
        return max(minimum, min(float(value), maximum))
    except:
        return minimum

def rainfall_score(rain):
    rain = max(float(rain or 0), 0)
    if rain <= 0.2:
        return rain * 5
    if rain <= 2:
        return 1 + (rain - 0.2) * 5
    if rain <= 5:
        return 10 + (rain - 2) * 7
    if rain <= 10:
        return 31 + (rain - 5) * 7
    if rain <= 20:
        return 66 + (rain - 10) * 3
    if rain <= 40:
        return 96 + (rain - 20) * 0.2
    return 100

def precipitation_probability_score(probability):
    probability = clamp(probability)
    if probability < 20:
        return probability * 0.15
    if probability < 40:
        return 3 + (probability - 20) * 0.35
    if probability < 60:
        return 10 + (probability - 40) * 0.75
    if probability < 80:
        return 25 + (probability - 60) * 1.5
    return min(100, 55 + (probability - 80) * 2.25)

def wind_score(wind):
    wind = max(float(wind or 0), 0)
    if wind <= 10:
        return wind * 0.5
    if wind <= 20:
        return 5 + (wind - 10) * 1.5
    if wind <= 30:
        return 20 + (wind - 20) * 2.5
    if wind <= 40:
        return 45 + (wind - 30) * 3
    if wind <= 60:
        return 75 + (wind - 40) * 1.25
    return 100

def gust_score(gust):
    if gust is None:
        return 0
    gust = max(float(gust or 0), 0)
    if gust <= 15:
        return gust * 0.4
    if gust <= 25:
        return 6 + (gust - 15) * 1.4
    if gust <= 35:
        return 20 + (gust - 25) * 2.5
    if gust <= 45:
        return 45 + (gust - 35) * 3
    if gust <= 60:
        return 75 + (gust - 45) * 1.67
    return 100

def humidity_score(humidity):
    humidity = clamp(humidity)
    if humidity < 60:
        return 0
    if humidity < 75:
        return (humidity - 60) * 0.35
    if humidity < 85:
        return 5.25 + (humidity - 75) * 0.75
    if humidity < 95:
        return 12.75 + (humidity - 85) * 1.25
    return min(100, 25.25 + (humidity - 95) * 2)

def pressure_score(pressure):
    try:
        pressure = float(pressure)
    except:
        return 0
    if pressure >= 1015:
        return 0
    if pressure >= 1010:
        return (1015 - pressure) * 1.5
    if pressure >= 1005:
        return 7.5 + (1010 - pressure) * 3
    if pressure >= 995:
        return 22.5 + (1005 - pressure) * 4
    if pressure >= 985:
        return 62.5 + (995 - pressure) * 3
    return 100

def weather_code_score(weather_code):
    try:
        code = int(weather_code)
    except:
        return 0
    mapping = {
        0: 0,
        1: 3,
        2: 5,
        3: 8,
        45: 12,
        48: 15,
        51: 15,
        53: 20,
        55: 28,
        56: 30,
        57: 35,
        61: 30,
        63: 45,
        65: 70,
        66: 55,
        67: 75,
        71: 25,
        73: 40,
        75: 65,
        77: 35,
        80: 35,
        81: 55,
        82: 80,
        85: 40,
        86: 70,
        95: 90,
        96: 97,
        99: 100
    }
    return mapping.get(code, 0)

def alert_score(alerts):
    if not alerts:
        return 0
    score = 0
    dangerous_keywords = [
        "flood",
        "flash flood",
        "thunderstorm",
        "tornado",
        "cyclone",
        "hurricane",
        "heavy rain",
        "strong wind",
        "extreme heat",
        "extreme cold",
        "landslide"
    ]
    for alert in alerts:
        severity = str(alert.get("severity", "")).lower()
        event = str(alert.get("event", "")).lower()
        if "extreme" in severity:
            current = 80
        elif "severe" in severity:
            current = 65
        elif "moderate" in severity:
            current = 45
        elif "minor" in severity:
            current = 25
        else:
            current = 20
        for keyword in dangerous_keywords:
            if keyword in event:
                current += 15
                break
        score = max(score, current)
    return clamp(score)

def combined_hazard_score(rain, probability, wind, gust, weather_code):
    boost = 0
    if rain >= 5 and probability >= 60:
        boost += 8
    if rain >= 10 and probability >= 70:
        boost += 12
    if rain >= 15:
        boost += 8
    if wind >= 30 and (gust or 0) >= 40:
        boost += 10
    if wind >= 40:
        boost += 8
    if weather_code >= 95:
        boost += 15
    if weather_code in [65, 67, 82, 86]:
        boost += 8
    if rain >= 5 and weather_code in [63, 65, 80, 81, 82]:
        boost += 8
    return min(boost, 35)

def calculate_hourly_risk(hourly, index, weatherapi_hour=None):
    rainfall = float(hourly.get("precipitation", [0])[index] or 0)
    probability = float(hourly.get("precipitation_probability", [0])[index] or 0)
    wind = float(hourly.get("wind_speed_10m", [0])[index] or 0)
    humidity = float(hourly.get("relative_humidity_2m", [0])[index] or 0)
    pressure = float(hourly.get("pressure_msl", [1013])[index] or 1013)
    weather_code = int(hourly.get("weather_code", [0])[index] or 0)
    gust = None
    api_probability = None
    if weatherapi_hour:
        gust = weatherapi_hour.get("gust_kph")
        api_probability = weatherapi_hour.get("chance_of_rain")
        if api_probability is not None:
            probability = max(probability, float(api_probability))
    rain_component = rainfall_score(rainfall)
    probability_component = precipitation_probability_score(probability)
    wind_component = wind_score(wind)
    humidity_component = humidity_score(humidity)
    pressure_component = pressure_score(pressure)
    weather_component = weather_code_score(weather_code)
    gust_component = gust_score(gust)
    score = (
        rain_component * 0.28 +
        probability_component * 0.18 +
        wind_component * 0.17 +
        gust_component * 0.12 +
        humidity_component * 0.05 +
        pressure_component * 0.08 +
        weather_component * 0.12
    )
    score += combined_hazard_score(
        rainfall,
        probability,
        wind,
        gust,
        weather_code
    )
    if weather_code >= 95:
        score += 10
    return {
        "score": round(clamp(score), 1),
        "level": get_level(score)
    }

def get_level(score):
    score = float(score)
    if score >= 70:
        return "SEVERE"
    if score >= 40:
        return "MODERATE"
    if score >= 25:
        return "ELEVATED"
    return "LOW"

def calculate_risk(current, hourly, weatherapi_summary=None, alerts=None):
    weatherapi_summary = weatherapi_summary or {}
    alerts = alerts or []
    rainfall = float(current.get("precipitation", 0) or 0)
    wind = float(current.get("wind_speed_10m", 0) or 0)
    humidity = float(current.get("relative_humidity_2m", 0) or 0)
    pressure = float(current.get("pressure_msl", 1013) or 1013)
    weather_code = int(current.get("weather_code", 0) or 0)
    probability = 0
    gust = None
    api_rain = weatherapi_summary.get("precipitation_mm")
    api_probability = weatherapi_summary.get("chance_of_rain")
    api_wind = weatherapi_summary.get("wind_kph")
    api_gust = weatherapi_summary.get("gust_kph")
    if api_rain is not None:
        rainfall = max(rainfall, float(api_rain))
    if api_wind is not None:
        wind = max(wind, float(api_wind))
    if api_gust is not None:
        gust = float(api_gust)
    if api_probability is not None:
        probability = float(api_probability)
    hourly_probabilities = hourly.get("precipitation_probability", [])
    if hourly_probabilities:
        try:
            probability = max(
                probability,
                max(float(x or 0) for x in hourly_probabilities[:4])
            )
        except:
            pass
    rain_component = rainfall_score(rainfall)
    probability_component = precipitation_probability_score(probability)
    wind_component = wind_score(wind)
    gust_component = gust_score(gust)
    humidity_component = humidity_score(humidity)
    pressure_component = pressure_score(pressure)
    weather_component = weather_code_score(weather_code)
    score = (
        rain_component * 0.28 +
        probability_component * 0.18 +
        wind_component * 0.17 +
        gust_component * 0.12 +
        humidity_component * 0.05 +
        pressure_component * 0.08 +
        weather_component * 0.12
    )
    score += combined_hazard_score(
        rainfall,
        probability,
        wind,
        gust,
        weather_code
    )
    if weather_code >= 95:
        score += 10
    official_alert_points = alert_score(alerts)
    score += official_alert_points
    forecast_risks = []
    number_of_hours = min(
        4,
        len(hourly.get("time", []))
    )
    for i in range(number_of_hours):
        forecast_risks.append(
            calculate_hourly_risk(hourly, i)
        )
    future_scores = [
        item["score"]
        for item in forecast_risks
    ]
    maximum_future_score = max(future_scores) if future_scores else 0
    average_future_score = (
        sum(future_scores) / len(future_scores)
        if future_scores else 0
    )
    current_score = score
    if maximum_future_score > current_score:
        difference = maximum_future_score - current_score
        score += min(difference * 0.35, 18)
    if average_future_score > current_score + 10:
        score += min(
            (average_future_score - current_score) * 0.15,
            8
        )
    if maximum_future_score >= 70 and current_score < 60:
        score += 8
    score = round(clamp(score), 1)
    level = get_level(score)
    reasons = []
    if rainfall >= 20:
        reasons.append(
            f"Very heavy rainfall detected ({rainfall:.1f} mm)"
        )
    elif rainfall >= 10:
        reasons.append(
            f"Heavy rainfall detected ({rainfall:.1f} mm)"
        )
    elif rainfall >= 5:
        reasons.append(
            f"Moderate rainfall detected ({rainfall:.1f} mm)"
        )
    elif rainfall > 1:
        reasons.append(
            f"Light rainfall detected ({rainfall:.1f} mm)"
        )
    if probability >= 80:
        reasons.append(
            f"Very high rain probability ({probability:.0f}%)"
        )
    elif probability >= 60:
        reasons.append(
            f"High rain probability ({probability:.0f}%)"
        )
    elif probability >= 40:
        reasons.append(
            f"Moderate rain probability ({probability:.0f}%)"
        )
    if wind >= 50:
        reasons.append(
            f"Extremely strong winds ({wind:.1f} km/h)"
        )
    elif wind >= 35:
        reasons.append(
            f"Strong winds ({wind:.1f} km/h)"
        )
    elif wind >= 25:
        reasons.append(
            f"Elevated wind speed ({wind:.1f} km/h)"
        )
    if gust is not None:
        if gust >= 60:
            reasons.append(
                f"Extremely strong wind gusts ({gust:.1f} km/h)"
            )
        elif gust >= 45:
            reasons.append(
                f"Strong wind gusts ({gust:.1f} km/h)"
            )
        elif gust >= 30:
            reasons.append(
                f"Elevated wind gusts ({gust:.1f} km/h)"
            )
    if humidity >= 90:
        reasons.append(
            f"Very high humidity ({humidity:.0f}%)"
        )
    elif humidity >= 80:
        reasons.append(
            f"High humidity ({humidity:.0f}%)"
        )
    if pressure < 995:
        reasons.append(
            f"Very low atmospheric pressure ({pressure:.1f} hPa)"
        )
    elif pressure < 1005:
        reasons.append(
            f"Low atmospheric pressure ({pressure:.1f} hPa)"
        )
    if weather_code >= 95:
        reasons.append("Thunderstorm conditions detected")
    elif weather_code in [65, 67, 82, 86]:
        reasons.append("Heavy or intense precipitation conditions detected")
    elif weather_code in [63, 81]:
        reasons.append("Significant rain conditions detected")
    if rainfall >= 5 and probability >= 60:
        reasons.append(
            "Rainfall intensity and rain probability indicate an elevated combined hazard"
        )
    if maximum_future_score >= current_score + 15:
        reasons.append(
            "Weather risk is expected to increase in the next few hours"
        )
    if alerts:
        for alert in alerts:
            event = alert.get("event")
            severity = alert.get("severity")
            if event and severity:
                reasons.append(
                    f"Official weather alert: {event} ({severity})"
                )
            elif event:
                reasons.append(
                    f"Official weather alert: {event}"
                )
            else:
                reasons.append("Official weather alert is active")
    if not reasons:
        reasons.append(
            "No significant severe-weather indicators detected"
        )
    return {
        "score": score,
        "level": level,
        "reasons": reasons,
        "components": {
            "rainfall": round(rain_component, 1),
            "rain_probability": round(probability_component, 1),
            "wind": round(wind_component, 1),
            "wind_gust": round(gust_component, 1),
            "humidity": round(humidity_component, 1),
            "pressure": round(pressure_component, 1),
            "weather_condition": round(weather_component, 1),
            "official_alert": round(official_alert_points, 1),
            "maximum_forecast_risk": round(maximum_future_score, 1)
        },
        "forecast_summary": {
            "maximum_risk": round(maximum_future_score, 1),
            "average_risk": round(average_future_score, 1)
        }
    }