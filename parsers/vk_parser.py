import requests
import json
import re
import time
from bs4 import BeautifulSoup
from utils.browser import setup_driver

def parse_vk_clips(query, limit=20):
    """
    Парсит ВК Клипы по заданному запросу
    
    Args:
        query (str): Поисковый запрос
        limit (int): Максимальное количество видео для сбора
        
    Returns:
        list: Список словарей с данными о видео
    """
    results = []
    
    # Прямой доступ через requests
    try:
        url = f"https://vk.com/clips?q={query.replace(' ', '%20')}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            # Ищем JSON-данные в исходном коде страницы
            catalog_match = re.search(r'clips_catalog_data\s*:\s*({.+?}),\s*clips_draft_data', response.text)
            if catalog_match:
                try:
                    catalog_data = json.loads(catalog_match.group(1))
                    
                    if 'clips' in catalog_data:
                        for clip in catalog_data['clips'][:limit]:
                            clip_id = clip.get('id', '')
                            owner_id = clip.get('owner_id', '')
                            
                            # Формируем URL клипа
                            clip_url = f"https://vk.com/clip{owner_id}_{clip_id}"
                            
                            # Извлекаем метрики
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
                
                except json.JSONDecodeError as e:
                    print(f"Ошибка при парсинге JSON данных ВК: {e}")
            
            # Если не удалось извлечь данные из JSON, пробуем через HTML
            if not results:
                soup = BeautifulSoup(response.text, 'html.parser')
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
                    
                    except Exception as e:
                        print(f"Ошибка при обработке клипа ВК: {e}")
    
    except Exception as e:
        print(f"Ошибка при парсинге ВК Клипов через requests: {e}")
    
    # Если не удалось получить данные через requests, используем Selenium
    if not results:
        driver = None
        try:
            driver = setup_driver()
            
            # Открываем страницу поиска
            driver.get(f"https://vk.com/clips?q={query.replace(' ', '%20')}")
            time.sleep(5)
            
            # Скроллим для загрузки контента
            for _ in range(3):
                driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(2)
            
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
                    
                    # Получаем дополнительные данные, открыв страницу клипа
                    additional_data = _get_vk_clip_details(driver, url)
                    
                    results.append({
                        "platform": "ВК Клипы",
                        "title": title,
                        "url": url,
                        "video_id": clip_id,
                        "views": _clean_count(views),
                        "likes": _clean_count(likes),
                        "comments": additional_data.get("comments", "N/A"),
                        "shares": additional_data.get("shares", "N/A"),
                        "author": author,
                        "publish_time": additional_data.get("publish_time", "N/A"),
                        "query": query,
                        "collected_at": time.strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                except Exception as e:
                    print(f"Ошибка при обработке клипа ВК через Selenium: {e}")
        
        except Exception as e:
            print(f"Ошибка при парсинге ВК Клипов через Selenium: {e}")
        
        finally:
            if driver:
                driver.quit()
    
    return results[:limit]

def _get_vk_clip_details(driver, url):
    """
    Получает дополнительные данные о клипе ВК
    
    Args:
        driver: Selenium WebDriver
        url (str): URL клипа
        
    Returns:
        dict: Словарь с дополнительными данными
    """
    details = {"comments": "N/A", "shares": "N/A", "publish_time": "N/A"}
    
    try:
        # Открываем страницу клипа
        driver.get(url)
        time.sleep(3)
        
        # Парсим HTML
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Комментарии
        comments_elem = soup.select_one(".comments_count")
        if comments_elem:
            details["comments"] = _clean_count(comments_elem.text.strip())
        
        # Репосты
        shares_elem = soup.select_one(".share_count")
        if shares_elem:
            details["shares"] = _clean_count(shares_elem.text.strip())
        
        # Дата публикации
        time_elem = soup.select_one(".clips_video_info_date")
        if time_elem:
            details["publish_time"] = time_elem.text.strip()
    
    except Exception as e:
        print(f"Ошибка при получении деталей для клипа ВК {url}: {e}")
    
    return details

def _clean_count(count_str):
    """
    Преобразует строку с числом (например, "1.5K" или "1,5К") в строку с числом
    
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