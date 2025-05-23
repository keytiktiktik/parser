import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import re
import numpy as np
from datetime import datetime
from collections import Counter
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.util import ngrams

# Скачиваем необходимые данные для NLTK при первом использовании
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

def generate_dashboard(data, query):
    """
    Создает комплексную визуализацию результатов парсинга
    с анализом ключевых слов
    
    Args:
        data (list): Список словарей с данными о видео
        query (str): Поисковый запрос
        
    Returns:
        str: Путь к сохраненному файлу визуализации
    """
    try:
        # Конвертируем в DataFrame
        df = pd.DataFrame(data)
        
        # Проверяем, есть ли данные
        if len(df) == 0:
            print("Недостаточно данных для визуализации")
            return None
        
        # Конвертируем числовые колонки
        numeric_cols = ['views', 'likes', 'comments']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        # Создаем директорию для визуализаций
        os.makedirs('visualization/output', exist_ok=True)
        
        # Создаем фигуру и сетку подграфиков для 3x2 графиков
        fig = plt.figure(figsize=(22, 18))
        plt.clf()  # Очищаем фигуру перед использованием
        
        # Заголовок
        plt.suptitle(f'Анализ виральных видео по запросу "{query}"', fontsize=20)
        
        # 1. Анализ ключевых слов в заголовках
        plt.subplot(3, 2, 1)
        keywords = analyze_keywords(df['title'].tolist(), query)
        plot_keywords(keywords, "Связанные ключевые слова", plt)
        
        # 2. Топ-10 видео по просмотрам
        plt.subplot(3, 2, 2)
        if 'views' in df.columns and len(df) > 0:
            top10 = df.sort_values('views', ascending=False).head(10)
            top10['short_title'] = top10['title'].apply(lambda x: str(x)[:20] + '...' if len(str(x)) > 20 else str(x))
            
            # Визуализируем топ-10 по просмотрам
            if len(top10) > 0:
                sns.barplot(x='views', y='short_title', data=top10, palette='viridis')
                plt.xlabel('Просмотры')
                plt.ylabel('Название')
                plt.title('Топ-10 видео по просмотрам')
            else:
                plt.text(0.5, 0.5, 'Недостаточно данных для анализа', 
                        horizontalalignment='center', verticalalignment='center', fontsize=12)
                plt.title('Топ-10 видео по просмотрам')
        else:
            plt.text(0.5, 0.5, 'Недостаточно данных для анализа', 
                    horizontalalignment='center', verticalalignment='center', fontsize=12)
            plt.title('Топ-10 видео по просмотрам')
        
        # 3. Анализ сочетаний слов (n-grams)
        plt.subplot(3, 2, 3)
        keyword_phrases = analyze_keyword_phrases(df['title'].tolist())
        plot_keywords(keyword_phrases, "Популярные словосочетания", plt)
        
        # 4. Распределение видео по возрасту (дням)
        plt.subplot(3, 2, 4)
        if 'days_ago' in df.columns and len(df) > 0:
            try:
                # Конвертируем в числовой формат, если нужно
                if df['days_ago'].dtype == 'object':
                    df['days_ago_num'] = pd.to_numeric(df['days_ago'], errors='coerce')
                else:
                    df['days_ago_num'] = df['days_ago']
                
                # Создаем bins для гистограммы
                bins = [0, 1, 3, 7, 14, 30, 60, 90, 180, 365]
                labels = ['1 день', '2-3 дня', '4-7 дней', '1-2 недели', '2-4 недели', 
                          '1-2 месяца', '2-3 месяца', '3-6 месяцев', '6-12 месяцев']
                
                df['age_group'] = pd.cut(df['days_ago_num'], bins=bins, labels=labels, right=False)
                age_counts = df['age_group'].value_counts().sort_index()
                
                if len(age_counts) > 0:
                    sns.barplot(x=age_counts.index, y=age_counts.values, palette='viridis')
                    plt.xticks(rotation=45, ha='right')
                    plt.xlabel('Возраст видео')
                    plt.ylabel('Количество видео')
                    plt.title('Распределение видео по возрасту')
                else:
                    plt.text(0.5, 0.5, 'Недостаточно данных для анализа', 
                            horizontalalignment='center', verticalalignment='center', fontsize=12)
                    plt.title('Распределение видео по возрасту')
            except Exception as e:
                print(f"Ошибка при анализе возраста видео: {e}")
                plt.text(0.5, 0.5, 'Ошибка при анализе возраста видео', 
                        horizontalalignment='center', verticalalignment='center', fontsize=12)
                plt.title('Распределение видео по возрасту')
        else:
            plt.text(0.5, 0.5, 'Недостаточно данных для анализа', 
                    horizontalalignment='center', verticalalignment='center', fontsize=12)
            plt.title('Распределение видео по возрасту')
        
        # 5. Вопросительные ключевые слова
        plt.subplot(3, 2, 5)
        question_keywords = analyze_question_keywords(df['title'].tolist())
        plot_keywords(question_keywords, "Ключевые слова вопросного типа", plt)
        
        # 6. Поисковый объем и ключевые слова
        plt.subplot(3, 2, 6)
        plot_keywords_vs_views(df, "Ключевые слова и просмотры", plt)
        
        # Добавляем время создания и информацию о запросе
        plt.figtext(0.5, 0.01, f'Дата создания: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | Всего видео: {len(df)}', 
                    ha='center', fontsize=12)
        
        # Сохраняем изображение
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_file = f'visualization/output/dashboard_{query.replace(" ", "_")}_{timestamp}.png'
        
        # Регулировка макета для предотвращения перекрытия
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.savefig(output_file, dpi=300)
        plt.close()
        
        return output_file
    
    except Exception as e:
        print(f"Ошибка при создании визуализации: {e}")
        import traceback
        traceback.print_exc()
        return None

