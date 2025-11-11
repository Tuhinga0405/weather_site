import locale
import requests as rq
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime


locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")

def parse_data(date_str):
    dt = datetime.fromisoformat(date_str)
    return dt.strftime("%b") 

def make_dict_from_url(url):
    r = rq.get(url)
    data = r.json()    

    temp = [] #для сбора месячной температуры
    data_dict = dict()

    for i in range(len(data)-1):

        t = data[i]["temp"]
        temp.append(t)

        if parse_data(data[i]["date"]) != parse_data(data[i+1]["date"]):
            d = parse_data(data[i]["date"])
            avg_temp = np.average(temp)
            data_dict[d] = np.round(avg_temp, 2) 
            temp = []

    return data_dict

def make_avg_months_plot(data):
    
    x_axis = list(data.keys())
    #перевожу числовой тип данных numpy в стандартный float, т.к. не уверен, что matplotlib будет работать с ним
    y_axis = list(map(lambda x: float(np.round(x,2)), data.values()))

    plt.plot(x_axis, y_axis, marker='o')
    plt.title("Среднемесячные температуры")
    plt.xlabel("Месяц")
    plt.ylabel("Температура (°C)")
    plt.grid(True)
    # plt.show()
    plt.savefig('foo.png', bbox_inches='tight')


x = make_dict_from_url("http://localhost:9000/devices/get_data/2")
make_avg_months_plot(x)
