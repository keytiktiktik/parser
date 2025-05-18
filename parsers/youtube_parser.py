import requests
import re
import json
import time
from bs4 import BeautifulSoup
from requests_html import HTMLSession
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from utils.browser import setup_driver

def parse_youtube_shorts(query, limit=20):
    """
    Парсит YouTube Shorts по заданному запросу
    
    Args:
        query (str): Поисковый запрос
        limit (int): Максимальное количество видео для сбора
        
    Returns:
        list: Список словарей с данными о видео
    """
    results = []
    
    # Пробуем через requests_html (быстрее)
    try:
        session = HTMLSession()
        
        # Поисковый URL для YouTube Shorts
        url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}&sp=EgIoAQ%253D%253D"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        r = session.get(url, headers=headers)
        r.html.render(sleep=3, timeout=20)  # Выполнение JavaScript
        
        # Поиск данных в скриптах
        data = None
        for script in r.html.find('script'):
            if 'ytInitialData' in script.text:
                data_str = script.text.split('var ytInitialData = ')[1].split(';</script>')[0]
                data = json.loads(data_str)
                break
        
        if data:
            # Извлечение видео
            items = data['contents']['twoColumnSearchResultsRenderer']['primaryContents'][
                'sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents']
            
            for item in items:
                if 'videoRenderer' in item:
                    renderer = item['videoRenderer']
                    
                    # Проверка на шорт
                    is_short = False
                    for badge in renderer.get('badges', []):
                        if 'metadataBadgeRenderer' in badge:
                            if 'short' in badge['metadataBadgeRenderer'].get('label', '').lower():
                                is_short = True
                                break
                    
                    if not is_short:
                        # Проверяем длительность (шорты обычно до 60 секунд)
                        length = renderer.get('lengthText', {}).get('simpleText', '10:00')
                        if ':' in length:
                            parts = length.split(':')
                            if len(parts) > 1 and int(parts[0]) > 0:
                                continue  # Пропускаем видео длиннее 1 минуты
                    
                    video_id = renderer.get('videoId', '')
                    title = renderer['title']['runs'][0]['text']
                    
                    # Извлекаем метрики
                    view_count_text = "0"
                    if 'viewCountText' in renderer:
                        view_count_text = renderer['viewCountText'].get('simpleText', 
                            renderer['viewCountText'].get('runs', [{}])[0].get('text', '0'))
                    
                    views = _clean_count(view_count_text)
                    
                    # Время публикации
                    publish_time = "Неизвестно"
                    if 'publishedTimeText' in renderer:
                        publish_time = renderer['publishedTimeText']['simpleText']
                    
                    # Канал
                    channel = renderer['ownerText']['runs'][0]['text']
                    
                    # URL
                    shorts_url = f"https://www.youtube.com/shorts/{video_id}"
                    
                    # Получаем дополнительные метрики (лайки, комментарии)
                    extra_metrics = _get_youtube_short_metrics(video_id)
                    
                    results.append({
                        "platform": "YouTube Shorts",
                        "title": title,
                        "url": shorts_url,
                        "video_id": video_id,
                        "views": views,
                        "likes": extra_metrics.get('likes', 'N/A'),
                        "comments": extra_metrics.get('comments', 'N/A'), 
                        "publish_time": publish_time,
                        "channel": channel,
                        "query": query,
                        "collected_at": time.strftime('%Y-%m-%d %H:%M:%S')
                    })
                    
                    if len(results) >= limit:
                        break
                        
        session.close()
    
    except Exception as e:
        print(f"Ошибка при парсинге YouTube Shorts через requests: {e}")
    
    # Если с requests_html не получилось, пробуем через Selenium
    if not results:
        try:
            driver = setup_driver()
            
            try:
                # Формируем URL поиска
                url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}&sp=EgIoAQ%253D%253D"
                
                # Загрузка страницы
                driver.get(url)
                time.sleep(5)
                
                # Скроллинг для загрузки видео
                for i in range(3):
                    driver.execute_script("window.scrollBy(0, 1000);")
                    time.sleep(2)
                
                # Парсинг через BeautifulSoup
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Находим видео
                video_items = soup.select("ytd-video-renderer, ytd-reel-item-renderer")
                
                for item in video_items[:limit]:
                    try:
                        # Название и URL
                        title_elem = item.select_one("#video-title, #title")
                        if not title_elem:
                            continue
                            
                        title = title_elem.text.strip()
                        
                        # Получаем ссылку
                        link_elem = item.select_one("a#thumbnail, a.ytd-thumbnail")
                        if not link_elem or 'href' not in link_elem.attrs:
                            continue
                            
                        href = link_elem['href']
                        video_id = re.search(r'(?:v=|shorts\/)([^&\/]+)', href).group(1)
                        
                        # Проверяем, это шорт или нет
                        is_short = 'shorts' in href or item.select_one("span.ytd-thumbnail-overlay-time-status-renderer[aria-label='Shorts']")
                        
                        if not is_short:
                            # Проверяем длительность
                            time_elem = item.select_one("span.ytd-thumbnail-overlay-time-status-renderer")
                            if time_elem and ':' in time_elem.text:
                                parts = time_elem.text.strip().split(':')
                                if len(parts) > 1 and int(parts[0]) > 0:
                                    continue  # Пропускаем видео длиннее 1 минуты
                        
                        # Метаданные
                        metadata = item.select_one("#metadata-line, ytd-video-meta-block")
                        metadata_text = metadata.text.strip() if metadata else ""
                        
                        # Просмотры
                        views_match = re.search(r'(\d+(?:[\.,]\d+)*(?:\s*[KkМмТтBb])?)\s*(?:просмотр|views)', metadata_text)
                        views = _clean_count(views_match.group(1)) if views_match else "0"
                        
                        # Формируем URL для шортса
                        shorts_url = f"https://www.youtube.com/shorts/{video_id}"
                        
                        # Получаем время публикации
                        time_match = re.search(r'(\d+\s+\w+\s+назад|\d+\s+\w+\s+ago)', metadata_text)
                        publish_time = time_match.group(1) if time_match else "Неизвестно"
                        
                        # Получаем канал
                        channel_elem = item.select_one("#channel-name a, ytd-channel-name a")
                        channel = channel_elem.text.strip() if channel_elem else "Неизвестно"
                        
                        # Получаем дополнительные метрики
                        extra_metrics = _get_youtube_short_metrics(video_id)
                        
                        results.append({
                            "platform": "YouTube Shorts",
                            "title": title,
                            "url": shorts_url,
                            "video_id": video_id,
                            "views": views,
                            "likes": extra_metrics.get('likes', 'N/A'),
                            "comments": extra_metrics.get('comments', 'N/A'),
                            "publish_time": publish_time,
                            "channel": channel,
                            "query": query,
                            "collected_at": time.strftime('%Y-%m-%d %H:%M:%S')
                        })
                        
                        if len(results) >= limit:
                            break
                            
                    except Exception as e:
                        print(f"Ошибка при обработке видео: {e}")
            
            finally:
                driver.quit()
                
        except Exception as e:
            print(f"Ошибка при парсинге YouTube Shorts через Selenium: {e}")
    
    return results[:limit]

