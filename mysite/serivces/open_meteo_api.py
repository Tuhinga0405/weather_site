import openmeteo_requests
import pandas as pd
import numpy as np
import requests_cache
from retry_requests import retry
from datetime import datetime, timedelta, timezone
from django.core.cache import cache
from devices.models import Data

# === Глобальная настройка клиента ===
cache_session = requests_cache.CachedSession(".cache", expire_after=300)
retry_session = retry(cache_session, retries=3, backoff_factor=0.1)
openmeteo = openmeteo_requests.Client(session=retry_session)


def fetch_hourly_data(latitude: float, longitude: float, 
                      hours: int = 24) -> pd.DataFrame:
    """
    Загружает почасовые данные за последние <hours> часов.
    ТОЛЬКО температура и влажность.
    """
    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d")
    
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        # ✅ ТОЛЬКО нужные поля
        "hourly": [
            "temperature_2m", 
            "relative_humidity_2m"
        ],
        "wind_speed_unit": "ms",
        "start_date": start_date,
        "end_date": end_date,
        "timezone": "auto"
    }

    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]
    hourly = response.Hourly()
    
    # ✅ Создаём DataFrame только с двумя колонками
    df = pd.DataFrame({
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        ),
        "temp": hourly.Variables(0).ValuesAsNumpy(),
        "humidity": hourly.Variables(1).ValuesAsNumpy(),
    })
    
    df = df.copy()
    
    # ✅ Округление только для оставшихся числовых полей
    for col in ['temp', 'humidity']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').round(2)
    
    return df


def save_device_data(df: pd.DataFrame, device_id: int) -> int:
    """
    Сохраняет данные для устройства в БД (только temp и humidity).
    """
    df = df.copy()
    df["device_id"] = device_id
    
    # Удаляем строки с отсутствующими критическими данными
    df = df.dropna(subset=['date', 'temp'])
    
    # Проверка на дубликаты
    existing_dates = set(
        Data.objects.filter(
            device_id=device_id,
            date__in=df['date']
        ).values_list('date', flat=True)
    )
    df = df[~df['date'].isin(existing_dates)]
    
    if df.empty:
        return 0
    
    # ✅ Подготовка объектов ТОЛЬКО с нужными полями
    records = [
        Data(
            date=row['date'].to_pydatetime(),
            temp=row['temp'],
            humidity=row['humidity'],
            device_id=device_id
            # ❌ wind_speed, wind_direction, uv, pressure — исключены
        )
        for _, row in df.iterrows()
    ]
    
    Data.objects.bulk_create(records, ignore_conflicts=True)
    return len(records)


def update_device_if_needed(device_id: int, latitude: float, longitude: float, 
                           interval_minutes: int = 5) -> dict:
    """
    Проверяет интервал и обновляет данные если нужно.
    """
    cache_key = f"weather_last_update_{device_id}"
    last_update = cache.get(cache_key)
    now = datetime.now(timezone.utc)
    
    if last_update and (now - last_update).total_seconds() < interval_minutes * 60:
        return {
            "updated": False,
            "reason": f"last update {int((now - last_update).total_seconds() / 60)} min ago"
        }
    
    try:
        df = fetch_hourly_data(latitude, longitude, hours=24)
        df = df[df["date"] > (now - timedelta(hours=24))]
        
        saved_count = save_device_data(df, device_id)
        cache.set(cache_key, now, timeout=3600)
        
        return {
            "updated": True,
            "records_saved": saved_count,
            "total_records": len(df)
        }
        
    except Exception as e:
        return {
            "updated": False,
            "error": str(e)
        }


def update_all_devices(interval_minutes: int = 5) -> dict:
    """
    Обновляет данные для всех устройств.
    """
    locations = [
        {"latitude": 53.9, "longitude": 27.5667, "device_id": 1, "name": "Минск"},
        {"latitude": 52.0975, "longitude": 23.6878, "device_id": 2, "name": "Брест"}
    ]
    
    results = {}
    for loc in locations:
        results[loc["device_id"]] = update_device_if_needed(
            device_id=loc["device_id"],
            latitude=loc["latitude"],
            longitude=loc["longitude"],
            interval_minutes=interval_minutes
        )
        results[loc["device_id"]]["location"] = loc["name"]
    
    return results