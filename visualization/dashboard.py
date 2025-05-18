import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from datetime import datetime

def generate_dashboard(data, query):
    """
    Создает визуализацию результатов парсинга
    
    Args:
        data (list): Список словарей с данными о видео
        query (str): Поисковый запрос
        
    Returns:
        str: Путь к сохраненному файлу визуализации
    """
    try:
        # Конвертируем в DataFrame
        df = pd.DataFrame(data)
        
        # Конвертируем числовые колонки
        numeric_cols = ['views', 'likes', 'comments']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        # Создаем директорию для визуализаций
        os.makedirs('visualization/output', exist_ok=True)
        
        # Создаем фигуру и сетку подграфиков
        plt.figure(figsize=(16, 12))
        
        # Заголовок
        plt.suptitle(f'Анализ виральных видео по запросу "{query}"', fontsize=16)
        
        # 1. Топ-10 видео по вирусному показателю
        plt.subplot(2, 2, 1)
        top10 = df.sort_values('viral_score', ascending=False).head(10)
        
        # Создаем понятные названия для графика (обрезаем длинные названия)
        top10['short_title'] = top10['title'].apply(lambda x: str(x)[:20] + '...' if len(str(x)) > 20 else str(x))
        
        # Делаем бары горизонтальными для лучшей читаемости
        sns.barplot(x='viral_score', y='short_title', data=top10, hue='platform', dodge=False)
        plt.xlabel('Вирусный показатель')
        plt.ylabel('Название')
        plt.title('Топ-10 видео по вирусному показателю')
        
        # 2. Распределение видео по платформам
        plt.subplot(2, 2, 2)
        platform_counts = df['platform'].value_counts()
        plt.pie(platform_counts, labels=platform_counts.index, autopct='%1.1f%%', startangle=90)
        plt.axis('equal')
        plt.title('Распределение видео по платформам')
        
        # 3. Среднее количество просмотров по платформам
        plt.subplot(2, 2, 3)
        platform_views = df.groupby('platform')['views'].mean().sort_values(ascending=False)
        sns.barplot(x=platform_views.index, y=platform_views.values)
        plt.xlabel('Платформа')
        plt.ylabel('Среднее количество просмотров')
        plt.title('Среднее количество просмотров по платформам')
        plt.xticks(rotation=45)
        
        # 4. Корреляция между просмотрами, лайками и комментариями
        plt.subplot(2, 2, 4)
        
        # Проверяем наличие числовых данных о лайках и комментариях
        has_likes = 'likes' in df.columns and df['likes'].astype(str).str.lower().str.contains('n/a').sum() < len(df)
        has_comments = 'comments' in df.columns and df['comments'].astype(str).str.lower().str.contains('n/a').sum() < len(df)
        
        if has_likes and has_comments:
            # Создаем датафрейм только с числовыми значениями
            df_numeric = df[['views', 'likes', 'comments']].copy()
            for col in df_numeric.columns:
                df_numeric[col] = pd.to_numeric(df_numeric[col], errors='coerce').fillna(0)
            
            # Создаем корреляционную матрицу
            corr = df_numeric.corr()
            sns.heatmap(corr, annot=True, cmap='coolwarm')
            plt.title('Корреляция между метриками')
        else:
            plt.text(0.5, 0.5, 'Недостаточно данных для корреляционного анализа', 
                    horizontalalignment='center', verticalalignment='center', fontsize=12)
        
        # Добавляем время создания и информацию о запросе
        plt.figtext(0.5, 0.01, f'Дата создания: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 
                    ha='center', fontsize=10)
        
        # Сохраняем изображение
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_file = f'visualization/output/dashboard_{query.replace(" ", "_")}_{timestamp}.png'
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.savefig(output_file, dpi=300)
        plt.close()
        
        return output_file
    
    except Exception as e:
        print(f"Ошибка при создании визуализации: {e}")
        return None