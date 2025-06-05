import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.transform import cumsum
from bokeh.palettes import Category20c, Viridis256, Set3_12
from bokeh.embed import components
from bokeh.layouts import column, row
import math
from typing import Dict, List
from app.db import SessionLocal
from app.models import Question, Answer, Response

# Конфигурация размеров графиков
CHART_SIZES = {
    'desktop': {
        'pie_chart': {'width': 550, 'height': 550},
        'bar_chart': {'width': 1100, 'height': 500},
        'horizontal_bar': {'width': 1200, 'height': 400},
        'fee_chart': {'width': 750, 'height': 600},
        'heatmap': {'width': 1100, 'height': 500}
    },
    'tablet': {
        'pie_chart': {'width': 400, 'height': 400},
        'bar_chart': {'width': 800, 'height': 450},
        'horizontal_bar': {'width': 850, 'height': 350},
        'fee_chart': {'width': 600, 'height': 500},
        'heatmap': {'width': 800, 'height': 450}
    },
    'mobile': {
        'pie_chart': {'width': 350, 'height': 350},
        'bar_chart': {'width': 350, 'height': 400},
        'horizontal_bar': {'width': 350, 'height': 300},
        'fee_chart': {'width': 350, 'height': 450},
        'heatmap': {'width': 350, 'height': 400}
    }
}

def get_chart_size(chart_type: str, device_type: str = 'desktop') -> Dict:
    """Получает размеры графика в зависимости от типа устройства"""
    return CHART_SIZES.get(device_type, CHART_SIZES['desktop']).get(chart_type, {'width': 500, 'height': 400})

def detect_device_type(user_agent: str = '') -> str:
    """Определяет тип устройства по User-Agent"""
    user_agent = user_agent.lower()
    if 'mobile' in user_agent or 'iphone' in user_agent or 'android' in user_agent:
        return 'mobile'
    elif 'tablet' in user_agent or 'ipad' in user_agent:
        return 'tablet'
    else:
        return 'desktop'

def get_survey_statistics() -> Dict:
    """
    Получает статистику по всем вопросам опроса используя pandas для анализа данных
    Возвращает данные готовые для создания графиков Bokeh
    """
    db = SessionLocal()
    try:
        # Получаем ответы - сначала все завершенные
        query = """
        SELECT 
            q.id as question_id,
            q.text as question_text,
            q.qtype as question_type,
            q.[order] as question_order,
            a.value as answer_value,
            r.id as response_id,
            r.status as response_status
        FROM questions q
        LEFT JOIN answers a ON q.id = a.question_id
        LEFT JOIN responses r ON a.response_id = r.id
        WHERE r.status = 'complete'
        ORDER BY q.[order], a.value
        """
        
        # Загружаем данные в pandas DataFrame
        df = pd.read_sql_query(query, db.bind)
        
        # Получаем общую статистику
        total_responses_complete = df[df['response_status'] == 'complete']['response_id'].nunique() if not df.empty else 0
        
        # Для базовых вопросов получаем дополнительный запрос
        query_basic = """
        SELECT 
            q.id as question_id,
            a.value as answer_value,
            r.id as response_id,
            r.status as response_status
        FROM questions q
        LEFT JOIN answers a ON q.id = a.question_id
        LEFT JOIN responses r ON a.response_id = r.id
        WHERE q.id IN (4, 5) AND r.status IN ('consent', 'complete')
        """
        
        df_basic = pd.read_sql_query(query_basic, db.bind)
        total_responses_basic = df_basic['response_id'].nunique() if not df_basic.empty else 0
        
        stats = {
            'total_responses': total_responses_complete,
            'total_basic_responses': total_responses_basic,  # Базовые ответы (включая consent)
            'questions_stats': {}
        }
        
        if df.empty:
            return stats
            
        # Анализируем каждый вопрос отдельно
        for question_id in df['question_id'].unique():
            if pd.isna(question_id):
                continue
                
            question_data = df[df['question_id'] == question_id]
            if question_data.empty:
                continue
                
            question_info = question_data.iloc[0]
            question_text = question_info['question_text']
            question_type = question_info['question_type']
            
            # Для базовых вопросов (4 и 5) используем данные из df_basic
            if question_id in [4, 5] and not df_basic.empty:
                basic_question_data = df_basic[df_basic['question_id'] == question_id]
                if not basic_question_data.empty:
                    value_counts = basic_question_data['answer_value'].value_counts()
                    stats['questions_stats'][question_id] = {
                        'text': question_text,
                        'type': question_type,
                        'values': value_counts.to_dict(),
                        'total': value_counts.sum()
                    }
                    continue
            
            # Подсчитываем ответы для остальных вопросов
            if question_type in ['choice', 'priority']:
                # Для вопросов с выбором считаем частоту каждого варианта
                value_counts = question_data['answer_value'].value_counts()
                stats['questions_stats'][question_id] = {
                    'text': question_text,
                    'type': question_type,
                    'values': value_counts.to_dict(),
                    'total': value_counts.sum()
                }
            elif question_type == 'checkbox':
                # Для чекбоксов нужно разобрать множественные ответы
                # Ответы сохраняются как строка через запятую
                all_options = []
                for answer_value in question_data['answer_value'].dropna():
                    if answer_value:
                        options = [opt.strip() for opt in str(answer_value).split(',')]
                        all_options.extend(options)
                
                checkbox_counts = pd.Series(all_options).value_counts()
                stats['questions_stats'][question_id] = {
                    'text': question_text,
                    'type': question_type,
                    'values': checkbox_counts.to_dict(),
                    'total': len(question_data['answer_value'].dropna())
                }
        
        return stats
    
    finally:
        db.close()

