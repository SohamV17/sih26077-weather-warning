"""Rainfall warning risk engine.

The XGBoost model predicts rainfall in mm for each hour.  The warning score
therefore looks at both the peak predicted hour and the accumulated predicted
rainfall across the four-hour warning window.  This avoids the old behaviour
where a sequence such as 4 + 6 + 8 + 5 mm could look low simply because its
maximum single hour was only 8 mm.
"""


def clamp(value, minimum=0, maximum=100):
    return max(minimum, min(float(value), maximum))


def _piecewise(value, points):
    """Linear interpolation through (input, score) points."""
    value = max(float(value or 0), 0)
    if value <= points[0][0]:
        return points[0][1]
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        if value <= x2:
            fraction = (value - x1) / (x2 - x1)
            return y1 + fraction * (y2 - y1)
    return points[-1][1]


def rainfall_score(rain):
    """Score one-hour rainfall intensity on a 0-100 scale."""
    return _piecewise(float(rain or 0), [
        (0, 0), (1, 5), (3, 15), (5, 28), (10, 55),
        (20, 78), (30, 90), (40, 97), (50, 100),
    ])


def accumulation_score(rain):
    """Score rainfall accumulated over the four-hour warning window."""
    return _piecewise(float(rain or 0), [
        (0, 0), (1, 5), (3, 15), (5, 28), (10, 52),
        (15, 68), (20, 80), (30, 92), (40, 100),
    ])


def precipitation_probability_score(probability):
    probability = clamp(probability or 0)
    # Keep probability useful without letting it dominate actual rainfall.
    return (probability / 100.0) * 22


def wind_score(wind):
    wind = max(float(wind or 0), 0)
    return _piecewise(wind, [
        (0, 0), (10, 3), (20, 10), (30, 22),
        (40, 42), (60, 82), (80, 100),
    ])


def gust_score(gust):
    if gust is None:
        return 0
    return _piecewise(float(gust or 0), [
        (0, 0), (20, 3), (30, 10), (40, 22),
        (50, 40), (70, 80), (90, 100),
    ])


def humidity_score(humidity):
    humidity = clamp(humidity or 0)
    if humidity < 60:
        return 0
    if humidity < 75:
        return (humidity - 60) * 0.15
    if humidity < 85:
        return 2.25 + (humidity - 75) * 0.25
    if humidity < 95:
        return 4.75 + (humidity - 85) * 0.5
    return 9.75


def pressure_score(pressure):
    pressure = float(pressure or 1013)
    if pressure >= 1013:
        return 0
    if pressure >= 1005:
        return (1013 - pressure) * 0.5
    if pressure >= 995:
        return 4 + (1005 - pressure) * 0.8
    if pressure >= 980:
        return 12 + (995 - pressure) * 1.2
    return 30


def weather_code_score(weather_code):
    code = int(weather_code or 0)
    if code <= 3:
        return 0
    if code in (45, 48):
        return 3
    if code in (51, 53, 55):
        return 8
    if code in (56, 57):
        return 12
    if code in (61, 63, 65):
        return {61: 12, 63: 18, 65: 28}[code]
    if code in (66, 67):
        return 25
    if code in (71, 73, 75, 77):
        return 15
    if code in (80, 81, 82):
        return {80: 15, 81: 22, 82: 32}[code]
    if code in (95, 96, 99):
        return {95: 65, 96: 80, 99: 90}[code]
    return 0


def alert_score(alerts):
    if not alerts:
        return 0
    score = 0
    dangerous_keywords = (
        "flood", "flash flood", "thunderstorm", "tornado",
        "cyclone", "hurricane", "heavy rain", "strong wind",
        "extreme heat", "extreme cold"
    )
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
        if any(keyword in event for keyword in dangerous_keywords):
            score += 10
    return clamp(score, 0, 55)


def _num(values, index, default=0):
    try:
        value = values[index]
        return default if value is None else float(value)
    except (IndexError, TypeError, ValueError, KeyError):
        return float(default)


def _level(score):
    if score >= 70:
        return "SEVERE"
    if score >= 40:
        return "MODERATE"
    return "LOW"


