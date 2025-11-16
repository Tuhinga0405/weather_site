import requests as rq
import plotly.io as pio
import plotly.express as px

def turning_nums_to_months(ls):
    months = {
    "1": "янв",
    "2": "фев",
    "3": "мар",
    "4": "апр",
    "5": "май",
    "6": "июн",
    "7": "июл",
    "8": "авг",
    "9": "сен",
    "10": "окт",
    "11": "ноя",
    "12": "дек"
    }
    ls_res = list(map(lambda x: months[x], ls))
    return ls_res

class Plot_d:
    def __init__(self, url, id):
        self.data = rq.get(f"{url}{id}").json()
        self.avg_temp = self.data["avg_temp"]
        self.rosa_vetrov = self.data["roza"]

    def make_avg_temp_plot(self):
        
        months = turning_nums_to_months(list(self.avg_temp.keys())) # api from analitics returns months as nums
        temps = self.avg_temp.values()

        #make plot 
        fig = px.line(x=months, y=temps)
        plot_temp = pio.to_html(fig, full_html=False)
        return plot_temp

    def make_roza(self):
    
        figure = px.bar_polar(
        self.rosa_vetrov,
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
            )
        )

        plot_roza = pio.to_html(figure, full_html=False)
        return plot_roza