def create_pie_chart(question_data: Dict, title: str, device_type: str = 'desktop'):
    """Создает круговую диаграмму для вопроса"""
    values = question_data['values']
    if not values:
        return None
    
    # Подготавливаем данные для круговой диаграммы
    df_pie = pd.DataFrame(list(values.items()), columns=['category', 'value'])
    df_pie['angle'] = df_pie['value'] / df_pie['value'].sum() * 2 * math.pi
    df_pie['percentage'] = (df_pie['value'] / df_pie['value'].sum() * 100).round(1)
    
    # Вычисляем позиции для подписей (в центре каждого сегмента)
    df_pie['start_angle'] = df_pie['angle'].cumsum() - df_pie['angle']
    df_pie['mid_angle'] = df_pie['start_angle'] + df_pie['angle'] / 2
    df_pie['text_x'] = 0.25 * pd.Series([math.cos(angle) for angle in df_pie['mid_angle']])
    df_pie['text_y'] = 1 + 0.25 * pd.Series([math.sin(angle) for angle in df_pie['mid_angle']])
    
    # Яркие цвета без жёлтого
    bright_colors = [
        '#2E8B57',  # зелёный
        '#4169E1',  # синий
        '#FF6347',  # красный
        '#9370DB',  # фиолетовый
        '#20B2AA',  # бирюзовый
        '#FF1493',  # розовый
        '#00CED1',  # голубой
        '#FFD700'   # (жёлтый, не используем)
    ]
    num_categories = len(df_pie)
    colors = bright_colors[:num_categories]
    
    df_pie['color'] = colors
    
    # Создаем фигуру
    size = get_chart_size('pie_chart', device_type)
    width, height = size['width'], size['height']
    p = figure(height=height, width=width, title=title, toolbar_location=None,
               tools="hover", tooltips="@category: @value (@percentage%)", x_range=(-0.7, 0.7), y_range=(0.3, 1.7))
    
    # Добавляем сегменты круговой диаграммы
    p.wedge(x=0, y=1, radius=0.4,
            start_angle=cumsum('angle', include_zero=True), end_angle=cumsum('angle'),
            line_color="white", fill_color='color', legend_field='category', source=df_pie)
    
    # Добавляем текстовые подписи с количеством прямо на сегменты
    p.text(x='text_x', y='text_y', text='value', text_align='center', text_baseline='middle',
           text_font_size='14pt', text_color='white', source=df_pie)
    
    p.axis.axis_label = None
    p.axis.visible = False
    p.grid.grid_line_color = None
    
    return p

