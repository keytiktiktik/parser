import requests
import json
import re
import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.browser import setup_driver

def parse_tiktok(query, limit=20):
    """
    Парсит TikTok по заданному запросу
    
    Args:
        query (str): Поисковый запрос
        limit (int): Максимальное количество видео для сбора
        
    Returns:
        list: Список словарей с данными о видео
    """
    results = []
    
    # Сначала пробуем через недокументированное API
    try:
        # Используем API-endpoint который TikTok использует внутренне
        api_url = f"https://www.tiktok.com/api/search/general/full/?aid=1988&keyword={query.replace(' ', '%20')}&count={limit}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
            'Referer': 'https://www.tiktok.com/search?q=' + query.replace(' ', '%20')
        }
        
        response = requests.get(api_url, headers=headers)
        
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
    
    except Exception as e:
        print(f"Ошибка при парсинге TikTok через API: {e}")
        
    # Если через API не получилось, используем Selenium как запасной вариант
    if not results:
        driver = None
        try:
            driver = setup_driver()
            
            # Открываем страницу поиска
            driver.get(f"https://www.tiktok.com/search?q={query.replace(' ', '%20')}")
            time.sleep(5)  # Ждем загрузку
            
            # Соглашаемся с cookies, если появится окно
            try:
                cookie_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'Принять')]"))
                )
                cookie_button.click()
                time.sleep(1)
            except:
                pass  # Игнорируем, если окна нет
            
            # Скроллим для загрузки видео
            for _ in range(3):
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
                
                except Exception as e:
                    print(f"Ошибка при обработке видео TikTok: {e}")
        
        except Exception as e:
            print(f"Ошибка при парсинге TikTok через Selenium: {e}")
        
        finally:
            if driver:
                driver.quit()
    
    return results[:limit]

def _clean_count(count_str):
    """
    Преобразует строку с числом (например, "1.5M" или "1,5М") в строку с числом
    
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
        return str(int(float(count_str) * multiplier))
    except:
        return "0"