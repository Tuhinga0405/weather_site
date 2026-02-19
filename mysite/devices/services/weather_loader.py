import openmeteo_requests
import pandas as pd
import numpy as np
import requests_cache
from retry_requests import retry
from ..models import Data


# --- Вспомогательные функции ---

def deg_to_sector(deg: float) -> str:
    """Округляет угол в градусах до ближайшего сектора (каждые 22.5°)."""
    deg = deg % 360
    sectors = {
        0: "С", 22.5: "С-СВ", 45: "СВ", 67.5: "В-СВ",
        90: "В", 112.5: "В-ЮВ", 135: "ЮВ", 157.5: "Ю-ЮВ",
        180: "Ю", 202.5: "Ю-ЮЗ", 225: "ЮЗ", 247.5: "З-ЮЗ",
        270: "З", 292.5: "З-СЗ", 315: "СЗ", 337.5: "С-СЗ"
    }
    keys = np.array(list(sectors.keys()))
    nearest = keys[np.argmin(np.abs(keys - deg))]
    return sectors[nearest]


def convert_pressure_to_mmhg(pressure_hpa: pd.Series) -> pd.Series:
    """Перевод давления из hPa в мм рт. ст. с округлением до 2 знаков."""
    return (pressure_hpa.astype("float64") * 0.75006).round(2)


def fetch_weather(latitude: float, longitude: float,
                  start_date: str, end_date: str,
                  device_id: int) -> pd.DataFrame:
    """Загружает и обрабатывает погодные данные для указанной локации."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": [
            "temperature_2m", "relative_humidity_2m",
            "wind_speed_10m", "wind_direction_10m",
            "uv_index", "surface_pressure"
        ],
        "wind_speed_unit": "ms",
        "start_date": start_date,
        "end_date": end_date,
    }

    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]

    hourly = response.Hourly()
    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        ),
        "temp": hourly.Variables(0).ValuesAsNumpy(),
        "humidity": hourly.Variables(1).ValuesAsNumpy(),
        "wind_speed": hourly.Variables(2).ValuesAsNumpy(),
        "wind_direction": hourly.Variables(3).ValuesAsNumpy(),
        "uv": hourly.Variables(4).ValuesAsNumpy(),
        "pressure": hourly.Variables(5).ValuesAsNumpy(),
        "device_id": device_id
    }

    df = pd.DataFrame(hourly_data)

    # фильтрация по часам
    target_hours = [0, 8, 14, 19]
    df = df[df["date"].dt.hour.isin(target_hours)].copy()

    # преобразования
    df["pressure"] = convert_pressure_to_mmhg(df["pressure"])
    df["wind_direction"] = df["wind_direction"].apply(deg_to_sector)

    return df


# --- Настройка клиента Open-Meteo ---
cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)


def save_weather():
    # --- Получение данных для двух локаций ---
    df1 = fetch_weather(latitude=53.9, longitude=27.5667,
                        start_date="2025-10-01", end_date="2025-11-01",
                        device_id=1)

    df2 = fetch_weather(latitude=52.0975, longitude=23.6878,
                        start_date="2025-09-01", end_date="2025-11-01",
                        device_id=2)

    # --- Объединение ---
    final_df = pd.concat([df1, df2], ignore_index=True)
    
    records = [
        Data(
            device_id=row["device_id"],
            timestamp=row["date"],
            temp=row["temp"],
            humidity=row["humidity"],
            wind_speed=row["wind_speed"],
            wind_direction=row["wind_direction"]
        )
        for _, row in final_df.iterrows()
    ]

    Data.objects.bulk_create(records, batch_size=1000)
