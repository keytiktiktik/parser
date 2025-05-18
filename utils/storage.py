import os
import csv
import glob
import time
from datetime import datetime

def save_to_csv(data, filename):
    """
    Сохраняет данные в CSV-файл
    
    Args:
        data (list): Список словарей с данными
        filename (str): Имя файла для сохранения
        
    Returns:
        bool: True если успешно, иначе False
    """
    try:
        # Создаем директорию, если её нет
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        if not data:
            print(f"Нет данных для сохранения в {filename}")
            return False
            
        # Определяем заголовки (все возможные ключи)
        fieldnames = set()
        for item in data:
            fieldnames.update(item.keys())
        
        fieldnames = sorted(list(fieldnames))
        
        # Записываем данные
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
            
        print(f"Данные сохранены в {filename}")
        return True
        
    except Exception as e:
        print(f"Ошибка при сохранении данных в CSV: {e}")
        return False

def load_previous_data(query=None):
    """
    Загружает предыдущие данные для сравнения
    
    Args:
        query (str, optional): Поисковый запрос для загрузки данных
        
    Returns:
        list: Список словарей с предыдущими данными
    """
    try:
        # Находим все CSV-файлы в папке history
        pattern = f"data/history/viral_videos_{query.replace(' ', '_')}*.csv" if query else "data/history/*.csv"
        files = glob.glob(pattern)
        
        if not files:
            return []
        
        # Сортируем файлы по времени создания (от нового к старому)
        files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        # Берем самый свежий файл
        latest_file = files[0]
        
        # Проверяем, не слишком ли старый файл (более 7 дней)
        file_age = time.time() - os.path.getmtime(latest_file)
        if file_age > 7 * 24 * 60 * 60:  # Более 7 дней
            print(f"Предупреждение: последний файл данных старше 7 дней ({latest_file})")
        
        # Загружаем данные
        result = []
        with open(latest_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Преобразуем числовые значения к числам
                for key in row:
                    if key in ['views', 'likes', 'comments', 'shares', 'views_growth', 
                               'likes_growth', 'comments_growth', 'views_velocity', 
                               'likes_velocity', 'comments_velocity', 'viral_score']:
                        try:
                            row[key] = int(float(row[key])) if '.' in row[key] else int(row[key])
                        except (ValueError, TypeError):
                            pass
                result.append(row)
                
        return result
    
    except Exception as e:
        print(f"Ошибка при загрузке предыдущих данных: {e}")
        return []

def get_history_for_video(video_id, platform=None):
    """
    Получает историю метрик для конкретного видео
    
    Args:
        video_id (str): ID видео
        platform (str, optional): Название платформы
        
    Returns:
        list: Список словарей с историческими данными
    """
    try:
        # Находим все CSV-файлы в папке history
        files = glob.glob("data/history/*.csv")
        
        if not files:
            return []
        
        # Сортируем файлы по времени создания (от старого к новому)
        files.sort(key=lambda x: os.path.getmtime(x))
        
        history = []
        
        # Ищем видео во всех файлах
        for file in files:
            with open(file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # Фильтруем по ID и платформе
                    if row.get('video_id') == video_id:
                        if platform is None or row.get('platform') == platform:
                            # Преобразуем числовые значения
                            for key in row:
                                if key in ['views', 'likes', 'comments', 'shares', 'views_growth', 
                                           'likes_growth', 'comments_growth', 'views_velocity', 
                                           'likes_velocity', 'comments_velocity', 'viral_score']:
                                    try:
                                        row[key] = int(float(row[key])) if '.' in row[key] else int(row[key])
                                    except (ValueError, TypeError):
                                        pass
                            history.append(row)
        
        return history
    
    except Exception as e:
        print(f"Ошибка при получении истории для видео {video_id}: {e}")
        return []