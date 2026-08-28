# AI-Driven Hyper-Local Early Warning System for Severe Weather Nowcasting

An AI-assisted hyper-local weather risk assessment and early warning system that analyzes real-time weather conditions for a selected location and provides a short-term severe-weather risk assessment, hazard information, and disaster preparedness guidance.

## Overview

The system allows users to search for a city or area, select a location directly from an interactive map, or use their current location.

Once a location is selected, the system collects weather information from multiple sources and evaluates the current and upcoming weather conditions to generate an explainable risk score.

The system is designed as a rapid MVP for SIH 26077 and focuses on hyper-local weather monitoring and early warning.

## Key Features

- Hyper-local weather analysis using latitude and longitude
- Search locations by city or area name
- Interactive map-based location selection
- Current weather monitoring
- 4-hour short-term weather nowcasting
- Risk score from 0–100
- LOW, MODERATE, and SEVERE risk classification
- Rainfall and precipitation probability analysis
- Wind speed and wind gust analysis
- Humidity and atmospheric pressure analysis
- Weather-condition analysis using weather codes
- Official weather alert integration
- Multiple weather data sources
- Monitored locations
- Explainable risk assessment
- Hazard detection
- Disaster-management and preparedness recommendations
- Responsive web interface

## System Architecture

```text
                    User
                     |
                     v
             Interactive Web UI
             HTML + CSS + JavaScript
                     |
          +----------+----------+
          |                     |
          v                     v
     City/Area Search       Map Selection
          |                     |
          +----------+----------+
                     |
                     v
                Flask Backend
                     |
          +----------+----------+
          |                     |
          v                     v
     Open-Meteo API        WeatherAPI.com
          |                     |
          +----------+----------+
                     |
                     v
              Risk Engine
                     |
          +----------+----------+
          |                     |
          v                     v
      Current Risk          4-Hour Forecast
       Assessment              Risk
          |                     |
          +----------+----------+
                     |
                     v
             Frontend Dashboard
                     |
          +----------+----------+
          |          |           |
          v          v           v
      Risk Score   Hazards   Safety Actions
