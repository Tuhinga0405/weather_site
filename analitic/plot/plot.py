import plotly.express
import locale
import requests as rq
import pandas as pd
# import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime


class DeviceMeasurments:
    def __init__(self, url):
        self.data = rq.get(url).json()
        self.data_frame = pd.DataFrame(self.data)
        self.data_frame["date"] = pd.to_datetime(self.data_frame["date"])

    def avg_temp(self):
        
        self.data_frame["month"] = self.data_frame["date"].dt.month

        # calculating avg_temp per_month
        monthly_avg = np.round(self.data_frame.groupby("month")["temp"].mean(), 2)

        return dict(monthly_avg)
    
    def roza_vetrov(self):

        direction_to_deg = {
            "С": 0, "С-СВ": 22.5, "СВ": 45, "В-СВ": 67.5,
            "В": 90, "В-ЮВ": 112.5, "ЮВ": 135, "Ю-ЮВ": 157.5,
            "Ю": 180, "Ю-ЮЗ": 202.5, "ЮЗ": 225, "З-ЮЗ": 247.5,
            "З": 270, "З-СЗ": 292.5, "СЗ": 315, "С-СЗ": 337.5
        }

        df = self.data_frame[["wind_speed", "wind_direction"]].copy()
        df = df[df["wind_speed"] > 0]

        # Преобразуем направления в градусы
        df["wind_deg"] = df["wind_direction"].map(direction_to_deg)

        # Группы по скорости
        bins = [0, 5, 8, 11, 14]
        labels = ["<5", "5–8", "8–11", "11–14"]
        df["speed_group"] = pd.cut(df["wind_speed"], bins=bins, labels=labels, right=False)

        # Группировка уже по градусам
        grouped = df.groupby(["wind_deg", "speed_group"]).size().reset_index(name="count")

        # Общее количество всех наблюдений
        total = grouped["count"].sum()

        # Вычисляем r как процент
        grouped["r"] = (grouped["count"] / total * 100).round(2)
        
        return dict(grouped)


raw_data = DeviceMeasurments(url=f"http://localhost:9000/devices/get_data/2")

figure = plotly.express.bar_polar(
  raw_data.roza_vetrov(),
  r="r",
  theta="wind_deg",
  color="speed_group",
  template="plotly_dark",
  color_discrete_sequence=plotly.express.colors.sequential.Plasma_r
)
