import argparse
import time
import os
import csv
import webbrowser
from datetime import datetime

# Импорт парсеров
from parsers.youtube_parser import parse_youtube_shorts
from parsers.vk_parser import parse_vk_clips
from parallel_processing import run_parallel_search

# Утилиты
from utils.viral_metrics import calculate_viral_score
from utils.storage import save_to_csv, load_previous_data

def main():
    parser = argparse.ArgumentParser(description='Парсер виральных видео')
    parser.add_argument('--query', type=str, required=True, help='Поисковый запрос или тематика')
    parser.add_argument('--limit', type=int, default=200, help='Максимальное количество видео для сбора')
    parser.add_argument('--days', type=int, default=30, help='Только видео за последние N дней')
    parser.add_argument('--visualize', action='store_true', help='Создать визуализацию результатов')
    parser.add_argument('--parallel', action='store_true', help='Использовать многопроцессорную обработку')
    parser.add_argument('--workers', type=int, default=0, help='Количество параллельных процессов (0 = авто)')
    parser.add_argument('--strict-match', action='store_true', help='Строгая проверка наличия запроса в контенте')
    parser.add_argument('--platforms', type=str, default='youtube', 
                        help='Платформы для сбора данных (youtube,vk или all)')
    parser.add_argument('--no-headless', action='store_true', 
                        help='Показывать браузер при парсинге (для отладки)')
    parser.add_argument('--browser-profile', type=str, default=None,
                        help='Путь к профилю браузера для использования существующих cookies')
    parser.add_argument('--manual-auth', action='store_true',
                        help='Включить паузу для ручной авторизации')
    
    args = parser.parse_args()
    
    print(f"Начинаю сбор данных по запросу: '{args.query}' за последние {args.days} дней")
    
    # Создаем директории
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/history", exist_ok=True)
    os.makedirs("visualization/output", exist_ok=True)
    
    # Собираем данные с выбранных платформ
    all_results = []
    
    # Определяем платформы для сбора данных
    platforms = args.platforms.lower().split(',')
    if 'all' in platforms:
        platforms = ['youtube', 'vk']
    
    # Сбор данных с YouTube
    if 'youtube' in platforms:
        print(f"Сбор данных с YouTube Shorts...")
        start_time = time.time()
        
        try:
            # Определяем метод сбора данных - параллельный или последовательный
            if args.parallel:
                print(f"Используется многопроцессорная обработка")
                youtube_results = run_parallel_search(
                    main_query=args.query,
                    limit=args.limit,
                    days_ago=args.days,
                    max_workers=args.workers if args.workers > 0 else None,
                    strict_query_match=args.strict_match
                )
            else:
                print(f"Используется однопоточная обработка")
                youtube_results = parse_youtube_shorts(
                    query=args.query,
                    limit=args.limit,
                    days_ago=args.days,
                    strict_query_match=args.strict_match
                )
                
            all_results.extend(youtube_results)
            elapsed = time.time() - start_time
            print(f"Сбор данных с YouTube занял {elapsed:.2f} секунд. Собрано {len(youtube_results)} видео")
        except Exception as e:
            print(f"Ошибка при сборе данных с YouTube Shorts: {e}")
            import traceback
            traceback.print_exc()
    
    # Сбор данных с VK
    if 'vk' in platforms:
        print(f"Сбор данных с VK Клипов...")
        start_time = time.time()
        
        try:
            if args.manual_auth:
                print("\n========== ИНСТРУКЦИЯ ПО РУЧНОЙ АВТОРИЗАЦИИ ==========")
                print("1. В открывшемся окне браузера войдите в свой аккаунт VK, если требуется")
                print("2. После успешного входа скрипт автоматически продолжит работу")
                print("========================================================\n")
            
            vk_results = parse_vk_clips(
                query=args.query,
                limit=args.limit,
                days_ago=args.days,
                headless=not args.no_headless,
                browser_profile=args.browser_profile
            )
            
            all_results.extend(vk_results)
            elapsed = time.time() - start_time
            print(f"Сбор данных с VK занял {elapsed:.2f} секунд. Собрано {len(vk_results)} видео")
        except Exception as e:
            print(f"Ошибка при сборе данных с VK Клипов: {e}")
            import traceback
            traceback.print_exc()
    
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
        
        print(f"Всего собрано {len(results_with_metrics)} видео")
        
        # Показываем топ-10 по виральности с указанием платформы
        print("\nТоп-10 самых виральных видео:")
        for i, item in enumerate(results_with_metrics[:min(10, len(results_with_metrics))], 1):
            title = item.get('title', '')
            if isinstance(title, str) and len(title) > 40:
                title = title[:37] + "..."
                
            platform = item.get('platform', 'Неизвестно')
            print(f"{i}. [{platform}] {title}")
            print(f"   👁️ {item.get('views', 'N/A')} | 👍 {item.get('likes', 'N/A')} | 💬 {item.get('comments', 'N/A')}")
            print(f"   📅 Опубликовано: {item.get('publish_date_formatted', 'N/A')} ({item.get('days_ago', 'N/A')} дней назад)")
            print(f"   URL: {item.get('url', 'N/A')}")
        
        # Выводим статистику по платформам
        platforms_stats = {}
        for item in results_with_metrics:
            platform = item.get('platform', 'Неизвестно')
            if platform not in platforms_stats:
                platforms_stats[platform] = 0
            platforms_stats[platform] += 1
        
        print("\nСтатистика по платформам:")
        for platform, count in platforms_stats.items():
            print(f"- {platform}: {count} видео ({count/len(results_with_metrics)*100:.1f}%)")
        
        # Визуализация если требуется
        if args.visualize:
            try:
                # Сначала пробуем создать HTML-отчет (без зависимостей)
                from visualization.html_report import generate_html_report
                html_file = generate_html_report(results_with_metrics, args.query)
                if html_file:
                    print(f"\nHTML-отчет сохранен в {html_file}")
                    # Открываем в браузере
                    webbrowser.open('file://' + os.path.abspath(html_file))
                else:
                    # Если не удалось создать HTML, пробуем Dashboard (требует matplotlib)
                    try:
                        from visualization.dashboard import generate_dashboard
                        dashboard_file = generate_dashboard(results_with_metrics, args.query)
                        if dashboard_file:
                            print(f"\nДашборд сохранен в {dashboard_file}")
                            # Открываем в браузере
                            webbrowser.open('file://' + os.path.abspath(dashboard_file))
                    except Exception as e:
                        print(f"\nОшибка при создании дашборда: {e}")
            except Exception as e:
                print(f"\nОшибка при создании отчета: {e}")
                import traceback
                traceback.print_exc()
    else:
        print("Не удалось собрать данные. Проверьте запрос, соединение или доступность платформ.")

if __name__ == "__main__":
    main()