def create_bar_chart(question_data: Dict, title: str, device_type: str = 'desktop'):
    """Создает столбчатую диаграмму для вопроса"""
    values = question_data['values']
    if not values:
        return None
    
    # Получаем размеры из конфигурации
    size = get_chart_size('bar_chart', device_type)
    width, height = size['width'], size['height']
    
    # Подготавливаем данные
    categories = list(values.keys())
    counts = list(values.values())
    
    # Исправляем логику выбора цветов
    num_categories = len(categories)
    if num_categories <= 3:
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'][:num_categories]
    elif num_categories <= 12:
        colors = Set3_12[:num_categories]
    else:
        colors = Viridis256[:num_categories]
    
    # Создаем фигуру
    p = figure(x_range=categories, height=height, width=width, title=title,
               toolbar_location=None, tools="hover", 
               tooltips=[("Вариант", "@x"), ("Количество", "@top")])
    
    # Добавляем столбцы
    p.vbar(x=categories, top=counts, width=0.8, color=colors)
    
    p.xgrid.grid_line_color = None
    p.y_range.start = 0
    p.xaxis.major_label_orientation = 45
    
    return p

def create_dynamic_priority_chart(stats: Dict, device_type: str = 'desktop'):
    """Создает динамический chart приоритетов: 7 столбцов возрастающей высоты, названия аспектов над столбцами, без коллизий"""
    # Получаем размеры из конфигурации
    size = get_chart_size('heatmap', device_type)
    width, height = size['width'], size['height']
    
    # Находим все вопросы о приоритетах (qtype = 'priority')
    priority_questions = {}
    for qid, qdata in stats['questions_stats'].items():
        if qdata['type'] == 'priority':
            # Убираем "(приоритет)" из названия и сокращаем
            clean_title = qdata['text'].replace(' (приоритет)', '')
            
            # Сокращаем названия аспектов - правильные названия из БД
            short_names = {
                'Содержание дорог в хорошем состоянии': 'Содержание дорог в хорошем состоянии',
                'Организация вывоза мусора': 'Организация вывоза мусора',
                'Благоустройство территории': 'Благоустройство территории',
                'Безопасность и охрана': 'Безопасность и охрана',
                'Обслуживание электросетей': 'Обслуживание электросетей',
                'Прозрачная отчётность': 'Прозрачная отчётность',
                'Минимальные взносы': 'Минимальные взносы'
            }
            
            short_title = short_names.get(clean_title, clean_title[:12])
            priority_questions[short_title] = qdata['values']
    
    if not priority_questions:
        return None
    
    # Новые градации: 1=неважно, 7=очень важно
    priority_weights = {
        '1 - Совсем не важно': 1,
        '2': 2,
        '3': 3,
        '4': 4,
        '5': 5,
        '6': 6,
        '7 - Очень важно': 7
    }
    
    # Вычисляем медиану, среднее и количество голосов для каждого аспекта
    aspect_metrics = []  # Список (аспект, медиана, среднее, количество_голосов)
    
    for aspect, values in priority_questions.items():
        # Создаем список всех оценок (каждую оценку повторяем count раз)
        all_ratings = []
        total_score = 0
        total_votes = 0
        
        for priority_text, count in values.items():
            weight = priority_weights.get(priority_text, 4)
            all_ratings.extend([weight] * count)  # Добавляем оценку count раз
            total_score += weight * count
            total_votes += count
        
        if total_votes > 0:
            # Вычисляем медиану
            all_ratings.sort()
            n = len(all_ratings)
            if n % 2 == 0:
                median = (all_ratings[n//2 - 1] + all_ratings[n//2]) / 2
            else:
                median = all_ratings[n//2]
            
            # Вычисляем среднее
            average = total_score / total_votes
        else:
            median = 4.0
            average = 4.0
            total_votes = 0
        
        aspect_metrics.append((aspect, median, average, total_votes))
    
    # Сортируем по: 1) медиане, 2) среднему, 3) количеству голосов
    # Это гарантирует отсутствие коллизий без искусственных манипуляций
    aspect_metrics.sort(key=lambda x: (x[1], x[2], -x[3]))  # median ASC, average ASC, votes DESC
    
    # Распределяем аспекты по 7 столбцам пропорционально
    aspect_placements = {}  # level -> aspect_name
    num_aspects = len(aspect_metrics)
    
    for i, (aspect, median, average, votes) in enumerate(aspect_metrics):
        # Пропорционально распределяем по 7 столбцам
        if num_aspects == 1:
            level = 4  # В середину если только один аспект
        else:
            # Равномерно распределяем от 1 до 7
            level = int(1 + (i / (num_aspects - 1)) * 6)  # Диапазон 1-7
            level = max(1, min(7, level))  # Ограничиваем
        
        aspect_placements[level] = aspect
    
    # Функция для разбивки названий на две строчки по смыслу
    def split_name(name):
        # Смысловые разбивки для каждого аспекта на основе названий из формы
        smart_splits = {
            # Сокращенные варианты
            'Дороги': 'Содержание\nдорог',
            'Мусор': 'Вывоз\nмусора', 
            'Благоустройство': 'Благоустройство\nтерритории',
            'Охрана': 'Безопасность\nи охрана',
            'Электричество': 'Обслуживание\nэлектросетей',
            'Вода': 'Водоснабжение\nи качество',
            'Свет': 'Освещение\nтерритории',
            # Полные названия из формы
            'Содержание дорог в хорошем состоянии': 'Содержание\nдорог',
            'Организация вывоза мусора': 'Вывоз\nмусора',
            'Благоустройство территории': 'Благоустройство\nтерритории', 
            'Безопасность и охрана': 'Безопасность\nи охрана',
            'Обслуживание электросетей': 'Обслуживание\nэлектросетей',
            'Прозрачная отчётность': 'Прозрачная\nотчётность',
            'Минимальные взносы': 'Размер\nвзносов'
        }
        
        # Если есть готовая смысловая разбивка
        if name in smart_splits:
            return smart_splits[name]
        
        # Для составных названий разбиваем по первому пробелу
        if ' ' in name:
            parts = name.split(' ', 1)  # Разбиваем только по первому пробелу
            return parts[0] + '\n' + parts[1]
        
        # Короткие названия оставляем как есть
        return name
    
    # 7 столбцов ПОВЫШЕННОЙ высоты для лучшей наглядности
    x_positions = [1, 2, 3, 4, 5, 6, 7]
    heights = [8, 12, 16, 20, 24, 28, 32]  # Увеличенные размеры столбцов
    
    # Цвета от красного (неважно) к зелёному (важно)
    colors = ['#e74c3c', '#f39c12', '#f1c40f', '#95a5a6', '#3498db', '#2ecc71', '#27ae60']
    
    # Создаем фигуру
    p = figure(title="Важность различных аспектов СНТ",
               x_range=(0.5, 7.5),
               width=width, height=height,
               toolbar_location=None,
               tools="")  # Убираем hover
    
    # Добавляем 7 столбцов возрастающей высоты
    source = ColumnDataSource(data={
        'x': x_positions,
        'top': heights,
        'color': colors
    })
    
    p.vbar(x='x', top='top', width=0.7, color='color', alpha=0.8, source=source)
    
    # Добавляем названия аспектов НАД столбцами в две строчки
    for level in range(1, 8):
        if level in aspect_placements:
            aspect = aspect_placements[level]
            column_height = heights[level-1]  # Высота этого столбца
            
            # Разбиваем название на строчки
            display_name = split_name(aspect)
            
            # Размещаем название НАД столбцом
            y_position = column_height + 3  # На 3 единицы выше столбца
            
            p.text(x=[level], y=[y_position], text=[display_name],
                   text_align='center', text_baseline='bottom',
                   text_font_size='10pt', text_color='#2c3e50')
    
    # Настройки осей
    p.xaxis.ticker = [1, 2, 3, 4, 5, 6, 7]
    p.xaxis.major_label_overrides = {
        1: "1\nНеважно",
        2: "2",
        3: "3", 
        4: "4",
        5: "5",
        6: "6",
        7: "7\nВажно"
    }
    p.xaxis.axis_label = "Уровень важности"
    
    # Убираем ось Y - она не нужна
    p.yaxis.visible = False
    p.ygrid.visible = False
    
    # Убираем вертикальные линии (xgrid) полностью
    p.xgrid.grid_line_color = None
    p.y_range.start = 0
    p.y_range.end = 42  # Увеличенный диапазон для названий в две строчки
    
    return p

def create_horizontal_bar_chart(question_data: Dict, title: str, device_type: str = 'desktop'):
    """Создает горизонтальную столбчатую диаграмму"""
    values = question_data['values']
    if not values:
        return None
    
    # Получаем размеры из конфигурации
    size = get_chart_size('horizontal_bar', device_type)
    width, height = size['width'], size['height']
    
    # Подготавливаем данные - сортируем по убыванию
    sorted_items = sorted(values.items(), key=lambda x: x[1], reverse=True)
    categories = [item[0] for item in sorted_items]
    counts = [item[1] for item in sorted_items]
    
    # Преобразуем внутренние коды в КОРОТКИЕ читаемые названия
    readable_names = []
    name_mapping = {
        'size_fees': 'Размер взносов',
        'transparency': 'Прозрачность средств', 
        'management': 'Качество управления',
        'legal_risks': 'Правовые риски',
        'infrastructure': 'Обязательства по инфраструктуре',
        'bureaucracy': 'Бюрократические сложности',
        'other': 'Другое'
    }
    
    for cat in categories:
        readable_names.append(name_mapping.get(cat, cat))
    
    # Яркие цвета
    bright_colors = [
        '#2E8B57',  # Sea Green
        '#4169E1',  # Royal Blue  
        '#FF6347',  # Tomato
        '#32CD32',  # Lime Green
        '#FF8C00',  # Dark Orange
        '#9370DB',  # Medium Purple
        '#20B2AA',  # Light Sea Green
        '#FF1493',  # Deep Pink
        '#00CED1',  # Dark Turquoise
        '#FFD700'   # Gold
    ]
    
    colors = bright_colors[:len(categories)]
    
    # Создаем позиции для столбцов (числовые индексы вместо названий)
    y_positions = list(range(len(readable_names)))
    y_positions.reverse()  # Переворачиваем чтобы самые большие были сверху
    
    # Создаем фигуру с базовыми инструментами, но БЕЗ hover
    p = figure(height=height, width=width, title=title, 
               toolbar_location=None, tools="")
    
    # Создаем данные для столбцов
    source_data = {
        'y': y_positions,
        'right': counts,
        'color': colors
    }
    
    # Добавляем горизонтальные столбцы
    p.hbar(y='y', right='right', height=0.7, color='color', alpha=0.8, source=source_data)
    
    # Добавляем текстовые подписи ВНУТРИ столбцов
    # Позиция текста - в середине столбца
    text_x = [count / 2 for count in counts]  # Середина каждого столбца
    
    # Определяем цвет текста (белый или черный в зависимости от яркости фона)
    text_colors = []
    for color in colors:
        # Для темных цветов - белый текст, для светлых - черный
        if color in ['#2E8B57', '#4169E1', '#9370DB', '#20B2AA']:
            text_colors.append('white')
        else:
            text_colors.append('black')
    
    # Добавляем текст внутри столбцов
    p.text(x=text_x, y=y_positions, text=readable_names, 
           text_align='center', text_baseline='middle',
           text_font_size='12pt', text_color=text_colors)
    
    # Добавляем цифры в конце столбцов
    p.text(x=[count + max(counts) * 0.02 for count in counts], y=y_positions, text=counts,
           text_align='left', text_baseline='middle',
           text_font_size='14pt', text_color='black')
    
    # Настройки осей
    p.ygrid.grid_line_color = None
    p.xgrid.grid_line_color = None
    p.x_range.start = 0
    p.x_range.end = max(counts) * 1.15  # Добавляем место для цифр справа
    p.xaxis.axis_label = "Количество ответов"
    
    # Убираем подписи по Y-оси
    p.yaxis.visible = False
    
    return p

def create_fee_bar_chart(question_data: Dict, title: str, device_type: str = 'desktop'):
    """Создает столбчатую диаграмму для взносов с сортировкой по возрастанию"""
    values = question_data['values']
    if not values:
        return None
    
    # Получаем размеры из конфигурации
    size = get_chart_size('fee_chart', device_type)
    width, height = size['width'], size['height']
    
    # Специальная сортировка для взносов по возрастанию
    fee_order = {
        '500': (1, '500₽'),
        '1000': (2, '1000₽'),
        '1500': (3, '1500₽'),
        '2000': (4, '2000₽'),
        'refuse': (5, '0')  # Отказ = 0
    }
    
    # Сортируем по порядку
    sorted_items = []
    for value, count in values.items():
        if value in fee_order:
            order, display_name = fee_order[value]
            sorted_items.append((order, display_name, count))
    
    sorted_items.sort(key=lambda x: x[0])  # Сортируем по порядку
    
    categories = [item[1] for item in sorted_items]  # Отображаемые названия
    counts = [item[2] for item in sorted_items]      # Количества
    
    # Яркие цвета для взносов
    colors = ['#32CD32', '#4169E1', '#FF8C00', '#FF6347', '#DC143C'][:len(categories)]
    
    # Создаем фигуру
    p = figure(x_range=categories, height=height, width=width, title=title,
               toolbar_location=None, tools="")
    
    # Добавляем столбцы
    p.vbar(x=categories, top=counts, width=0.8, color=colors, alpha=0.8)
    
    # Добавляем цифры на столбцах
    p.text(x=categories, y=[count + max(counts) * 0.02 for count in counts], 
           text=counts, text_align='center', text_baseline='bottom',
           text_font_size='14pt', text_color='black')
    
    p.xgrid.grid_line_color = None
    p.y_range.start = 0
    p.y_range.end = max(counts) * 1.15
    p.xaxis.major_label_orientation = 0  # Горизонтальные подписи
    p.yaxis.axis_label = "Количество"
    
    return p

def create_fees_pie_chart(question_data: Dict, title: str, device_type: str = 'desktop'):
    """Пирог для взносов: только 5 вариантов, без жёлтого, 0 словом"""
    values = question_data['values']
    if not values:
        return None
    
    options = [
        ('500', '500₽'),
        ('1000', '1000₽'),
        ('1500', '1500₽'),
        ('2000', '2000₽'),
        ('refuse', 'ноль')
    ]
    data = []
    for key, label in options:
        data.append((label, values.get(key, 0)))
    # Цвета без жёлтого
    pie_data = {'values': dict(data)}
    return create_pie_chart(pie_data, title, device_type)

def create_participation_pie_chart(question_data: Dict, title: str, device_type: str = 'desktop'):
    """Пирог для участия в управлении с 5 вариантами как в форме"""
    values = question_data['values']
    if not values:
        return None
    
    # Жестко фиксируем порядок и подписи
    options = [
        ('board', 'Войти в правление'),
        ('committees', 'В комитетах'),
        ('meetings', 'Только собрания'),
        ('observer', 'Наблюдатель'),
        ('no', 'Нет времени')
    ]
    data = []
    for key, label in options:
        data.append((label, values.get(key, 0)))
    
    # Формируем dict для create_pie_chart
    pie_data = {'values': dict(data)}
    return create_pie_chart(pie_data, title, device_type)

def generate_bokeh_charts(stats: Dict, device_type: str = 'desktop') -> str:
    """
    Генерирует все графики Bokeh как отдельные независимые компоненты
    """
    charts = {}  # Словарь для хранения отдельных графиков
    
    # График 1: Поддержка создания СНТ (question_id = 4)
    if 4 in stats['questions_stats']:
        chart = create_pie_chart(
            stats['questions_stats'][4], 
            "Поддержка создания нового СНТ",
            device_type
        )
        if chart:
            script, div = components(chart)
            charts['snt_support'] = {'script': script, 'div': div}
    
    # График 2: Готовность к финансовым обязательствам (question_id = 5)
    if 5 in stats['questions_stats']:
        chart = create_pie_chart(
            stats['questions_stats'][5],
            "Готовность к финансовым обязательствам",
            device_type
        )
        if chart:
            script, div = components(chart)
            charts['financial_ready'] = {'script': script, 'div': div}
    
    # График 3: Основные опасения (question_id = 6)
    if 6 in stats['questions_stats']:
        chart = create_horizontal_bar_chart(
            stats['questions_stats'][6],
            "Основные опасения жителей",
            device_type
        )
        if chart:
            script, div = components(chart)
            charts['concerns'] = {'script': script, 'div': div}
    
    # График 4: Желаемый ежемесячный взнос (question_id = 7)
    if 7 in stats['questions_stats']:
        chart = create_fees_pie_chart(
            stats['questions_stats'][7],
            "Желаемый ежемесячный взнос",
            device_type
        )
        if chart:
            script, div = components(chart)
            charts['fees'] = {'script': script, 'div': div}
    
    # График 5: Участие в управлении (question_id = 8) - теперь пирог
    if 8 in stats['questions_stats']:
        chart = create_participation_pie_chart(
            stats['questions_stats'][8],
            "Готовность участвовать в управлении СНТ",
            device_type
        )
        if chart:
            script, div = components(chart)
            charts['participation'] = {'script': script, 'div': div}
    
    # График 6: Тепловая карта приоритетов
    priority_chart = create_dynamic_priority_chart(stats, device_type)
    if priority_chart:
        script, div = components(priority_chart)
        charts['priorities'] = {'script': script, 'div': div}
    
    # Объединяем все скрипты
    all_scripts = []
    for chart_data in charts.values():
        if chart_data['script']:
            all_scripts.append(chart_data['script'])
    
    combined_script = '\n'.join(all_scripts)
    
    return combined_script, charts 

def get_comments_data() -> Dict:
    """
    Получает комментарии жителей для отображения на дашборде
    Возвращает топ-3 комментария по лайкам и общую статистику
    """
    db = SessionLocal()
    try:
        # Ищем question_id для комментариев (текст содержит "комментарии" или "предложения")
        query = """
        SELECT 
            q.id as question_id,
            q.text as question_text,
            a.id as answer_id,
            a.value as comment_text,
            r.created_at as created_at,
            COUNT(cl.id) as likes_count
        FROM questions q
        LEFT JOIN answers a ON q.id = a.question_id
        LEFT JOIN responses r ON a.response_id = r.id
        LEFT JOIN comment_likes cl ON a.id = cl.answer_id
        WHERE r.status = 'complete' 
        AND (LOWER(q.text) LIKE '%комментари%' OR LOWER(q.text) LIKE '%предложени%')
        AND a.value IS NOT NULL 
        AND TRIM(a.value) != ''
        AND a.moderated = 1
        GROUP BY q.id, q.text, a.id, a.value, r.created_at
        ORDER BY likes_count DESC, r.created_at DESC
        """
        
        # Загружаем данные в pandas DataFrame
        df = pd.read_sql_query(query, db.bind)
        
        if df.empty:
            return {
                'total_comments': 0,
                'recent_comments': [],
                'has_comments': False
            }
        
        # Фильтруем пустые комментарии
        df = df[df['comment_text'].str.len() > 10]  # Минимум 10 символов
        
        total_comments = len(df)
        
        # Получаем топ-3 комментария (по лайкам, потом по дате)
        recent_comments = []
        for _, row in df.head(3).iterrows():
            comment_text = row['comment_text']
            
            # Обрезаем длинные комментарии для предварительного просмотра
            if len(comment_text) > 120:
                preview_text = comment_text[:120] + "..."
            else:
                preview_text = comment_text
            
            recent_comments.append({
                'answer_id': int(row['answer_id']),
                'text': preview_text,
                'full_text': comment_text,
                'likes_count': int(row['likes_count']),
                'created_at': row['created_at'].strftime('%d.%m.%Y') if pd.notna(row['created_at']) and hasattr(row['created_at'], 'strftime') else str(row['created_at']) if pd.notna(row['created_at']) else 'Дата неизвестна'
            })
        
        return {
            'total_comments': total_comments,
            'recent_comments': recent_comments,
            'has_comments': total_comments > 0
        }
    
    finally:
        db.close()

def get_all_comments() -> List[Dict]:
    """
    Получает все комментарии для отдельной страницы
    Сортирует по лайкам (популярности), затем по дате
    """
    db = SessionLocal()
    try:
        query = """
        SELECT 
            a.id as answer_id,
            a.value as comment_text,
            r.created_at as created_at,
            COUNT(cl.id) as likes_count
        FROM questions q
        LEFT JOIN answers a ON q.id = a.question_id
        LEFT JOIN responses r ON a.response_id = r.id
        LEFT JOIN comment_likes cl ON a.id = cl.answer_id
        WHERE r.status = 'complete' 
        AND (LOWER(q.text) LIKE '%комментари%' OR LOWER(q.text) LIKE '%предложени%')
        AND a.value IS NOT NULL 
        AND TRIM(a.value) != ''
        AND a.moderated = 1
        GROUP BY a.id, a.value, r.created_at
        ORDER BY likes_count DESC, r.created_at DESC
        """
        
        df = pd.read_sql_query(query, db.bind)
        
        if df.empty:
            return []
        
        # Фильтруем пустые комментарии
        df = df[df['comment_text'].str.len() > 10]
        
        comments = []
        for _, row in df.iterrows():
            comments.append({
                'answer_id': int(row['answer_id']),
                'text': row['comment_text'],
                'likes_count': int(row['likes_count']),
                'created_at': row['created_at'].strftime('%d.%m.%Y %H:%M') if pd.notna(row['created_at']) and hasattr(row['created_at'], 'strftime') else str(row['created_at']) if pd.notna(row['created_at']) else 'Дата неизвестна'
            })
        
        return comments
    
    finally:
        db.close() 