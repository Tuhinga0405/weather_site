import requests as rq
import plotly.io as pio
import plotly.express as px
import pandas as pd
import numpy as np
from devices.models import Data, Device
from django.db.models import Count

class Plots:
     
    def __init__(self, user_id):
        self.qs = (Data.objects.all().filter(device__owner_id=user_id)
              .annotate(num=Count("device__data"))
              .filter(num__gte=108)).values()
        self.df = pd.DataFrame(self.qs)
        self.df["date"] = pd.to_datetime(self.df["date"])
        self.time_period = (
            "C " +
            str(self.df["date"].dt.strftime('%m-%y').min()) + 
            " по "
            + str(self.df["date"].dt.strftime('%m-%y').max())
        )

    def avg_temp(self):
                
        self.df["month"] = self.df["date"].dt.strftime('%m-%y')

        # calculating avg_temp per_month
        result = (self.df.groupby(["device_id", "month"])["temp"]
                  .mean().round(2)
                  .unstack(fill_value=None).to_dict("index"))

        return result

    def avg_humidity(self): 
        self.df["month"] = self.df["date"].dt.strftime('%m-%y')

        res = (self.df.groupby(["device_id", "month"])["humidity"]
               .mean().round(2)
               .unstack(fill_value=None).to_dict("index"))

        return res

    def roza_vetrov(self):

        direction_to_deg = {
            "С": 0, "С-СВ": 22.5, "СВ": 45, "В-СВ": 67.5,
            "В": 90, "В-ЮВ": 112.5, "ЮВ": 135, "Ю-ЮВ": 157.5,
            "Ю": 180, "Ю-ЮЗ": 202.5, "ЮЗ": 225, "З-ЮЗ": 247.5,
            "З": 270, "З-СЗ": 292.5, "СЗ": 315, "С-СЗ": 337.5
        }

        # Берём только нужные колонки
        df = (self.df[["device_id", "date", "wind_speed", "wind_direction"]]
              .copy())
        df = df[df["wind_speed"] > 0]

        # Преобразуем направления в градусы
        df["wind_deg"] = df["wind_direction"].map(direction_to_deg)

        # Группы по скорости
        bins = [0, 5, 8, 11, 14]
        labels = ["<5", "5–8", "8–11", "11–14"]
        df["speed_group"] = pd.cut(df["wind_speed"], bins=bins,
                                   labels=labels, right=False)

        # Группировка по устройству, градусам и диапазону скоростей
        grouped = (
            df.groupby(["device_id", "wind_deg", "speed_group"])
            .size()
            .reset_index(name="count")
        )

        results = {}
        for device_id, subdf in grouped.groupby("device_id"):
            total = subdf["count"].sum()
            subdf["r"] = (subdf["count"] / total * 100).round(2)

            # считаем период отдельно для каждого устройства
            device_dates = df[df["device_id"] == device_id]["date"]
            time_period = (
                "C " +
                str(device_dates.dt.strftime('%m-%y').min()) +
                " по " +
                str(device_dates.dt.strftime('%m-%y').max())
            )

            results[device_id] = {
                "time_period": time_period,
                "data": subdf.to_dict(orient="records")
            }

        return {"devices": results}

    #make_plots
    def avg_temp_plot(self, device_id):
        data = self.avg_temp()[device_id]

        months = data.keys()
        temps = data.values()

        #make plot 
        fig = px.line(x=months, y=temps,
            labels={
                        "y":"Градусы (°C)",
                        "x":"Месяц-Год"
            },
        )
        plot_temp = pio.to_html(fig, full_html=False)
        return plot_temp
    
    def roza_vetrov_plot(self, device_id):
        data = self.roza_vetrov()["devices"][device_id]


        figure = px.bar_polar(
        data["data"],
        r="r",
        theta="wind_deg",
        color="speed_group",
        color_continuous_scale="Jet",
        template="plotly_dark",

        )

        figure.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',  # прозрачный фон
            plot_bgcolor='rgba(0,0,0,0)',   # прозрачный фон области графика
            font=dict(color='black'),      # белый цвет текста
            polar=dict(
                bgcolor='rgba(0,0,0,0)',
                angularaxis=dict(
                    tickfont=dict(color='black'),  # подписи направлений
                    linecolor='white',
                    gridcolor='gray'
                ),
                radialaxis=dict(
                    tickfont=dict(color='rgba(0,0,0,0)'),  # подписи радиуса
                    linecolor='black',
                    gridcolor='gray'
                )
            ),
            title={
                    'text': data["time_period"],
                    'y':0.99,
                    'x':0.5,
                    'xanchor': "center",
                    'yanchor': "top"
            },
            margin_l=130,
        )

        plot_roza = pio.to_html(figure, full_html=False)
        return plot_roza
