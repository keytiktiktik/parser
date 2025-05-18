import os
import re
import json
import csv
from collections import Counter
from datetime import datetime

def generate_html_report(data, query):
    """
    Создает HTML-отчет вместо matplotlib-визуализации
    без зависимостей от numpy/pandas/matplotlib
    
    Args:
        data (list): Список словарей с данными о видео
        query (str): Поисковый запрос
        
    Returns:
        str: Путь к сохраненному HTML-файлу
    """
    try:
        # Создаем директорию для отчетов
        os.makedirs('visualization/output', exist_ok=True)
        
        # Подготовка данных для отчета
        # Преобразуем числовые значения
        for item in data:
            for key in ['views', 'likes', 'comments']:
                if key in item:
                    try:
                        item[key] = int(item[key])
                    except:
                        item[key] = 0
        
        # Сортировка по просмотрам
        top_videos = sorted(data, key=lambda x: x.get('views', 0), reverse=True)[:10]
        
        # Анализ ключевых слов
        all_titles = [item.get('title', '') for item in data]
        keywords = analyze_keywords(all_titles)
        question_keywords = analyze_question_keywords(all_titles)
        matching_keywords = analyze_matching_keywords(all_titles, query)
        keywords_by_views = analyze_keywords_by_views(data)
        
        # Генерируем HTML-контент
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Анализ виральных видео: {query}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
                h1, h2, h3 {{ color: #2c3e50; }}
                h1 {{ border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; }}
                h2 {{ margin-top: 30px; background-color: #f8f9fa; padding: 8px; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:hover {{ background-color: #f5f5f5; }}
                .keyword-table {{ width: 48%; float: left; margin-right: 2%; }}
                .section {{ margin-bottom: 30px; overflow: hidden; }}
                .clearfix {{ clear: both; }}
                .stats {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .info {{ color: #3498db; }}
                a {{ color: #2980b9; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <h1>Анализ виральных видео по запросу "{query}"</h1>
            <div class="stats">
                <p><strong>Дата создания:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                <p><strong>Всего собрано видео:</strong> {len(data)}</p>
                <p><strong>Общее количество просмотров:</strong> {sum(item.get('views', 0) for item in data):,}</p>
            </div>
            
            <div class="section">
                <h2>Топ-10 видео по просмотрам</h2>
                <table>
                    <tr>
                        <th>№</th>
                        <th>Платформа</th>
                        <th>Название</th>
                        <th>Просмотры</th>
                        <th>Лайки</th>
                        <th>Комментарии</th>
                        <th>Дата публикации</th>
                        <th>Ссылка</th>
                    </tr>
        """
        
        # Топ-10 видео по просмотрам
        for i, item in enumerate(top_videos, 1):
            title = item.get('title', '')
            if len(title) > 50:
                title = title[:47] + "..."
                
            html_content += f"""
                    <tr>
                        <td>{i}</td>
                        <td>{item.get('platform', '')}</td>
                        <td>{title}</td>
                        <td>{item.get('views', 0):,}</td>
                        <td>{item.get('likes', 0):,}</td>
                        <td>{item.get('comments', 0):,}</td>
                        <td>{item.get('publish_time', 'Неизвестно')}</td>
                        <td><a href="{item.get('url', '#')}" target="_blank">Открыть</a></td>
                    </tr>
            """
        
        html_content += """
                </table>
            </div>
            
            <div class="section">
                <h2>Анализ ключевых слов</h2>
        """
        
        # Анализ ключевых слов
        html_content += """
                <div class="keyword-table">
                    <h3>Связанные ключевые слова</h3>
                    <table>
                        <tr>
                            <th>Слово</th>
                            <th>Частота</th>
                        </tr>
        """
        
        for word, count in keywords[:15]:
            html_content += f"""
                        <tr>
                            <td>{word}</td>
                            <td>{count}</td>
                        </tr>
            """
        
        html_content += """
                    </table>
                </div>
        """
        
        # Вопросительные ключевые слова
        html_content += """
                <div class="keyword-table">
                    <h3>Ключевые слова вопросного типа</h3>
                    <table>
                        <tr>
                            <th>Фраза</th>
                            <th>Частота</th>
                        </tr>
        """
        
        for phrase, count in question_keywords[:10]:
            html_content += f"""
                        <tr>
                            <td>{phrase}</td>
                            <td>{count}</td>
                        </tr>
            """
        
        html_content += """
                    </table>
                </div>
                <div class="clearfix"></div>
            </div>
            
            <div class="section">
                <h2>Анализ запросов и метрик</h2>
        """
        
        # Matching keywords
        html_content += """
                <div class="keyword-table">
                    <h3>Точные совпадения с запросом</h3>
                    <table>
                        <tr>
                            <th>Слово</th>
                            <th>Частота</th>
                        </tr>
        """
        
        for word, count in matching_keywords[:15]:
            html_content += f"""
                        <tr>
                            <td>{word}</td>
                            <td>{count}</td>
                        </tr>
            """
        
        html_content += """
                    </table>
                </div>
        """
        
        # Ключевые слова по просмотрам
        html_content += """
                <div class="keyword-table">
                    <h3>Ключевые слова по просмотрам</h3>
                    <table>
                        <tr>
                            <th>Слово</th>
                            <th>Просмотры</th>
                        </tr>
        """
        
        for word, views in keywords_by_views[:15]:
            html_content += f"""
                        <tr>
                            <td>{word}</td>
                            <td>{views:,}</td>
                        </tr>
            """
        
        html_content += """
                    </table>
                </div>
                <div class="clearfix"></div>
            </div>
            
            <div class="section">
                <h2>Экспорт данных</h2>
                <p>Полные данные доступны в CSV-файле в каталоге data/</p>
            </div>
            
            <footer>
                <p>Отчет создан: {}</p>
            </footer>
        </body>
        </html>
        """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        # Сохраняем HTML-файл
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_file = f'visualization/output/report_{query.replace(" ", "_")}_{timestamp}.html'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_file
    
    except Exception as e:
        print(f"Ошибка при создании HTML-отчета: {e}")
        import traceback
        traceback.print_exc()
        return None

def analyze_keywords(titles):
    """
    Анализирует ключевые слова в заголовках без использования nltk
    """
    try:
        # Стоп-слова (русские и английские)
        stop_words = {
            'и', 'в', 'на', 'с', 'по', 'для', 'за', 'от', 'к', 'у', 'из', 'о', 'при', 'во', 'со',
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'by',
            'как', 'что', 'кто', 'где', 'когда', 'почему', 'чтобы', 'это', 'этот', 'эта', 'эти',
            'of', 'from', 'это', 'не', 'да', 'нет', 'же', 'вы', 'ты', 'я', 'он', 'она', 'они', 'мы',
            'так', 'его', 'ее', 'их', 'был', 'была', 'были', 'мой', 'моя', 'твой', 'твоя', 'наш',
            'ваш', 'этого', 'этой', 'том', 'тех', 'всех', 'всего', 'можно', 'нужно', 'надо'
        }
        
        # Подсчет слов
        word_counts = {}
        for title in titles:
            if not isinstance(title, str):
                continue
                
            # Очистка и токенизация
            cleaned_title = re.sub(r'[^\w\s]', ' ', title.lower())
            words = cleaned_title.split()
            
            # Подсчет слов
            for word in words:
                if len(word) > 2 and word not in stop_words:
                    word_counts[word] = word_counts.get(word, 0) + 1
        
        # Сортировка по частоте
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_words
    except Exception as e:
        print(f"Ошибка при анализе ключевых слов: {e}")
        return []

def analyze_question_keywords(titles):
    """
    Анализирует вопросительные слова в заголовках без nltk
    """
    try:
        question_pattern = re.compile(r'(как|почему|что|где|когда|кто|how|why|what|where|when|who)\s+(\w+)', re.IGNORECASE)
        
        phrase_counts = {}
        for title in titles:
            if not isinstance(title, str):
                continue
                
            # Поиск вопросительных слов
            matches = question_pattern.findall(title.lower())
            for match in matches:
                phrase = match[0] + ' ' + match[1]
                phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
        
        # Сортировка по частоте
        sorted_phrases = sorted(phrase_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_phrases
    except Exception as e:
        print(f"Ошибка при анализе вопросительных ключевых слов: {e}")
        return []

def analyze_matching_keywords(titles, query):
    """
    Анализирует совпадающие ключевые слова с запросом без nltk
    """
    try:
        query_words = set(query.lower().split())
        matches = {}
        
        for title in titles:
            if not isinstance(title, str):
                continue
                
            # Очистка и разбиение на слова
            cleaned_title = re.sub(r'[^\w\s]', ' ', title.lower())
            title_words = set(cleaned_title.split())
            
            # Находим пересечение с запросом
            common_words = title_words.intersection(query_words)
            for word in common_words:
                matches[word] = matches.get(word, 0) + 1
        
        # Сортировка по частоте
        sorted_matches = sorted(matches.items(), key=lambda x: x[1], reverse=True)
        return sorted_matches
    except Exception as e:
        print(f"Ошибка при анализе совпадающих ключевых слов: {e}")
        return []

def analyze_keywords_by_views(data):
    """
    Анализирует ключевые слова по количеству просмотров без pandas
    """
    try:
        keyword_views = {}
        stop_words = {
            'и', 'в', 'на', 'с', 'по', 'для', 'за', 'от', 'к', 'у', 'из', 'о', 'при', 'во', 'со',
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'by',
            'как', 'что', 'кто', 'где', 'когда', 'почему', 'чтобы', 'это', 'этот', 'эта', 'эти',
            'of', 'from', 'это', 'не', 'да', 'нет', 'же', 'вы', 'ты', 'я', 'он', 'она', 'они'
        }
        
        for item in data:
            title = item.get('title', '')
            views = item.get('views', 0)
            
            if not isinstance(title, str) or not views:
                continue
            
            # Очистка и токенизация
            cleaned_title = re.sub(r'[^\w\s]', ' ', title.lower())
            words = cleaned_title.split()
            
            # Уникальные слова в заголовке
            unique_words = set()
            for word in words:
                if len(word) > 3 and word not in stop_words:
                    unique_words.add(word)
            
            # Добавляем просмотры для каждого слова
            for word in unique_words:
                if word in keyword_views:
                    keyword_views[word] += views
                else:
                    keyword_views[word] = views
        
        # Сортировка по числу просмотров
        sorted_keywords = sorted(keyword_views.items(), key=lambda x: x[1], reverse=True)
        return sorted_keywords
    except Exception as e:
        print(f"Ошибка при анализе ключевых слов по просмотрам: {e}")
        return []