def analyze_keywords(titles, query):
    """Анализирует ключевые слова в заголовках"""
    try:
        # Составляем стоп-слова на основе русского и английского языков + добавляем слова из запроса
        stop_words = set(stopwords.words('russian') + stopwords.words('english'))
        query_words = query.lower().split()
        
        # Добавляем спецификаторы, которые нужно исключить
        custom_stop = ['как', 'для', 'the', 'что', 'это', 'все', 'без', 'или']
        stop_words.update(custom_stop)
        
        all_words = []
        for title in titles:
            if not isinstance(title, str):
                continue
            # Токенизация и очистка
            words = word_tokenize(title.lower())
            words = [word for word in words if word.isalpha() and len(word) > 2 and word not in stop_words]
            all_words.extend(words)
        
        # Подсчет частоты
        word_counts = Counter(all_words)
        
        # Берем топ-15 слов
        return word_counts.most_common(15)
    except Exception as e:
        print(f"Ошибка при анализе ключевых слов: {e}")
        return []

def analyze_keyword_phrases(titles, min_length=2, max_length=3):
    """Анализирует сочетания слов (n-grams) в заголовках"""
    try:
        # Составляем стоп-слова
        stop_words = set(stopwords.words('russian') + stopwords.words('english'))
        custom_stop = ['как', 'для', 'the', 'что', 'это', 'все', 'без', 'или']
        stop_words.update(custom_stop)
        
        # Подсчет n-gram
        ngram_counts = Counter()
        
        for title in titles:
            if not isinstance(title, str):
                continue
                
            # Токенизация и очистка
            words = word_tokenize(title.lower())
            words = [word for word in words if word.isalpha() and len(word) > 2 and word not in stop_words]
            
            # Подсчет ngrams разной длины
            for n in range(min_length, min(max_length + 1, len(words) + 1)):
                title_ngrams = ngrams(words, n)
                for ngram in title_ngrams:
                    ngram_counts[' '.join(ngram)] += 1
        
        # Берем топ-15 сочетаний
        return ngram_counts.most_common(15)
    except Exception as e:
        print(f"Ошибка при анализе сочетаний слов: {e}")
        return []

