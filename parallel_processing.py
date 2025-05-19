import multiprocessing
import time
from datetime import datetime
import os
import sys
from functools import partial

def process_in_parallel(func, items, max_workers=None, chunk_size=1):
    """
    Запускает функцию для обработки списка элементов в параллельных процессах
    
    Args:
        func (callable): Функция для обработки элементов
        items (list): Список элементов для обработки
        max_workers (int, optional): Максимальное число параллельных процессов
        chunk_size (int, optional): Размер части списка для одного процесса
        
    Returns:
        list: Список результатов выполнения функции для каждого элемента
    """
    if max_workers is None:
        # Используем количество доступных процессоров - 1, чтобы не загружать систему
        max_workers = max(1, multiprocessing.cpu_count() - 1)
    
    print(f"Запуск многопроцессорной обработки с {max_workers} процессами...")
    
    # Создаем пул процессов
    start_time = time.time()
    with multiprocessing.Pool(processes=max_workers) as pool:
        # Запускаем обработку с использованием map_async
        results = pool.map(func, items, chunk_size)
        
    elapsed = time.time() - start_time
    print(f"Многопроцессорная обработка выполнена за {elapsed:.2f} секунд")
    
    return results

def split_search_queries(query, max_workers):
    """
    Разделяет поисковый запрос на части для параллельной обработки
    
    Args:
        query (str): Основной поисковый запрос
        max_workers (int): Количество процессов
        
    Returns:
        list: Список запросов для параллельной обработки
    """
    # Определяем более точные и специфичные подзапросы для улучшения качества результатов
    base_queries = [query]
    
    # Добавляем варианты с указанием даты, если это имеет смысл
    today = datetime.now()
    current_year = today.year
    current_month = today.month
    
    # Добавляем запрос с годом
    base_queries.append(f"{query} {current_year}")
    
    # Добавляем запрос с указанием "trending", "viral", "popular"
    modifiers = ["trending", "viral", "popular", "best", "top"]
    for modifier in modifiers:
        base_queries.append(f"{query} {modifier}")
    
    # Ограничиваем количество запросов доступным числом процессов
    return base_queries[:max_workers]

def parallel_search_worker(query_config):
    """
    Функция-обработчик для параллельного поиска
    
    Args:
        query_config (dict): Конфигурация поискового запроса
        
    Returns:
        list: Результаты поиска
    """
    try:
        from parsers.youtube_parser import parse_youtube_shorts
        
        query = query_config['query']
        limit = query_config['limit']
        days_ago = query_config['days_ago']
        strict_query_match = query_config.get('strict_query_match', True)
        
        print(f"[Процесс {os.getpid()}] Обработка запроса: '{query}'")
        
        # Выполняем поиск и получаем результаты
        results = parse_youtube_shorts(
            query=query, 
            limit=limit, 
            days_ago=days_ago,
            strict_query_match=strict_query_match
        )
        
        print(f"[Процесс {os.getpid()}] Собрано {len(results)} видео по запросу '{query}'")
        return results
    
    except Exception as e:
        print(f"[Процесс {os.getpid()}] Ошибка при обработке запроса '{query}': {e}")
        import traceback
        traceback.print_exc()
        return []

def run_parallel_search(main_query, limit=200, days_ago=30, max_workers=None, strict_query_match=True):
    """
    Запускает параллельный поиск по нескольким вариациям запроса
    
    Args:
        main_query (str): Основной поисковый запрос
        limit (int): Общий лимит результатов
        days_ago (int): Фильтр по дате
        max_workers (int, optional): Максимальное число параллельных процессов
        
    Returns:
        list: Объединенные результаты со всех запросов
    """
    if max_workers is None:
        max_workers = max(1, multiprocessing.cpu_count() - 1)
    
    # Разделяем запрос на вариации
    queries = split_search_queries(main_query, max_workers)
    
    # Определяем количество результатов для каждого запроса
    per_query_limit = max(50, limit // len(queries))
    
    # Подготавливаем конфигурации для параллельных процессов
    query_configs = [
        {
            'query': q,
            'limit': per_query_limit,
            'days_ago': days_ago,
            'strict_query_match': strict_query_match
        }
        for q in queries
    ]
    
    # Запускаем параллельный поиск
    results_lists = process_in_parallel(
        parallel_search_worker,
        query_configs,
        max_workers=len(queries),
        chunk_size=1
    )
    
    # Объединяем и дедуплицируем результаты
    all_results = []
    seen_video_ids = set()
    
    for results in results_lists:
        for video in results:
            video_id = video.get('video_id')
            if video_id not in seen_video_ids:
                seen_video_ids.add(video_id)
                all_results.append(video)
    
    print(f"Всего собрано уникальных видео: {len(all_results)}")
    
    # Сортируем по просмотрам и возвращаем в пределах общего лимита
    all_results.sort(key=lambda x: int(x.get('views', 0)), reverse=True)
    return all_results[:limit]