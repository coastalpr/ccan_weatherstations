# weather_dashboard.py
# Public, secure Streamlit Weather Dashboard (NetCDF)

import streamlit as st
import pandas as pd
import numpy as np
import xarray as xr
import plotly.express as px
import datetime
import pytz

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="CCAN Weather Dashboard",
    layout="wide"
)

st.title("🌦️ CCAN Weather Dashboard")
st.caption("Los datos meteorológicos recopilados por la estación Tempest se proporcionan únicamente con fines informativos. Su exactitud no está garantizada y toda interpretación, análisis o uso de los datos se realiza bajo la exclusiva responsabilidad del usuario.")

# -----------------------------
# LOAD DATA
# -----------------------------
@st.cache_data(ttl=60)
def load_weather_data(nc_file):
    ds = xr.open_dataset(nc_file)
    df = ds.to_dataframe().reset_index()

    # Ensure timestamp
    if "time" in df.columns:
        df["Hora"] = pd.to_datetime(df["time"]) - pd.Timedelta(hours=4)
        df["timestamp_ampm"] = df["Hora"].dt.strftime("%I:%M %p")
    return df.sort_values("Hora")

# -----------------------------
# FILE PATH
# -----------------------------
DATA_FILE = "weather_data.nc"
df = load_weather_data(DATA_FILE)

# -----------------------------
# ADJUSTING
# -----------------------------
df["air_temperature"] = df["air_temperature"] * 1.8 + 32
df["wind_avg"] = df["wind_avg"] * 1.94384
df["rain_accumulated"] = df["rain_accumulated"] * 0.0393701
df["lightning_strike_avg_distance"] = df["lightning_strike_avg_distance"] * 0.621371
# -----------------------------
# SIDEBAR FILTERS
# -----------------------------
#st.sidebar.header("📅 Filters")

#start_date = st.sidebar.date_input(
#    "Start date", df.timestamp.min().date()
#)

#end_date = st.sidebar.date_input(
#    "End date", df.timestamp.max().date()
#)

#start_time = st.sidebar.time_input("Hora inicio", datetime.time(0, 0))
#end_time = st.sidebar.time_input("Hora fin", datetime.time(23, 59))

#mask = (
#    (df.timestamp.dt.date >= start_date) &
#    (df.timestamp.dt.date <= end_date)
#)
#df = df.loc[mask]

# -----------------------------
# CURRENT CONDITIONS
# -----------------------------

