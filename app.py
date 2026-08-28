from flask import Flask, render_template, jsonify, request
import requests
import os
from dotenv import load_dotenv

from risk_engine import calculate_risk, calculate_hourly_risk

load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "").strip()

app = Flask(__name__)

@app.route("/")
def home():

    return render_template("index.html")

@app.route("/weather")
def weather():

    lat = request.args.get(
        "lat",
        18.5204
    )

    lon = request.args.get(
        "lon",
        73.8567
    )

    url = "https://api.open-meteo.com/v1/forecast"

    params = {

        "latitude": lat,

        "longitude": lon,

        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation,"
            "pressure_msl,"
            "wind_speed_10m,"
            "weather_code"
        ),

        "hourly": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation_probability,"
            "precipitation,"
            "rain,"
            "pressure_msl,"
            "wind_speed_10m,"
            "weather_code"
        ),

        "forecast_hours": 24,

        "timezone": "auto"
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        return jsonify(data)

    except requests.RequestException as e:

        return jsonify({

            "error":
                "Unable to fetch Open-Meteo data",

            "details":
                str(e)

        }), 500

@app.route("/predict")
def predict():

    lat = request.args.get(
        "lat",
        18.5204
    )

    lon = request.args.get(
        "lon",
        73.8567
    )

    open_meteo_url = (
        "https://api.open-meteo.com/v1/forecast"
    )

    open_meteo_params = {

        "latitude": lat,

        "longitude": lon,

        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation,"
            "pressure_msl,"
            "wind_speed_10m,"
            "weather_code"
        ),

        "hourly": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation_probability,"
            "precipitation,"
            "rain,"
            "pressure_msl,"
            "wind_speed_10m,"
            "weather_code"
        ),

        "forecast_hours": 24,

        "timezone": "auto"
    }

    weather_api_url = (
        "https://api.weatherapi.com/v1/forecast.json"
    )

    weather_api_params = {

        "key":
            WEATHER_API_KEY,

        "q":
            f"{lat},{lon}",

        "days":
            1,

        "alerts":
            "yes"

    }

    try:

        open_meteo_response = requests.get(

            open_meteo_url,

            params=open_meteo_params,

            timeout=10

        )

        open_meteo_response.raise_for_status()

        open_meteo_data = (
            open_meteo_response.json()
        )

        weather_api_data = {}
        weatherapi_error = None

        if WEATHER_API_KEY:
            try:
                weather_api_response = requests.get(
                    weather_api_url,
                    params=weather_api_params,
                    timeout=10
                )
                weather_api_response.raise_for_status()
                weather_api_data = weather_api_response.json()
            except requests.RequestException as e:
                weatherapi_error = str(e)
        else:
            weatherapi_error = "WEATHER_API_KEY is not configured"

        current = (
            open_meteo_data["current"]
        )

        hourly = (
            open_meteo_data["hourly"]
        )

        weatherapi_current = (

            weather_api_data
            .get("current", {})

        )

        alerts = (

            weather_api_data
            .get("alerts", {})
            .get("alert", [])

        )

        weatherapi_summary = {

            "temperature_c":

                weatherapi_current.get(
                    "temp_c"
                ),

            "feels_like_c":

                weatherapi_current.get(
                    "feelslike_c"
                ),

            "humidity":

                weatherapi_current.get(
                    "humidity"
                ),

            "wind_kph":

                weatherapi_current.get(
                    "wind_kph"
                ),

            "gust_kph":

                weatherapi_current.get(
                    "gust_kph"
                ),

            "pressure_mb":

                weatherapi_current.get(
                    "pressure_mb"
                ),

            "precipitation_mm":

                weatherapi_current.get(
                    "precip_mm"
                ),

            "cloud":

                weatherapi_current.get(
                    "cloud"
                ),

            "visibility_km":

                weatherapi_current.get(
                    "vis_km"
                ),

            "uv":

                weatherapi_current.get(
                    "uv"
                ),

            "chance_of_rain":

                weatherapi_current.get(
                    "chance_of_rain"
                ),

            "chance_of_snow":

                weatherapi_current.get(
                    "chance_of_snow"
                ),

            "condition":

                weatherapi_current
                .get("condition", {})
                .get("text")

        }

        weatherapi_forecast_days = (

            weather_api_data
            .get("forecast", {})
            .get("forecastday", [])

        )

        weatherapi_hourly = []

        if weatherapi_forecast_days:

            weatherapi_hourly = (

                weatherapi_forecast_days[0]
                .get("hour", [])

            )

        risk = calculate_risk(

            current,

            hourly,

            weatherapi_summary,

            alerts

        )

        forecast = []

        number_of_hours = min(

            4,

            len(hourly["time"])

        )

        for i in range(
            number_of_hours
        ):

            hourly_risk = (

                calculate_hourly_risk(

                    hourly,

                    i

                )

            )

            forecast.append({

                "time":

                    hourly["time"][i],

                "temperature":

                    hourly["temperature_2m"][i],

                "rain":

                    hourly["rain"][i],

                "precipitation":

                    hourly["precipitation"][i],

                "precipitation_probability":

                    hourly[
                        "precipitation_probability"
                    ][i],

                "wind":

                    hourly["wind_speed_10m"][i],

                "risk":

                    hourly_risk

            })

        return jsonify({

            "location": {

                "latitude":
                    float(lat),

                "longitude":
                    float(lon)

            },

            "current":
                current,

            "risk":
                risk,

            "forecast":
                forecast,

            "weatherapi": {

                "current":
                    weatherapi_summary,

                "alerts":
                    alerts,

                "hourly":
                    weatherapi_hourly,

                "available":
                    bool(weather_api_data),

                "error":
                    weatherapi_error

            }

        })

    except requests.RequestException as e:

        return jsonify({

            "error":
                "Unable to fetch weather data",

            "details":
                str(e)

        }), 500

    except Exception as e:

        return jsonify({

            "error":
                "Weather prediction failed",

            "details":
                str(e)

        }), 500


