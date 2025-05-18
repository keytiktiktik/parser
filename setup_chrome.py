import os
import sys
import re
import subprocess
import winreg
import requests
import zipfile
import shutil
import platform
from pathlib import Path
from tqdm import tqdm

def check_firefox_installed():
    """Проверяет, установлен ли Firefox и возвращает его версию"""
    try:
        # Проверяем через реестр Windows
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Mozilla\Mozilla Firefox") as key:
            version = winreg.QueryValue(key, None)
            if version:
                return True, version.split(' ')[0]
    except (FileNotFoundError, PermissionError, WindowsError):
        pass
    
    # Альтернативный способ поиска Firefox
    possible_paths = [
        os.path.expandvars(r"%ProgramFiles%\Mozilla Firefox\firefox.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                result = subprocess.run([path, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                version_match = re.search(r'Mozilla Firefox\s+(\d+\.\d+)', result.stdout)
                if version_match:
                    return True, version_match.group(1)
                return True, None
            except:
                return True, None
    
    return False, None

def download_firefox():
    """Скачивает и устанавливает Firefox"""
    print("Скачиваю Mozilla Firefox...")
    
    # URL для скачивания Firefox
    firefox_url = "https://download.mozilla.org/?product=firefox-latest&os=win64&lang=ru"
    installer_path = os.path.join(os.getcwd(), "firefox_installer.exe")
    
    # Скачиваем файл с прогресс-баром
    response = requests.get(firefox_url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(installer_path, 'wb') as f, tqdm(
        desc="Скачивание Firefox",
        total=total_size,
        unit='B',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in response.iter_content(chunk_size=1024):
            size = f.write(data)
            bar.update(size)
    
    print("Установка Firefox...")
    
    # Запускаем установщик
    try:
        subprocess.run([installer_path, '-ms'], check=True)
        print("Mozilla Firefox успешно установлен!")
    except subprocess.SubprocessError as e:
        print(f"Ошибка при установке Firefox: {e}")
        print("Пожалуйста, установите Firefox вручную: https://www.mozilla.org/firefox/")
    
    # Удаляем установщик
    try:
        os.remove(installer_path)
    except:
        pass

def get_geckodriver_url():
    """Получает URL для скачивания последней версии geckodriver"""
    # Получаем информацию о последней версии
    releases_url = "https://api.github.com/repos/mozilla/geckodriver/releases/latest"
    response = requests.get(releases_url)
    release_data = response.json()
    
    version = release_data['tag_name']
    print(f"Последняя версия geckodriver: {version}")
    
    # Определяем ОС и архитектуру
    is_64bits = platform.machine().endswith('64')
    if sys.platform.startswith('win'):
        platform_name = "win64" if is_64bits else "win32"
    elif sys.platform.startswith('linux'):
        platform_name = "linux64" if is_64bits else "linux32"
    elif sys.platform.startswith('darwin'):
        platform_name = "macos"
    else:
        raise Exception(f"Неподдерживаемая платформа: {sys.platform}")
    
    # Находим подходящий архив
    for asset in release_data['assets']:
        if platform_name in asset['name'] and asset['name'].endswith('.zip'):
            return asset['browser_download_url']
    
    raise Exception(f"Не найден подходящий geckodriver для {platform_name}")

def download_geckodriver():
    """Скачивает подходящую версию geckodriver"""
    print("Скачиваю geckodriver...")
    
    try:
        download_url = get_geckodriver_url()
        print(f"URL для скачивания: {download_url}")
        
        zip_path = os.path.join(os.getcwd(), "geckodriver.zip")
        
        # Скачиваем файл с прогресс-баром
        response = requests.get(download_url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        with open(zip_path, 'wb') as f, tqdm(
            desc="Скачивание geckodriver",
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for data in response.iter_content(chunk_size=1024):
                size = f.write(data)
                bar.update(size)
        
        # Распаковываем архив
        extract_dir = os.path.join(os.getcwd(), "temp_geckodriver")
        os.makedirs(extract_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Находим geckodriver.exe в распакованных файлах
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.startswith('geckodriver'):
                    source_path = os.path.join(root, file)
                    dest_path = os.path.join(os.getcwd(), file)
                    shutil.copy2(source_path, dest_path)
                    print(f"Geckodriver успешно установлен: {dest_path}")
        
        # Очистка
        shutil.rmtree(extract_dir, ignore_errors=True)
        os.remove(zip_path)
        
    except Exception as e:
        print(f"Ошибка при скачивании geckodriver: {e}")
        print("Пожалуйста, скачайте geckodriver вручную: https://github.com/mozilla/geckodriver/releases")

def update_project_code():
    """Обновляет код проекта для использования Firefox вместо Chrome"""
    print("Обновляю код проекта для использования Firefox...")
    
    # Путь к файлу browser.py
    browser_path = os.path.join(os.getcwd(), "utils", "browser.py")
    
    if os.path.exists(browser_path):
        with open(browser_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Модифицируем код для использования Firefox
        updated_content = """import random
import time
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

def setup_driver():
    \"\"\"
    Настраивает и возвращает экземпляр веб-драйвера Firefox
    \"\"\"
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
        
        # Путь к geckodriver
        gecko_path = "./geckodriver.exe"  # Или "geckodriver" для Linux/Mac
        
        # Инициализация драйвера
        service = Service(executable_path=gecko_path)
        driver = webdriver.Firefox(service=service, options=options)
        
        return driver
    except Exception as e:
        print(f"Ошибка при настройке драйвера Firefox: {e}")
        return None

def human_like_scroll(driver, scroll_count=5):
    \"\"\"
    Имитирует человеческое поведение при прокрутке страницы
    \"\"\"
    for i in range(scroll_count):
        # Прокрутка с различной скоростью
        scroll_amount = random.randint(300, 1000)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        
        # Случайная пауза
        time.sleep(random.uniform(0.5, 2.0))
        
        # Иногда делаем короткую остановку
        if random.random() < 0.3:
            time.sleep(random.uniform(1.0, 3.0))
"""
        
        # Записываем обновленный код
        with open(browser_path, 'w', encoding='utf-8') as file:
            file.write(updated_content)
        
        print("Файл utils/browser.py успешно обновлен для работы с Firefox!")
    else:
        print(f"Файл {browser_path} не найден. Убедитесь, что вы запускаете скрипт из корневой папки проекта.")

def main():
    print("=== Установка Firefox и geckodriver ===")
    
    # Проверяем наличие Firefox
    is_firefox_installed, firefox_version = check_firefox_installed()
    
    if not is_firefox_installed:
        print("Mozilla Firefox не найден. Начинаю установку...")
        download_firefox()
        
        # Проверяем еще раз после установки
        is_firefox_installed, firefox_version = check_firefox_installed()
    
    if is_firefox_installed:
        if firefox_version:
            print(f"Mozilla Firefox установлен. Версия: {firefox_version}")
        else:
            print("Mozilla Firefox установлен, но не удалось определить версию.")
            
        # Скачиваем geckodriver
        download_geckodriver()
        
        # Обновляем код проекта
        update_project_code()
    else:
        print("Не удалось установить или найти Mozilla Firefox.")
        print("Пожалуйста, установите Firefox вручную: https://www.mozilla.org/firefox/")

if __name__ == "__main__":
    # Запрос прав администратора для установки Firefox
    if sys.platform.startswith('win'):
        try:
            # Если скрипт уже запущен с правами администратора
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                print("Для установки Firefox требуются права администратора.")
                print("Пожалуйста, запустите этот скрипт с правами администратора.")
                input("Нажмите Enter для выхода...")
                sys.exit(1)
        except:
            pass
    
    main()
    print("\nУстановка завершена. Firefox и geckodriver установлены и настроены.")
    print("Теперь ваш парсер будет использовать Firefox вместо Chrome.")
    input("Нажмите Enter для выхода...")