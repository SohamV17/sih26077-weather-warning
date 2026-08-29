from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
import os
import requests

from src.weather import fetch_weather, fetch_weatherapi
from src.features import build_row, elevation_from_response
from src.model import NowcastModel
from src.risk import calculate, calculate_hourly_risk
from src.actions import actions_for

load_dotenv()

BASE = os.path.dirname(os.path.abspath(__file__))

# The supplied trained model is models/model.json.  Keep support for an
# explicitly configured MODEL_PATH, but never default to the old missing name.
configured_model_path = os.getenv("MODEL_PATH", "").strip()
if configured_model_path:
    candidate_model_path = os.path.join(BASE, configured_model_path)
else:
    candidate_model_path = os.path.join(BASE, "models/model.json")

# Be forgiving if an older .env still points to the previous missing
# four_hour_model.json name. The supplied trained model is model.json.
if os.path.exists(candidate_model_path):
    MODEL_PATH = candidate_model_path
else:
    MODEL_PATH = os.path.join(BASE, "models/model.json")

configured_feature_path = os.getenv("FEATURE_LIST_PATH", "").strip()
FEATURE_PATH = (
    os.path.join(BASE, configured_feature_path)
    if configured_feature_path
    else os.path.join(BASE, "models/feature_list.json")
)

API_KEY = os.getenv("WEATHER_API_KEY", "").strip()

model = NowcastModel(MODEL_PATH, FEATURE_PATH)

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)


@app.route("/")
def home():
    return render_template("index.html")


def valid_coords(lat, lon):
    lat = float(lat)
    lon = float(lon)

    if not -90 <= lat <= 90:
        raise ValueError("Invalid latitude")
    if not -180 <= lon <= 180:
        raise ValueError("Invalid longitude")

    return lat, lon


@app.route("/predict")
def predict():
    try:
        lat, lon = valid_coords(
            request.args.get("lat", 18.5204),
            request.args.get("lon", 73.8567),
        )

        weather = fetch_weather(lat, lon)
        hourly = weather.get("hourly", {})
        current = weather.get("current", {})
        times = hourly.get("time", [])

        if not times:
            raise RuntimeError("Weather API returned no hourly forecast.")

        elevation = elevation_from_response(weather)

        # Build exactly the same 47-feature rows expected by the supplied
        # XGBoost model.  The API gives 24 past hours + 4 forecast hours.
        rows = [
            build_row(hourly, i, lat, lon, elevation)
            for i in range(len(times))
        ]

        predictions = model.predict(rows)

        # The last four records are the actual forecast window because
        # fetch_weather() requests past_hours=24 and forecast_hours=4.
        start = max(0, len(times) - 4)
        forecast_indexes = list(range(start, len(times)))

        # WeatherAPI is supplementary.  The rainfall warning must still
        # work when WEATHER_API_KEY is absent or WeatherAPI is unavailable.
        wa, wa_error = fetch_weatherapi(lat, lon, API_KEY)
        wa = wa or {}

        alerts = (
            wa.get("alerts", {}).get("alert", [])
            if isinstance(wa.get("alerts", {}), dict)
            else []
        )

        wa_current = wa.get("current", {}) or {}

        weatherapi_summary = {
            "temperature_c": wa_current.get("temp_c"),
            "feels_like_c": wa_current.get("feelslike_c"),
            "humidity": wa_current.get("humidity"),
            "wind_kph": wa_current.get("wind_kph"),
            "gust_kph": wa_current.get("gust_kph"),
            "pressure_mb": wa_current.get("pressure_mb"),
            "precipitation_mm": wa_current.get("precip_mm"),
            "cloud": wa_current.get("cloud"),
            "visibility_km": wa_current.get("vis_km"),
            "uv": wa_current.get("uv"),
            "chance_of_rain": wa_current.get("chance_of_rain"),
            "chance_of_snow": wa_current.get("chance_of_snow"),
            "condition": (
                wa_current.get("condition", {}) or {}
            ).get("text"),
        }

        forecast = []

        selected_predictions = []
        for i in forecast_indexes:
            # Never allow a negative regression output to become a negative
            # rainfall warning.
            prediction = max(float(predictions[i] or 0), 0)
            selected_predictions.append(prediction)

            hourly_risk = calculate_hourly_risk(
                hourly,
                i,
                prediction=prediction,
            )

            forecast.append({
                "time": times[i],
                "temperature": hourly.get("temperature_2m", [0] * len(times))[i],
                "rain": hourly.get("rain", hourly.get("precipitation", [0] * len(times)))[i],
                "precipitation": hourly.get("precipitation", [0] * len(times))[i],
                "precipitation_probability": hourly.get(
                    "precipitation_probability",
                    [0] * len(times)
                )[i],
                "wind": hourly.get("wind_speed_10m", [0] * len(times))[i],
                "prediction": round(prediction, 2),
                "risk": hourly_risk,
            })

        # Overall warning: XGBoost + current weather + official alerts.
        risk = calculate(
            selected_predictions,
            current,
            alerts=alerts,
            weatherapi_summary=weatherapi_summary,
            hourly=hourly,
        )

        actions = actions_for(current, risk, forecast)

        return jsonify({
            "location": {
                "latitude": lat,
                "longitude": lon,
                "elevation": elevation,
            },
            "current": current,
            "risk": risk,
            "forecast": forecast,
            "actions": actions,
            "weatherapi": {
                "current": wa_current,
                "summary": weatherapi_summary,
                "alerts": alerts,
                "available": bool(wa),
                "error": wa_error,
            },
            "model": {
                "available": model.available,
                "features": len(model.features),
                "type": "XGBoost 4-hour rainfall regression",
                "path": os.path.relpath(MODEL_PATH, BASE),
            },
        })

    except requests.RequestException as e:
        return jsonify({
            "error": "Unable to fetch weather data",
            "details": str(e),
            "model_available": model.available,
        }), 502

    except Exception as e:
        app.logger.exception("Rainfall warning prediction failed")
        return jsonify({
            "error": "Weather prediction failed",
            "details": str(e),
            "model_available": model.available,
            "model_path": os.path.relpath(MODEL_PATH, BASE),
        }), 500