def analyze_question_keywords(titles):
    """Анализирует вопросительные слова в заголовках"""
    try:
        question_words = ['как', 'почему', 'что', 'где', 'когда', 'кто', 'how', 'why', 'what', 'where', 'when', 'who']
        question_pattern = re.compile(r'(как|почему|что|где|когда|кто|how|why|what|where|when|who)\s+(\w+)', re.IGNORECASE)
        
        question_phrases = []
        for title in titles:
            if not isinstance(title, str):
                continue
                
            matches = question_pattern.findall(title.lower())
            for match in matches:
                question_phrases.append(match[0] + ' ' + match[1])
        
        # Подсчет частоты
        phrase_counts = Counter(question_phrases)
        
        # Берем топ-10
        return phrase_counts.most_common(10)
    except Exception as e:
        print(f"Ошибка при анализе вопросительных ключевых слов: {e}")
        return []

def plot_keywords(keywords, title, plt):
    """Визуализирует ключевые слова"""
    try:
        if not keywords:
            plt.text(0.5, 0.5, 'Недостаточно данных для анализа', 
                    horizontalalignment='center', verticalalignment='center', fontsize=12)
            plt.title(title)
            return
            
        words = [item[0] for item in keywords]
        counts = [item[1] for item in keywords]
        
        # Строим горизонтальный барплот
        bars = plt.barh(words, counts, color=sns.color_palette("viridis", len(words)))
        
        # Добавляем подписи значений
        for bar in bars:
            width = bar.get_width()
            plt.text(width + 0.1, bar.get_y() + bar.get_height()/2, 
                    f'{int(width)}', ha='left', va='center')
        
        plt.xlabel('Частота')
        plt.title(title)
    except Exception as e:
        print(f"Ошибка при визуализации ключевых слов: {e}")
        plt.text(0.5, 0.5, f'Ошибка: {str(e)}', 
                horizontalalignment='center', verticalalignment='center', fontsize=12)
        plt.title(title)

def plot_keywords_vs_views(df, title, plt):
    """Визуализирует взаимосвязь между ключевыми словами и просмотрами"""
    try:
        # Извлекаем и анализируем ключевые слова
        all_keywords = {}
        
        if 'title' not in df.columns or 'views' not in df.columns or len(df) == 0:
            plt.text(0.5, 0.5, 'Недостаточно данных для анализа', 
                    horizontalalignment='center', verticalalignment='center', fontsize=12)
            plt.title(title)
            return
        
        for _, row in df.iterrows():
            if not isinstance(row['title'], str):
                continue
                
            # Токенизация текста
            words = word_tokenize(row['title'].lower())
            words = [word for word in words if word.isalpha() and len(word) > 3]
            
            # Для каждого слова добавляем просмотры
            for word in set(words):  # используем set для уникальности слов в одном видео
                if word not in all_keywords:
                    all_keywords[word] = {'count': 0, 'views': 0}
                all_keywords[word]['count'] += 1
                all_keywords[word]['views'] += int(row['views'])
        
        # Фильтруем слова, которые встречаются хотя бы 2 раза
        filtered_keywords = {k: v for k, v in all_keywords.items() if v['count'] >= 2}
        
        # Сортируем по количеству просмотров
        top_keywords = sorted(filtered_keywords.items(), key=lambda x: x[1]['views'], reverse=True)[:15]
        
        if not top_keywords:
            plt.text(0.5, 0.5, 'Недостаточно данных для анализа', 
                    horizontalalignment='center', verticalalignment='center', fontsize=12)
            plt.title(title)
            return
        
        words = [item[0] for item in top_keywords]
        views = [item[1]['views'] for item in top_keywords]
        
        # Строим горизонтальный барплот
        bars = plt.barh(words, views, color=sns.color_palette("viridis", len(words)))
        
        # Добавляем подписи значений
        for bar in bars:
            width = bar.get_width()
            plt.text(width + 0.1, bar.get_y() + bar.get_height()/2, 
                    f'{int(width):,}', ha='left', va='center')
        
        plt.xlabel('Общее количество просмотров')
        plt.title(title)
    except Exception as e:
        print(f"Ошибка при визуализации ключевых слов и просмотров: {e}")
        plt.text(0.5, 0.5, f'Ошибка: {str(e)}', 
                horizontalalignment='center', verticalalignment='center', fontsize=12)
        plt.title(title)