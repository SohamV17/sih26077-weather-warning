# WEATHER RISK ENGINE
#
# Converts:
#   XGBoost nowcast predictions
#   + Current weather
#   + Weather alerts
# into:
#   Risk score: 0-100
#   Risk level: LOW / MODERATE / SEVERE
#   Explainable reasons


def clamp(value, minimum=0, maximum=100):
    return max(minimum, min(float(value), maximum))


def rainfall_score(rain):
    rain = max(float(rain), 0)

    if rain <= 1:
        return rain * 2
    elif rain <= 5:
        return 2 + (rain - 1) * 2.5
    elif rain <= 10:
        return 12 + (rain - 5) * 3.5
    elif rain <= 20:
        return 29.5 + (rain - 10) * 3
    elif rain <= 40:
        return 59.5 + (rain - 20) * 1.5

    return 89.5


def precipitation_probability_score(probability):
    probability = clamp(probability)
    return ((probability / 100) ** 1.5) * 25


def wind_score(wind):
    wind = max(float(wind), 0)

    if wind <= 10:
        return wind * 0.3
    elif wind <= 20:
        return 3 + (wind - 10) * 0.7
    elif wind <= 30:
        return 10 + (wind - 20) * 1.2
    elif wind <= 40:
        return 22 + (wind - 30) * 2
    elif wind <= 60:
        return 42 + (wind - 40) * 2

    return 82


def gust_score(gust):
    if gust is None:
        return 0

    gust = max(float(gust), 0)

    if gust <= 20:
        return gust * 0.15
    elif gust <= 30:
        return 3 + (gust - 20) * 0.7
    elif gust <= 40:
        return 10 + (gust - 30) * 1.2
    elif gust <= 50:
        return 22 + (gust - 40) * 1.8
    elif gust <= 70:
        return 40 + (gust - 50) * 2

    return 80


def humidity_score(humidity):
    humidity = clamp(humidity)

    if humidity < 60:
        return 0
    elif humidity < 75:
        return (humidity - 60) * 0.15
    elif humidity < 85:
        return 2.25 + (humidity - 75) * 0.25
    elif humidity < 95:
        return 4.75 + (humidity - 85) * 0.5

    return 9.75


def pressure_score(pressure):
    pressure = float(pressure)

    if pressure >= 1013:
        return 0
    elif pressure >= 1005:
        return (1013 - pressure) * 0.5
    elif pressure >= 995:
        return 4 + (1005 - pressure) * 0.8
    elif pressure >= 980:
        return 12 + (995 - pressure) * 1.2

    return 30


def weather_code_score(weather_code):
    code = int(weather_code)

    if code <= 3:
        return 0
    elif code in [45, 48]:
        return 3
    elif code in [51, 53, 55]:
        return 8
    elif code in [56, 57]:
        return 12
    elif code in [61, 63, 65]:
        return {61: 12, 63: 18, 65: 28}.get(code, 12)
    elif code in [66, 67]:
        return 25
    elif code in [71, 73, 75, 77]:
        return 15
    elif code in [80, 81, 82]:
        return {80: 15, 81: 22, 82: 32}.get(code, 15)
    elif code in [95, 96, 99]:
        return {95: 65, 96: 80, 99: 90}.get(code, 65)

    return 0


def alert_score(alerts):
    if not alerts:
        return 0

    score = 0

    for alert in alerts:
        severity = str(alert.get("severity", "")).lower()
        event = str(alert.get("event", "")).lower()

        if "extreme" in severity:
            score = max(score, 45)
        elif "severe" in severity:
            score = max(score, 35)
        elif "moderate" in severity:
            score = max(score, 25)
        elif "minor" in severity:
            score = max(score, 10)

        dangerous_keywords = [
            "flood", "flash flood", "thunderstorm", "tornado",
            "cyclone", "hurricane", "heavy rain", "strong wind",
            "extreme heat", "extreme cold",
        ]

        for keyword in dangerous_keywords:
            if keyword in event:
                score += 10
                break

    return clamp(score, 0, 55)


def nowcast_risk_component(rain_probability, predicted_rain_mm):
    probability_component = precipitation_probability_score(
        rain_probability * 100
    )
    rainfall_component = rainfall_score(predicted_rain_mm)

    return probability_component * 0.45 + rainfall_component * 0.55


