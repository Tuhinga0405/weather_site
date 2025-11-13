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

ls = ["1", "2", "3"]
print(turning_nums_to_months(ls))