def calculate_hourly_risk(hourly, index, prediction=None, weatherapi_hour=None):
    rainfall = _num(hourly.get("precipitation", []), index)
    probability = _num(hourly.get("precipitation_probability", []), index)
    wind = _num(hourly.get("wind_speed_10m", []), index)
    humidity = _num(hourly.get("relative_humidity_2m", []), index)
    pressure = _num(hourly.get("pressure_msl", []), index, 1013)
    weather_code = int(_num(hourly.get("weather_code", []), index, 0))

    model_rain = max(float(prediction or 0), 0)
    rain_for_warning = max(rainfall, model_rain)

    gust = _num(hourly.get("wind_gusts_10m", []), index, None)
    if weatherapi_hour:
        wa_gust = weatherapi_hour.get("gust_kph")
        if wa_gust is not None:
            gust = max(float(gust or 0), float(wa_gust))

    score = (
        rainfall_score(model_rain) * 0.55
        + rainfall_score(rainfall) * 0.10
        + precipitation_probability_score(probability) * 0.12
        + wind_score(wind) * 0.08
        + gust_score(gust) * 0.06
        + humidity_score(humidity) * 0.02
        + pressure_score(pressure) * 0.02
        + weather_code_score(weather_code) * 0.05
    )

    if model_rain >= 10 and probability >= 70:
        score += 7
    if model_rain >= 10 and wind >= 30:
        score += 5
    if weather_code >= 95:
        score += 10

    score = round(clamp(score), 1)

    reasons = []
    if model_rain >= 20:
        reasons.append(f"XGBoost predicts very heavy rainfall ({model_rain:.1f} mm).")
    elif model_rain >= 10:
        reasons.append(f"XGBoost predicts heavy rainfall ({model_rain:.1f} mm).")
    elif model_rain >= 5:
        reasons.append(f"XGBoost predicts moderate rainfall ({model_rain:.1f} mm).")
    elif model_rain >= 2:
        reasons.append(f"XGBoost predicts rainfall ({model_rain:.1f} mm).")

    if probability >= 80:
        reasons.append(f"Very high rain probability ({probability:.0f}%).")
    elif probability >= 60:
        reasons.append(f"High rain probability ({probability:.0f}%).")
    if rain_for_warning >= 10 and rainfall > 0:
        reasons.append(f"Forecast precipitation is elevated ({rainfall:.1f} mm).")
    if wind >= 35:
        reasons.append(f"Strong winds ({wind:.1f} km/h).")
    if gust is not None and gust >= 45:
        reasons.append(f"Strong wind gusts ({gust:.1f} km/h).")
    if weather_code >= 95:
        reasons.append("Thunderstorm conditions detected.")
    if not reasons:
        reasons.append("No significant rainfall or severe-weather indicators detected.")

    return {
        "score": score,
        "level": _level(score),
        "reasons": reasons,
        "prediction": round(model_rain, 2),
        "components": {
            "xgboost_rainfall": round(rainfall_score(model_rain), 1),
            "rainfall": round(rainfall_score(rainfall), 1),
            "rain_probability": round(precipitation_probability_score(probability), 1),
            "wind": round(wind_score(wind), 1),
            "wind_gust": round(gust_score(gust), 1),
            "weather_condition": round(weather_code_score(weather_code), 1),
        },
    }


