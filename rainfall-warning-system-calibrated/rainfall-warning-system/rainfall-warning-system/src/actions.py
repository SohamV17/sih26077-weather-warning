def actions_for(current, risk, forecast):
    rain=max([float(h.get("prediction",0) or 0) for h in forecast], default=0)
    wind=max(float(current.get("wind_speed_10m",0) or 0), float(current.get("wind_gusts_10m",0) or 0))
    code=int(current.get("weather_code",0) or 0)
    actions=[]
    if rain>=20:
        actions += ["🌧️ Avoid low-lying, waterlogged and flood-prone areas.", "🚫 Do not cross flooded roads or rapidly flowing water.", "📱 Monitor official rainfall/flood advisories closely."]
    elif rain>=10:
        actions += ["🌧️ Expect periods of heavy rain; allow extra travel time and avoid waterlogged routes.", "📱 Monitor official weather updates for rapid changes."]
    elif rain>2:
        actions += ["🌧️ Carry rain protection and remain alert for worsening rainfall."]
    if wind>=50:
        actions += ["💨 Stay indoors where possible and secure loose outdoor objects.", "🌳 Avoid trees, billboards and temporary structures."]
    elif wind>=35:
        actions += ["💨 Use caution around trees, temporary structures and exposed areas."]
    if code>=95:
        actions += ["⛈️ Move indoors during thunderstorms and avoid open fields and isolated trees.", "⚡ Avoid unnecessary contact with electrical equipment during the storm."]
    if risk["level"]=="SEVERE":
        actions += ["🚨 Treat this as a high-risk period and follow instructions from local authorities/emergency services."]
    elif risk["level"]=="MODERATE":
        actions += ["⚠️ Stay alert and reassess conditions as the next few hours develop."]
    if not actions: actions=["✅ No immediate severe-weather action is indicated.", "📱 Continue monitoring the nowcast and official advisories."]
    # de-duplicate while preserving order
    return list(dict.fromkeys(actions))
