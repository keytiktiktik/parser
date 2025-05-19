import yt_dlp
from datetime import datetime, timedelta
import time
import urllib.parse
import re

def parse_youtube_shorts(query, limit=1000, days_ago=30, strict_query_match=True):
    """Парсер YouTube Shorts с использованием yt-dlp
    
    Args:
        query (str): Поисковый запрос
        limit (int): Максимальное количество видео для сбора
        days_ago (int): Сбор видео за последние N дней
        strict_query_match (bool): Строгая проверка наличия слов запроса в заголовке/описании видео
        
    Returns:
        list: Список словарей с данными о видео
    """
    results = []
    collected_video_ids = set()  # Для отслеживания уникальных видео
    cutoff_date = datetime.now() - timedelta(days=days_ago)
    
    print(f"Сбор YouTube Shorts за последние {days_ago} дней по запросу '{query}'...")

    # Настройка yt-dlp для получения дополнительных метаданных
    ydl_opts = {
        'quiet': True,  # Минимизировать вывод логов
        'extract_flat': False,  # Извлекать полные метаданные, не только плоские 
        'skip_download': True,  # Не загружать видео
        'noplaylist': True,  # Игнорировать плейлисты
        'ignoreerrors': True,  # Игнорировать ошибки
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'cookiefile': None,  # Можно указать путь к cookies для обхода ограничений
    }

    # Формируем поисковый запрос
    search_query = f"{query} shorts"
    # Подготовка слов запроса для проверки совпадений
    query_words = query.lower().split()

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Выполняем поиск с увеличенным лимитом для компенсации фильтрации
            search_results = ydl.extract_info(f"ytsearch{limit*2}:{search_query}", download=False)
            videos = search_results.get('entries', [])
            
            print(f"Получено {len(videos)} результатов поиска, обрабатываем...")

            for index, video in enumerate(videos):
                if len(results) >= limit:
                    break

                if not video:  # Пропускаем None объекты, которые могут появиться при ошибках
                    continue
                
                video_id = video.get('id')
                if not video_id or video_id in collected_video_ids:
                    continue

                # Проверяем, является ли видео шортом
                is_short = False
                
                # Метод 1: Длительность <= 60 секунд
                duration = video.get('duration')
                if duration and duration <= 60:
                    is_short = True
                # Метод 2: Проверка URL на /shorts/
                elif video.get('webpage_url', '').find('/shorts/') != -1:
                    is_short = True
                # Метод 3: Проверка тега #shorts в описании или заголовке
                elif (video.get('description', '').lower().find('#shorts') != -1 or 
                      video.get('title', '').lower().find('#shorts') != -1):
                    is_short = True
                
                if not is_short:
                    continue
                
                # Строгая проверка совпадения с запросом
                if strict_query_match:
                    title = video.get('title', '').lower()
                    description = video.get('description', '').lower()
                    content = title + " " + description
                    
                    # Проверяем, что хотя бы одно слово из запроса присутствует
                    match_found = False
                    for word in query_words:
                        if word in content:
                            match_found = True
                            break
                            
                    if not match_found:
                        continue  # Пропускаем видео без совпадений с запросом

                # Получение и обработка даты публикации
                # Проверяем несколько возможных полей с датой
                upload_date = None
                video_date = None
                days_ago_value = None
                
                # Список полей для проверки
                date_fields = ['upload_date', 'release_date', 'upload_date_utc', 'timestamp']
                
                for field in date_fields:
                    if field in video and video[field]:
                        try:
                            # Пробуем разные форматы даты
                            if field == 'upload_date' and isinstance(video[field], str) and len(video[field]) == 8:
                                # Формат YYYYMMDD
                                upload_date = video[field]
                                video_date = datetime.strptime(upload_date, '%Y%m%d')
                                days_ago_value = (datetime.now() - video_date).days
                                break
                            elif field == 'timestamp' and isinstance(video[field], (int, float)):
                                # Формат timestamp
                                video_date = datetime.fromtimestamp(video[field])
                                upload_date = video_date.strftime('%Y%m%d')
                                days_ago_value = (datetime.now() - video_date).days
                                break
                        except (ValueError, TypeError) as e:
                            print(f"Ошибка обработки даты из поля {field} для видео {video_id}: {e}")
                            continue
                
                # Если не нашли дату в явных полях, попробуем альтернативные методы
                if video_date is None:
                    # Попробуем использовать альтернативное поле с датой публикации
                    if 'published_time' in video and video['published_time']:
                        try:
                            publication_date_str = video['published_time']
                            # Могут быть разные форматы даты
                            if 'T' in publication_date_str:
                                # ISO формат
                                video_date = datetime.fromisoformat(publication_date_str.replace('Z', '+00:00'))
                            else:
                                # Проверяем другие распространенные форматы
                                for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%b %d, %Y']:
                                    try:
                                        video_date = datetime.strptime(publication_date_str, fmt)
                                        break
                                    except ValueError:
                                        continue
                                    
                            if video_date:
                                upload_date = video_date.strftime('%Y%m%d')
                                days_ago_value = (datetime.now() - video_date).days
                        except Exception as e:
                            print(f"Ошибка при парсинге published_time для видео {video_id}: {e}")
                            
                # Если все методы не сработали, устанавливаем текущую дату с пометкой                   
                if video_date is None:
                    # Для отладки выведем доступные поля даты
                    date_related_fields = {k: v for k, v in video.items() if 'date' in k.lower() or 'time' in k.lower()}
                    if date_related_fields:
                        print(f"Поля с датами для видео {video_id}: {date_related_fields}")
                    
                    # Если дату не удалось определить, используем текущую, но с пометкой
                    video_date = datetime.now()
                    upload_date = "Неизвестно"
                    days_ago_value = "Неизвестно"
                    print(f"Дата публикации не найдена для видео {video_id} (обработан {index+1}/{len(videos)})")

                # Проверяем возраст видео если дата определена
                if isinstance(days_ago_value, int) and days_ago_value > days_ago:
                    print(f"Пропуск видео {video_id} - слишком старое ({days_ago_value} дней)")
                    continue

                collected_video_ids.add(video_id)

                # Извлекаем метрики и безопасно преобразуем их в строки
                view_count = _safe_str(video.get('view_count', 0))
                like_count = _safe_str(video.get('like_count', 0))
                comment_count = _safe_str(video.get('comment_count', 0))
                share_count = _safe_str(video.get('repost_count', 0))
                
                # Формируем дату публикации для отображения
                if isinstance(video_date, datetime):
                    publish_date_formatted = video_date.strftime('%Y-%m-%d')
                else:
                    publish_date_formatted = "Неизвестно"
                
                video_data = {
                    'platform': 'YouTube Shorts',
                    'title': video.get('title', 'Неизвестно'),
                    'url': f"https://www.youtube.com/shorts/{video_id}",
                    'video_id': video_id,
                    'views': view_count,
                    'likes': like_count,
                    'comments': comment_count,
                    'shares': share_count,
                    'publish_time': upload_date,
                    'publish_date_formatted': publish_date_formatted,
                    'days_ago': days_ago_value,
                    'channel': video.get('uploader', 'Неизвестно'),
                    'query': query,
                    'collected_at': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                results.append(video_data)
                
                # Периодически выводим прогресс
                if (index + 1) % 10 == 0:
                    print(f"Обработано {index+1}/{len(videos)} видео, найдено шортсов: {len(results)}")

            print(f"Собрано {len(results)} видео")

        except Exception as e:
            print(f"Ошибка при парсинге YouTube Shorts: {e}")
            import traceback
            traceback.print_exc()

    # Сортируем результаты по просмотрам
    results.sort(key=lambda x: _safe_int(x.get('views', 0)), reverse=True)

    # Выводим статистику по метрикам
    if results:
        # Безопасно подсчитываем метрики
        with_likes = sum(1 for v in results if _safe_int(v.get('likes', 0)) > 0)
        with_comments = sum(1 for v in results if _safe_int(v.get('comments', 0)) > 0)
        with_shares = sum(1 for v in results if _safe_int(v.get('shares', 0)) > 0)
        
        print(f"Статистика метрик: видео с лайками: {with_likes}/{len(results)}, с комментариями: {with_comments}/{len(results)}, с репостами: {with_shares}/{len(results)}")

    # Возвращаем результаты в пределах запрошенного лимита
    return results[:limit]

def _safe_str(value):
    """Безопасно преобразует значение в строку"""
    if value is None:
        return "0"
    try:
        return str(value)
    except:
        return "0"

def _safe_int(value):
    """Безопасно преобразует значение в целое число"""
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0

def _clean_count(count_str):
    """Преобразует строку с числом в число"""
    if not count_str or count_str == "N/A":
        return "0"
    
    # Удаление пробелов и замена запятых на точки
    count_str = str(count_str).replace(' ', '').replace(',', '.')
    
    # Обработка суффиксов
    multiplier = 1
    
    if any(x in count_str.lower() for x in ['k', 'к', 'тыс']):
        multiplier = 1000
        count_str = re.sub(r'[kкK]|тыс\.?', '', count_str.lower())
    elif any(x in count_str.lower() for x in ['m', 'м', 'млн']):
        multiplier = 1000000
        count_str = re.sub(r'[mмM]|млн\.?', '', count_str.lower())
    elif any(x in count_str.lower() for x in ['b', 'б', 'млрд']):
        multiplier = 1000000000
        count_str = re.sub(r'[bбB]|млрд\.?', '', count_str.lower())
    
    try:
        # Извлекаем числовую часть
        number_match = re.search(r'(\d+\.?\d*)', count_str)
        if number_match:
            number = float(number_match.group(1))
            return str(int(number * multiplier))
    except:
        pass
    
    return "0"

# Пример использования
if __name__ == "__main__":
    query = "funny cats"
    videos = parse_youtube_shorts(query, limit=50, days_ago=30, strict_query_match=True)
    for video in videos[:5]:  # Выводим первые 5 для примера
        print(f"Title: {video['title']}, URL: {video['url']}, Views: {video['views']}, Likes: {video['likes']}, Publish Date: {video['publish_date_formatted']}, Days Ago: {video['days_ago']}")