@app.route("/geocode")
def geocode():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "City or area name is required"}), 400
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": query,
                "format": "jsonv2",
                "limit": 1,
                "addressdetails": 1
            },
            headers={
                "User-Agent": "SIH26077-WeatherWarning-MVP/1.0"
            },
            timeout=8
        )
        response.raise_for_status()
        results = response.json()
        if not results:
            return jsonify({"error": f"Location '{query}' was not found"}), 404
        result = results[0]
        address = result.get("address", {})
        area = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
            or address.get("county")
            or address.get("state")
            or result.get("display_name", query)
        )
        state = address.get("state", "")
        name = f"{area}, {state}" if state and area != state else area
        return jsonify({
            "name": name,
            "latitude": float(result["lat"]),
            "longitude": float(result["lon"]),
            "display_name": result.get("display_name", name)
        })
    except requests.RequestException as e:
        return jsonify({
            "error": "Unable to search for the location",
            "details": str(e)
        }), 502
    except Exception as e:
        return jsonify({
            "error": "Location search failed",
            "details": str(e)
        }), 500

@app.route("/reverse-geocode")
def reverse_geocode():
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    if not lat or not lon:
        return jsonify({"error": "Latitude and longitude are required"}), 400
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "format": "jsonv2",
                "lat": lat,
                "lon": lon,
                "zoom": 18,
                "addressdetails": 1
            },
            headers={
                "User-Agent": "SIH26077-WeatherWarning-MVP/1.0"
            },
            timeout=8
        )
        response.raise_for_status()
        result = response.json()
        address = result.get("address", {})
        area = (
            address.get("neighbourhood")
            or address.get("suburb")
            or address.get("village")
            or address.get("town")
            or address.get("city_district")
            or address.get("city")
            or address.get("municipality")
            or address.get("county")
            or address.get("state")
            or "Selected Area"
        )
        state = address.get("state", "")
        name = f"{area}, {state}" if state and area != state else area
        return jsonify({
            "name": name,
            "area": area,
            "state": state,
            "country": address.get("country", "")
        })
    except requests.RequestException as e:
        return jsonify({"error": "Unable to resolve location name", "details": str(e)}), 502
    except Exception as e:
        return jsonify({"error": "Location name lookup failed", "details": str(e)}), 500

if __name__ == "__main__":

    app.run(
        debug=True
    )
