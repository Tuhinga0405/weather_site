# devices/services/report_generator.py

from datetime import datetime, timedelta
from django.utils import timezone
from devices.models import Data, Device
import pandas as pd

# matplotlib настройки (ДО импорта pyplot)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import os


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
        df = self.get_data(period)
        
        if df.empty:
            return {'error': 'Нет данных за выбранный период'}
        
        stats = {}
        
        temp_stats = self._get_extreme_stats(df, 'temp', 'temperature')
        stats['temperature'] = temp_stats
        
        humid_stats = self._get_extreme_stats(df, 'humidity', 'humidity')
        stats['humidity'] = humid_stats
        
        stats['averages'] = df.groupby('device__nickname').agg({
            'temp': 'mean',
            'humidity': 'mean'
        }).round(2).to_dict('index')
        
        stats['chart_data'] = self._prepare_chart_data(df)
        stats['chart_images'] = self.get_chart_images(period)
        
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
    
    def _get_font_path(self) -> str:
        """Возвращает путь к шрифту с поддержкой кириллицы."""
        font_paths = [
            '/usr/share/fonts/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf',
        ]
        for path in font_paths:
            if os.path.exists(path):
                return path
        return ''
    
    def _generate_line_chart(self, data: dict, all_dates: list, title: str, ylabel: str) -> str:
        """Генерирует линейный график с реальными датами на оси X."""
        if not data or not any(v for v in data.values() if v):
            return ''
        
        font_path = self._get_font_path()
        
        if font_path:
            from matplotlib.font_manager import FontProperties
            font_props = FontProperties(fname=font_path)
        else:
            font_props = None
        
        x_positions = list(range(len(all_dates)))
        x_labels = all_dates
        
        fig, ax = plt.subplots(figsize=(10, 5), dpi=100)
        
        colors = plt.cm.tab10.colors
        
        for idx, (device, values) in enumerate(data.items()):
            if values and any(v is not None for v in values):
                valid_indices = [i for i, v in enumerate(values) if v is not None]
                valid_x = [x_positions[i] for i in valid_indices]
                valid_y = [values[i] for i in valid_indices]
                
                if valid_x:
                    ax.plot(valid_x, valid_y, 
                           label=device, 
                           color=colors[idx % len(colors)],
                           marker='o', markersize=4, linewidth=2,
                           markerfacecolor='white', markeredgewidth=1)
        
        ax.set_xlabel('Дата', fontproperties=font_props, fontsize=10)
        ax.set_ylabel(ylabel, fontproperties=font_props, fontsize=10)
        ax.set_title(title, fontproperties=font_props, fontsize=12, pad=15, fontweight='bold')
        
        if x_labels:
            step = max(1, len(x_labels) // 10)
            ax.set_xticks(x_positions[::step])
            ax.set_xticklabels([x_labels[i] for i in range(0, len(x_labels), step)], 
                              rotation=45, ha='right', fontsize=9)
        
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        ax.legend(prop=font_props, fontsize=9, loc='best', framealpha=0.9)
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', facecolor='white')
        buf.seek(0)
        
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        plt.close(fig)
        
        return f'data:image/png;base64,{image_base64}'
    
    def _prepare_chart_data_for_matplotlib(self, df: pd.DataFrame) -> dict:
        """Подготавливает данные для matplotlib с реальными датами."""
        df = df.copy()
        df['date_only'] = df['date'].dt.date
        df['date_label'] = df['date'].dt.strftime('%d.%m')
        
        grouped = df.groupby(['device__nickname', 'date_only', 'date_label']).agg({
            'temp': 'mean',
            'humidity': 'mean'
        }).round(2).reset_index()
        
        all_dates = sorted(grouped['date_label'].unique().tolist())
        
        result = {
            'devices': {},
            'all_dates': all_dates
        }
        
        for device in grouped['device__nickname'].unique():
            device_data = grouped[grouped['device__nickname'] == device].sort_values('date_only')
            
            temp_series = []
            humid_series = []
            
            for date_label in all_dates:
                row = device_data[device_data['date_label'] == date_label]
                if not row.empty:
                    temp_series.append(float(row['temp'].iloc[0]))
                    humid_series.append(float(row['humidity'].iloc[0]))
                else:
                    temp_series.append(None)
                    humid_series.append(None)
            
            result['devices'][device] = {
                'dates': all_dates,
                'temp': temp_series,
                'humidity': humid_series
            }
        
        return result
    
    def get_chart_images(self, period: str) -> dict:
        """✅ ИСПРАВЛЕНО: все строки метода с отступом 4 пробела"""
        df = self.get_data(period)
        if df.empty:
            return {'temp_chart': '', 'humidity_chart': ''}
        
        chart_data = self._prepare_chart_data_for_matplotlib(df)
        
        if not chart_data['devices']:
            return {'temp_chart': '', 'humidity_chart': ''}
        
        # Извлекаем данные для графиков (комментарий с отступом!)
        temp_data = {
            dev: data['temp'] 
            for dev, data in chart_data['devices'].items() 
            if data['temp'] and any(v is not None for v in data['temp'])
        }
        
        humid_data = {
            dev: data['humidity'] 
            for dev, data in chart_data['devices'].items() 
            if data['humidity'] and any(v is not None for v in data['humidity'])
        }
        
        all_dates = chart_data['all_dates']
        
        # Генерация графиков с передачей реальных дат (комментарий с отступом!)
        temp_chart = self._generate_line_chart(
            data=temp_data,
            all_dates=all_dates,
            title='Средняя температура по устройствам',
            ylabel='°C'
        )
        
        humid_chart = self._generate_line_chart(
            data=humid_data,
            all_dates=all_dates,
            title='Средняя влажность по устройствам',
            ylabel='%'
        )
        
        return {
            'temp_chart': temp_chart,
            'humidity_chart': humid_chart
        }
    
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