def wind_direction_cardinal(degrees):
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    ix = int((degrees + 22.5) // 45) % 8
    return dirs[ix]

#st.subheader("Datos en Tiempo Real")
st.markdown(
    "<h3 style='color:#1f77b4;'>Datos en Tiempo Real</h3>",
    unsafe_allow_html=True
)
latest = df.iloc[-1]

st.caption(f"🕒 Última observación: {latest.timestamp_ampm}")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🌡️ Temperatura (°F)", f"{latest.air_temperature:.1f}")
c2.metric("💧 Humedad (%)", f"{latest.relative_humidity:.0f}")
c3.metric("🌬️ Velocidad del Viento (kts)", f"{latest.wind_avg:.1f}")
c4.metric("🧭 Dirección del Viento (º)", f"{wind_direction_cardinal(latest.wind_direction)} ({latest.wind_direction:.0f}°)")
c5.metric("☀️ Índice UV", f"{latest.uv:.1f}")

# -----------------------------
# PLOTS
# -----------------------------

st.subheader("")
st.markdown(
    "<h3 style='color:#1f77b4;'>Datos Adicionales</h3>",
    unsafe_allow_html=True
)


## Air Temperature
fig = px.line(df, x="Hora", y="air_temperature", title="Temperatura del Aire",labels={"air_temperature": "Temperatura (ºF)"})

fig.update_layout(
    xaxis=dict(
        tickformatstops=[
            dict(dtickrange=[None, None], value="%y-%m-%d\n%H:%M %p")
        ],
        nticks=23
    )
)
fig.update_layout(
    xaxis_title="Hora del Día",
    yaxis_title="Temperatura (°F)"
)
st.plotly_chart(fig, use_container_width=True)
    ## Humidity
fig = px.line(df, x="Hora", y="relative_humidity", title="Humedad Relativa",labels={"relative_humidity": "Humedad Relativa (%)"})

fig.update_layout(
    xaxis=dict(
        tickformatstops=[
            dict(dtickrange=[None, None], value="%Y-%m-%d\n%I:%M %p")
        ],
        nticks=23
    )
)
fig.update_layout(
    xaxis_title="Hora del Día",
    yaxis_title="Humedad Relativa (%)"
)
st.plotly_chart(fig, use_container_width=True)

    ## Wind Speed
fig = px.line(df, x="Hora", y="wind_avg", title="Velocidad del Viento",labels={"wind_avg": "Velocidad del Viento (kts)"})

fig.update_layout(
    xaxis=dict(
        tickformat="%Y-%m-%d\n%I:%M %p",  # format for each tick
        dtick=12 * 3600000,                     # 1-hour intervals
        tickangle=45                        # optional, rotate labels if crowded
    )
)

fig.update_layout(
    xaxis_title="Hora del Día",
    yaxis_title="Velocidad del Viento (nudos)"
)
st.plotly_chart(fig, use_container_width=True)

    ## Wind Direction
fig = px.line(df, x="Hora", y="wind_direction", title="Dirección del Viento",labels={"wind_direction": "Dirección del Vienton(º)"})

fig.update_layout(
    xaxis=dict(
        tickformatstops=[
            dict(dtickrange=[None, None], value="%Y-%m-%d\n%I:%M %p")
        ],
        nticks=23
    )
)
fig.update_layout(
    xaxis_title="Hora del Día",
    yaxis_title="Dirección del Viento (grados)"
)
st.plotly_chart(fig, use_container_width=True)

    ## Rain Accumulation
fig = px.bar(df, x="Hora", y="rain_accumulated", title="Precipitación Acumulada",labels={"rain_accumulated": "Precipitación (\")"})

fig.update_layout(
    xaxis=dict(
        tickformatstops=[
            dict(dtickrange=[None, None], value="%Y-%m-%d\n%I:%M %p")
        ],
        nticks=23
    )
)
fig.update_layout(
    xaxis_title="Hora del Día",
    yaxis_title="Precipitación Acumulada (pulgadas)"
)
st.plotly_chart(fig, use_container_width=True)

    ## Solar Radiation
fig = px.line(df, x="Hora", y="solar_radiation", title="Radiación Solar",labels={"solar_radiation": "Radiación Solar (Wm-2)"})

fig.update_layout(
    xaxis=dict(
        tickformatstops=[
            dict(dtickrange=[None, None], value="%Y-%m-%d\n%I:%M %p")
        ],
        nticks=23
    )
)
fig.update_layout(
    xaxis_title="Hora del Día",
    yaxis_title="Radiación Solar (Wm-2)"
)

st.plotly_chart(fig, use_container_width=True)

    ## UV
fig = px.line(df, x="Hora", y="uv", title="Índice UV",labels={"uv": "UV"})

fig.update_layout(
    xaxis=dict(
        tickformatstops=[
            dict(dtickrange=[None, None], value="%Y-%m-%d\n%I:%M %p")
        ],
        nticks=23
    )
)

fig.update_layout(
    xaxis_title="Hora del Día",
    yaxis_title="Índice UV"
)
st.plotly_chart(fig, use_container_width=True)

    ## Strike
fig = px.line(df, x="Hora", y="lightning_strike_avg_distance", title="Distancia del Rayo",labels={"lightning_strike_avg_distance": "Distancia del Rayo (mi)"})

fig.update_layout(
    xaxis=dict(
        tickformatstops=[
            dict(dtickrange=[None, None], value="%Y-%m-%d\n%I:%M %p")
        ],
        nticks=23
    )
)
fig.update_layout(
    xaxis_title="Hora del Día",
    yaxis_title="Distancia del Rayo (millas)"
)
st.plotly_chart(fig, use_container_width=True)
# -----------------------------
# FOOTER
# -----------------------------
st.markdown("---")
st.caption("Powered by Streamlit • Plotly • NetCDF • Python")
































