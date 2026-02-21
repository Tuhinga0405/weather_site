import openmeteo_requests
import pandas as pd
import numpy as np
import requests_cache
from retry_requests import retry
from datetime import datetime, timedelta
from devices.models import Data, Device


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

    print(f"Coordinates: {response.Latitude()}°N {response.Longitude()}°E")
    print(f"Elevation: {response.Elevation()} m asl")
    print(f"Timezone offset: {response.UtcOffsetSeconds()}s")

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


def get_date_range_for_device(device_id: int) -> tuple[str, str]:
    """
    Исправленная функция для определения диапазона дат.
    Теперь правильно работает с объектами datetime.
    """
    today = datetime.now().date()

    # if is_table_empty():
        # Правильное вычисление даты 4 недели назад
        # start_date = (datetime.now() - timedelta(weeks=4)).strftime("%Y-%m-%d")
        # end_date = today.strftime("%Y-%m-%d")
        # return start_date, end_date

    last_date = get_last_date(device_id)
    # if last_date is None:
    #     start_date = (datetime.now() - timedelta(weeks=4)).strftime("%Y-%m-%d")
    #     end_date = today.strftime("%Y-%m-%d")
    #     return start_date, end_date

    if last_date.date() < today:
        start_date = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        return start_date, end_date

    return None, None

def update_weather_data():
    """Основная функция обновления погодных данных."""
    locations = [
        {"latitude": 53.9, "longitude": 27.5667, "device_id": 1},
        {"latitude": 52.0975, "longitude": 23.6878, "device_id": 2}
    ]

    for location in locations:
        date_range = get_date_range_for_device(location["device_id"])

        if date_range[0] is None:
            print(f"Данные для device_id {location['device_id']} уже актуальны.")
            continue

        start_date, end_date = date_range
        print(f"Загрузка данных для device_id {location['device_id']}: {start_date} - {end_date}")

        df = fetch_weather(
            latitude=location["latitude"],
            longitude=location["longitude"],
            start_date=start_date,
            end_date=end_date,
            device_id=location["device_id"]
        )

        # ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА ТИПОВ ДАННЫХ
        print("Типы данных до преобразования:")
        print(df.dtypes)

        # ПРАВИЛЬНОЕ ОКРУГЛЕНИЕ С ПРОВЕРКОЙ
        cols_to_round = ['temp', 'wind_speed', 'uv']
        for col in cols_to_round:
            # Убедимся, что данные числовые
            if df[col].dtype in ['float64', 'int64', 'float32']:
                df[col] = df[col].round(2)
            else:
                # Принудительное преобразование, если тип не числовой
                df[col] = pd.to_numeric(df[col], errors='coerce').round(2)

        # ПРОВЕРКА ПОСЛЕ ПРЕОБРАЗОВАНИЯ
        print("\nПримеры данных после округления:")
        print(df[cols_to_round].head())

        if not df.empty:
            weather_records = []
            for _, row in df.iterrows():
                record = Data(
                    date=row['date'],
                    temp=row['temp'],
                    humidity=row['humidity'],
                    wind_speed=row['wind_speed'],
                    wind_direction=row['wind_direction'],
                    uv=row['uv'],
                    pressure=row['pressure'],
                    device_id=row['device_id']
                )
                weather_records.append(record)

            print(weather_records)
            Data.objects.bulk_create(weather_records)
            print(f"Сохранено {len(df)} записей для device_id {location['device_id']}")


# --- Заглушки для Django-моделей ---
def get_last_date(device_id: int) -> datetime:

    try:
        latest_record = Data.objects.filter(device_id=device_id).order_by('-date').first()
        return latest_record.date if latest_record else None
    except AttributeError:
        return None

def is_table_empty() -> bool:
    """
    Заглушка: проверить, пуста ли таблица.
    Реализуйте через Django ORM: WeatherData.objects.count() == 0
    """
    return Data.objects.count() == 0


#def save_weather_data(df: pd.DataFrame):
    """
    Заглушка: сохранить DataFrame в базу.
    Реализуйте через Django ORM bulk_create или bulk_update
    """
#    return bulk_update


# --- Настройка клиента Open-Meteo ---
cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)


# --- Запуск обновления ---
if __name__ == "__main__":
    update_weather_data()