def calculate(predictions, current, alerts=None, weatherapi_summary=None, hourly=None):
    predictions = [max(float(x or 0), 0) for x in (predictions or [])]
    current = current or {}
    alerts = alerts or []
    weatherapi_summary = weatherapi_summary or {}
    hourly = hourly or {}

    current_rain = float(current.get("precipitation", 0) or 0)
    current_wind = float(current.get("wind_speed_10m", 0) or 0)
    current_humidity = float(current.get("relative_humidity_2m", 0) or 0)
    current_pressure = float(current.get("pressure_msl", 1013) or 1013)
    current_code = int(current.get("weather_code", 0) or 0)

    gust = weatherapi_summary.get("gust_kph")
    if gust is None:
        gust = current.get("wind_gusts_10m")

    wa_probability = weatherapi_summary.get("chance_of_rain")
    if wa_probability is None:
        # Open-Meteo probability for the first forecast hour is a safer
        # fallback than assuming 0% when WeatherAPI is not configured.
        wa_probability = _num(hourly.get("precipitation_probability", []), 0, 0)

    peak_prediction = max(predictions, default=0)
    accumulated_prediction = sum(predictions)

    # Rainfall is the core of this system.  Accumulation captures persistent
    # rain; peak captures short intense bursts.
    accumulation_risk = accumulation_score(accumulated_prediction)
    peak_risk = rainfall_score(peak_prediction)

    probability_values = [
        _num(hourly.get("precipitation_probability", []), i, 0)
        for i in range(min(len(predictions), len(hourly.get("time", []))))
    ]
    peak_probability = max(probability_values, default=float(wa_probability or 0))
    probability_risk = precipitation_probability_score(peak_probability)

    current_risk = (
        rainfall_score(current_rain) * 0.25
        + probability_risk * 0.10
        + wind_score(current_wind) * 0.25
        + gust_score(gust) * 0.20
        + humidity_score(current_humidity) * 0.05
        + pressure_score(current_pressure) * 0.05
        + weather_code_score(current_code) * 0.10
    )
    official_alert = alert_score(alerts)

    # Main score: 70% rainfall forecast, 15% corroborating current weather,
    # 15% official alerts.  The rainfall forecast itself is split between
    # accumulation and peak intensity.
    rainfall_risk = accumulation_risk * 0.60 + peak_risk * 0.40
    score = rainfall_risk * 0.70 + current_risk * 0.15 + official_alert * 0.15

    # Extra confidence/compound-hazard boosts, deliberately capped.
    if peak_prediction >= 10 and peak_probability >= 70:
        score += 5
    if accumulated_prediction >= 30:
        score += 4
    if peak_prediction >= 20:
        score += 8
    if accumulated_prediction >= 10 and current_rain >= 2:
        score += 5
    if peak_prediction >= 10 and current_wind >= 30:
        score += 4
    if current_code >= 95:
        score += 8

    hourly_risks = []
    if hourly.get("time"):
        n = min(len(predictions), len(hourly["time"]))
        start = len(hourly["time"]) - n
        for j, i in enumerate(range(start, len(hourly["time"]))):
            hourly_risks.append(calculate_hourly_risk(hourly, i, predictions[j]))

    max_hourly = max((x["score"] for x in hourly_risks), default=peak_risk)
    score = round(clamp(score), 1)

    reasons = []
    if accumulated_prediction >= 20:
        reasons.append(f"XGBoost predicts {accumulated_prediction:.1f} mm accumulated rainfall over the next {len(predictions)} hours.")
    elif accumulated_prediction >= 10:
        reasons.append(f"XGBoost predicts {accumulated_prediction:.1f} mm accumulated rainfall over the next {len(predictions)} hours.")
    elif accumulated_prediction >= 5:
        reasons.append(f"XGBoost predicts {accumulated_prediction:.1f} mm accumulated rainfall over the next {len(predictions)} hours.")
    elif peak_prediction > 0:
        reasons.append(f"XGBoost predicts up to {peak_prediction:.1f} mm of rainfall in a single hour.")

    if peak_prediction >= 20:
        reasons.append(f"Peak hourly rainfall is very high ({peak_prediction:.1f} mm).")
    elif peak_prediction >= 10:
        reasons.append(f"Peak hourly rainfall is high ({peak_prediction:.1f} mm).")
    elif peak_prediction >= 5:
        reasons.append(f"Peak hourly rainfall is moderate ({peak_prediction:.1f} mm).")

    if peak_probability >= 70:
        reasons.append(f"Rain probability reaches {peak_probability:.0f}% in the warning window.")
    if current_rain >= 10:
        reasons.append(f"Current precipitation is elevated ({current_rain:.1f} mm).")
    elif current_rain > 1:
        reasons.append(f"Rain is currently detected ({current_rain:.1f} mm).")
    if current_wind >= 35:
        reasons.append(f"Strong current winds ({current_wind:.1f} km/h).")
    if gust is not None and float(gust) >= 45:
        reasons.append(f"Strong wind gusts ({float(gust):.1f} km/h).")
    if current_humidity >= 90:
        reasons.append(f"Very high humidity ({current_humidity:.0f}%).")
    if current_pressure < 995:
        reasons.append(f"Very low atmospheric pressure ({current_pressure:.1f} hPa).")
    if current_code >= 95:
        reasons.append("Thunderstorm conditions detected.")
    if alerts:
        reasons.append("Official weather alert is active.")
    if not reasons:
        reasons.append("No significant rainfall or severe-weather indicators detected.")

    return {
        "score": score,
        "level": _level(score),
        "reasons": reasons,
        "components": {
            "model": round(rainfall_risk, 1),
            "xgboost": round(rainfall_risk, 1),
            "xgboost_accumulation": round(accumulation_risk, 1),
            "xgboost_peak": round(peak_risk, 1),
            "current_conditions": round(current_risk, 1),
            "current": round(current_risk, 1),
            "wind": round(max(wind_score(current_wind), gust_score(gust)), 1),
            "alerts": round(official_alert, 1),
            "official_alert": round(official_alert, 1),
            "peak_hourly_risk": round(max_hourly, 1),
        },
        "forecast_summary": {
            "maximum_risk": round(max_hourly, 1),
            "average_risk": round(sum(x["score"] for x in hourly_risks) / len(hourly_risks), 1) if hourly_risks else 0,
            "predicted_rainfall_total_mm": round(accumulated_prediction, 2),
            "predicted_peak_hourly_mm": round(peak_prediction, 2),
            "peak_rain_probability": round(peak_probability, 1),
        },
    }
