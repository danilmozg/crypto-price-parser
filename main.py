from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from typing import Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'parsing_results'),
    'user': os.getenv('DB_USER', 'danilpik'),
    'password': os.getenv('DB_PASSWORD', ''),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432')
}

def get_db_connection():
    """Создает соединение с базой данных"""
    try:
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        return conn
    except psycopg2.Error as e:
        print(f"Ошибка подключения к БД: {e}")
        raise


@app.get('/1method/')
def first_method(ticker: str = Query(..., description="Тикер валюты"),
    limit: int = Query(50, description="Количество записей"),
    offset: int = Query(0, description="Смещение"),
    sort_by: str = Query("unix_time", description="Поле для сортировки"),
    sort_order: str = Query("desc", description="Порядок сортировки")):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем существование тикера
        cursor.execute("SELECT DISTINCT ticket FROM currency_prices WHERE ticket = %s", (ticker,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Тикер {ticker} не найден в базе данных")
        
        order_direction = "DESC" if sort_order.lower() == "desc" else "ASC"

        query = f"""
            SELECT 
                id,
                ticket,
                price::float as price,
                unix_time,
                to_char(created_at, 'YYYY-MM-DD HH24:MI:SS') as created_at
            FROM currency_prices 
            WHERE ticket = %s 
            ORDER BY {sort_by} {order_direction}
            LIMIT %s OFFSET %s
        """
        
        cursor.execute(query, (ticker, limit, offset))
        results = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM currency_prices WHERE ticket = %s", (ticker,))
        total_count = cursor.fetchone()['count']

        for row in results:
            row['human_time'] = datetime.fromtimestamp(row['unix_time']).strftime('%Y-%m-%d %H:%M:%S')
            row['date'] = datetime.fromtimestamp(row['unix_time']).strftime('%Y-%m-%d')
            row['time'] = datetime.fromtimestamp(row['unix_time']).strftime('%H:%M:%S')



        html = f"""
        <html>
        <head>
            <title>Цены {ticker}</title>
        </head>
        <body>
            <h2>Цены {ticker}</h2>
            <table border="1" cellpadding="5" cellspacing="0">
                <tr>
                    <th>ID</th>
                    <th>Тикер</th>
                    <th>Цена</th>
                    <th>Unix Time</th>
                    <th>Дата создания</th>
                </tr>
        """
        
        # Добавляем строки с данными
        for row in results:
            html += f"""
                <tr>
                    <td>{row['id']}</td>
                    <td>{row['ticket']}</td>
                    <td>{float(row['price']):.2f}</td>
                    <td>{row['unix_time']}</td>
                    <td>{row['created_at']}</td>
                </tr>
            </body>
            </html>
            """
        
        return HTMLResponse(content=html, status_code=200)
        
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Ошибка базы данных: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.get('/2method/')
def get_latest_price(
    ticker: str = Query(..., description="Тикер валюты")
):
    """
    Получение последней цены валюты
    """
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем последнюю запись для указанного тикера
        cursor.execute("""
            SELECT 
                id,
                ticket,
                price::float as price,
                unix_time,
                to_char(created_at, 'YYYY-MM-DD HH24:MI:SS') as created_at
            FROM currency_prices 
            WHERE ticket = %s 
            ORDER BY unix_time DESC 
            LIMIT 1
        """, (ticker,))
        
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Данные для тикера {ticker} не найдены")
        
        # Преобразуем время Unix в человекочитаемый формат
        human_time = datetime.fromtimestamp(result['unix_time']).strftime('%Y-%m-%d %H:%M:%S')
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Последняя цена {ticker}</title>
    <meta charset="UTF-8">
</head>
<body>
    <h2>Последняя цена {ticker}</h2>
    
    <table border="1" cellpadding="8" cellspacing="0">
        <tr>
            <th>ID</th>
            <th>Тикер</th>
            <th>Цена (USD)</th>
            <th>Unix Time</th>
            <th>Человеческое время</th>
            <th>Создано</th>
        </tr>
        <tr>
            <td>{result['id']}</td>
            <td><strong>{result['ticket']}</strong></td>
            <td><strong style="color: green;">${float(result['price']):.2f}</strong></td>
            <td>{result['unix_time']}</td>
            <td>{human_time}</td>
            <td>{result['created_at']}</td>
        </tr>
    </table>
</body>
</html>"""
        
        return HTMLResponse(content=html, status_code=200)
        
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Ошибка базы данных: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.get('/3method/', response_class=HTMLResponse)
def get_prices_by_date(
    ticker: str = Query(..., description="Тикер валюты"),
    date_param: str = Query(..., description="Дата в формате ГГГГ-ММ-ДД"),
    limit: int = Query(100, description="Количество записей")
):
    """
    Получение цены валюты с фильтром по дате (в виде HTML таблицы)
    """
    conn = None
    cursor = None
    
    try:
        # Парсим дату
        try:
            filter_date = datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            return HTMLResponse(content="<h2>Неверный формат даты. Используйте ГГГГ-ММ-ДД</h2>", status_code=400)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем существование тикера
        cursor.execute("SELECT DISTINCT ticket FROM currency_prices WHERE ticket = %s", (ticker,))
        if not cursor.fetchone():
            return HTMLResponse(content=f"<h2>Тикер {ticker} не найден в базе данных</h2>", status_code=404)
        
        # Конвертируем дату в Unix timestamp
        start_of_day = int(datetime.combine(filter_date, datetime.min.time()).timestamp())
        end_of_day = int(datetime.combine(filter_date, datetime.max.time()).timestamp())
        
        # Получаем данные за указанную дату
        cursor.execute("""
            SELECT 
                id,
                ticket,
                price::float as price,
                unix_time,
                to_char(created_at, 'YYYY-MM-DD HH24:MI:SS') as created_at
            FROM currency_prices 
            WHERE ticket = %s 
                AND unix_time BETWEEN %s AND %s
            ORDER BY unix_time DESC 
            LIMIT %s
        """, (ticker, start_of_day, end_of_day, limit))
        
        results = cursor.fetchall()
        
        if not results:
            return HTMLResponse(content=f"<h2>Данные для тикера {ticker} за {date_param} не найдены</h2>", status_code=404)
        
        # Получаем общее количество записей за этот день
        cursor.execute("""
            SELECT COUNT(*) 
            FROM currency_prices 
            WHERE ticket = %s AND unix_time BETWEEN %s AND %s
        """, (ticker, start_of_day, end_of_day))
        
        total_for_day = cursor.fetchone()['count']
        
        # Получаем минимальную и максимальную цену за день
        cursor.execute("""
            SELECT 
                MIN(price) as min_price,
                MAX(price) as max_price,
                AVG(price) as avg_price
            FROM currency_prices 
            WHERE ticket = %s AND unix_time BETWEEN %s AND %s
        """, (ticker, start_of_day, end_of_day))
        
        stats = cursor.fetchone()
        
        # Формируем HTML
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Цены {ticker} за {date_param}</title>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h2 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th {{ background-color: #4CAF50; color: white; }}
        th, td {{ padding: 10px; text-align: left; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .stats {{ background-color: #e7f3e7; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .nav {{ margin: 20px 0; }}
        .nav a {{ margin-right: 15px; text-decoration: none; color: #4CAF50; }}
        .price-up {{ color: green; }}
        .price-down {{ color: red; }}
    </style>
</head>
<body>
    <h2>Цены {ticker} за {date_param}</h2>
    
    <div class="stats">
        <h3>Статистика за день:</h3>
        <p>Всего записей: <strong>{total_for_day}</strong> | Показано: <strong>{len(results)}</strong></p>
        <p>
            Min цена: <strong class="price-down">${float(stats['min_price']):.2f}</strong> | 
            Max цена: <strong class="price-up">${float(stats['max_price']):.2f}</strong> | 
            Средняя цена: <strong>${float(stats['avg_price']):.2f}</strong>
        </p>
    </div>
    
    <table border="1" cellpadding="5" cellspacing="0">
        <tr>
            <th>ID</th>
            <th>Тикер</th>
            <th>Цена (USD)</th>
            <th>Unix Time</th>
            <th>Время</th>
            <th>Полное время</th>
        </tr>"""
        
        for row in results:
            human_time = datetime.fromtimestamp(row['unix_time']).strftime('%Y-%m-%d %H:%M:%S')
            time_only = datetime.fromtimestamp(row['unix_time']).strftime('%H:%M:%S')
            html += f"""
        <tr>
            <td>{row['id']}</td>
            <td>{row['ticket']}</td>
            <td><strong>${float(row['price']):.2f}</strong></td>
            <td>{row['unix_time']}</td>
            <td>{time_only}</td>
            <td>{human_time}</td>
        </tr>"""
        
        html += f"""
    </table>
    
    <div class="nav">
        <h3>Навигация по датам:</h3>
        <form action="/3method/" method="get" style="margin: 20px 0;">
            <input type="hidden" name="ticker" value="{ticker}">
            <label for="date_param">Выберите дату:</label>
            <input type="date" name="date_param" value="{date_param}" onchange="this.form.submit()">
            &nbsp;&nbsp;
            <label for="limit">Записей:</label>
            <select name="limit" onchange="this.form.submit()">
                <option value="10" {"selected" if limit == 10 else ""}>10</option>
                <option value="25" {"selected" if limit == 25 else ""}>25</option>
                <option value="50" {"selected" if limit == 50 else ""}>50</option>
                <option value="100" {"selected" if limit == 100 else ""}>100</option>
                <option value="200" {"selected" if limit == 200 else ""}>200</option>
            </select>
        </form>
        
        <p>
            <a href="/3method/?ticker=btc_usd&date={date_param}">BTC/USD за {date_param}</a> | 
            <a href="/3method/?ticker=eth_usd&date={date_param}">ETH/USD за {date_param}</a>
        </p>
        
        <p>
            <a href="/2method/?ticker={ticker}">🔍 Последняя цена {ticker}</a> |
            <a href="/1method/?ticker={ticker}&limit=10">📊 Вся история {ticker}</a>
        </p>
        
        <p>
            <a href="/">🏠 Главная</a>
        </p>
    </div>
</body>
</html>"""
        
        return HTMLResponse(content=html, status_code=200)
        
    except psycopg2.Error as e:
        return HTMLResponse(content=f"<h2>Ошибка базы данных: {str(e)}</h2>", status_code=500)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()