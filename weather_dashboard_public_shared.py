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
# SATELLITE / RADAR LOOP
# -----------------------------
import requests
from PIL import Image
from io import BytesIO
import time
import re

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
# SATELLITE / RADAR LOOP
# -----------------------------
st.subheader("🌐 Radar Satelital Local - Caribe")
st.caption("Animación de radar usando imágenes locales descargadas de MRMS")

# Path to local radar images folder
RADAR_FOLDER = "radar_images"

# Get list of PNG images
radar_images = sorted([f for f in os.listdir(RADAR_FOLDER) if f.endswith(".png")])

if not radar_images:
    st.warning("No se encontraron imágenes de radar locales.")
else:
    radar_placeholder = st.empty()

    # Loop images continuously
    import itertools
    for img_file in itertools.cycle(radar_images):
        img_path = os.path.join(RADAR_FOLDER, img_file)
        img = Image.open(img_path).convert("RGBA")
        radar_placeholder.image(img, use_column_width=True)
        time.sleep(0.5)  # Adjust speed as desired
    
# -----------------------------
# PLOTS
# -----------------------------

# Determine last 3 days
end_date = df['Hora'].max()
start_date = end_date - pd.Timedelta(days=3)

# Generate hourly ticks (optional: every 1 hour)
ticks = pd.date_range(df['Hora'].min(), df['Hora'].max(), freq='6H')

# Tick labels: first and last tick show date, others show hour
meses = ["enero","febrero","marzo","abril","mayo","junio",
         "julio","agosto","septiembre","octubre","noviembre","diciembre"]

tick_labels = [f"{t.day}-{meses[t.month-1]}-{t.year}<br>{t.strftime('%I:%M %p')}" for t in ticks]
#tick_labels = [t.strftime("%m-%d\n%I:%M %p") for t in ticks]
tick_labels[0] = ticks[0].strftime("%Y-%m-%d")
tick_labels[-1] = ticks[-1].strftime("%Y-%m-%d")


st.subheader("")
st.markdown(
    "<h3 style='color:#1f77b4;'>Datos Adicionales</h3>",
    unsafe_allow_html=True
)


## ----------------------------------------
# Air Temperature
## ----------------------------------------

fig = px.line(df, x="Hora", y="air_temperature", title="Temperatura del Aire",labels={"air_temperature": "Temperatura (ºF)"})

# Hover: only y-value, no colored box
fig.update_traces(
    hovertemplate='%{y:.1f} °F<extra></extra>',
)

# Layout
fig.update_layout(
    hovermode="x unified",
    xaxis=dict(
        tickmode='array',
        tickvals=ticks,
        ticktext=tick_labels,   # date + hour for all ticks
        tickangle=90,
        showline=False,         # no black line
        showspikes=True,       # no vertical blue line
        spikecolor='rgb(128,128,128)',
        range=[start_date, end_date],
        side='bottom'
    ),
    yaxis_title="Temperatura (°F)",
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)

## ----------------------------------------
# Humidity
## ----------------------------------------
fig = px.line(df, x="Hora", y="relative_humidity", title="Humedad Relativa",labels={"relative_humidity": "Humedad Relativa (%)"})

# Hover: only y-value, no colored box
fig.update_traces(
    hovertemplate='%{y:.1f} °F<extra></extra>',
)

# Layout
fig.update_layout(
    hovermode="x unified",
    xaxis=dict(
        tickvals=ticks,
        ticktext=tick_labels,   # date + hour for all ticks
        tickangle=90,
        showline=False,         # no black line
        showspikes=True,       # no vertical blue line
        spikecolor='rgb(128,128,128)',
        range=[start_date, end_date],
        side='bottom'
    ),
    yaxis_title="Humedad Relative (%)",
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)

## ----------------------------------------
# Wind Speed
## ----------------------------------------
fig = px.line(df, x="Hora", y="wind_avg", title="Velocidad del Viento",labels={"wind_avg": "Velocidad del Viento (kts)"})

# Hover: only y-value, no colored box
fig.update_traces(
    hovertemplate='%{y:.1f} °F<extra></extra>',
)

# Layout
fig.update_layout(
    hovermode="x unified",
    xaxis=dict(
        tickvals=ticks,
        ticktext=tick_labels,   # date + hour for all ticks
        tickangle=90,
        showline=False,         # no black line
        showspikes=True,       # no vertical blue line
        spikecolor='rgb(128,128,128)',
        range=[start_date, end_date],
        side='bottom'
    ),
    yaxis_title="Velocidad del Viento (kts)",
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)

