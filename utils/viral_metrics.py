def calculate_viral_score(current_data, previous_data=None):
    """
    Рассчитывает показатели виральности на основе текущих и предыдущих данных
    
    Args:
        current_data (list): Список словарей с текущими данными о видео
        previous_data (list, optional): Список словарей с предыдущими данными о видео
        
    Returns:
        list: Список словарей с добавленными метриками виральности
    """
    result = []
    
    for video in current_data:
        # Создаем копию текущего видео для добавления метрик
        video_with_metrics = video.copy()
        
        # Поиск предыдущих данных для этого видео (если они есть)
        prev_data = None
        if previous_data:
            for prev_video in previous_data:
                if (prev_video.get("video_id") == video.get("video_id") and 
                    prev_video.get("platform") == video.get("platform")):
                    prev_data = prev_video
                    break
        
        # Если есть предыдущие данные, рассчитываем динамику
        if prev_data:
            # Рост просмотров
            prev_views = _convert_to_int(prev_data.get("views", 0))
            current_views = _convert_to_int(video.get("views", 0))
            views_growth = current_views - prev_views
            
            # Рост лайков
            prev_likes = _convert_to_int(prev_data.get("likes", 0))
            current_likes = _convert_to_int(video.get("likes", 0))
            likes_growth = current_likes - prev_likes
            
            # Рост комментариев
            prev_comments = _convert_to_int(prev_data.get("comments", 0))
            current_comments = _convert_to_int(video.get("comments", 0))
            comments_growth = current_comments - prev_comments
            
            # Время между измерениями (в часах)
            try:
                from datetime import datetime
                prev_time = datetime.strptime(prev_data.get("collected_at"), "%Y-%m-%d %H:%M:%S")
                current_time = datetime.strptime(video.get("collected_at"), "%Y-%m-%d %H:%M:%S")
                time_diff_hours = (current_time - prev_time).total_seconds() / 3600
                
                # Скорости роста (в час)
                if time_diff_hours > 0:
                    views_velocity = views_growth / time_diff_hours
                    likes_velocity = likes_growth / time_diff_hours
                    comments_velocity = comments_growth / time_diff_hours
                else:
                    views_velocity = likes_velocity = comments_velocity = 0
            except:
                views_velocity = likes_velocity = comments_velocity = 0
                
            # Добавление метрик
            video_with_metrics["views_growth"] = views_growth
            video_with_metrics["likes_growth"] = likes_growth
            video_with_metrics["comments_growth"] = comments_growth
            video_with_metrics["views_velocity"] = round(views_velocity, 2)
            video_with_metrics["likes_velocity"] = round(likes_velocity, 2)
            video_with_metrics["comments_velocity"] = round(comments_velocity, 2)
            
            # Расчет общего показателя виральности
            # Формула может быть скорректирована в зависимости от ваших требований
            viral_score = (
                views_velocity * 0.5 + 
                likes_velocity * 0.3 + 
                comments_velocity * 0.2
            )
            
            video_with_metrics["viral_score"] = round(viral_score, 2)
            
        else:
            # Если предыдущих данных нет, используем абсолютные метрики
            views = _convert_to_int(video.get("views", 0))
            likes = _convert_to_int(video.get("likes", 0))
            comments = _convert_to_int(video.get("comments", 0))
            
            # Оценка на основе общего количества действий
            actions_sum = views + likes * 10 + comments * 20  # Взвешенная сумма
            
            # Вычисляем примерную вовлеченность (лайки/просмотры)
            engagement = (likes * 100 / views) if views > 0 else 0
            
            # Расчет виральности для новых видео
            viral_score = (actions_sum / 10000) * (1 + engagement / 10)
            
            video_with_metrics["views_growth"] = 0
            video_with_metrics["likes_growth"] = 0
            video_with_metrics["comments_growth"] = 0
            video_with_metrics["views_velocity"] = 0
            video_with_metrics["likes_velocity"] = 0
            video_with_metrics["comments_velocity"] = 0
            video_with_metrics["viral_score"] = round(viral_score, 2)
        
        result.append(video_with_metrics)
    
    # Сортировка по viral_score (от высокого к низкому)
    result.sort(key=lambda x: float(x["viral_score"]), reverse=True)
    
    return result

def _convert_to_int(value):
    """
    Преобразует различные форматы значений в целые числа
    
    Args:
        value: Значение для преобразования
        
    Returns:
        int: Преобразованное целое число
    """
    if isinstance(value, int):
        return value
    
    if isinstance(value, float):
        return int(value)
    
    if isinstance(value, str):
        if value.lower() == 'n/a':
            return 0
            
        try:
            # Удаляем все нецифровые символы, кроме десятичной точки
            clean_str = ''.join(c for c in value if c.isdigit() or c == '.')
            if clean_str:
                if '.' in clean_str:
                    return int(float(clean_str))
                return int(clean_str)
            return 0
        except:
            return 0
    
    return 0