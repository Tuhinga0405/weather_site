# devices/services/weather_collector.py

import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
from datetime import datetime, timedelta, timezone
from django.core.cache import cache
from django.utils import timezone as django_timezone
from devices.models import Data

# === Глобальная настройка клиента ===
cache_session = requests_cache.CachedSession(".cache", expire_after=300)
retry_session = retry(cache_session, retries=3, backoff_factor=0.1)
openmeteo = openmeteo_requests.Client(session=retry_session)


def get_last_data_date(device_id: int) -> datetime | None:
    """
    Получает последнюю дату данных для устройства из БД.
    """
    last_record = Data.objects.filter(
        device_id=device_id
    ).order_by('-date').first()
    
    if last_record:
        last_date = last_record.date
        if last_date.tzinfo is None:
            last_date = django_timezone.make_aware(last_date)
        return last_date
    
    return None


def fetch_hourly_data(latitude: float, longitude: float,
                      start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Загружает почасовые данные за указанный период.
    ТОЛЬКО температура и влажность.
    """
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        # ✅ ТОЛЬКО нужные поля
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m"
        ],
        "start_date": start_str,
        "end_date": end_str,
        "timezone": "auto"
    }

    try:
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
        
        # Фильтрация по целевым часам
        target_hours = [0, 8, 14, 19]
        df = df[df["date"].dt.hour.isin(target_hours)].copy()
        
        # ✅ Округление только для temp и humidity
        for col in ['temp', 'humidity']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').round(2)
        
        return df
        
    except Exception as e:
        print(f"❌ Ошибка загрузки данных от API: {e}")
        return pd.DataFrame()


def save_device_data(df: pd.DataFrame, device_id: int) -> int:
    """
    Сохраняет данные для устройства в БД (только temp и humidity).
    """
    if df.empty:
        return 0
    
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
    Умная проверка: загружает данные только если есть пропущенные даты.
    """
    cache_key = f"weather_last_update_{device_id}"
    last_update = cache.get(cache_key)
    now = django_timezone.now()
    
    # 1. Проверка rate limiting
    if last_update and (now - last_update).total_seconds() < interval_minutes * 60:
        return {
            "updated": False,
            "reason": f"rate limit: last update {int((now - last_update).total_seconds() / 60)} min ago"
        }
    
    # 2. Проверка последней даты в БД
    last_data_date = get_last_data_date(device_id)
    
    if last_data_date:
        last_data_date_local = last_data_date.astimezone(django_timezone.get_current_timezone())
        today_local = now.astimezone(django_timezone.get_current_timezone())
        
        if last_data_date_local.date() == today_local.date():
            # 3. Последняя дата — сегодня, пропускаем загрузку
            cache.set(cache_key, now, timeout=3600)
            return {
                "updated": False,
                "reason": "data is current (today)",
                "last_date": last_data_date_local.strftime('%Y-%m-%d %H:%M')
            }
        
        # 4. Есть пропущенные даты — загружаем с последней даты
        start_date = last_data_date
        end_date = now
        print(f"📊 Устройство #{device_id}: загрузка с {start_date} по {end_date}")
        
    else:
        # 5. Нет данных в БД — загружаем последние 7 дней
        start_date = now - timedelta(days=7)
        end_date = now
        print(f"📊 Устройство #{device_id}: первая загрузка, последние 7 дней")
    
    # 6. Загрузка данных от API
    try:
        df = fetch_hourly_data(latitude, longitude, start_date, end_date)
        
        if df.empty:
            cache.set(cache_key, now, timeout=300)
            return {
                "updated": False,
                "reason": "no data from API",
                "period": f"{start_date} - {end_date}"
            }
        
        # 7. Фильтрация: только данные после последней записи в БД
        if last_data_date:
            df = df[df['date'] > last_data_date]
        
        # 8. Сохранение в БД
        saved_count = save_device_data(df, device_id)
        
        # 9. Обновление кэша
        cache.set(cache_key, now, timeout=3600)
        
        return {
            "updated": True,
            "records_saved": saved_count,
            "total_records": len(df),
            "period": f"{start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}",
            "last_data_date": last_data_date.strftime('%Y-%m-%d %H:%M') if last_data_date else None
        }
        
    except Exception as e:
        cache.set(cache_key, now, timeout=300)
        return {
            "updated": False,
            "error": str(e),
            "period": f"{start_date} - {end_date}"
        }


def update_all_devices(interval_minutes: int = 5) -> dict:
    """
    Обновляет данные для всех настроенных устройств.
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