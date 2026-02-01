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
].iloc[::4].copy()  # downsample for clarity

# Convert meteorological → mathematical angle (radians)
theta = np.deg2rad(270 - df_wind["wind_direction"])

# Unit vectors
ux = np.cos(theta)
uy = np.sin(theta)

# Arrow length proportional to wind magnitude
max_arrow_len = 5  # max arrow length in y-axis units (kts)
dx = ux * df_wind["wind_avg"] / df_wind["wind_avg"].max() * max_arrow_len
dy = uy * df_wind["wind_avg"] / df_wind["wind_avg"].max() * max_arrow_len

# Color mapping
colorscale = px.colors.sequential.Turbo
norm = (df_wind["wind_avg"] - df_wind["wind_avg"].min()) / (
    df_wind["wind_avg"].max() - df_wind["wind_avg"].min()
)

# ----------------------------------------
# Build figure
# ----------------------------------------
fig = go.Figure()

for i, row in df_wind.iterrows():
    color = colorscale[int(norm.loc[i] * (len(colorscale) - 1))]
    
    # Arrow shaft
    fig.add_trace(go.Scatter(
        x=[row["Hora"], row["Hora"] + pd.to_timedelta(dx.loc[i], unit="s")],
        y=[row["wind_avg"], row["wind_avg"] + dy.loc[i]],
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
    arrow_angle = (270 - row["wind_direction"]) % 360
    fig.add_trace(go.Scatter(
        x=[row["Hora"] + pd.to_timedelta(dx.loc[i], unit="s")],
        y=[row["wind_avg"] + dy.loc[i]],
        mode="markers",
        marker=dict(
            symbol="triangle-up",
            size=8,
            angle=arrow_angle,
            color=color
        ),
        showlegend=False,
        hoverinfo="skip"
    ))

# Dummy trace for colorbar
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

# Layout
fig.update_layout(
    title="Wind Quiver Plot",
    xaxis_title="Hora",
    yaxis_title="Wind speed (kts)",
    template="plotly_white",
    xaxis=dict(range=[start_date, end_date])
)

# Streamlit
st.plotly_chart(fig, use_container_width=True)


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





































































































































































