import os
import pandas as pd
import glob
import time

def save_to_csv(data, filename):
    """
    Сохраняет данные в CSV-файл
    
    Args:
        data (list): Список словарей с данными
        filename (str): Имя файла для сохранения
    """
    try:
        df = pd.DataFrame(data)
        
        # Создаем директорию, если её нет
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Сохраняем в CSV
        df.to_csv(filename, index=False, encoding='utf-8-sig')
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
        df = pd.read_csv(latest_file)
        return df.to_dict('records')
    
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
            df = pd.read_csv(file)
            
            # Фильтруем по ID и платформе
            filters = df['video_id'] == video_id
            if platform:
                filters &= df['platform'] == platform
                
            video_data = df[filters].to_dict('records')
            
            if video_data:
                history.append(video_data[0])
        
        return history
    
    except Exception as e:
        print(f"Ошибка при получении истории для видео {video_id}: {e}")
        return []