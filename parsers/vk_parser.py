import time
import re
import json
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

def parse_vk_clips(query, limit=100, days_ago=30, headless=True, wait_time=10, browser_profile=None):
    """
    Парсер VK Клипов с использованием Selenium
    
    Args:
        query (str): Поисковый запрос
        limit (int): Максимальное количество видео для сбора
        days_ago (int): Сбор видео за последние N дней
        headless (bool): Запускать браузер в фоновом режиме
        wait_time (int): Время ожидания загрузки элементов (в секундах)
        browser_profile (str): Путь к профилю браузера (для использования существующих cookies)

    Returns:
        list: Список словарей с данными о видео
    """
    results = []
    collected_video_ids = set()  # Для отслеживания уникальных видео
    cutoff_date = datetime.now() - timedelta(days=days_ago)
    
    print(f"Сбор VK Клипов за последние {days_ago} дней по запросу '{query}'...")

    # Настройка Selenium
    if browser_profile:
        driver = setup_driver_with_profile(browser_profile, headless)
    else:
        # Запрашиваем ручную авторизацию, если профиль не указан
        driver = setup_driver(headless)
    
    if not driver:
        print("Не удалось инициализировать драйвер браузера")
        return results

    try:
        # Переходим на страницу клипов
        driver.get("https://vk.com/clips")
        
        # Проверяем, авторизованы ли мы
        if not is_logged_in(driver):
            print("Вы не авторизованы в VK. Дайте 15 секунд, чтобы войти вручную...")
            time.sleep(15)  # Даем время для ручного входа
            
            # Проверяем еще раз после паузы
            if not is_logged_in(driver):
                print("Авторизация не выполнена. Парсинг может быть ограничен.")
        else:
            print("Авторизация в VK успешна!")
        
        # Ждем загрузки страницы
        time.sleep(3)
        
        # Ищем клипы по запросу
        search_clips(driver, query, wait_time)
        
        # Прокручиваем страницу для загрузки большего количества клипов
        clips_loaded = scroll_for_clips(driver, limit, wait_time)
        
        print(f"Найдено клипов: {clips_loaded}. Извлекаем данные...")

        # Извлекаем данные о клипах
        clips_data = extract_clips_data(driver, limit, query, cutoff_date, collected_video_ids)
        
        # Добавляем полученные данные в результаты
        results.extend(clips_data)
        
        print(f"Собрано {len(results)} VK клипов")
    
    except Exception as e:
        print(f"Ошибка при парсинге VK клипов: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Закрываем браузер
        driver.quit()
    
    # Сортируем результаты по просмотрам (если есть)
    results.sort(key=lambda x: _safe_int(x.get('views', '0').replace(' ', '')), reverse=True)
    
    # Статистика по метрикам
    if results:
        with_likes = len([v for v in results if _safe_int(v.get('likes', '0').replace(' ', '')) > 0])
        with_comments = len([v for v in results if _safe_int(v.get('comments', '0').replace(' ', '')) > 0])
        
        print(f"Статистика метрик: клипы с лайками: {with_likes}/{len(results)}, с комментариями: {with_comments}/{len(results)}")
    
    return results[:limit]

def setup_driver(headless=True):
    """
    Настраивает и возвращает веб-драйвер для Selenium
    
    Args:
        headless (bool): Запускать браузер в фоновом режиме

    Returns:
        WebDriver: Экземпляр веб-драйвера
    """
    try:
        from selenium.webdriver.firefox.options import Options as FirefoxOptions
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        
        # Сначала пробуем Firefox
        try:
            options = FirefoxOptions()
            if headless:
                options.add_argument("--headless")
            
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.set_preference("dom.webdriver.enabled", False)
            options.set_preference("useAutomationExtension", False)
            
            driver = webdriver.Firefox(options=options)
            return driver
        except Exception as e:
            print(f"Не удалось инициализировать Firefox драйвер: {e}")
            
            # Пробуем Chrome
            try:
                options = ChromeOptions()
                if headless:
                    options.add_argument("--headless")
                
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option("useAutomationExtension", False)
                
                driver = webdriver.Chrome(options=options)
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                return driver
            except Exception as e:
                print(f"Не удалось инициализировать Chrome драйвер: {e}")
                return None
    
    except Exception as e:
        print(f"Ошибка при настройке драйвера: {e}")
        return None

def setup_driver_with_profile(profile_path, headless=True):
    """
    Настраивает и возвращает веб-драйвер с использованием существующего профиля браузера
    
    Args:
        profile_path (str): Путь к профилю браузера
        headless (bool): Запускать браузер в фоновом режиме

    Returns:
        WebDriver: Экземпляр веб-драйвера
    """
    try:
        # Определяем, какой это профиль - Firefox или Chrome
        if 'firefox' in profile_path.lower() or 'mozilla' in profile_path.lower():
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            from selenium.webdriver.firefox.service import Service as FirefoxService
            
            options = FirefoxOptions()
            if headless:
                options.add_argument("--headless")
            
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.set_preference("dom.webdriver.enabled", False)
            options.set_preference("useAutomationExtension", False)
            
            # Используем указанный профиль
            options.set_preference("profile", profile_path)
            
            try:
                driver = webdriver.Firefox(options=options)
                return driver
            except Exception as e:
                print(f"Ошибка при запуске Firefox с профилем: {e}")
                return None
        else:
            # Предполагаем, что это профиль Chrome
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.chrome.service import Service as ChromeService
            
            options = ChromeOptions()
            if headless:
                options.add_argument("--headless")
            
            options.add_argument(f"--user-data-dir={profile_path}")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            
            try:
                driver = webdriver.Chrome(options=options)
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                return driver
            except Exception as e:
                print(f"Ошибка при запуске Chrome с профилем: {e}")
                return None
    
    except Exception as e:
        print(f"Ошибка при настройке драйвера с профилем: {e}")
        return None

def is_logged_in(driver, timeout=5):
    """
    Проверяет, авторизован ли пользователь в VK
    
    Args:
        driver: Экземпляр веб-драйвера
        timeout (int): Время ожидания

    Returns:
        bool: True если пользователь авторизован, иначе False
    """
    try:
        # Проверяем наличие элементов, доступных только авторизованным пользователям
        # Например, меню профиля или значок уведомлений
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "top_profile_link"))
        )
        return True
    except:
        try:
            # Альтернативный элемент для проверки
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.ID, "l_pr"))
            )
            return True
        except:
            return False

