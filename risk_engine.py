# ============================================================
# AI-DRIVEN HYPER-LOCAL WEATHER RISK ENGINE
# ============================================================
#
# Explainable MVP risk engine using:
#
# 1. Open-Meteo current weather
# 2. Open-Meteo hourly forecast
# 3. WeatherAPI additional conditions
# 4. WeatherAPI wind gusts
# 5. WeatherAPI rain probability
# 6. Official weather alerts
# 7. Short-term forecast trend
#
# Output:
#   Risk score: 0 - 100
#   Risk level: LOW / MODERATE / SEVERE
#   Reasons explaining the assessment
#
# ============================================================


# ============================================================
# UTILITY
# ============================================================

def clamp(value, minimum=0, maximum=100):
    """
    Keep a value between minimum and maximum.
    """

    return max(
        minimum,
        min(float(value), maximum)
    )


# ============================================================
# RAINFALL SCORE
# ============================================================

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

    else:
        return 89.5


# ============================================================
# PRECIPITATION PROBABILITY
# ============================================================

def precipitation_probability_score(probability):

    probability = clamp(probability)

    return (
        (probability / 100) ** 1.5
    ) * 25


# ============================================================
# WIND SCORE
# ============================================================

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

    else:

        return 82


# ============================================================
# WIND GUST SCORE
# ============================================================

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

    else:

        return 80


# ============================================================
# HUMIDITY SCORE
# ============================================================

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

    else:

        return 9.75


# ============================================================
# PRESSURE SCORE
# ============================================================

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

    else:

        return 30


# ============================================================
# WEATHER CODE SCORE
# ============================================================

def weather_code_score(weather_code):

    code = int(weather_code)

    # Clear / mainly clear / partly cloudy
    if code <= 3:

        return 0

    # Fog
    elif code in [45, 48]:

        return 3

    # Drizzle
    elif code in [51, 53, 55]:

        return 8

    # Freezing drizzle
    elif code in [56, 57]:

        return 12

    # Rain
    elif code in [61, 63, 65]:

        return {
            61: 12,
            63: 18,
            65: 28
        }.get(code, 12)

    # Freezing rain
    elif code in [66, 67]:

        return 25

    # Snow
    elif code in [71, 73, 75, 77]:

        return 15

    # Rain showers
    elif code in [80, 81, 82]:

        return {
            80: 15,
            81: 22,
            82: 32
        }.get(code, 15)

    # Thunderstorms
    elif code in [95, 96, 99]:

        return {
            95: 65,
            96: 80,
            99: 90
        }.get(code, 65)

    return 0


# ============================================================
# WEATHERAPI ALERT SCORE
# ============================================================

def alert_score(alerts):

    if not alerts:

        return 0

    score = 0

    for alert in alerts:

        severity = str(
            alert.get(
                "severity",
                ""
            )
        ).lower()

        event = str(
            alert.get(
                "event",
                ""
            )
        ).lower()


        # Severity

        if "extreme" in severity:

            score = max(
                score,
                45
            )

        elif "severe" in severity:

            score = max(
                score,
                35
            )

        elif "moderate" in severity:

            score = max(
                score,
                25
            )

        elif "minor" in severity:

            score = max(
                score,
                10
            )


        # Hazard-specific boost

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
            "extreme cold"

        ]


        for keyword in dangerous_keywords:

            if keyword in event:

                score += 10

                break


    return clamp(score, 0, 55)


# ============================================================
# HOURLY RISK
# ============================================================

