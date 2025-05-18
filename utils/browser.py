import random
import time
import os
import pickle
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

def setup_driver(headless=True):
    """
    Настраивает и возвращает экземпляр веб-драйвера Firefox
    
    Args:
        headless (bool): Запускать браузер в фоновом режиме без UI
        
    Returns:
        WebDriver: Экземпляр веб-драйвера или None в случае ошибки
    """
    # Список user-agent для имитации разных браузеров
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0'
    ]
    
    try:
        # Настройка опций Firefox
        options = Options()
        options.set_preference("general.useragent.override", random.choice(user_agents))
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        
        # Фоновый режим (без интерфейса)
        if headless:
            options.add_argument("--headless")
        
        # Путь к geckodriver
        gecko_path = "./geckodriver.exe"  # Или "geckodriver" для Linux/Mac
        
        # Инициализация драйвера
        service = Service(executable_path=gecko_path)
        driver = webdriver.Firefox(service=service, options=options)
        
        return driver
    except Exception as e:
        print(f"Ошибка при настройке драйвера Firefox: {e}")
        return None

def save_cookies(driver, platform):
    """
    Сохраняет cookies после авторизации на платформе
    
    Args:
        driver: WebDriver экземпляр
        platform (str): Название платформы (youtube, tiktok, instagram, vk)
    """
    cookies_dir = os.path.join(os.getcwd(), "cookies")
    os.makedirs(cookies_dir, exist_ok=True)
    
    cookies_file = os.path.join(cookies_dir, f"{platform}_cookies.pkl")
    pickle.dump(driver.get_cookies(), open(cookies_file, "wb"))
    print(f"Cookies для {platform} сохранены")

def load_cookies(driver, platform):
    """
    Загружает сохраненные cookies для платформы
    
    Args:
        driver: WebDriver экземпляр
        platform (str): Название платформы (youtube, tiktok, instagram, vk)
        
    Returns:
        bool: True если cookies были загружены, иначе False
    """
    cookies_file = os.path.join(os.getcwd(), "cookies", f"{platform}_cookies.pkl")
    
    if os.path.exists(cookies_file):
        cookies = pickle.load(open(cookies_file, "rb"))
        # Сначала переходим на домен
        domain_urls = {
            "youtube": "https://www.youtube.com",
            "tiktok": "https://www.tiktok.com",
            "instagram": "https://www.instagram.com",
            "vk": "https://vk.com"
        }
        
        driver.get(domain_urls.get(platform, "https://www.google.com"))
        
        # Загружаем cookies
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except:
                pass
                
        print(f"Cookies для {platform} загружены")
        return True
    return False

def human_like_scroll(driver, scroll_count=5):
    """
    Имитирует человеческое поведение при прокрутке страницы
    
    Args:
        driver: WebDriver экземпляр
        scroll_count (int): Количество прокруток
    """
    for i in range(scroll_count):
        # Прокрутка с различной скоростью
        scroll_amount = random.randint(300, 1000)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        
        # Случайная пауза
        time.sleep(random.uniform(0.5, 2.0))
        
        # Иногда делаем короткую остановку
        if random.random() < 0.3:
            time.sleep(random.uniform(1.0, 3.0))