## ----------------------------------------
# Wind Direction
## ----------------------------------------
fig = px.line(df, x="Hora", y="wind_direction", title="Dirección del Viento",labels={"wind_direction": "Dirección del Vienton(º)"})

fig.update_traces(
    hovertemplate='%{y:.1f} °F<extra></extra>',
)

# Layout
fig.update_layout(
    hovermode="x unified",
    xaxis=dict(
        tickvals=ticks,
        ticktext=tick_labels,   # date + hour for all ticks
        tickangle=90,
        showline=False,         # no black line
        showspikes=True,       # no vertical blue line
        spikecolor='rgb(128,128,128)',
        range=[start_date, end_date],
        side='bottom'
    ),
    yaxis_title="Dirección del Viento (º)",
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)

## ----------------------------------------
# Rain Accumulation
## ----------------------------------------
fig = px.bar(df, x="Hora", y="rain_accumulated", title="Precipitación Acumulada",labels={"rain_accumulated": "Precipitación (\")"})

fig.update_traces(
    hovertemplate='%{y:.1f} °F<extra></extra>',
)

# Layout
fig.update_layout(
    hovermode="x unified",
    xaxis=dict(
        tickvals=ticks,
        ticktext=tick_labels,   # date + hour for all ticks
        tickangle=90,
        showline=False,         # no black line
        showspikes=True,       # no vertical blue line
        spikecolor='rgb(128,128,128)',
        range=[start_date, end_date],
        side='bottom'
    ),
    yaxis_title="Precipitación Acumulada (\")",
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)

## ----------------------------------------
# Solar Radiation
## ----------------------------------------
#fig = px.line(df, x="Hora", y="solar_radiation", title="Radiación Solar",labels={"solar_radiation": "Radiación Solar (Wm-2)"})

#fig.update_traces(
#    hovertemplate='%{y:.1f} °F<extra></extra>',
#)

# Layout
#fig.update_layout(
#    hovermode="x unified",
#    xaxis=dict(
#        tickvals=ticks,
#        ticktext=tick_labels,   # date + hour for all ticks
#        tickangle=90,
#        showline=False,         # no black line
#        showspikes=True,       # no vertical blue line
#        spikecolor='rgb(128,128,128)',
#        range=[start_date, end_date],
#        side='bottom'
#    ),
#    yaxis_title="Radiación Solar (Wm-2)",
#    showlegend=False
#)

#st.plotly_chart(fig, use_container_width=True)

## ----------------------------------------
# UV
## ----------------------------------------
fig = px.line(df, x="Hora", y="uv", title="Índice UV",labels={"uv": "UV"})

fig.update_traces(
    hovertemplate='%{y:.1f} °F<extra></extra>',
)

# Layout
fig.update_layout(
    hovermode="x unified",
    xaxis=dict(
        tickvals=ticks,
        ticktext=tick_labels,   # date + hour for all ticks
        tickangle=90,
        showline=False,         # no black line
        showspikes=True,       # no vertical blue line
        spikecolor='rgb(128,128,128)',
        range=[start_date, end_date],
        side='bottom'
    ),
    yaxis_title="Índice UV",
    showlegend=False
)
st.plotly_chart(fig, use_container_width=True)

## ----------------------------------------
# Lightning Strike
## ----------------------------------------
fig = px.line(df, x="Hora", y="lightning_strike_avg_distance", title="Distancia del Rayo",labels={"lightning_strike_avg_distance": "Distancia del Rayo (mi)"})

fig.update_traces(
    hovertemplate='%{y:.1f} °F<extra></extra>',
)

# Layout
fig.update_layout(
    hovermode="x unified",
    xaxis=dict(
        tickvals=ticks,
        ticktext=tick_labels,   # date + hour for all ticks
        tickangle=90,
        showline=False,         # no black line
        showspikes=True,       # no vertical blue line
        spikecolor='rgb(128,128,128)',
        range=[start_date, end_date],
        side='bottom'
    ),
    yaxis_title="Distancia del Rayo (mi)",
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# FOOTER
# -----------------------------
st.markdown("---")
st.caption("Powered by Streamlit • Plotly • NetCDF • Python")
























