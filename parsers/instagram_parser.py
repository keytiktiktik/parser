import requests
import json
import re
import time
from bs4 import BeautifulSoup
from requests_html import HTMLSession
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.browser import setup_driver

def parse_instagram_reels(query, limit=20):
    """
    Парсит Instagram Reels по заданному запросу
    
    Args:
        query (str): Поисковый запрос (хэштег)
        limit (int): Максимальное количество видео для сбора
        
    Returns:
        list: Список словарей с данными о видео
    """
    results = []
    
    # Пробуем через requests-html
    try:
        session = HTMLSession()
        
        # Формируем URL для поиска по хэштегу
        clean_query = query.replace(' ', '').replace('#', '')
        url = f"https://www.instagram.com/explore/tags/{clean_query}/"
        
        # Установка заголовков для имитации браузера
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        r = session.get(url, headers=headers)
        r.html.render(sleep=5, timeout=30)  # Ждем загрузку JS-контента
        
        # Ищем данные в скриптах
        for script in r.html.find('script'):
            if 'window._sharedData' in script.text:
                data_str = script.text.split('window._sharedData = ')[1].split(';</script>')[0]
                data = json.loads(data_str)
                
                # Извлекаем данные о постах
                if 'entry_data' in data and 'TagPage' in data['entry_data']:
                    tag_page = data['entry_data']['TagPage'][0]
                    if 'graphql' in tag_page and 'hashtag' in tag_page['graphql']:
                        posts = tag_page['graphql']['hashtag']['edge_hashtag_to_media']['edges']
                        
                        count = 0
                        for post in posts:
                            node = post['node']
                            
                            # Проверяем, является ли это видео
                            if node.get('is_video', False):
                                shortcode = node.get('shortcode', '')
                                if not shortcode:
                                    continue
                                
                                # Получаем детальную информацию о Reel
                                reel_details = _get_instagram_reel_details(shortcode)
                                
                                results.append({
                                    "platform": "Instagram Reels",
                                    "title": reel_details.get("caption", "Без описания"),
                                    "url": f"https://www.instagram.com/reel/{shortcode}/",
                                    "video_id": shortcode,
                                    "views": reel_details.get("views", "N/A"),
                                    "likes": reel_details.get("likes", node.get('edge_liked_by', {}).get('count', 0)),
                                    "comments": reel_details.get("comments", node.get('edge_media_to_comment', {}).get('count', 0)),
                                    "author": reel_details.get("author", "Неизвестно"),
                                    "publish_time": reel_details.get("publish_time", "N/A"),
                                    "query": query,
                                    "collected_at": time.strftime('%Y-%m-%d %H:%M:%S')
                                })
                                
                                count += 1
                                if count >= limit:
                                    break
                
                break  # Выход из цикла по скриптам
        
        session.close()
    
    except Exception as e:
        print(f"Ошибка при парсинге Instagram Reels через requests-html: {e}")
    
    # Если не удалось через requests-html, пробуем через Selenium
    if not results:
        driver = None
        try:
            driver = setup_driver()
            
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
            
            # Скроллим для загрузки контента
            for _ in range(3):
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
                            "title": caption,
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
                
                except Exception as e:
                    print(f"Ошибка при обработке Instagram поста: {e}")
        
        except Exception as e:
            print(f"Ошибка при парсинге Instagram через Selenium: {e}")
        
        finally:
            if driver:
                driver.quit()
    
    return results[:limit]

def _get_instagram_reel_details(shortcode):
    """
    Получает детальную информацию о Reel по его shortcode
    
    Args:
        shortcode (str): Код поста
        
    Returns:
        dict: Словарь с деталями о Reel
    """
    details = {"views": "N/A", "likes": "N/A", "comments": "N/A", "caption": "Без описания", "author": "Неизвестно", "publish_time": "N/A"}
    
    try:
        url = f"https://www.instagram.com/reel/{shortcode}/"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        session = HTMLSession()
        r = session.get(url, headers=headers)
        r.html.render(sleep=3)
        
        # Поиск данных в HTML
        soup = BeautifulSoup(r.html.html, 'html.parser')
        
        # Просмотры
        views_elem = soup.select_one("span[class*='videoViews']")
        if views_elem:
            details["views"] = _clean_count(views_elem.text.strip())
        
        # Лайки
        likes_elem = soup.select_one("[class*='like'] span")
        if likes_elem:
            details["likes"] = _clean_count(likes_elem.text.strip())
        
        # Комментарии
        comments_elem = soup.select_one("[class*='comment'] span")
        if comments_elem:
            details["comments"] = _clean_count(comments_elem.text.strip())
        
        # Описание
        caption_elem = soup.select_one("div[class*='caption'] span")
        if caption_elem:
            details["caption"] = caption_elem.text.strip()
        
        # Автор
        author_elem = soup.select_one("a[class*='profile'] span")
        if author_elem:
            details["author"] = author_elem.text.strip()
        
        # Дата публикации
        time_elem = soup.select_one("time")
        if time_elem and time_elem.has_attr('datetime'):
            details["publish_time"] = time_elem['datetime'][:10]  # Берем только дату
        
        session.close()
    
    except Exception as e:
        print(f"Ошибка при получении деталей для Instagram Reel {shortcode}: {e}")
    
    return details

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