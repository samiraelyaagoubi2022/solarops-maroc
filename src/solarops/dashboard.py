# ruff: noqa: E501
import math
from datetime import datetime, timedelta

import altair as alt
import numpy as np
import pandas as pd
import requests
import streamlit as st
from streamlit_geolocation import streamlit_geolocation

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="SolarOps Maroc",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded",
)

MOIS = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet",
        "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

VILLES = {
    "Rabat": (34.02, -6.84),
    "Casablanca": (33.57, -7.59),
    "Marrakech": (31.63, -8.00),
    "Ouarzazate (Noor)": (30.92, -6.89),
    "Laâyoune": (27.15, -13.20),
    "Dakhla": (23.68, -15.96),
}

# ----------------------------------------------------------------------------
# Style
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .block-container {padding-top: 1.5rem;}
    .hero {
        background: linear-gradient(120deg, #f59e0b 0%, #ea580c 55%, #b91c1c 100%);
        padding: 1.6rem 2rem; border-radius: 16px; color: white; margin-bottom: 1.2rem;
    }
    .hero h1 {margin: 0; font-size: 2rem; color: white;}
    .hero p {margin: .3rem 0 0 0; opacity: .92;}
    div[data-testid="stMetric"] {
        background: rgba(128,128,128,.08);
        border: 1px solid rgba(128,128,128,.2);
        border-left: 5px solid #f59e0b;
        padding: 14px 18px; border-radius: 12px;
    }
    .footer {text-align:center; opacity:.6; font-size:.85rem; margin-top:2rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <h1>☀️ SolarOps Maroc</h1>
        <p>Prévision de production photovoltaïque par intelligence artificielle</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# Fonctions utilitaires
# ----------------------------------------------------------------------------
def solar_geometry(hour: int, month: int, lat: float):
    day_of_year = int(30.4 * month - 15)
    decl = math.radians(23.45) * math.sin(2 * math.pi * (284 + day_of_year) / 365)
    hour_angle = math.radians(15 * (hour - 12))
    lat_r = math.radians(lat)
    cos_z = (math.sin(lat_r) * math.sin(decl)
             + math.cos(lat_r) * math.cos(decl) * math.cos(hour_angle))
    cos_z = max(-1.0, min(1.0, cos_z))
    zenith = math.degrees(math.acos(cos_z))
    return zenith, max(0.0, cos_z)


def build_payload(hour, month, lat, radiation_lag, cloud, temp, humidity, pressure, wind_speed, wind_dir) -> dict:
    zenith, clear_sky = solar_geometry(hour, month, lat)
    return {
        "hour_sin": float(np.sin(2 * np.pi * hour / 24)),
        "hour_cos": float(np.cos(2 * np.pi * hour / 24)),
        "month_sin": float(np.sin(2 * np.pi * month / 12)),
        "month_cos": float(np.cos(2 * np.pi * month / 12)),
        "radiation_lag_24h": float(radiation_lag),
        "solar_zenith": float(zenith),
        "clear_sky_proxy": float(clear_sky),
        "temperature_2m": float(temp),
        "relative_humidity_2m": float(humidity),
        "surface_pressure": float(pressure),
        "cloud_cover": float(cloud),
        "cloud_cover_low": float(cloud / 2),
        "cloud_cover_mid": 0.0,
        "cloud_cover_high": 0.0,
        "wind_speed_10m": float(wind_speed),
        "wind_direction_10m": float(wind_dir),
    }


def call_api(api_url: str, payload: dict, timeout: int = 10) -> float:
    r = requests.post(f"{api_url.rstrip('/')}/predict", json=payload, timeout=timeout)
    r.raise_for_status()
    return float(r.json()["prediction_kw"])


@st.cache_data(ttl=5, show_spinner=False)
def api_online(api_url: str) -> bool:
    try:
        return requests.get(f"{api_url.rstrip('/')}/docs", timeout=2).status_code == 200
    except requests.RequestException:
        return False


def get_open_meteo_forecast(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "shortwave_radiation,temperature_2m,relative_humidity_2m,surface_pressure,cloud_cover,cloud_cover_low,cloud_cover_mid,cloud_cover_high,wind_speed_10m,wind_direction_10m",
        "timezone": "GMT",
        "past_days": 1,
        "forecast_days": 2
    }
    response = requests.get(url, params=params)
    return response.json() if response.status_code == 200 else None


# ----------------------------------------------------------------------------
# Barre latérale
# ----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Paramètres")
    
    mode = st.radio("Mode de fonctionnement", ["📍 GPS Temps Réel", "🎛️ Mode Manuel"])

    capacity = st.number_input("Puissance installée (kW)", 10, 1_000_000, 1000, step=100)
    api_url = st.text_input("URL de l'API", "http://localhost:8000")
    
    online = api_online(api_url)
    if online:
        st.success("API connectée", icon="🟢")
    else:
        st.error("API injoignable", icon="🔴")

    st.divider()

    if mode == "📍 GPS Temps Réel":
        st.subheader("Localisation")
        location = streamlit_geolocation()
        
        if location and location['latitude'] is not None:
            lat = location['latitude']
            lon = location['longitude']
            st.info(f"Position : {lat:.4f}, {lon:.4f}")
            run = st.button("Calculer (Temps Réel) ⚡", type="primary", use_container_width=True)
            mode_gps = True
        else:
            st.warning("Veuillez autoriser la géolocalisation.")
            run = False
            mode_gps = False
            
    else:
        st.subheader("Paramètres manuels")
        ville = st.selectbox("Site", list(VILLES.keys()))
        lat, _lon = VILLES[ville]
        
        month = st.select_slider("Mois", options=list(range(1, 13)), value=6, format_func=lambda m: MOIS[m - 1])
        hour = st.slider("Heure (0-23)", 0, 23, 13, format="%dh")
        
        radiation_lag = st.slider("Rayonnement d'hier (W/m²)", 0, 1200, 600)
        cloud_cover = st.slider("Couverture nuageuse (%)", 0, 100, 10)
        temp = st.slider("Température (°C)", -5, 50, 25)
        
        with st.expander("Paramètres avancés"):
            humidity = st.slider("Humidité relative (%)", 0, 100, 50)
            pressure = st.slider("Pression de surface (hPa)", 900, 1100, 1010)
            wind_speed = st.slider("Vitesse du vent (km/h)", 0, 100, 15)
            wind_dir = st.slider("Direction du vent (°)", 0, 360, 180)

        run = st.button("Calculer (Manuel) ⚡", type="primary", use_container_width=True)
        mode_gps = False

# ----------------------------------------------------------------------------
# Calcul
# ----------------------------------------------------------------------------
if run:
    try:
        with st.spinner("Interrogation du modèle..."):
            if mode_gps:
                forecast = get_open_meteo_forecast(lat, lon)
                if not forecast:
                    st.error("Impossible de récupérer la météo Open-Meteo.")
                    st.stop()
                
                hourly = forecast["hourly"]
                curve = []
                
                # Heure UTC pour trouver le bon index dans la réponse API
                now_utc = datetime.utcnow()
                now_str = now_utc.strftime("%Y-%m-%dT%H:00")
                
                # Heure locale pour l'affichage
                now_local = now_utc + timedelta(hours=1)
                
                try:
                    start_idx = hourly["time"].index(now_str)
                except ValueError:
                    start_idx = 24
                
                for i in range(start_idx, start_idx + 24):
                    dt = datetime.fromisoformat(hourly["time"][i])
                    lag_idx = i - 24
                    
                    payload = build_payload(
                        hour=dt.hour, month=dt.month, lat=lat,
                        radiation_lag=hourly["shortwave_radiation"][lag_idx] if lag_idx >= 0 else 0.0,
                        cloud=hourly["cloud_cover"][i], temp=hourly["temperature_2m"][i],
                        humidity=hourly["relative_humidity_2m"][i], pressure=hourly["surface_pressure"][i],
                        wind_speed=hourly["wind_speed_10m"][i], wind_dir=hourly["wind_direction_10m"][i]
                    )
                    curve.append(max(0.0, call_api(api_url, payload)))
                
                result_hour = now_local.hour
                result_month = now_local.month
                result_ville = f"GPS ({lat:.2f}, {lon:.2f})"
                current_pred = curve[0]
                
            else:
                kwargs = dict(month=month, lat=lat, radiation_lag=radiation_lag, cloud=cloud_cover,
                              temp=temp, humidity=humidity, pressure=pressure,
                              wind_speed=wind_speed, wind_dir=wind_dir)
                current_pred = call_api(api_url, build_payload(hour=hour, **kwargs))
                curve = [max(0.0, call_api(api_url, build_payload(hour=h, **kwargs))) for h in range(24)]
                result_hour = hour
                result_month = month
                result_ville = ville

        st.session_state["result"] = {
            "current": current_pred,
            "curve": curve,
            "hour": result_hour,
            "capacity": capacity,
            "ville": result_ville,
            "month": result_month,
            "time": (datetime.utcnow() + timedelta(hours=1)).strftime("%H:%M:%S"),
        }
    except requests.exceptions.ConnectionError:
        st.error("Impossible de joindre l'API.")
    except Exception as e:
        st.error(f"Erreur : {e}")

# ----------------------------------------------------------------------------
# Affichage
# ----------------------------------------------------------------------------
res = st.session_state.get("result")

tab_prev, tab_data, tab_about = st.tabs(["📈 Prévision", "📋 Données", "ℹ️ À propos"])

with tab_prev:
    if not res:
        st.info("Réglez les paramètres puis cliquez sur le bouton de calcul.")
    else:
        curve = res["curve"]
        cap = res["capacity"]
        pred = res["current"]
        yield_pct = min(pred / cap * 100, 100)
        energy = sum(curve)
        peak_h = int(np.argmax(curve))

        st.caption(f"{res['ville']} · Mois {res['month']} · calculé à {res['time']}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"Production (maintenant)", f"{pred:,.1f} kW")
        c2.metric("Taux de charge", f"{yield_pct:.1f} %")
        c3.metric("Énergie sur la journée", f"{energy:,.0f} kWh")
        c4.metric("Pic de production", f"{max(curve):,.0f} kW", f"à {peak_h}h", delta_color="off")

        st.progress(int(yield_pct), text=f"Utilisation de la capacité : {yield_pct:.1f} %")

        st.subheader("Profil de production sur 24 h")
        df = pd.DataFrame({"Heure": range(24), "Production (kW)": curve})
        base = alt.Chart(df).encode(
            x=alt.X("Heure:Q", scale=alt.Scale(domain=[0, 23]), axis=alt.Axis(title="Heure de la journée", tickMinStep=1)),
            y=alt.Y("Production (kW):Q", axis=alt.Axis(title="kW")),
            tooltip=["Heure", alt.Tooltip("Production (kW):Q", format=".1f")],
        )
        area = base.mark_area(
            line={"color": "#ea580c"},
            color=alt.Gradient(
                gradient="linear",
                stops=[alt.GradientStop(color="#f59e0b", offset=0),
                       alt.GradientStop(color="rgba(245,158,11,0.05)", offset=1)],
                x1=1, x2=1, y1=1, y2=0),
        )
        marker = alt.Chart(pd.DataFrame({"Heure": [res["hour"]], "Production (kW)": [pred]})) \
            .mark_point(size=160, filled=True, color="#b91c1c") \
            .encode(x="Heure:Q", y="Production (kW):Q")
        st.altair_chart((area + marker).properties(height=350), use_container_width=True)

with tab_data:
    if not res:
        st.info("Aucune donnée pour l'instant.")
    else:
        df = pd.DataFrame({
            "Heure": [f"{h:02d}:00" for h in range(24)],
            "Production (kW)": np.round(res["curve"], 2),
            "Taux de charge (%)": np.round(np.array(res["curve"]) / res["capacity"] * 100, 1),
        })
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Exporter en CSV", df.to_csv(index=False).encode("utf-8"),
                           file_name="prevision_solaire.csv", mime="text/csv")

with tab_about:
    st.markdown(
        """
        **SolarOps Maroc** estime la production d'une centrale photovoltaïque à partir
        de conditions météorologiques et de la position du soleil.

        - **Mode GPS** : Récupère la vraie météo via l'API Open-Meteo Forecast.
        - **Mode Manuel** : Utilise les curseurs pour simuler des scénarios.
        - Le modèle de prévision est servi par une API **FastAPI**.
        """
    )

st.markdown('<div class="footer">SolarOps Maroc · Propulsé par FastAPI & Streamlit</div>',
            unsafe_allow_html=True)