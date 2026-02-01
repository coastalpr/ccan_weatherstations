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
#MAPBOX_API_KEY = st.secrets["MAPBOX_API_KEY"]
#px.set_mapbox_access_token(MAPBOX_API_KEY)

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

with c5:
   st.markdown(f"<h3 style='color:{color}; font-size: 1rem; margin-top: -30px; padding: 0;'> {description}</h3>", unsafe_allow_html=True)

# -----------------------------
# SATELLITE / RADAR LOOP
# -----------------------------
st.subheader("🌐 Radar Satelital - Caribe")
st.caption("Animación de radar usando imágenes locales desde radar_images/")
import streamlit as st
import plotly.graph_objects as go
import rasterio
from rasterio.plot import reshape_as_image
from rasterio.warp import transform_bounds
from pathlib import Path
from PIL import Image
import numpy as np
import time

#st.set_page_config(layout="wide")
#st.title("🌐 Radar Satelital Animado - Caribe (Plotly Mapbox)")

# -----------------------------
# Radar folder
# -----------------------------
RADAR_FOLDER = Path("radar_images")
if not RADAR_FOLDER.exists():
    st.error(f"Radar folder not found: {RADAR_FOLDER}")
    st.stop()

tif_files = sorted(RADAR_FOLDER.glob("*.tif"))
if not tif_files:
    st.warning("No TIF files found in radar_images folder.")
    st.stop()

st.markdown(f"Found {len(tif_files)} radar frames.")

# -----------------------------
# Map settings
# -----------------------------
map_lat, map_lon = 18.0, -66.0
map_zoom = 8
DELAY_SECONDS = 0.8  # Animation speed in seconds

# -----------------------------
# Preload TIFs
# -----------------------------
frames = []
for tif_path in tif_files:
    try:
        with rasterio.open(tif_path) as src:
            img = src.read()
            # Handle single-band
            if img.shape[0] == 1:
                img = np.repeat(img, 3, axis=0)
            img = reshape_as_image(img)
            # Normalize to 0-255
            if img.dtype != np.uint8:
                img = ((img - img.min()) / (img.max() - img.min()) * 255).astype(np.uint8)
            pil_img = Image.fromarray(img)

            # Transform bounds to lat/lon if needed
            bounds = src.bounds
            if src.crs.to_string() != "EPSG:4326":
                bounds = transform_bounds(src.crs, "EPSG:4326", *bounds)

            frames.append({"image": pil_img, "bounds": bounds, "name": tif_path.name})
if not frames:
    st.stop()

# Single placeholder for the map
map_placeholder = st.empty()

# Loop through frames
for frame in frames:
    fig = go.Figure()
    fig.add_layout_image(
        dict(
            source=frame["image"],
            xref="x",
            yref="y",
            x=frame["bounds"].left,
            y=frame["bounds"].top,
            sizex=frame["bounds"].right - frame["bounds"].left,
            sizey=frame["bounds"].top - frame["bounds"].bottom,
            sizing="stretch",
            opacity=0.6,
            layer="above"
        )
    )

    # OpenStreetMap background (no API key needed)
    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=map_lat, lon=map_lon),
            zoom=map_zoom
        ),
        margin={"r":0,"t":0,"l":0,"b":0},
        showlegend=False
    )

    # **Update the same placeholder**
    map_placeholder.plotly_chart(fig, use_container_width=True)

    time.sleep(DELAY_SECONDS)
# -----------------------------
# PLOTS
# -----------------------------

# Determine last 2 days
end_date = df['Hora'].max()
start_date = end_date - pd.Timedelta(days=2)

# Generate hourly ticks (optional: every 1 hour)
ticks = pd.date_range(df['Hora'].min(), df['Hora'].max(), freq='6h')
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
# Wind Speed
## ----------------------------------------

df_wind = df[
    (df["wind_avg"] > 0.5) &
    (df["wind_direction"].notna())
].iloc[::4].copy()

# Convert meteorological → mathematical angle
theta = np.deg2rad(270 - df_wind["wind_direction"])

# Direction unit vectors
ux = np.cos(theta)
uy = np.sin(theta)

# Normalize axes (seconds vs kts)
x_scale = 30 * 60          # 30 minutes in seconds
y_scale = df_wind["wind_avg"].max()

# Arrow magnitude proportional to speed
speed_norm = df_wind["wind_avg"] / df_wind["wind_avg"].max()

# Final components
dx = ux * speed_norm * x_scale
dy = uy * speed_norm * y_scale * 0.25