def _get_youtube_short_metrics(video_id):
    """
    Получает метрики (лайки, комментарии) для YouTube Short
    
    Args:
        video_id (str): ID видео
        
    Returns:
        dict: Словарь с метриками
    """
    metrics = {'likes': 'N/A', 'comments': 'N/A'}
    
    try:
        # Пробуем через API запрос
        url = f"https://returnyoutubedislikeapi.com/votes?videoId={video_id}"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            likes = data.get('likes', 0)
            if likes > 0:
                metrics['likes'] = str(likes)
    
    except:
        pass
    
    # Если не получилось через API, пробуем через HTML
    if metrics['likes'] == 'N/A':
        try:
            url = f"https://www.youtube.com/shorts/{video_id}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                # Поиск в HTML
                likes_match = re.search(r'"topLevelButtons":\[\{"toggleButtonRenderer":\{"accessibilityData":\{"accessibilityData":\{"label":"([^"]*? likes)"}', response.text)
                if likes_match:
                    likes_text = likes_match.group(1)
                    likes_count = re.search(r'([\d,]+)', likes_text)
                    if likes_count:
                        metrics['likes'] = likes_count.group(1).replace(',', '')
                
                # Комментарии
                comments_match = re.search(r'"commentCount":\{"simpleText":"([^"]+)"}', response.text)
                if comments_match:
                    metrics['comments'] = comments_match.group(1).replace(',', '')
        
        except:
            pass
    
    return metrics

def _clean_count(count_str):
    """
    Преобразует строку с числом (например, "1.5M" или "1,5 млн") в число
    
    Args:
        count_str (str): Строка с числом
        
    Returns:
        str: Очищенное число в виде строки
    """
    if not count_str or count_str == "N/A":
        return "0"
    
    # Удаление пробелов и замена запятых на точки
    count_str = count_str.replace(' ', '').replace(',', '.')
    
    # Обработка суффиксов
    multiplier = 1
    if 'K' in count_str or 'к' in count_str or 'К' in count_str or 'тыс' in count_str:
        multiplier = 1000
        count_str = count_str.replace('K', '').replace('к', '').replace('К', '').replace('тыс', '')
    elif 'M' in count_str or 'млн' in count_str or 'М' in count_str:
        multiplier = 1000000
        count_str = count_str.replace('M', '').replace('млн', '').replace('М', '')
    elif 'B' in count_str or 'млрд' in count_str or 'Б' in count_str:
        multiplier = 1000000000
        count_str = count_str.replace('B', '').replace('млрд', '').replace('Б', '')
        
    try:
        return str(int(float(count_str) * multiplier))
    except:
        return "0"