def search_clips(driver, query, wait_time=10):
    """
    Выполняет поиск клипов по запросу
    
    Args:
        driver: Экземпляр веб-драйвера
        query (str): Поисковый запрос
        wait_time (int): Время ожидания элементов

    Returns:
        bool: True если поиск выполнен успешно, иначе False
    """
    try:
        # Ждем, когда появится поисковая строка
        search_input = WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input.VideoSearchInput__input"))
        )
        
        # Очищаем поисковую строку и вводим запрос
        search_input.clear()
        search_input.send_keys(query)
        search_input.send_keys(Keys.ENTER)
        
        # Ждем загрузки результатов
        time.sleep(3)
        
        print(f"Поиск клипов по запросу '{query}' выполнен")
        return True
    
    except Exception as e:
        print(f"Ошибка при поиске клипов: {e}")
        return False

def scroll_for_clips(driver, limit, wait_time=10):
    """
    Прокручивает страницу для загрузки большего количества клипов
    
    Args:
        driver: Экземпляр веб-драйвера
        limit (int): Максимальное количество клипов для загрузки
        wait_time (int): Время ожидания элементов

    Returns:
        int: Количество загруженных клипов
    """
    try:
        scroll_count = 0
        max_scrolls = 30  # Ограничение на количество прокруток
        
        # Находим контейнер с клипами
        clips_container = WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.VideoHighlights__list"))
        )
        
        # Функция для получения текущего количества клипов
        def get_clips_count():
            clips = driver.find_elements(By.CSS_SELECTOR, "div.VideoHighlights__item")
            return len(clips)
        
        # Начальное количество клипов
        current_clips = get_clips_count()
        
        print(f"Начальное количество клипов: {current_clips}")
        
        # Прокручиваем страницу, пока не загрузим достаточное количество клипов или не достигнем ограничения
        while current_clips < limit and scroll_count < max_scrolls:
            # Прокручиваем к последнему клипу
            driver.execute_script("arguments[0].scrollIntoView(false);", clips_container)
            driver.execute_script("window.scrollBy(0, 500);")
            
            # Ждем загрузки новых клипов
            time.sleep(2)
            
            # Проверяем, загрузились ли новые клипы
            new_clips_count = get_clips_count()
            
            if new_clips_count > current_clips:
                print(f"Загружено {new_clips_count} клипов")
                current_clips = new_clips_count
            else:
                # Если количество не изменилось, делаем еще одну прокрутку
                driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(2)
                
                # Проверяем еще раз
                new_clips_count = get_clips_count()
                if new_clips_count == current_clips:
                    scroll_count += 1
                else:
                    current_clips = new_clips_count
                    print(f"Загружено {current_clips} клипов")
            
            scroll_count += 1
        
        print(f"Всего загружено {current_clips} клипов после {scroll_count} прокруток")
        return current_clips
    
    except Exception as e:
        print(f"Ошибка при прокрутке страницы: {e}")
        return 0

