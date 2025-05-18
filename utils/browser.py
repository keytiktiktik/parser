from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import random
import time

def setup_driver():
    """
    Настраивает и возвращает экземпляр веб-драйвера Chrome
    
    Returns:
        WebDriver: Настроенный экземпляр веб-драйвера
    """
    # Список user-agent для имитации разных браузеров
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36 Edg/96.0.1054.53'
    ]
    
    # Настройка опций
    options = Options()
    options.add_argument(f"--user-agent={random.choice(user_agents)}")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # В некоторых случаях headless режим может быть обнаружен
    # options.add_argument("--headless")
    
    # Инициализация сервиса и драйвера
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    # Обход обнаружения веб-драйвера
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def human_like_scroll(driver, scroll_count=5):
    """
    Имитирует человеческое поведение при прокрутке страницы
    
    Args:
        driver: Selenium WebDriver
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