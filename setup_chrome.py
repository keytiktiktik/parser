#!/usr/bin/env python3
import os
import sys
import re
import subprocess
import requests
import zipfile
import shutil
import platform
from pathlib import Path
from tqdm import tqdm

def check_firefox_installed():
    """Проверяет, установлен ли Firefox и возвращает его версию"""
    try:
        # Проверяем через which
        result = subprocess.run(['which', 'firefox'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            # Пытаемся получить версию
            firefox_path = result.stdout.strip()
            version_result = subprocess.run([firefox_path, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if version_result.returncode == 0:
                version_match = re.search(r'Mozilla Firefox\s+(\d+\.\d+)', version_result.stdout)
                if version_match:
                    return True, version_match.group(1)
                return True, None
    except:
        pass
    
    # Проверяем через Applications
    applications_path = "/Applications/Firefox.app/Contents/MacOS/firefox"
    if os.path.exists(applications_path):
        try:
            version_result = subprocess.run([applications_path, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if version_result.returncode == 0:
                version_match = re.search(r'Mozilla Firefox\s+(\d+\.\d+)', version_result.stdout)
                if version_match:
                    return True, version_match.group(1)
                return True, None
        except:
            return True, None
    
    return False, None

def install_firefox_with_brew():
    """Устанавливает Firefox с помощью Homebrew"""
    print("Проверяю наличие Homebrew...")
    
    # Проверяем установлен ли Homebrew
    try:
        result = subprocess.run(['which', 'brew'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print("Homebrew не установлен. Устанавливаю Homebrew...")
            install_command = '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
            subprocess.run(install_command, shell=True, check=True)
        
        # Устанавливаем Firefox
        print("Устанавливаю Firefox с помощью Homebrew...")
        subprocess.run(['brew', 'install', '--cask', 'firefox'], check=True)
        print("Firefox успешно установлен!")
        return True
    except subprocess.SubprocessError as e:
        print(f"Ошибка при установке Firefox: {e}")
        print("Пожалуйста, установите Firefox вручную с сайта https://www.mozilla.org/firefox/")
        return False

def download_firefox_manually():
    """Скачивает Firefox вручную, если Homebrew не доступен"""
    print("Скачиваю Firefox вручную...")
    
    # URL для скачивания Firefox
    firefox_url = "https://download.mozilla.org/?product=firefox-latest&os=osx&lang=ru"
    dmg_path = os.path.join(os.getcwd(), "firefox.dmg")
    
    # Скачиваем файл с прогресс-баром
    response = requests.get(firefox_url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(dmg_path, 'wb') as f, tqdm(
        desc="Скачивание Firefox",
        total=total_size,
        unit='B',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in response.iter_content(chunk_size=1024):
            size = f.write(data)
            bar.update(size)
    
    print("Firefox скачан. Пожалуйста, откройте dmg-файл и перетащите Firefox в папку Applications.")
    print(f"Путь к dmg-файлу: {dmg_path}")
    
    # Открываем Finder с dmg-файлом
    subprocess.run(['open', dmg_path])
    
    input("После установки Firefox нажмите Enter для продолжения...")

def get_geckodriver_url():
    """Получает URL для скачивания последней версии geckodriver для macOS"""
    # Получаем информацию о последней версии
    releases_url = "https://api.github.com/repos/mozilla/geckodriver/releases/latest"
    response = requests.get(releases_url)
    release_data = response.json()
    
    version = release_data['tag_name']
    print(f"Последняя версия geckodriver: {version}")
    
    # Определяем архитектуру процессора
    is_arm = platform.machine() == 'arm64' or platform.machine() == 'aarch64'
    
    # В версиях до v0.34.0 нет отдельных бинарников для ARM
    use_intel_binary = False
    version_num = version[1:].split('.')  # Удаляем 'v' и разбиваем на части
    if len(version_num) >= 2 and (int(version_num[0]) < 0 or (int(version_num[0]) == 0 and int(version_num[1]) < 34)):
        use_intel_binary = True
    
    # Определяем правильный архив в зависимости от архитектуры
    if is_arm and not use_intel_binary:
        platform_name = "macos-aarch64"
    else:
        platform_name = "macos"
    
    # Находим подходящий архив
    for asset in release_data['assets']:
        if platform_name in asset['name'] and asset['name'].endswith('.tar.gz'):
            return asset['browser_download_url']
        # Запасной вариант, если нет tar.gz
        elif platform_name in asset['name'] and asset['name'].endswith('.zip'):
            return asset['browser_download_url']
    
    # Если не найдено для конкретной архитектуры, ищем общий для macOS
    for asset in release_data['assets']:
        if "macos" in asset['name'] and asset['name'].endswith('.tar.gz'):
            return asset['browser_download_url']
        elif "macos" in asset['name'] and asset['name'].endswith('.zip'):
            return asset['browser_download_url']
    
    raise Exception(f"Не найден подходящий geckodriver для macOS")

def download_geckodriver():
    """Скачивает подходящую версию geckodriver"""
    print("Скачиваю geckodriver...")
    
    try:
        download_url = get_geckodriver_url()
        print(f"URL для скачивания: {download_url}")
        
        is_tar_gz = download_url.endswith('.tar.gz')
        if is_tar_gz:
            archive_path = os.path.join(os.getcwd(), "geckodriver.tar.gz")
        else:
            archive_path = os.path.join(os.getcwd(), "geckodriver.zip")
        
        # Скачиваем файл с прогресс-баром
        response = requests.get(download_url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        with open(archive_path, 'wb') as f, tqdm(
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
        
        if is_tar_gz:
            import tarfile
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(extract_dir)
        else:
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
        
        # Находим geckodriver в распакованных файлах
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.startswith('geckodriver'):
                    source_path = os.path.join(root, file)
                    dest_path = os.path.join(os.getcwd(), "geckodriver")
                    shutil.copy2(source_path, dest_path)
                    
                    # Делаем файл исполняемым
                    os.chmod(dest_path, 0o755)
                    
                    print(f"Geckodriver успешно установлен: {dest_path}")
                    
                    # Очистка
                    shutil.rmtree(extract_dir, ignore_errors=True)
                    os.remove(archive_path)
                    
                    return True
        
        print("Geckodriver не найден в архиве.")
        return False
        
    except Exception as e:
        print(f"Ошибка при скачивании geckodriver: {e}")
        print("Пожалуйста, скачайте geckodriver вручную: https://github.com/mozilla/geckodriver/releases")
        return False

def update_project_code():
    """Обновляет код проекта для использования Firefox на macOS"""
    print("Обновляю код проекта для использования Firefox на macOS...")
    
    # Путь к файлу browser.py
    browser_path = os.path.join(os.getcwd(), "utils", "browser.py")
    
    if os.path.exists(browser_path):
        with open(browser_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Модифицируем путь к geckodriver для macOS
        updated_content = content.replace('gecko_path = "./geckodriver.exe"', 'gecko_path = "./geckodriver"')
        
        # Записываем обновленный код
        with open(browser_path, 'w', encoding='utf-8') as file:
            file.write(updated_content)
        
        print("Файл utils/browser.py успешно обновлен для работы с macOS!")
    else:
        print(f"Файл {browser_path} не найден. Убедитесь, что вы запускаете скрипт из корневой папки проекта.")

def main():
    print("=== Установка Firefox и geckodriver для macOS ===")
    
    # Проверяем наличие Firefox
    is_firefox_installed, firefox_version = check_firefox_installed()
    
    if not is_firefox_installed:
        print("Mozilla Firefox не найден. Начинаю установку...")
        success = install_firefox_with_brew()
        if not success:
            download_firefox_manually()
        
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
        
        print("\nУстановка завершена. Теперь ваш парсер должен работать на macOS!")
    else:
        print("Не удалось установить или найти Mozilla Firefox.")
        print("Пожалуйста, установите Firefox вручную: https://www.mozilla.org/firefox/")

if __name__ == "__main__":
    main()