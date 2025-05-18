import requests
import json
import re
import time
import urllib.parse
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.browser import setup_driver, load_cookies

def parse_youtube_shorts(query, limit=20):
    """
    Парсит YouTube Shorts используя прямой HTTP-запрос.
    Если не получается - переключается на Selenium.
    """
    results = []
    
    # Попытка через прямой HTTP-запрос
    try:
        results = parse_youtube_direct(query, limit)
        if results:
            return results
    except Exception as e:
        print(f"Ошибка при прямом парсинге YouTube: {e}")
    
    # Если прямой запрос не сработал - используем Selenium
    return parse_youtube_selenium(query, limit)

def parse_youtube_direct(query, limit=20):
    """Парсит YouTube Shorts напрямую через HTTP-запрос без Selenium"""
    results = []
    
    # Кодируем запрос
    encoded_query = urllib.parse.quote(query)
    
    # URL для поиска шортсов
    url = f"https://www.youtube.com/results?search_query={encoded_query}&sp=EgIoAQ%253D%253D"
    
    # Имитируем обычный браузер
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    # Делаем запрос
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        # Ищем ytInitialData в HTML
        initial_data_match = re.search(r'var ytInitialData = (.+?);</script>', response.text)
        
        if initial_data_match:
            # Извлекаем и парсим JSON
            json_str = initial_data_match.group(1)
            data = json.loads(json_str)
            
            # Извлекаем информацию о видео
            try:
                items = data['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents']
                
                for item in items:
                    if 'videoRenderer' in item:
                        renderer = item['videoRenderer']
                        
                        # Проверяем, является ли это шортом
                        is_short = False
                        for badge in renderer.get('badges', []):
                            if 'metadataBadgeRenderer' in badge and 'short' in badge['metadataBadgeRenderer'].get('label', '').lower():
                                is_short = True
                                break
                        
                        # Если это не явный шорт, проверяем длительность
                        if not is_short and 'lengthText' in renderer:
                            length = renderer['lengthText'].get('simpleText', '10:00')
                            if ':' in length and int(length.split(':')[0]) > 0:
                                continue
                        
                        # Собираем данные о видео
                        video_id = renderer.get('videoId', '')
                        title = renderer['title']['runs'][0]['text']
                        url = f"https://www.youtube.com/shorts/{video_id}"
                        
                        # Просмотры
                        views = "0"
                        if 'viewCountText' in renderer:
                            view_text = renderer['viewCountText']
                            if 'simpleText' in view_text:
                                views = view_text['simpleText']
                            elif 'runs' in view_text:
                                views = view_text['runs'][0]['text']
                        
                        # Добавляем в результаты
                        results.append({
                            "platform": "YouTube Shorts",
                            "title": title,
                            "url": url,
                            "video_id": video_id,
                            "views": _clean_count(views),
                            "likes": "N/A",  # Без API сложно получить точное число лайков
                            "comments": "N/A",
                            "publish_time": renderer.get('publishedTimeText', {}).get('simpleText', 'Неизвестно'),
                            "channel": renderer['ownerText']['runs'][0]['text'],
                            "query": query,
                            "collected_at": time.strftime('%Y-%m-%d %H:%M:%S')
                        })
                        
                        if len(results) >= limit:
                            break
            except KeyError:
                print("Структура данных YouTube изменилась, попробуем резервный вариант")
    
    return results

def parse_youtube_selenium(query, limit=20):
    """Парсит YouTube Shorts через Selenium, если прямой запрос не сработал"""
    results = []
    driver = None
    
    try:
        driver = setup_driver()
        if not driver:
            return results
        
        # Загружаем cookies, если есть
        load_cookies(driver, "youtube")
        
        # URL для поиска шортсов
        url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}&sp=EgIoAQ%253D%253D"
        
        # Загружаем страницу
        driver.get(url)
        time.sleep(3)
        
        # Парсим через BeautifulSoup
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
                
                results.append({
                    "platform": "YouTube Shorts",
                    "title": title,
                    "url": shorts_url,
                    "video_id": video_id,
                    "views": views,
                    "likes": "N/A",
                    "comments": "N/A",
                    "publish_time": publish_time,
                    "channel": channel,
                    "query": query,
                    "collected_at": time.strftime('%Y-%m-%d %H:%M:%S')
                })
                
                if len(results) >= limit:
                    break
                    
            except Exception as e:
                print(f"Ошибка при обработке видео YouTube: {e}")
    
    except Exception as e:
        print(f"Ошибка при парсинге YouTube через Selenium: {e}")
    
    finally:
        if driver:
            driver.quit()
    
    return results

def _clean_count(count_str):
    """Преобразует строку с числом в число"""
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
        # Извлекаем числовую часть
        number_match = re.search(r'(\d+\.?\d*)', count_str)
        if number_match:
            number = float(number_match.group(1))
            return str(int(number * multiplier))
    except:
        pass
    
    return "0"