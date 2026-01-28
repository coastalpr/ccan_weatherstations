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
import os
import itertools
import rasterio
import itertools
import numpy as np


# -----------------------------
# PAGE CONFIG
# -----------------------------
# Add logo at the top
redirect_url = "https://ccan-upr.org"
#st.image("radar_images/logo.png", width=300)  # You can adjust width as needed
#st.image("radar_images/logo.png", caption=f"({redirect_url})", use_column_width=True)  # You can adjust width as needed

#st.title("🌦️ CCAN Weather Dashboard")
#st.title("ESTACIÓN METEOROLÓGICA")
#st.title("Estación Meteorológica")

# Image URL or local path
image_url = "radar_images/logo.png"  # Replace with your image URL or local path

# Title text
title_text = "Weather Dashboard"

# Create columns
col1, col2 = st.columns([1, 5])  # Column width ratio: first column for the image, second for the title

with col1:
    st.image(image_url, width=200)  # Adjust width as needed

with col2:
    st.title(title_text)



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

# -----------------------------
# UV
# -----------------------------
# Assuming latest.uv is the UV index value
uv_index = latest.uv  # Replace with actual UV index value

# Define color based on UV index
if latest.uv <= 2:
    color = "green"
    background_color = "#d4edda"  # Light green background
    description = "Riesgo: Bajo"
elif 3 <= latest.uv <= 5:
    color = "yellow"
    background_color = "#fff3cd"  # Light yellow background
    description = "Riesgo: Moderado"
elif 6 <= latest.uv <= 7:
    color = "orange"
    background_color = "#ffeeba"  # Light orange background
    description = "Riesgo: Alto"
elif 8 <= latest.uv <= 10:
    color = "red"
    background_color = "#f8d7da"  # Light red background
    description = "Riesgo: Muy Alto"
else:
    color = "purple"
    background_color = "#f1c6e7"  # Light purple background
    description = "Riesgo: Extremo"



st.caption(f"🕒 Última observación: {latest.timestamp_ampm}")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🌡️ Temperatura (°F)", f"{latest.air_temperature:.1f}")
c2.metric("💧 Humedad (%)", f"{latest.relative_humidity:.0f}")
c3.metric("🌬️ Velocidad del Viento (kts)", f"{latest.wind_avg:.1f}")
c4.metric("🧭 Dirección del Viento (º)", f"{wind_direction_cardinal(latest.wind_direction)} ({latest.wind_direction:.0f}°)")
#c5.metric("☀️ Índice UV", f"{latest.uv:.1f}", color=color)
# Display the metric using c5
c5.metric("☀️ Índice UV", f"{latest.uv:.1f}")

# Display the UV index with background color using markdown (custom styling)
# In the last column (c5), display UV index and description on the same line
# In the last column (c5), display UV index and description on the same line with matching font size

with c5:
    # Use st.markdown to display both UV index and description on the same line
#    st.markdown(f"<p style=color:#000000; font-size: 0.5rem; display:inline; margin: 0; line-height: 1;'>☀️ Índice UV</p>", unsafe_allow_html=True)
#    st.markdown(f"<p style='color:{color}; font-size: 2.2rem; display:inline; margin-top: -5px; line-height: 1;'>{latest.uv:.1f}</p>", unsafe_allow_html=True)
   st.markdown(f"<h3 style='color:{color}; font-size: 1rem; margin-top: -30px; padding: 0;'> {description}</h3>", unsafe_allow_html=True)

# In the last column (c5), display UV index and description with matching font size, no bold text, and minimal space
#with c5:
#    st.markdown(
#        f"""
#        <p style='color:#000000; font-size: 0.8rem; font-weight: normal; margin: 0; line-height: 1;'>☀️ Índice UV </p>
#        <p style='color:#000000; font-size: 1.5rem; font-weight: normal; margin: 0; line-height: 1;'> {latest.uv:.1f} </p>
#        <p style='color:{color}; font-size: 2rem; font-weight: normal; margin: 0; line-height: 1;'> {description}</p>
#        """, 
#        unsafe_allow_html=True
#    )
# -----------------------------
# SATELLITE / RADAR LOOP
# -----------------------------
st.subheader("🌐 Radar Satelital Local - Caribe")
st.caption("Animación de radar usando imágenes locales descargadas de MRMS")

RADAR_FOLDER = "radar_images"

#if not os.path.exists(RADAR_FOLDER):
#    st.warning(f"Radar folder not found: {RADAR_FOLDER}. Please create it and add TIF images.")
#else:
#    tif_files = sorted([f for f in os.listdir(RADAR_FOLDER) if f.endswith(".tif")])

#    if not tif_files:
#        st.warning(f"No TIF radar images found in {RADAR_FOLDER}.")
#    else:
#        radar_placeholder = st.empty()

#        for tif_file in itertools.cycle(tif_files):
#            tif_path = os.path.join(RADAR_FOLDER, tif_file)
#            try:
                # Open GeoTIFF with rasterio
                #with rasterio.open(tif_path) as src:
                    # Read first band
                #    band1 = src.read(1)
                #    # Normalize to 0-255
                #    band1 = band1.astype(float)
                #    band1 -= band1.min()
                #    band1 /= band1.max()
                #    band1 *= 255
                #    img = Image.fromarray(band1.astype(np.uint8)).convert("RGBA")
                    
               # radar_placeholder.image(img, use_column_width=True)
           # except Exception as e:
                #st.warning(f"Error loading {tif_file}: {e}")
    
# -----------------------------
# PLOTS
# -----------------------------

# Determine last 2 days
end_date = df['Hora'].max()
start_date = end_date - pd.Timedelta(days=2)

# Generate hourly ticks (optional: every 1 hour)
ticks = pd.date_range(df['Hora'].min(), df['Hora'].max(), freq='6H')

# Tick labels: first and last tick show date, others show hour
meses = ["enero","febrero","marzo","abril","mayo","junio",
         "julio","agosto","septiembre","octubre","noviembre","diciembre"]

tick_labels = [f"{t.day}-{meses[t.month-1]}-{t.year}<br>{t.strftime('%I:%M %p')}" for t in ticks]
tick_labels = [f"{t.day}/{meses[t.month-1]}<br>{t.strftime('%I:%M %p')}" for t in ticks]

#tick_labels = [t.strftime("%m-%d\n%I:%M %p") for t in ticks]
#tick_labels[0] = ticks[0].strftime("%Y-%m-%d")
#tick_labels[-1] = ticks[-1].strftime("%Y-%m-%d")


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





























































