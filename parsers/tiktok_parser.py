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

def parse_tiktok(query, limit=20):
    """
    Парсит TikTok используя прямой API-запрос.
    Если не получается - переключается на Selenium.
    """
    results = []
    
    # Попытка через прямой API-запрос
    try:
        results = parse_tiktok_direct(query, limit)
        if results:
            return results
    except Exception as e:
        print(f"Ошибка при прямом парсинге TikTok: {e}")
    
    # Если API-запрос не сработал - используем Selenium
    return parse_tiktok_selenium(query, limit)

def parse_tiktok_direct(query, limit=20):
    """Парсит TikTok напрямую через API-запрос без Selenium"""
    results = []
    
    # Кодируем запрос
    encoded_query = urllib.parse.quote(query)
    
    # API-подобный URL TikTok
    url = f"https://www.tiktok.com/api/search/general/full/?aid=1988&keyword={encoded_query}&count={limit}"
    
    # Заголовки для имитации браузера
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0',
        'Referer': f'https://www.tiktok.com/search?q={encoded_query}',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    # Делаем запрос
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        
        if 'data' in data and 'videos' in data['data']:
            for video in data['data']['videos']:
                video_id = video.get('id', '')
                author = video.get('author', {}).get('uniqueId', '')
                
                results.append({
                    "platform": "TikTok",
                    "title": video.get('desc', 'Без описания'),
                    "url": f"https://www.tiktok.com/@{author}/video/{video_id}",
                    "video_id": video_id,
                    "views": video.get('stats', {}).get('playCount', 0),
                    "likes": video.get('stats', {}).get('diggCount', 0),
                    "comments": video.get('stats', {}).get('commentCount', 0),
                    "shares": video.get('stats', {}).get('shareCount', 0),
                    "author": author,
                    "publish_time": time.strftime('%Y-%m-%d', time.localtime(video.get('createTime', 0))),
                    "query": query,
                    "collected_at": time.strftime('%Y-%m-%d %H:%M:%S')
                })
                
                if len(results) >= limit:
                    break
    
    return results

def parse_tiktok_selenium(query, limit=20):
    """Парсит TikTok через Selenium, если прямой запрос не сработал"""
    results = []
    driver = None
    
    try:
        driver = setup_driver()
        if not driver:
            return results
        
        # Загружаем cookies, если есть
        load_cookies(driver, "tiktok")
        
        # Открываем страницу поиска
        driver.get(f"https://www.tiktok.com/search?q={query.replace(' ', '%20')}")
        time.sleep(5)
        
        # Соглашаемся с cookies, если появится окно
        try:
            cookie_button = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'Принять')]"))
            )
            cookie_button.click()
            time.sleep(1)
        except:
            pass  # Игнорируем, если окна нет
        
        # Скроллим для загрузки видео (минимальный скролл)
        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(2)
        
        # Используем BeautifulSoup для парсинга
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Извлекаем данные о видео
        video_elements = soup.select("[data-e2e='search-card-item'], .tiktok-1soki6-DivItemContainer")
        for video_element in video_elements[:limit]:
            try:
                # URL видео
                link_element = video_element.select_one("a")
                url = link_element['href'] if link_element and 'href' in link_element.attrs else ""
                
                if not url:
                    continue
                    
                # Извлекаем ID и автора из URL
                video_id = url.split("/")[-1] if url else ""
                author_match = re.search(r'@([^/]+)', url)
                author = author_match.group(1) if author_match else "unknown"
                
                # Текст описания
                desc_element = video_element.select_one(".tiktok-1ejylhp-DivContainer, .tiktok-j2a19r-DivDesContainer")
                description = desc_element.text.strip() if desc_element else "Без описания"
                
                # Метрики
                view_element = video_element.select_one("[data-e2e='video-views'], .video-count")
                views = view_element.text.strip() if view_element else "0"
                
                # Дополнительные метрики из HTML-кода
                likes = "N/A"
                comments = "N/A"
                shares = "N/A"
                
                # Метрики могут быть в разных форматах
                stats_elements = video_element.select(".tiktok-wxn977-StrongVideoStat, .stat-count")
                if len(stats_elements) >= 1:
                    likes = stats_elements[0].text.strip()
                if len(stats_elements) >= 2:
                    comments = stats_elements[1].text.strip()
                if len(stats_elements) >= 3:
                    shares = stats_elements[2].text.strip()
                
                results.append({
                    "platform": "TikTok",
                    "title": description,
                    "url": url,
                    "video_id": video_id,
                    "views": _clean_count(views),
                    "likes": _clean_count(likes),
                    "comments": _clean_count(comments),
                    "shares": _clean_count(shares),
                    "author": author,
                    "publish_time": "N/A",  # Трудно извлечь из HTML
                    "query": query,
                    "collected_at": time.strftime('%Y-%m-%d %H:%M:%S')
                })
                
                if len(results) >= limit:
                    break
            
            except Exception as e:
                print(f"Ошибка при обработке видео TikTok: {e}")
    
    except Exception as e:
        print(f"Ошибка при парсинге TikTok через Selenium: {e}")
    
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
    if 'K' in count_str or 'к' in count_str or 'К' in count_str:
        multiplier = 1000
        count_str = count_str.replace('K', '').replace('к', '').replace('К', '')
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