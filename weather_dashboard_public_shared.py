# weather_dashboard.py
# Public, secure Streamlit Weather Dashboard (NetCDF)

import streamlit as st
import pandas as pd
import numpy as np
import xarray as xr
import plotly.express as px
import datetime
import pytz
import pydeck as pdk
import requests
from PIL import Image
from io import BytesIO
import time
import re
import os
import itertools
import rasterio
import matplotlib.pyplot as plt
from matplotlib import cm
import plotly.graph_objects as go
import rasterio
from rasterio.plot import reshape_as_image
import folium
from streamlit_folium import st_folium
from rasterio.plot import reshape_as_image
from rasterio.warp import transform_bounds
from pathlib import Path
from rasterio.windows import from_bounds
# -----------------------------
# PAGE CONFIG
# -----------------------------
# Add logo at the top
redirect_url = "https://ccan-upr.org"
#st.image("radar_images/logo.png", caption=f"({redirect_url})", use_column_width=True)  # You can adjust width as needed

#st.title("🌦️ CCAN Weather Dashboard")

# Image URL or local path
image_url = "logo.png"  # Replace with your image URL or local path

# Title text
title_text = "Estación Meteorológica"

# Create columns
col1, col2 = st.columns([2, 5])  # Column width ratio: first column for the image, second for the title

with col1:
    st.image(image_url, width=300)  # Adjust width as needed
with col2:
    st.title(title_text)

st.caption("Los datos meteorológicos recopilados por la estación Tempest se proporcionan únicamente con fines informativos. Su exactitud no está garantizada y toda interpretación, análisis o uso de los datos se realiza bajo la exclusiva responsabilidad del usuario.")

# -----------------------------
# LOAD DATA
# -----------------------------
@st.cache_data(ttl=60)
def load_weather_data(nc_file):
    ds = xr.open_dataset(nc_file, decode_timedelta=True)
    df = ds.to_dataframe().reset_index()

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
# UV Ranges
# -----------------------------
# Assuming latest.uv is the UV index value
uv_index = latest.uv  # Replace with actual UV index value

# Define color based on UV index
if latest.uv <= 2:
    color = "green"
    background_color = "#d4edda"  # Light green background
    description = "Riesgo: Bajo"
elif 3 <= latest.uv <= 6:
    color = "#b58900"   # darker yellow / amber
    background_color = "#fff3cd"
    description = "Riesgo: Moderado"
elif 6 <= latest.uv <= 7:
    color = "orange"
    background_color = "#ffeeba"  # Light orange background
    description = "Riesgo: Alto"
elif 7 <= latest.uv <= 10:
    color = "red"
    background_color = "#f8d7da"  # Light red background
    description = "Riesgo: Muy Alto"
else:
    color = "purple"
    background_color = "#f1c6e7"  # Light purple background
    description = "Riesgo: Extremo"


st.caption(f"🕒 Última observación: {latest.timestamp_ampm}")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🌬️ Velocidad del Viento", f"{latest.wind_avg:.1f} kts")
#c2.metric("🧭 Dirección del Viento (º)",f"Del {wind_direction_cardinal(latest.wind_direction)}\n({latest.wind_direction:.0f}°)")
c2.metric("🧭 Dirección del Viento",f"Del {wind_direction_cardinal(latest.wind_direction)}")
c3.metric("🌡️ Temperatura", f"{latest.air_temperature:.1f} °F")
c4.metric("💧 Humedad", f"{latest.relative_humidity:.0f}%")
# Display the metric using c5
c5.metric("☀️ Índice UV", f"{latest.uv:.1f}")

with c2:
    st.markdown(
        f"""
        <div style=" font-size: 1.5rem; margin-top: -30px; padding: 0;">
            ({latest.wind_direction:.0f}°)
        </div>
        """,
        unsafe_allow_html=True
    )

with c5:
   st.markdown(f"<h3 style='color:{color}; font-size: 1rem; margin-top: -30px; padding: 0;'> {description}</h3>", unsafe_allow_html=True)

