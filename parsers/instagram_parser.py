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

def parse_instagram_reels(query, limit=20):
    """
    Парсит Instagram Reels используя прямой HTTP-запрос.
    Если не получается - переключается на Selenium.
    """
    results = []
    
    # Попытка через прямой HTTP-запрос
    try:
        results = parse_instagram_direct(query, limit)
        if results:
            return results
    except Exception as e:
        print(f"Ошибка при прямом парсинге Instagram: {e}")
    
    # Если прямой запрос не сработал - используем Selenium
    return parse_instagram_selenium(query, limit)

def parse_instagram_direct(query, limit=20):
    """Парсит Instagram Reels напрямую через HTTP-запрос без Selenium"""
    results = []
    
    # Чистим запрос для использования в хэштеге
    clean_tag = query.replace(' ', '').replace('#', '')
    
    # URL для страницы хэштега
    url = f"https://www.instagram.com/explore/tags/{clean_tag}/"
    
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
        cookies_file = os.path.join(os.getcwd(), "cookies", "instagram_cookies.pkl")
        if os.path.exists(cookies_file):
            cookie_jar = pickle.load(open(cookies_file, "rb"))
            for cookie in cookie_jar:
                cookies[cookie['name']] = cookie['value']
    except:
        pass
    
    # Делаем запрос
    response = requests.get(url, headers=headers, cookies=cookies)
    
    if response.status_code == 200:
        # Ищем _sharedData в HTML
        shared_data_match = re.search(r'window\._sharedData = (.+?);</script>', response.text)
        
        if shared_data_match:
            # Извлекаем и парсим JSON
            shared_data = json.loads(shared_data_match.group(1))
            
            # Извлекаем данные о постах
            if 'entry_data' in shared_data and 'TagPage' in shared_data['entry_data']:
                tag_page = shared_data['entry_data']['TagPage'][0]
                if 'graphql' in tag_page and 'hashtag' in tag_page['graphql']:
                    posts = tag_page['graphql']['hashtag']['edge_hashtag_to_media']['edges']
                    
                    for post in posts:
                        node = post['node']
                        
                        # Проверяем, является ли это видео
                        if node.get('is_video', False):
                            shortcode = node.get('shortcode', '')
                            
                            # Собираем данные
                            caption = ""
                            if 'edge_media_to_caption' in node and node['edge_media_to_caption']['edges']:
                                caption = node['edge_media_to_caption']['edges'][0]['node']['text']
                            
                            results.append({
                                "platform": "Instagram Reels",
                                "title": caption[:100] + ('...' if len(caption) > 100 else ''),
                                "url": f"https://www.instagram.com/p/{shortcode}/",
                                "video_id": shortcode,
                                "views": node.get('video_view_count', 'N/A'),
                                "likes": node.get('edge_liked_by', {}).get('count', 0),
                                "comments": node.get('edge_media_to_comment', {}).get('count', 0),
                                "author": node.get('owner', {}).get('username', 'Неизвестно'),
                                "publish_time": "N/A",
                                "query": query,
                                "collected_at": time.strftime('%Y-%m-%d %H:%M:%S')
                            })
                            
                            if len(results) >= limit:
                                break
    
    return results

def parse_instagram_selenium(query, limit=20):
    """Парсит Instagram Reels через Selenium, если прямой запрос не сработал"""
    results = []
    driver = None
    
    try:
        driver = setup_driver()
        if not driver:
            return results
        
        # Загружаем cookies, если есть
        load_cookies(driver, "instagram")
        
        # Формируем URL для поиска
        clean_query = query.replace(' ', '').replace('#', '')
        url = f"https://www.instagram.com/explore/tags/{clean_query}/"
        
        # Открываем страницу
        driver.get(url)
        time.sleep(5)
        
        # Закрываем модальное окно, если появится
        try:
            close_button = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now') or contains(text(), 'Не сейчас')]"))
            )
            close_button.click()
            time.sleep(1)
        except:
            pass
        
        # Минимальный скролл для загрузки контента
        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(2)
        
        # Парсим HTML
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Ищем видео посты
        posts = soup.select("article a")
        
        count = 0
        for post in posts:
            try:
                href = post.get('href', '')
                
                # Проверяем, это Reel или нет
                if '/reel/' in href or '/p/' in href:
                    shortcode = href.split('/')[-2]
                    
                    # Открываем страницу Reel для получения деталей
                    driver.get(f"https://www.instagram.com{href}")
                    time.sleep(3)
                    
                    post_soup = BeautifulSoup(driver.page_source, 'html.parser')
                    
                    # Извлекаем метрики
                    # Просмотры
                    views_elem = post_soup.select_one("span[class*='videoViews']")
                    views = _clean_count(views_elem.text.strip()) if views_elem else "N/A"
                    
                    # Лайки
                    likes_elem = post_soup.select_one("section span[class*='like']")
                    likes = _clean_count(likes_elem.text.strip()) if likes_elem else "N/A"
                    
                    # Описание
                    caption_elem = post_soup.select_one("div[class*='caption'] span")
                    caption = caption_elem.text.strip() if caption_elem else "Без описания"
                    
                    # Автор
                    author_elem = post_soup.select_one("a[class*='profile']")
                    author = author_elem.text.strip() if author_elem else "Неизвестно"
                    
                    results.append({
                        "platform": "Instagram Reels",
                        "title": caption[:100] + ('...' if len(caption) > 100 else ''),
                        "url": f"https://www.instagram.com{href}",
                        "video_id": shortcode,
                        "views": views,
                        "likes": likes,
                        "comments": "N/A",  # Трудно извлечь надежно
                        "author": author,
                        "publish_time": "N/A",
                        "query": query,
                        "collected_at": time.strftime('%Y-%m-%d %H:%M:%S')
                    })
                    
                    count += 1
                    if count >= limit:
                        break
                    
                    # Возвращаемся на страницу поиска
                    driver.get(url)
                    time.sleep(2)
            
            except Exception as e:
                print(f"Ошибка при обработке Instagram поста: {e}")
    
    except Exception as e:
        print(f"Ошибка при парсинге Instagram через Selenium: {e}")
    
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