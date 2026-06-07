# devices/services/report_generator.py

from datetime import datetime, timedelta
from django.utils import timezone
from devices.models import Data, Device
import pandas as pd


class ReportGenerator:
    """Генерация статистических отчётов по погодным данным."""
    
    PERIODS = {
        'day': timedelta(days=1),
        'week': timedelta(weeks=1),
        'month': timedelta(days=30),
        'year': timedelta(days=365)
    }
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.devices = Device.objects.filter(owner_id=user_id)
    
    def get_date_range(self, period: str) -> tuple:
        """Возвращает (start_date, end_date) для выбранного периода."""
        end = timezone.now()
        start = end - self.PERIODS.get(period, timedelta(days=30))
        return start, end
    
    def get_data(self, period: str) -> pd.DataFrame:
        """Загружает данные за период в DataFrame."""
        start, end = self.get_date_range(period)
        
        qs = Data.objects.filter(
            device__owner_id=self.user_id,
            date__range=[start, end]
        ).select_related('device').values(
            'id', 'date', 'temp', 'humidity',
            'device__id', 'device__nickname'
        )
        
        df = pd.DataFrame(list(qs))
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
        return df
    
    def get_statistics(self, period: str) -> dict:
        """Вычисляет статистику за период."""
        # ✅ Все строки метода должны иметь отступ 4 пробела
        df = self.get_data(period)
        
        if df.empty:
            return {'error': 'Нет данных за выбранный период'}
        
        stats = {}
        
        # Температура
        temp_stats = self._get_extreme_stats(df, 'temp', 'temperature')
        stats['temperature'] = temp_stats
        
        # Влажность
        humid_stats = self._get_extreme_stats(df, 'humidity', 'humidity')
        stats['humidity'] = humid_stats
        
        # Средние значения
        stats['averages'] = df.groupby('device__nickname').agg({
            'temp': 'mean',
            'humidity': 'mean'
        }).round(2).to_dict('index')
        
        # Для графиков
        stats['chart_data'] = self._prepare_chart_data(df)
        
        # Флаг для шаблона
        temp_diff = temp_stats['min']['device'] != temp_stats['max']['device']
        humid_diff = humid_stats['min']['device'] != humid_stats['max']['device']
        stats['show_extremes_details'] = temp_diff or humid_diff
        
        return stats
    
    def _get_extreme_stats(self, df: pd.DataFrame, column: str, label: str) -> dict:
        """Находит мин/макс значение с метаданными."""
        min_row = df.loc[df[column].idxmin()]
        max_row = df.loc[df[column].idxmax()]
        
        return {
            'min': {
                'value': round(min_row[column], 2),
                'date': min_row['date'].strftime('%d.%m.%Y %H:%M'),
                'device': min_row['device__nickname'],
                'device_id': min_row['device__id']
            },
            'max': {
                'value': round(max_row[column], 2),
                'date': max_row['date'].strftime('%d.%m.%Y %H:%M'),
                'device': max_row['device__nickname'],
                'device_id': max_row['device__id']
            },
            'avg': round(df[column].mean(), 2)
        }
    
    def _prepare_chart_data(self, df: pd.DataFrame) -> dict:
        """Готовит данные для графиков (среднее по дням)."""
        df = df.copy()
        df['date_only'] = df['date'].dt.date
        
        chart_data = df.groupby(['device__nickname', 'date_only']).agg({
            'temp': 'mean',
            'humidity': 'mean'
        }).round(2).reset_index()
        
        result = {
            'labels': [],
            'datasets': {}
        }
        
        result['labels'] = chart_data['date_only'].unique().tolist()
        result['labels'] = [d.strftime('%d.%m') for d in result['labels']]
        
        for device in chart_data['device__nickname'].unique():
            device_data = chart_data[chart_data['device__nickname'] == device]
            result['datasets'][device] = {
                'temp': device_data.set_index('date_only')['temp'].reindex(
                    chart_data['date_only'].unique()
                ).tolist(),
                'humidity': device_data.set_index('date_only')['humidity'].reindex(
                    chart_data['date_only'].unique()
                ).tolist()
            }
        
        return result
    
    def get_report_context(self, period: str) -> dict:
        """Полный контекст для шаблона отчёта."""
        devices_list = list(self.devices.values('id', 'nickname'))
        for d in devices_list:
            d['name'] = d.pop('nickname')
        
        context = {
            'period': period,
            'start_date': self.get_date_range(period)[0].strftime('%d.%m.%Y'),
            'end_date': timezone.now().strftime('%d.%m.%Y'),
            'devices': devices_list,
            'statistics': self.get_statistics(period)
        }
        return context