def calculate_nowcast_risk(
    nowcast,
    current=None,
    weatherapi_summary=None,
    alerts=None,
):
    current = current or {}
    weatherapi_summary = weatherapi_summary or {}
    alerts = alerts or []

    probabilities = [
        float(item.get("rain_probability", 0))
        for item in nowcast
    ]
    predicted_rain = [
        float(item.get("predicted_rain_mm", 0))
        for item in nowcast
    ]

    max_probability = max(probabilities, default=0)
    max_rain = max(predicted_rain, default=0)

    ml_component = nowcast_risk_component(
        max_probability,
        max_rain,
    )

    current_wind = float(current.get("wind_speed_10m", 0))
    current_humidity = float(current.get("relative_humidity_2m", 0))
    current_pressure = float(current.get("pressure_msl", 1013))
    current_weather_code = int(current.get("weather_code", 0))

    gust = weatherapi_summary.get("gust_kph")

    current_component = (
        wind_score(current_wind) * 0.20
        + gust_score(gust) * 0.20
        + humidity_score(current_humidity) * 0.10
        + pressure_score(current_pressure) * 0.15
        + weather_code_score(current_weather_code) * 0.35
    )

    official_alert_component = alert_score(alerts)

    score = (
        ml_component * 0.65
        + current_component * 0.20
        + official_alert_component * 0.15
    )

    score = round(clamp(score), 1)

    if score >= 70:
        level = "SEVERE"
    elif score >= 40:
        level = "MODERATE"
    else:
        level = "LOW"

    reasons = []

    if max_probability >= 0.80:
        reasons.append(
            f"XGBoost predicts a high probability of rainfall "
            f"({max_probability * 100:.0f}%)"
        )
    elif max_probability >= 0.50:
        reasons.append(
            f"XGBoost predicts a moderate probability of rainfall "
            f"({max_probability * 100:.0f}%)"
        )

    if max_rain >= 20:
        reasons.append(f"Potential heavy rainfall ({max_rain:.1f} mm)")
    elif max_rain >= 10:
        reasons.append(
            f"Potential significant rainfall ({max_rain:.1f} mm)"
        )

    if current_wind >= 35:
        reasons.append(f"Strong current winds ({current_wind:.1f} km/h)")

    if gust is not None and float(gust) >= 45:
        reasons.append(f"Strong wind gusts ({float(gust):.1f} km/h)")

    if current_weather_code >= 95:
        reasons.append("Thunderstorm conditions detected")

    if alerts:
        reasons.append("Official weather alert is active")

    if not reasons:
        reasons.append("No significant severe-weather indicators detected")

    return {
        "score": score,
        "level": level,
        "reasons": reasons,
        "components": {
            "xgboost": round(ml_component, 1),
            "current_conditions": round(current_component, 1),
            "official_alert": round(official_alert_component, 1),
        },
    }


def calculate_risk(
    current,
    hourly,
    weatherapi_summary=None,
    alerts=None,
    nowcast=None,
):
    """Compatibility wrapper used by the Flask application."""

    if nowcast:
        return calculate_nowcast_risk(
            nowcast,
            current=current,
            weatherapi_summary=weatherapi_summary,
            alerts=alerts,
        )

    # Fallback when no trained ML model is available.
    first_rain = 0
    first_probability = 0

    if hourly:
        first_rain = (hourly.get("rain") or [0])[0]
        first_probability = (
            hourly.get("precipitation_probability") or [0]
        )[0]

    fallback = [{
        "rain_probability": float(first_probability) / 100,
        "predicted_rain_mm": float(first_rain),
    }]

    result = calculate_nowcast_risk(
        fallback,
        current=current,
        weatherapi_summary=weatherapi_summary,
        alerts=alerts,
    )
    result["model"] = "fallback_rule_based"
    return result


def calculate_hourly_risk(hourly, index):
    rain = float((hourly.get("rain") or [0])[index])
    probability = float(
        (hourly.get("precipitation_probability") or [0])[index]
    )

    component = nowcast_risk_component(
        probability / 100,
        rain,
    )

    score = round(clamp(component), 1)

    if score >= 70:
        level = "SEVERE"
    elif score >= 40:
        level = "MODERATE"
    else:
        level = "LOW"

    return {
        "score": score,
        "level": level,
    }