def extract_clips_data(driver, limit, query, cutoff_date, collected_video_ids):
    """
    Извлекает данные о клипах со страницы
    
    Args:
        driver: Экземпляр веб-драйвера
        limit (int): Максимальное количество клипов для извлечения
        query (str): Поисковый запрос
        cutoff_date (datetime): Дата отсечки для фильтрации по времени
        collected_video_ids (set): Множество уже собранных ID видео

    Returns:
        list: Список словарей с данными о клипах
    """
    results = []
    
    try:
        # Находим все клипы на странице
        clips = driver.find_elements(By.CSS_SELECTOR, "div.VideoHighlights__item")
        
        print(f"Найдено {len(clips)} клипов для извлечения данных")
        
        for i, clip in enumerate(clips):
            if len(results) >= limit:
                break
            
            try:
                # Извлекаем URL и ID видео
                video_link_element = clip.find_element(By.CSS_SELECTOR, "a.VideoHighlightsItem__link")
                video_url = video_link_element.get_attribute("href")
                video_id = extract_video_id_from_url(video_url)
                
                if not video_id or video_id in collected_video_ids:
                    continue
                
                # Извлекаем заголовок видео
                try:
                    title_element = clip.find_element(By.CSS_SELECTOR, "div.VideoHighlightsItem__description")
                    title = title_element.text
                except:
                    title = "Без названия"
                
                # Извлекаем количество просмотров
                try:
                    views_element = clip.find_element(By.CSS_SELECTOR, "div.VideoHighlightsItem__views")
                    views = views_element.text.replace("просмотров", "").replace("просмотра", "").strip()
                except:
                    views = "0"
                
                # Извлекаем имя канала
                try:
                    channel_element = clip.find_element(By.CSS_SELECTOR, "div.VideoHighlightsItem__author")
                    channel = channel_element.text
                except:
                    channel = "Неизвестный автор"
                
                # Извлекаем дату публикации (если возможно)
                publish_date, days_ago_value = extract_publish_date(clip)
                
                # Проверяем, соответствует ли видео фильтру по дате
                if isinstance(days_ago_value, int) and days_ago_value > cutoff_date.days:
                    print(f"Пропуск видео {video_id} - слишком старое ({days_ago_value} дней)")
                    continue
                
                # Для получения дополнительных метрик (лайки, комментарии) нужно открыть страницу видео
                # В данном случае мы упрощаем и устанавливаем приблизительные значения
                
                # Собираем данные о видео
                video_data = {
                    'platform': 'VK Клипы',
                    'title': title,
                    'url': video_url,
                    'video_id': video_id,
                    'views': views,
                    'likes': '0',  # Требуется дополнительный запрос
                    'comments': '0',  # Требуется дополнительный запрос
                    'shares': '0',  # Требуется дополнительный запрос
                    'publish_time': publish_date,
                    'publish_date_formatted': publish_date,
                    'days_ago': days_ago_value,
                    'channel': channel,
                    'query': query,
                    'collected_at': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Добавляем ID в множество собранных
                collected_video_ids.add(video_id)
                
                # Добавляем данные в результаты
                results.append(video_data)
                
                if (i + 1) % 10 == 0:
                    print(f"Обработано {i+1}/{len(clips)} клипов")
            
            except Exception as e:
                print(f"Ошибка при извлечении данных о клипе {i}: {e}")
                continue
    
    except Exception as e:
        print(f"Ошибка при извлечении данных о клипах: {e}")
    
    return results

def extract_video_id_from_url(url):
    """
    Извлекает ID видео из URL
    
    Args:
        url (str): URL видео

    Returns:
        str: ID видео или None, если не удалось извлечь
    """
    try:
        # Паттерны для разных форматов URL
        patterns = [
            r'clips/(-?\d+_\d+)',  # Формат clips/{owner_id}_{video_id}
            r'video(-?\d+_\d+)',   # Формат video{owner_id}_{video_id}
            r'wall(-?\d+_\d+)',    # Формат wall{owner_id}_{post_id}
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    except Exception:
        return None

def extract_publish_date(clip_element):
    """
    Извлекает дату публикации из элемента клипа
    
    Args:
        clip_element: Элемент клипа

    Returns:
        tuple: (formatted_date, days_ago)
    """
    try:
        # Пытаемся найти элемент с датой
        date_element = clip_element.find_element(By.CSS_SELECTOR, "div.VideoHighlightsItem__date")
        date_text = date_element.text.strip().lower()
        
        now = datetime.now()
        
        # Обрабатываем различные форматы даты
        if "сегодня" in date_text:
            return now.strftime("%Y-%m-%d"), 0
        
        elif "вчера" in date_text:
            yesterday = now - timedelta(days=1)
            return yesterday.strftime("%Y-%m-%d"), 1
        
        elif "неделю назад" in date_text or "неделя назад" in date_text:
            date = now - timedelta(days=7)
            return date.strftime("%Y-%m-%d"), 7
        
        elif "месяц назад" in date_text:
            date = now - timedelta(days=30)
            return date.strftime("%Y-%m-%d"), 30
        
        elif "месяца назад" in date_text:
            # Извлекаем число месяцев
            months = re.search(r'(\d+)\s+месяц', date_text)
            if months:
                months_count = int(months.group(1))
                date = now - timedelta(days=30 * months_count)
                return date.strftime("%Y-%m-%d"), 30 * months_count
            else:
                date = now - timedelta(days=60)
                return date.strftime("%Y-%m-%d"), 60
        
        elif "год назад" in date_text:
            date = now - timedelta(days=365)
            return date.strftime("%Y-%m-%d"), 365
        
        else:
            # Пытаемся распарсить дату
            try:
                # Формат "дд.мм.гггг"
                date_match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', date_text)
                if date_match:
                    day, month, year = map(int, date_match.groups())
                    date = datetime(year, month, day)
                    days_ago = (now - date).days
                    return date.strftime("%Y-%m-%d"), days_ago
                
                # Формат "дд месяц гггг"
                months = {
                    'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4, 'май': 5, 'июн': 6,
                    'июл': 7, 'авг': 8, 'сен': 9, 'окт': 10, 'ноя': 11, 'дек': 12
                }
                
                for month_name, month_num in months.items():
                    if month_name in date_text:
                        date_match = re.search(r'(\d{1,2})\s+\w+\s+(\d{4})', date_text)
                        if date_match:
                            day, year = map(int, date_match.groups())
                            date = datetime(year, month_num, day)
                            days_ago = (now - date).days
                            return date.strftime("%Y-%m-%d"), days_ago
            except:
                pass
    
    except:
        pass
    
    # Если не удалось определить дату
    return "Неизвестно", "Неизвестно"

def _safe_int(value):
    """Безопасно преобразует значение в целое число"""
    if value is None:
        return 0
    
    try:
        # Удаляем все нечисловые символы, кроме цифр
        value_str = ''.join(c for c in str(value) if c.isdigit())
        if value_str:
            return int(value_str)
        return 0
    except (ValueError, TypeError):
        return 0

# Пример использования
if __name__ == "__main__":
    query = "смешные коты"
    
    # Вы можете указать путь к профилю браузера
    # Firefox: обычно это папка в ~/.mozilla/firefox/
    # Chrome: обычно это ~/.config/google-chrome/ на Linux или C:\Users\Username\AppData\Local\Google\Chrome\User Data на Windows
    # browser_profile = "C:\\Users\\Username\\AppData\\Local\\Google\\Chrome\\User Data\\Default"
    
    clips = parse_vk_clips(query, limit=20, days_ago=30, headless=False)
    for clip in clips[:5]:  # Выводим первые 5 для примера
        print(f"Title: {clip['title']}, Views: {clip['views']}, Channel: {clip['channel']}, URL: {clip['url']}")