st.markdown(
    """
    <style>
    /* Metric value */
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: bold;
    }
    /* Metric label */
    div[data-testid="stMetricLabel"] {
        font-size: 0.65rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

#################################################################################
## ----------------------------------------
# Radar
## ----------------------------------------
#################################################################################
radar_folder = Path("radar_images")
satellite_path = "satellite_image.png"  # static satellite image
zoom_bbox = { "lon_min": -80.5, "lon_max": -75.0, "lat_min": 17.5, "lat_max": 21.0 }  # zoom area

# -----------------------------
# LOAD RADAR FILES
# -----------------------------
tif_files = sorted(radar_folder.glob("*.tif"))
if not tif_files:
    st.warning("No radar files found in radar_images folder.")
    st.stop()

# -----------------------------
# FUNCTION TO CONVERT TIF TO RGBA
# -----------------------------
def tif_to_rgb_overlay(tif_path, bbox, alpha=0.5):
    cmap = plt.get_cmap("turbo")
    with rasterio.open(tif_path) as src:
        from rasterio.windows import from_bounds
        window = from_bounds(bbox["lon_min"], bbox["lat_min"],
                             bbox["lon_max"], bbox["lat_max"], transform=src.transform)
        data = src.read(1, window=window)
        nodata = src.nodata

    data_masked = np.ma.masked_where(data == nodata, data)
    norm_data = (data_masked - data_masked.min()) / (data_masked.max() - data_masked.min())
    rgb = (cmap(norm_data.filled(0))[:, :, :3] * 255).astype(np.uint8)
    img = Image.fromarray(rgb)
    img.putalpha(int(255 * alpha))
    return img

# -----------------------------
# LOAD SATELLITE IMAGE
# -----------------------------
sat_img = Image.open(satellite_path)
# Resize satellite image to match first radar frame
radar_img_sample = tif_to_rgb_overlay(tif_files[-1], zoom_bbox)
sat_img_resized = sat_img.resize(radar_img_sample.size)

# -----------------------------
# RADAR ANIMATION CONTROLS
# -----------------------------
if "play" not in st.session_state:
    st.session_state.play = False
if "index" not in st.session_state:
    st.session_state.index = 0

col1, col2 = st.columns([1,1])
with col1:
    if st.button("Play"):
        st.session_state.play = True
with col2:
    if st.button("Stop"):
        st.session_state.play = False

placeholder = st.empty()  # container for radar animation

# -----------------------------
# FUNCTION TO SHOW RADAR
# -----------------------------
def show_radar(index):
    radar_img = tif_to_rgb_overlay(tif_files[index], zoom_bbox)
    combined = Image.alpha_composite(sat_img_resized.convert("RGBA"), radar_img)
    placeholder.image(combined, caption=tif_files[index].name, use_column_width=True)

# -----------------------------
# PLAY RADAR ANIMATION
# -----------------------------
if st.session_state.play:
    for i in range(st.session_state.index, len(tif_files)):
        if not st.session_state.play:
            break
        st.session_state.index = i
        show_radar(i)
        time.sleep(1)
    st.session_state.index = 0  # loop back

# -----------------------------
# SHOW LATEST RADAR FRAME (if not playing)
# -----------------------------
if not st.session_state.play:
    show_radar(st.session_state.index)

#################################################################################
# -----------------------------
# PLOTS
# -----------------------------
#################################################################################

# Determine last 2 days
end_date = df['Hora'].max()
start_date = end_date - pd.Timedelta(days=1)

# Generate hourly ticks (optional: every 1 hour)
ticks = pd.date_range(df['Hora'].min(), df['Hora'].max(), freq='6h')
# Tick labels: first and last tick show date, others show hour
meses = ["enero","febrero","marzo","abril","mayo","junio",
         "julio","agosto","septiembre","octubre","noviembre","diciembre"]

tick_labels = [f"{t.day}-{meses[t.month-1]}-{t.year}<br>{t.strftime('%I:%M %p')}" for t in ticks]
tick_labels = [f"{t.day}/{meses[t.month-1]}<br>{t.strftime('%I:%M %p')}" for t in ticks]


st.subheader("")
st.markdown(
    "<h3 style='color:#1f77b4;font-size: 1.8rem; margin-top: -40px; padding: 0;'>Datos Adicionales</h3>",
    unsafe_allow_html=True
)

#################################################################################
## ----------------------------------------
# Wind Speed
## ----------------------------------------
#################################################################################

df["Hora"] = pd.to_datetime(df["Hora"])
df = df.sort_values("Hora")
#df["Hora"] = pd.to_datetime(df["Hora"])
df["wind_avg"] = pd.to_numeric(df["wind_avg"], errors="coerce")
df["wind_direction"] = pd.to_numeric(df["wind_direction"], errors="coerce")

#df_wind = df[
#    (df["wind_avg"] > 0.1) & 
#    (df["wind_direction"].notna())
#].iloc[::1].copy()  # downsample

df_wind = (
    df.set_index("Hora")[["wind_avg","wind_direction"]]
      .resample("15T")
      .mean()
      .dropna()
      .reset_index()
)

# Get the latest observation
latest = df[["Hora", "wind_avg", "wind_direction"]].sort_values("Hora").iloc[-1:]

# Append it to the resampled dataframe if it's not already included
if latest["Hora"].iloc[-1] not in df_wind["Hora"].values:
    df_wind = pd.concat([df_wind, latest], ignore_index=True)

# Sort again by time
df_wind = df_wind.sort_values("Hora").reset_index(drop=True)
#df_wind = df_wind.resample("10min", on="Hora").mean().dropna()

#arrow_angles = (270 - df_wind["wind_direction"]) % 360
arrow_angles = (df_wind["wind_direction"]+180) % 360

#arrow_angles = (df_wind["wind_direction"]) % 360


def wind_to_uv(wd_deg, magnitude=1.0):
    rad = np.deg2rad(wd_deg)
    u = np.cos(rad) * magnitude
    v = np.sin(rad) * magnitude
    return u, v

# Wind categories and colors

wind_categories = [
    {"label": "Calm", "color": "#08306b", "min": 0, "max": 3},
    {"label": "Light Breeze", "color": "#6baed6", "min": 3.01, "max": 10},
    {"label": "Moderate", "color": "#1a9850", "min": 10.01, "max": 16},
    {"label": "Fresh", "color": "#ffff33", "min": 16.01, "max": 21},
    {"label": "Strong", "color": "#fdae61", "min": 21.01, "max": 27},
    {"label": "Gale", "color": "#d73027", "min": 27.01, "max": 38},
    {"label": "Storm", "color": "#7b3294", "min": 38.01, "max": 50},
]

colorscale = [
    [i / (len(wind_categories) - 1), cat["color"]]
    for i, cat in enumerate(wind_categories)
]

def speed_to_color(speed):
    for cat in wind_categories:
        if cat["min"] <= speed <= cat["max"]:
            return cat["color"]
    return "#000000"  # fallback if out of range

df_wind["color"] = df_wind["wind_avg"].apply(speed_to_color)
df_wind["Hora"] = pd.to_datetime(df_wind["Hora"])

times =   df["Hora"] 
speeds = df_wind["wind_avg"] 
directions = df_wind["wind_direction"]

min_speed = speeds.min()
max_speed = speeds.max()

# Arrow parameters

from datetime import timedelta
annotations = []
scale = 0.8

for _, row in df_wind.iterrows():
    u, v = wind_to_uv(row.wind_direction, 1)
    
    # Safe normalization
    if max_speed > min_speed:
        norm_speed = (row.wind_avg - min_speed) / (max_speed - min_speed)
    else:
        norm_speed = 0.0  # fallback if all wind speeds are equal
    
    # Color by speed categories
    if norm_speed < 0.10:
        arrow_color = "#08306b"
    elif norm_speed < 0.25:
        arrow_color = "#6baed6"
    elif norm_speed < 0.40:
        arrow_color = "#1a9850"
    elif norm_speed < 0.55:
        arrow_color = "#ffff33"
    elif norm_speed < 0.70:
        arrow_color = "#fdae61"
    elif norm_speed < 0.90:
        arrow_color = "#d73027"
    else:
        arrow_color = "#7b3294"
    
    # Arrow positions
    arrow_end_time = row.Hora + timedelta(hours=u * scale * norm_speed)
    arrow_end_speed = row.wind_avg + v * scale * norm_speed * 10
    
    # Append annotation safely
    annotations.append(
        dict(
            x=arrow_end_time,
            y=arrow_end_speed,
            ax=row.Hora,
            ay=row.wind_avg,
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            arrowhead=3,
            arrowsize=0.5,
            arrowwidth=2,
            arrowcolor=arrow_color,
            showarrow=True,
            hovertext=(
                f"Time: {row.Hora}<br>"
                f"Speed: {row.wind_avg:.1f} kts<br>"
                f"Direction: {row.wind_direction:.0f}°"
            ),
        )
    )

category_labels = [cat["label"] for cat in wind_categories]
category_colors = [cat["color"] for cat in wind_categories]

def speed_to_id(speed):
    for i, cat in enumerate(wind_categories):
        if cat["min"] <= speed <= cat["max"]:
            return i
    return np.nan

df_wind["cat_id"] = df_wind["wind_avg"].apply(speed_to_id)

colorscale = [[i/(len(category_colors)-1), color] for i, color in enumerate(category_colors)]

scatter_colors = []
for speed in df_wind["wind_avg"]:
    norm_speed = (speed - min_speed) / (max_speed - min_speed)
    if norm_speed < 0.10:
        c = "#08306b"
    elif norm_speed < 0.25:
        c = "#6baed6"
    elif norm_speed < 0.40:
        c = "#1a9850"
    elif norm_speed < 0.55:
        c = "#ffff33"
    elif norm_speed < 0.70:
        c = "#fdae61"
    elif norm_speed < 0.90:
        c = "#d73027"
    else:
        c = "#7b3294"
    scatter_colors.append(c)

scatter = go.Scatter(
    x=df_wind["Hora"],
    y=df_wind["wind_avg"],
    mode="markers",
    marker=dict(
        symbol="arrow",
        size=20,
        angle=arrow_angles,              # important: rotate arrows
        #color=df_wind["wind_avg"],       # numeric for colorbar
        color=df_wind["cat_id"],       # numeric for colorbar
        colorscale=colorscale,
        cmin=0,
        #cmax=len(category_colors)-1,
        cmax=50,
        opacity=1.0,
        line=dict(width=0.25, color="white"),
        colorbar=dict(
            title="(nudos)",
            thickness=14,
            len=1.0
        ),
    ),
    text=df_wind["wind_direction"],
    hovertemplate="Velocidad: %{y:.1f} kts<br>Dirección: %{text:.1f}°<extra></extra>",
    name="Viento",
)


fig = go.Figure(data=[scatter])

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
        range=[start_date, end_date + timedelta(hours=3)],
        side='bottom',
    ),
)
fig.update_layout(
    title="Velocidad y Dirección del Viento",
    xaxis=dict(title="Hora"),
    yaxis=dict(title="Velocidad del viento (nudos)", range=[0, max_speed * 1.1]),
    hovermode="x unified",
   legend=dict(orientation="h"),
)


st.plotly_chart(fig, width="stretch")

#################################################################################
## ----------------------------------------
# Air Temperature
## ----------------------------------------
#################################################################################

fig = px.line(df, x="Hora", y="air_temperature", title="Temperatura del Aire",labels={"air_temperature": "Temperatura (ºF)"})

# Hover: only y-value, no colored box
fig.update_traces(
    hovertemplate="Temperatura: %{y:.1f}°F<extra></extra>",
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
        range=[start_date, end_date + timedelta(hours=3)],
        side='bottom',
        #fixedrange=True,  # Disable zoom on the x-axis
    ),
    #yaxis=dict(
        #fixedrange=True  # Disable zoom on the y-axis
    #),
    yaxis_title="Temperatura (°F)",
    showlegend=True,
    #showlegend=False,
    margin={"r": 10, "t": 40, "l": 40, "b": 40},  # Optional: Add margins for better fit
    autosize=True,  # Let Plotly automatically adjust size
    height=500,  # Fixed height for clarity
)

# Allow horizontal scrolling by not fixing x-axis range
fig.update_layout(
    dragmode=False,  # Disable panning (dragging)
    xaxis=dict(fixedrange=False),  # Allow scrolling zoom on x-axis
    yaxis=dict(fixedrange=False),  # Allow scrolling zoom on y-axis
    showlegend=True  # Optional: You can disable if not needed
)
st.plotly_chart(fig, width="stretch")

#################################################################################
## ----------------------------------------
# Rain Accumulation
## ----------------------------------------
#################################################################################

fig = px.bar(df, x="Hora", y="rain_accumulated", title="Precipitación Acumulada",labels={"rain_accumulated": "Precipitación (\")"})

fig.update_traces(
    hovertemplate='Lluvia: %{y:.4f}"<extra></extra>',
)

ymax = df["rain_accumulated"].max()

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
        range=[start_date, end_date + timedelta(hours=3)],
        side='bottom'
    ),
    yaxis_title="Lluvia (pulgadas)",
   # range=[0, ymax * 1.1],  # add 10% headroom
    showlegend=False
)

st.plotly_chart(fig, width="stretch")

#################################################################################
## ----------------------------------------
# UV
## ----------------------------------------
#################################################################################

fig = px.line(df, x="Hora", y="uv", title="Índice UV",labels={"uv": "UV"})

fig.update_traces(
    hovertemplate='UV: %{y}<extra></extra>',
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
        range=[start_date, end_date + timedelta(hours=3)],
        side='bottom'
    ),
    yaxis_title="Índice UV",
    showlegend=False
)
st.plotly_chart(fig, width="stretch")

#################################################################################
## ----------------------------------------
# Lightning Strike
## ----------------------------------------
#################################################################################

fig = px.line(df, x="Hora", y="lightning_strike_avg_distance", title="Distancia del Rayo",labels={"lightning_strike_avg_distance": "Distancia del Rayo (mi)"})

fig.update_traces(
    hovertemplate='Distancia: %{y:.1f} mi<extra></extra>',
)

# Layout
fig.update_layout(
    hovermode="x unified",
    xaxis=dict(
        tickvals=ticks,
        ticktext=tick_labels,      # pre-formatted labels
        tickangle=90,
        showline=False,
        showspikes=True,
        spikecolor='rgb(128,128,128)',
        side='bottom',
        range=[start_date, end_date + timedelta(hours=3)]
    ),
    yaxis=dict(
        title="Distancia del Rayo (mi)",
        range=[0, 6]   # y-axis min/max
    ),
    showlegend=False
)

st.plotly_chart(fig, width="stretch")

#################################################################################
# -----------------------------
# FOOTER
# -----------------------------
#################################################################################

st.markdown("---")
st.markdown(
    """
    <style>
    img {
        height: 90px;
        object-fit: contain;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("---")
cols = st.columns(5)

images = [
    "logo.png",
    "logoupr.png",
    "logocienciasmedicas.png",
    "logovela.png",
    "logocaricoos.png",
]

for col, img in zip(cols, images):
    col.image(img, use_container_width=True)

    
st.caption("Powered by Streamlit • Plotly • NetCDF • Python")









