def calculate_hourly_risk(
    hourly,
    index,
    weatherapi_hour=None
):

    rainfall = float(
        hourly["precipitation"][index]
    )


    probability = float(
        hourly["precipitation_probability"][index]
    )


    wind = float(
        hourly["wind_speed_10m"][index]
    )


    humidity = float(
        hourly["relative_humidity_2m"][index]
    )


    pressure = float(
        hourly["pressure_msl"][index]
    )


    weather_code = int(
        hourly["weather_code"][index]
    )


    # ========================================================
    # OPEN-METEO COMPONENTS
    # ========================================================

    rain_component = rainfall_score(
        rainfall
    )


    probability_component = (
        precipitation_probability_score(
            probability
        )
    )


    wind_component = wind_score(
        wind
    )


    humidity_component = humidity_score(
        humidity
    )


    pressure_component = pressure_score(
        pressure
    )


    weather_component = weather_code_score(
        weather_code
    )


    # ========================================================
    # BASE WEIGHTED SCORE
    # ========================================================

    score = (

        rain_component * 0.25

        + probability_component * 0.15

        + wind_component * 0.20

        + humidity_component * 0.05

        + pressure_component * 0.10

        + weather_component * 0.25

    )


    # ========================================================
    # THUNDERSTORM BOOST
    # ========================================================

    if weather_code >= 95:

        score += 10


    # ========================================================
    # COMBINED HAZARD EFFECTS
    # ========================================================

    if (
        rainfall >= 10
        and wind >= 30
    ):

        score += 8


    if (
        rainfall >= 10
        and probability >= 70
    ):

        score += 6


    if (
        wind >= 35
        and probability >= 70
    ):

        score += 5


    # ========================================================
    # WEATHERAPI HOURLY DATA
    # ========================================================

    if weatherapi_hour:

        gust = weatherapi_hour.get(
            "gust_kph"
        )

        chance_of_rain = weatherapi_hour.get(
            "chance_of_rain"
        )


        if gust is not None:

            score += (
                gust_score(gust)
                * 0.10
            )


        if chance_of_rain is not None:

            score += (
                precipitation_probability_score(
                    chance_of_rain
                )
                * 0.10
            )


    # ========================================================
    # FINAL SCORE
    # ========================================================

    score = round(
        clamp(score),
        1
    )


    # ========================================================
    # LEVEL
    # ========================================================

    if score >= 70:

        level = "SEVERE"

    elif score >= 40:

        level = "MODERATE"

    else:

        level = "LOW"


    return {

        "score": score,

        "level": level

    }


# ============================================================
# MAIN RISK CALCULATION
# ============================================================

