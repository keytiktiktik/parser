import argparse
import time
import os
import csv
from datetime import datetime
import pickle

# Импорт модулей парсеров
from parsers.youtube_parser import parse_youtube_shorts
from parsers.tiktok_parser import parse_tiktok
from parsers.instagram_parser import parse_instagram_reels
from parsers.vk_parser import parse_vk_clips

# Утилиты
from utils.viral_metrics import calculate_viral_score
from utils.storage import save_to_csv, load_previous_data
from utils.browser import setup_driver, save_cookies

def setup_auth_session():
    """Создает сессию для авторизации и сохранения cookies"""
    platforms = {
        "youtube": "https://www.youtube.com",
        "tiktok": "https://www.tiktok.com",
        "instagram": "https://www.instagram.com",
        "vk": "https://vk.com"
    }
    
    print("=== Настройка авторизации для парсера ===")
    
    # Создаем папку для cookies
    os.makedirs("cookies", exist_ok=True)
    
    for platform, url in platforms.items():
        choice = input(f"Настроить авторизацию для {platform}? (y/n): ")
        if choice.lower() == 'y':
            driver = None
            try:
                # Запускаем браузер с видимым интерфейсом
                driver = setup_driver(headless=False)
                if not driver:
                    print(f"Не удалось запустить браузер для {platform}")
                    continue
                
                # Открываем страницу
                print(f"Открываю {platform}... Пожалуйста, авторизуйтесь!")
                driver.get(url)
                
                # Ждем авторизацию пользователя
                input(f"После авторизации на {platform}, нажмите Enter для сохранения cookies...")
                
                # Сохраняем cookies
                save_cookies(driver, platform)
                
            except Exception as e:
                print(f"Ошибка при настройке авторизации для {platform}: {e}")
            
            finally:
                if driver:
                    driver.quit()
    
    print("Настройка авторизации завершена!")

def main():
    parser = argparse.ArgumentParser(description='Парсер виральных видео')
    parser.add_argument('--query', type=str, required=True, help='Поисковый запрос или тематика')
    parser.add_argument('--limit', type=int, default=20, help='Количество видео для сбора с каждой платформы')
    parser.add_argument('--platforms', type=str, default='all', 
                      help='Платформы для парсинга (youtube,tiktok,instagram,vk или all)')
    parser.add_argument('--visualize', action='store_true', help='Создать визуализацию результатов')
    parser.add_argument('--setup-auth', action='store_true', help='Настроить авторизацию для платформ')
    
    args = parser.parse_args()
    
    # Настройка авторизации, если запрошено
    if args.setup_auth:
        setup_auth_session()
        return
    
    print(f"Начинаю сбор данных по запросу: '{args.query}'")
    
    # Создаем директории
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/history", exist_ok=True)
    
    # Определяем платформы для сбора
    available_platforms = {
        'youtube': parse_youtube_shorts,
        'tiktok': parse_tiktok,
        'instagram': parse_instagram_reels,
        'vk': parse_vk_clips
    }
    
    selected_platforms = {}
    if args.platforms == 'all':
        selected_platforms = available_platforms
    else:
        platform_list = args.platforms.lower().split(',')
        for platform in platform_list:
            if platform in available_platforms:
                selected_platforms[platform] = available_platforms[platform]
    
    # Собираем данные с каждой платформы
    all_results = []
    
    for platform_name, parse_func in selected_platforms.items():
        print(f"Сбор данных с {platform_name}...")
        start_time = time.time()
        
        try:
            platform_results = parse_func(args.query, args.limit)
            all_results.extend(platform_results)
            print(f"Собрано {len(platform_results)} видео с {platform_name}")
        except Exception as e:
            print(f"Ошибка при сборе данных с {platform_name}: {e}")
        
        # Пауза между платформами
        time.sleep(2)
    
    # Загрузка предыдущих данных для сравнения
    previous_data = load_previous_data(args.query)
    
    # Расчет метрик виральности
    if all_results:
        results_with_metrics = calculate_viral_score(all_results, previous_data)
        
        # Сохранение результатов
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"data/viral_videos_{args.query.replace(' ', '_')}_{timestamp}.csv"
        save_to_csv(results_with_metrics, filename)
        
        # Сохранение копии для истории
        history_filename = f"data/history/viral_videos_{args.query.replace(' ', '_')}_{timestamp}.csv"
        save_to_csv(results_with_metrics, history_filename)
        
        print(f"Всего собрано {len(results_with_metrics)} видео со всех платформ")
        
        # Показываем топ-10 по виральности
        print("\nТоп-10 самых виральных видео:")
        for i, item in enumerate(results_with_metrics[:10], 1):
            title = item.get('title', '')
            if isinstance(title, str) and len(title) > 40:
                title = title[:37] + "..."
                
            print(f"{i}. [{item.get('platform')}] {title}")
            print(f"   👁️ {item.get('views', 'N/A')} | 👍 {item.get('likes', 'N/A')} | 💬 {item.get('comments', 'N/A')}")
            print(f"   URL: {item.get('url', 'N/A')}")
        
        # Визуализация если требуется
        if args.visualize:
            try:
                from visualization.dashboard import generate_dashboard
                dashboard_file = generate_dashboard(results_with_metrics, args.query)
                print(f"\nВизуализация сохранена в {dashboard_file}")
            except ImportError:
                print("\nДля визуализации требуются matplotlib и seaborn. Установите их: pip install matplotlib seaborn")
            except Exception as e:
                print(f"\nОшибка при создании визуализации: {e}")
    else:
        print("Не удалось собрать данные. Проверьте запрос или соединение.")

if __name__ == "__main__":
    main()