fig = go.Figure()

colorscale = px.colors.sequential.Turbo
norm = (df_wind["wind_avg"] - df_wind["wind_avg"].min()) / (
    df_wind["wind_avg"].max() - df_wind["wind_avg"].min()
)

for i, row in df_wind.iterrows():
    color = colorscale[int(norm.loc[i] * (len(colorscale) - 1))]

    # Arrow shaft
    fig.add_trace(go.Scatter(
        x=[
            row["Hora"],
            row["Hora"] + pd.to_timedelta(dx.loc[i], unit="s")
        ],
        y=[
            row["wind_avg"],
            row["wind_avg"] + dy.loc[i]
        ],
        mode="lines",
        line=dict(color=color, width=2),
        showlegend=False,
        hovertemplate=(
            f"Velocidad: {row['wind_avg']:.1f} kts<br>"
            f"Dirección: {row['wind_direction']:.0f}°"
            "<extra></extra>"
        )
    ))

    # Arrowhead
    fig.add_trace(go.Scatter(
        x=[row["Hora"] + pd.to_timedelta(dx.loc[i], unit="s")],
        y=[row["wind_avg"] + dy.loc[i]],
        mode="markers",
        marker=dict(
            symbol="triangle-up",
            size=8,
            angle=row["wind_direction"],
            color=color
        ),
        showlegend=False,
        hoverinfo="skip"
    ))

# Colorbar (dummy trace)
fig.add_trace(go.Scatter(
    x=[None],
    y=[None],
    mode="markers",
    marker=dict(
        colorscale="Turbo",
        cmin=df_wind["wind_avg"].min(),
        cmax=df_wind["wind_avg"].max(),
        color=df_wind["wind_avg"],
        showscale=True,
        colorbar=dict(title="Wind speed (kts)")
    ),
    hoverinfo="none"
))

fig.update_layout(
    title="Wind Quiver Plot",
    xaxis_title="Hora",
    yaxis_title="Wind speed (kts)",
    template="plotly_white"
)


st.plotly_chart(fig, use_container_width=True)


#

# Plot each arrow as a short line starting at (time, speed)
#for t, y, deltax, deltay, c, spd, wd in zip(time, speed, dx, dy, colors, speed, direction):
#    fig.add_trace(go.Scatter(
#        x=[t, t + np.timedelta64(int(deltax*3600*24), 's')],
#        y=[y, y + deltay],
#        mode="lines",
#        line=dict(color=c, width=3),
#        hovertemplate=f"Velocidad: {spd:.1f} kts<br>Dirección: {wd:.0f}°<extra></extra>",
#        showlegend=False
#    ))

# Layout
#fig.update_layout(
#    title="Viento: Velocidad y Dirección",
#    xaxis=dict(
#        title="Hora",
#        tickvals=ticks,
#        ticktext=tick_labels,
#        tickangle=0,
#        showspikes=True,
#        spikecolor="gray",
#    ),
#    yaxis=dict(title="Velocidad del viento (kts)"),
#    hovermode="x unified",
#    height=450,
#    width=1100
#)

#st.plotly_chart(fig, width="stretch")

#fig = px.line(df, x="Hora", y="wind_avg", title="Velocidad del Viento",labels={"wind_avg": "Velocidad del Viento (kts)"})

# Hover: only y-value, no colored box
#fig.update_traces(
    #hovertemplate='%{y:.1f} °F<extra></extra>',
#)

# Layout
#fig.update_layout(
    #hovermode="x unified",
    #xaxis=dict(
        #tickvals=ticks,
        #ticktext=tick_labels,   # date + hour for all ticks
        #tickangle=90,
        #showline=False,         # no black line
        #showspikes=True,       # no vertical blue line
        #spikecolor='rgb(128,128,128)',
        #range=[start_date, end_date],
        #side='bottom'
    #),
    #yaxis_title="Velocidad del Viento (kts)",
    #showlegend=False
#)

#st.plotly_chart(fig, use_container_width=True)

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

st.plotly_chart(fig, width="stretch")

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

st.plotly_chart(fig, width="stretch")



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

st.plotly_chart(fig, width="stretch")

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
st.plotly_chart(fig, width="stretch")

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

st.plotly_chart(fig, width="stretch")

# -----------------------------
# FOOTER
# -----------------------------
st.markdown("---")
st.caption("Powered by Streamlit • Plotly • NetCDF • Python")


















































































































































