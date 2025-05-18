import argparse
import time
import pandas as pd
import os
from datetime import datetime

# Импорт модулей парсеров
from parsers.youtube_parser import parse_youtube_shorts
from parsers.tiktok_parser import parse_tiktok
from parsers.instagram_parser import parse_instagram_reels
from parsers.vk_parser import parse_vk_clips

# Утилиты
from utils.viral_metrics import calculate_viral_score
from utils.storage import save_to_csv, load_previous_data

def main():
    parser = argparse.ArgumentParser(description='Парсер виральных видео')
    parser.add_argument('--query', type=str, required=True, help='Поисковый запрос или тематика')
    parser.add_argument('--limit', type=int, default=20, help='Количество видео для сбора с каждой платформы')
    parser.add_argument('--platforms', type=str, default='all', 
                      help='Платформы для парсинга (youtube,tiktok,instagram,vk или all)')
    parser.add_argument('--visualize', action='store_true', help='Создать визуализацию результатов')
    args = parser.parse_args()
    
    print(f"Начинаю сбор данных по запросу: '{args.query}'")
    
    # Создаем директории, если их нет
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/history", exist_ok=True)
    
    platforms = args.platforms.lower().split(',') if args.platforms != 'all' else ['youtube', 'tiktok', 'instagram', 'vk']
    all_results = []
    
    # YouTube Shorts
    if 'youtube' in platforms:
        print("Сбор данных с YouTube Shorts...")
        youtube_results = parse_youtube_shorts(args.query, args.limit)
        all_results.extend(youtube_results)
        print(f"Собрано {len(youtube_results)} видео с YouTube Shorts")
        time.sleep(3)
    
    # TikTok
    if 'tiktok' in platforms:
        print("Сбор данных с TikTok...")
        tiktok_results = parse_tiktok(args.query, args.limit)
        all_results.extend(tiktok_results)
        print(f"Собрано {len(tiktok_results)} видео с TikTok")
        time.sleep(3)
    
    # Instagram Reels
    if 'instagram' in platforms:
        print("Сбор данных с Instagram Reels...")
        instagram_results = parse_instagram_reels(args.query, args.limit)
        all_results.extend(instagram_results)
        print(f"Собрано {len(instagram_results)} видео с Instagram Reels")
        time.sleep(3)
    
    # ВК Клипы
    if 'vk' in platforms:
        print("Сбор данных с ВК Клипов...")
        vk_results = parse_vk_clips(args.query, args.limit)
        all_results.extend(vk_results)
        print(f"Собрано {len(vk_results)} видео с ВК Клипов")
    
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
        
        print(f"Данные сохранены в {filename}")
        print(f"Всего собрано {len(results_with_metrics)} видео со всех платформ")
        
        # Top-10 по виральности
        df = pd.DataFrame(results_with_metrics)
        top10 = df.sort_values(by='viral_score', ascending=False).head(10)
        
        print("\nТоп-10 самых виральных видео:")
        for i, (_, row) in enumerate(top10.iterrows(), 1):
            title = row['title']
            if isinstance(title, str) and len(title) > 50:
                title = title[:47] + "..."
            
            print(f"{i}. [{row['platform']}] {title} ({row['url']})")
            print(f"   Просмотры: {row['views']}, Лайки: {row['likes']}, Вирал. скор: {row['viral_score']}")
            
        # Визуализация если требуется
        if args.visualize:
            from visualization.dashboard import generate_dashboard
            dashboard_file = generate_dashboard(results_with_metrics, args.query)
            print(f"\nВизуализация сохранена в {dashboard_file}")
    else:
        print("Не удалось собрать данные. Проверьте запрос или соединение.")

if __name__ == "__main__":
    main()