def calculate_risk(
    current,
    hourly,
    weatherapi_summary=None,
    alerts=None
):

    # ========================================================
    # DEFAULT VALUES
    # ========================================================

    if weatherapi_summary is None:

        weatherapi_summary = {}


    if alerts is None:

        alerts = []


    # ========================================================
    # CURRENT VALUES
    # ========================================================

    rainfall = float(
        current.get(
            "precipitation",
            0
        )
    )


    probability = 0


    wind = float(
        current.get(
            "wind_speed_10m",
            0
        )
    )


    humidity = float(
        current.get(
            "relative_humidity_2m",
            0
        )
    )


    pressure = float(
        current.get(
            "pressure_msl",
            1013
        )
    )


    weather_code = int(
        current.get(
            "weather_code",
            0
        )
    )


    # ========================================================
    # WEATHERAPI DATA
    # ========================================================

    gust = weatherapi_summary.get(
        "gust_kph"
    )


    weatherapi_rain_probability = (
        weatherapi_summary.get(
            "chance_of_rain"
        )
    )


    weatherapi_wind = (
        weatherapi_summary.get(
            "wind_kph"
        )
    )


    weatherapi_rain = (
        weatherapi_summary.get(
            "precipitation_mm"
        )
    )


    # ========================================================
    # USE WEATHERAPI WHEN AVAILABLE
    # ========================================================

    if weatherapi_rain is not None:

        rainfall = max(
            rainfall,
            float(weatherapi_rain)
        )


    if weatherapi_wind is not None:

        wind = max(
            wind,
            float(weatherapi_wind)
        )


    if weatherapi_rain_probability is not None:

        probability = float(
            weatherapi_rain_probability
        )


    # ========================================================
    # CURRENT COMPONENTS
    # ========================================================

    rain_component = rainfall_score(
        rainfall
    )


    probability_component = (
        precipitation_probability_score(
            probability
        )
    )


    wind_component = wind_score(
        wind
    )


    humidity_component = humidity_score(
        humidity
    )


    pressure_component = pressure_score(
        pressure
    )


    weather_component = weather_code_score(
        weather_code
    )


    gust_component = gust_score(
        gust
    )


    # ========================================================
    # BASE CURRENT SCORE
    # ========================================================

    score = (

        rain_component * 0.23

        + probability_component * 0.15

        + wind_component * 0.17

        + gust_component * 0.12

        + humidity_component * 0.04

        + pressure_component * 0.09

        + weather_component * 0.20

    )


    # ========================================================
    # THUNDERSTORM BOOST
    # ========================================================

    if weather_code >= 95:

        score += 12


    # ========================================================
    # COMBINED HAZARD BOOSTS
    # ========================================================

    if (
        rainfall >= 10
        and wind >= 30
    ):

        score += 8


    if (
        rainfall >= 10
        and probability >= 70
    ):

        score += 7


    if (
        wind >= 35
        and gust is not None
        and gust >= 45
    ):

        score += 7


    # ========================================================
    # OFFICIAL WEATHER ALERT
    # ========================================================

    official_alert_points = alert_score(
        alerts
    )


    score += official_alert_points


    # ========================================================
    # FUTURE FORECAST RISK
    # ========================================================

    forecast_risks = []


    number_of_hours = min(

        4,

        len(
            hourly.get(
                "time",
                []
            )
        )

    )


    for i in range(
        number_of_hours
    ):

        hourly_result = calculate_hourly_risk(

            hourly,

            i

        )


        forecast_risks.append(
            hourly_result
        )


    # ========================================================
    # FUTURE RISK ANALYSIS
    # ========================================================

    future_scores = [

        item["score"]

        for item in forecast_risks

    ]


    if future_scores:

        maximum_future_score = max(
            future_scores
        )

        average_future_score = (
            sum(future_scores)
            /
            len(future_scores)
        )

    else:

        maximum_future_score = 0

        average_future_score = 0


    # ========================================================
    # EARLY WARNING
    # ========================================================

    current_score_before_forecast = score


    if (
        maximum_future_score
        >
        current_score_before_forecast + 25
    ):

        score += (

            maximum_future_score
            -
            current_score_before_forecast

        ) * 0.25


    elif (
        maximum_future_score
        >
        current_score_before_forecast + 15
    ):

        score += (

            maximum_future_score
            -
            current_score_before_forecast

        ) * 0.12


    # ========================================================
    # FINAL SCORE
    # ========================================================

    score = round(
        clamp(score),
        1
    )


    # ========================================================
    # FINAL LEVEL
    # ========================================================

    if score >= 70:

        level = "SEVERE"

    elif score >= 40:

        level = "MODERATE"

    else:

        level = "LOW"


    # ========================================================
    # EXPLANATIONS
    # ========================================================

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

        reasons.append(
            "Thunderstorm conditions detected"
        )


    # ========================================================
    # OFFICIAL ALERT REASON
    # ========================================================

    if alerts:

        for alert in alerts:

            event = alert.get(
                "event"
            )

            severity = alert.get(
                "severity"
            )


            if event:

                if severity:

                    reasons.append(
                        f"Official weather alert: {event} ({severity})"
                    )

                else:

                    reasons.append(
                        f"Official weather alert: {event}"
                    )

            else:

                reasons.append(
                    "Official weather alert is active"
                )


    # ========================================================
    # FUTURE RISK REASON
    # ========================================================

    if (
        maximum_future_score
        >
        score + 20
    ):

        reasons.append(
            "Weather risk is expected to increase significantly in the next few hours"
        )

    elif (
        maximum_future_score
        >
        current_score_before_forecast + 15
    ):

        reasons.append(
            "Weather risk is expected to increase in the near term"
        )


    # ========================================================
    # DEFAULT REASON
    # ========================================================

    if not reasons:

        reasons.append(
            "No significant severe-weather indicators detected"
        )


    # ========================================================
    # RETURN
    # ========================================================

    return {

        "score":
            score,

        "level":
            level,

        "reasons":
            reasons,

        "components": {

            "rainfall":
                round(
                    rain_component,
                    1
                ),

            "rain_probability":
                round(
                    probability_component,
                    1
                ),

            "wind":
                round(
                    wind_component,
                    1
                ),

            "wind_gust":
                round(
                    gust_component,
                    1
                ),

            "humidity":
                round(
                    humidity_component,
                    1
                ),

            "pressure":
                round(
                    pressure_component,
                    1
                ),

            "weather_condition":
                round(
                    weather_component,
                    1
                ),

            "official_alert":
                round(
                    official_alert_points,
                    1
                ),

            "maximum_forecast_risk":
                round(
                    maximum_future_score,
                    1
                )

        },

        "forecast_summary": {

            "maximum_risk":
                round(
                    maximum_future_score,
                    1
                ),

            "average_risk":
                round(
                    average_future_score,
                    1
                )

        }

    }