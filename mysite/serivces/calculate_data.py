import pandas as pd
import numpy as np
from devices.models import Data, Device
from django.db.models import Count
from pprint import pprint


class DataForPlots:

    def __init__(self, user_id):

        ''' создается поле num, которое отображает кол-во записей
            для каждого устройства. Условие num__gte=108 нужно 
            для отбора устройств которые собирали данные меньше 
            месяца
        '''
        self.qs = (Data.objects.all().filter(device__owner_id=user_id)
              .annotate(num=Count("device__data"))
              .filter(num__gte=108)).values()

        self.df = pd.DataFrame(self.qs)

        # в бд храняться numeric, для нормлаьной работы с pandas
        # нужно преобразовать в float
        self.df['temp'] = self.df['temp'].astype(float)
        self.df['wind_speed'] = self.df['wind_speed'].astype(float)

        # нужно, чтобы преобразовалось в удобный формат pandas
        self.df["date"] = pd.to_datetime(self.df["date"])

    def avg_temp(self):
                
        self.df["month"] = self.df["date"].dt.strftime('%m-%y')

        # calculating avg_temp per_month
        result = (self.df.groupby(["device_id", "month"])["temp"]
                  .mean()
                  .round(2)
                  .unstack()  # пустые ячейки станут NaN
                  .to_dict("index")
        )

        return result


    def avg_humidity(self): 
        self.df["month"] = self.df["date"].dt.strftime('%m-%y')

        res = (self.df.groupby(["device_id", "month"])["humidity"]
               .mean()
               .round(2)
               .unstack()
               .to_dict("index")
        )

        return res


    def wind_rose(self):

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