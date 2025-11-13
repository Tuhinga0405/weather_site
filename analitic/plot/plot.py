import locale
import requests as rq
import pandas as pd
# import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime


locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")

def parse_month(date_str):
    dt = datetime.fromisoformat(date_str)
    return dt.strftime("%b") 

def make_dict_from_url(url):
    r = rq.get(url)
    data = r.json()    
    
    data_frame = pd.DataFrame(data)

    data_frame["date"] = pd.to_datetime(data_frame["date"])
    data_frame["month"] = data_frame["date"].dt.month

    # calculating avg_temp per_month
    monthly_avg = np.round(data_frame.groupby("month")["temp"].mean(), 2)
    
    # старый метод анализа данных 
    # temp = [] #для сбора месячной температуры
    # data_dict = dict()
    #
    # for i in range(len(data)-1):
    #
    #     t = data[i]["temp"]
    #     temp.append(t)
    #
    #     if parse_month(data[i]["date"]) != parse_month(data[i+1]["date"]):
    #         d = parse_month(data[i]["date"])
    #         avg_temp = np.average(temp)
    #         data_dict[d] = np.round(avg_temp, 2) 
    #         temp = []
    #
    return dict(monthly_avg)

