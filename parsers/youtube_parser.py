import yt_dlp
from datetime import datetime, timedelta
import time
import urllib.parse
import re

def parse_youtube_shorts(query, limit=1000, days_ago=30):
    """Парсер YouTube Shorts с использованием yt-dlp"""
    results = []
    collected_video_ids = set()  # Для отслеживания уникальных видео
    cutoff_date = datetime.now() - timedelta(days=days_ago)
    
    print(f"Сбор YouTube Shorts за последние {days_ago} дней по запросу '{query}'...")

    # Настройка yt-dlp
    ydl_opts = {
        'quiet': True,  # Минимизировать вывод логов
        'extract_flat': True,  # Извлекать только метаданные
        'noplaylist': True,  # Игнорировать плейлисты
        'simulate': True,  # Не загружать видео
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'cookiefile': None,  # Можно указать путь к cookies для обхода ограничений
    }

    # Формируем поисковый запрос
    search_query = f"{query} shorts"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Выполняем поиск
            search_results = ydl.extract_info(f"ytsearch{limit}:{search_query}", download=False)
            videos = search_results.get('entries', [])

            for video in videos:
                if len(results) >= limit:
                    break

                video_id = video.get('id')
                if video_id in collected_video_ids:
                    continue

                # Проверяем, является ли видео шортом
                is_short = False
                # Метод 1: Длительность <= 60 секунд
                duration = video.get('duration', 0)
                if duration and duration <= 60:
                    is_short = True
                # Метод 2: Проверка URL на /shorts/
                elif video.get('url', '').find('/shorts/') != -1:
                    is_short = True
                # Метод 3: Проверка тега #shorts в описании
                elif video.get('description', '').lower().find('#shorts') != -1:
                    is_short = True

                if not is_short:
                    continue

                # Проверяем дату публикации
                upload_date = video.get('upload_date')  # Формат: YYYYMMDD
                if upload_date:
                    video_date = datetime.strptime(upload_date, '%Y%m%d')
                    if video_date < cutoff_date:
                        continue

                collected_video_ids.add(video_id)

                # Извлекаем метрики
                results.append({
                    'platform': 'YouTube Shorts',
                    'title': video.get('title', 'Неизвестно'),
                    'url': f"https://www.youtube.com/shorts/{video_id}",
                    'video_id': video_id,
                    'views': str(video.get('view_count', 0)),
                    'likes': str(video.get('like_count', 0)),
                    'comments': str(video.get('comment_count', 0)),
                    'shares': str(video.get('share_count', 0)),  # Может быть None
                    'publish_time': upload_date or 'Неизвестно',
                    'channel': video.get('uploader', 'Неизвестно'),
                    'query': query,
                    'collected_at': time.strftime('%Y-%m-%d %H:%M:%S')
                })

            print(f"Собрано {len(results)} видео")

        except Exception as e:
            print(f"Ошибка при парсинге YouTube Shorts: {e}")

    # Сортируем результаты по просмотрам
    results.sort(key=lambda x: int(x.get('views', 0)), reverse=True)

    # Выводим статистику по метрикам
    if results:
        with_likes = len([v for v in results if int(v.get('likes', 0)) > 0])
        with_comments = len([v for v in results if int(v.get('comments', 0)) > 0])
        with_shares = len([v for v in results if int(v.get('shares', 0)) > 0])
        
        print(f"Статистика метрик: видео с лайками: {with_likes}/{len(results)}, с комментариями: {with_comments}/{len(results)}, с репостами: {with_shares}/{len(results)}")

    # Возвращаем результаты в пределах запрошенного лимита
    return results[:limit]

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
    videos = parse_youtube_shorts(query, limit=50, days_ago=30)
    for video in videos[:5]:  # Выводим первые 5 для примера
        print(f"Title: {video['title']}, URL: {video['url']}, Views: {video['views']}, Likes: {video['likes']}")