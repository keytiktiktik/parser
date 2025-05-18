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

def parse_vk_clips(query, limit=20):
    """
    Парсит ВК Клипы используя прямой HTTP-запрос.
    Если не получается - переключается на Selenium.
    """
    results = []
    
    # Попытка через прямой HTTP-запрос
    try:
        results = parse_vk_direct(query, limit)
        if results:
            return results
    except Exception as e:
        print(f"Ошибка при прямом парсинге ВК Клипов: {e}")
    
    # Если прямой запрос не сработал - используем Selenium
    return parse_vk_selenium(query, limit)

def parse_vk_direct(query, limit=20):
    """Парсит ВК Клипы напрямую через HTTP-запрос без Selenium"""
    results = []
    
    # Кодируем запрос
    encoded_query = urllib.parse.quote(query)
    
    # URL для поиска клипов
    url = f"https://vk.com/clips?q={encoded_query}"
    
    # Заголовки для имитации браузера
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    # Загрузите cookies из файла, если они есть
    cookies = {}
    try:
        import os
        import pickle
        cookies_file = os.path.join(os.getcwd(), "cookies", "vk_cookies.pkl")
        if os.path.exists(cookies_file):
            cookie_jar = pickle.load(open(cookies_file, "rb"))
            for cookie in cookie_jar:
                cookies[cookie['name']] = cookie['value']
    except:
        pass
    
    # Делаем запрос
    response = requests.get(url, headers=headers, cookies=cookies)
    
    if response.status_code == 200:
        # Ищем clips_catalog_data в HTML
        catalog_match = re.search(r'clips_catalog_data\s*:\s*({.+?}),\s*clips_draft_data', response.text)
        
        if catalog_match:
            try:
                # Извлекаем и парсим JSON
                catalog_data = json.loads(catalog_match.group(1))
                
                if 'clips' in catalog_data:
                    for clip in catalog_data['clips'][:limit]:
                        clip_id = clip.get('id', '')
                        owner_id = clip.get('owner_id', '')
                        
                        # Формируем URL клипа
                        clip_url = f"https://vk.com/clip{owner_id}_{clip_id}"
                        
                        # Собираем данные
                        results.append({
                            "platform": "ВК Клипы",
                            "title": clip.get('title', 'Без названия'),
                            "url": clip_url,
                            "video_id": clip_id,
                            "views": clip.get('views', 0),
                            "likes": clip.get('likes', {}).get('count', 0),
                            "comments": clip.get('comments', {}).get('count', 0),
                            "shares": clip.get('reposts', {}).get('count', 0), 
                            "author": clip.get('author', {}).get('name', 'Неизвестно'),
                            "publish_time": clip.get('date_formatted', 'Неизвестно'),
                            "query": query,
                            "collected_at": time.strftime('%Y-%m-%d %H:%M:%S')
                        })
            except json.JSONDecodeError:
                print("Ошибка при парсинге JSON данных ВК")
    
    return results

def parse_vk_selenium(query, limit=20):
    """Парсит ВК Клипы через Selenium, если прямой запрос не сработал"""
    results = []
    driver = None
    
    try:
        driver = setup_driver()
        if not driver:
            return results
        
        # Загружаем cookies, если есть
        load_cookies(driver, "vk")
        
        # Открываем страницу поиска
        driver.get(f"https://vk.com/clips?q={query.replace(' ', '%20')}")
        time.sleep(5)
        
        # Парсим HTML
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Ищем клипы
        clip_items = soup.select('.clips_search_results .clips_items_item')
        
        for item in clip_items[:limit]:
            try:
                # URL и ID
                link = item.select_one('a.clips_items_cover')
                url = 'https://vk.com' + link['href'] if link and 'href' in link.attrs else ""
                
                if not url:
                    continue
                    
                # Извлекаем ID из URL
                url_match = re.search(r'clip-?(\d+)_(\d+)', url)
                owner_id = url_match.group(1) if url_match else "0"
                clip_id = url_match.group(2) if url_match else "0"
                
                # Название
                title_elem = item.select_one('.clips_items_info_title')
                title = title_elem.text.strip() if title_elem else "Без названия"
                
                # Просмотры
                views_elem = item.select_one('.clips_items_stats_views')
                views = views_elem.text.strip() if views_elem else "0"
                
                # Лайки
                likes_elem = item.select_one('.clips_items_stats_likes')
                likes = likes_elem.text.strip() if likes_elem else "0"
                
                # Автор
                author_elem = item.select_one('.clips_items_info_author')
                author = author_elem.text.strip() if author_elem else "Неизвестно"
                
                results.append({
                    "platform": "ВК Клипы",
                    "title": title,
                    "url": url,
                    "video_id": clip_id,
                    "views": _clean_count(views),
                    "likes": _clean_count(likes),
                    "comments": "N/A",  # Трудно получить из списка клипов
                    "shares": "N/A",
                    "author": author,
                    "publish_time": "N/A",  # Не отображается в списке
                    "query": query,
                    "collected_at": time.strftime('%Y-%m-%d %H:%M:%S')
                })
                
                if len(results) >= limit:
                    break
            
            except Exception as e:
                print(f"Ошибка при обработке клипа ВК: {e}")
    
    except Exception as e:
        print(f"Ошибка при парсинге ВК Клипов через Selenium: {e}")
    
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