# Rainfall Warning System

This version connects the supplied 47-feature XGBoost rainfall model to the
dashboard and restores the explainable rainfall-warning logic from the
original version.

## What was fixed

- The application was looking for `models/four_hour_model.json`, but the
  supplied trained model is `models/model.json`. The app now uses the actual
  model and also falls back to it if an old `.env` still contains the missing
  `four_hour_model.json` path.
- The XGBoost output is treated as predicted rainfall in **mm**, clipped at
  zero, and used as the primary rainfall-warning signal.
- The last four hourly records are used as the warning horizon. The weather
  fetch supplies 24 recent hours so the 47 lag/sum/change features remain
  meaningful.
- The original explainable risk scoring has been brought back and combined
  with the XGBoost prediction, rain probability, wind/gusts, pressure,
  weather code, and official WeatherAPI alerts.
- WeatherAPI is optional. If it is unavailable or no API key is configured,
  the rainfall warning still works using Open-Meteo + XGBoost.
- The dashboard response keeps the existing `risk`, `forecast`, `actions`,
  and `model` fields expected by the current frontend.

## Architecture

Browser → Flask `/predict` → Open-Meteo → 47-feature builder → supplied
XGBoost model → 4-hour rainfall predictions → rainfall risk engine →
actions/explainability → dashboard.

WeatherAPI is a secondary source for current conditions and official alerts.

## Install

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Then:

```bash
pip install -r requirements.txt
```

## Optional WeatherAPI

Copy `.env.example` to `.env` and add your key:

```text
WEATHER_API_KEY=your_key_here
```

The core rainfall-warning path does **not** require WeatherAPI.

## Run

```bash
python app.py
```

Then open:

`http://127.0.0.1:5000`

## Test endpoint

Example:

```text
http://127.0.0.1:5000/predict?lat=19.017980467662962&lon=73.71002197265626
```

A successful response should contain:

- `model.available: true`
- `model.features: 47`
- four `forecast` records
- a numeric `risk.score`
- `risk.level` (`LOW`, `MODERATE`, or `SEVERE`)
- `risk.reasons`
- `actions`

If `/predict` returns an error, the JSON now includes the actual exception
and the model path so the failure is visible instead of being hidden behind
a generic frontend message.

## Important

This is an early-warning prototype, not an official emergency-warning
service. Thresholds and model calibration should be validated against local
observations before operational deployment.