@app.route("/geocode")
def geocode():
    q = request.args.get("q", "").strip()

    if not q:
        return jsonify({"error": "City or area name is required"}), 400

    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": q,
                "format": "jsonv2",
                "limit": 1,
                "addressdetails": 1,
            },
            headers={"User-Agent": "HyperLocalWeatherWarning/1.0"},
            timeout=8,
        )
        r.raise_for_status()
        results = r.json()

        if not results:
            return jsonify({"error": f"Location '{q}' was not found"}), 404

        x = results[0]
        a = x.get("address", {})
        area = (
            a.get("city")
            or a.get("town")
            or a.get("village")
            or a.get("municipality")
            or a.get("county")
            or a.get("state")
            or x.get("display_name", q)
        )
        state = a.get("state", "")
        name = f"{area}, {state}" if state and area != state else area

        return jsonify({
            "name": name,
            "latitude": float(x["lat"]),
            "longitude": float(x["lon"]),
            "display_name": x.get("display_name", name),
        })

    except Exception as e:
        return jsonify({
            "error": "Location search failed",
            "details": str(e),
        }), 500


@app.route("/reverse-geocode")
def reverse_geocode():
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    if lat is None or lon is None:
        return jsonify({
            "error": "Latitude and longitude are required"
        }), 400

    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "lat": lat,
                "lon": lon,
                "format": "jsonv2",
                "zoom": 10,
            },
            headers={"User-Agent": "HyperLocalWeatherWarning/1.0"},
            timeout=8,
        )
        r.raise_for_status()

        x = r.json()
        a = x.get("address", {})
        area = (
            a.get("city")
            or a.get("town")
            or a.get("village")
            or a.get("municipality")
            or a.get("county")
            or a.get("state")
            or "Selected area"
        )
        state = a.get("state", "")

        return jsonify({
            "name": (
                f"{area}, {state}"
                if state and area != state
                else area
            )
        })

    except Exception as e:
        return jsonify({
            "error": "Reverse geocoding failed",
            "details": str(e),
        }), 500


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.getenv("PORT", 5000)),
        debug=True,
    )
