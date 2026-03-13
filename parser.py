import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from datetime import datetime
from bs4 import BeautifulSoup
import requests
import json
from celery import Celery
import requests
import time
from dotenv import load_dotenv

app = Celery('parser', broker='redis://localhost:6379/0')

app.conf.beat_schedule = {
    'Every_minute' : {
        'task' : 'parser.what_task_want_to_do',
        'schedule': 60.0,
    },
}

@app.task
def what_task_want_to_do():
    url = "https://www.deribit.com/api/v2/public/get_index_price?index_name=btc_usd"
    url2 = "https://www.deribit.com/api/v2/public/get_index_price?index_name=eth_usd"

    response = requests.get(url)
    response_2 = requests.get(url2)

    current_time = int(time.time())

    if response.status_code == 200:
        data = response.json()
        index_price = data['result']['index_price']
        ticker = 'btc_usd'
    else:
        print(f'Ошибка: {response.status_code}')
        return


    if response_2.status_code == 200:
        data_2 = response_2.json()
        index_price_2 = data_2['result']['index_price']
        ticker_2 = 'eth_usd'
    else:
        print(f'Ошибка: {response_2.status_code}')
        return

    try:
        conn = psycopg2.connect(
            dbname='parsing_results',
            user='danilpik',
            password='',
            host='localhost',
            port='5432'
        )
    
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        print("Подключение к базе данных успешно установлено")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS currency_prices (
            id BIGSERIAL PRIMARY KEY,
            ticket VARCHAR(10) NOT NULL,
            price DECIMAL(20, 2) NOT NULL,
            unix_time BIGINT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)
        try:
            cursor.execute("""
                INSERT INTO currency_prices (ticket, price, unix_time)
                VALUES 
                    (%(ticker1)s, %(price1)s, %(time)s),
                    (%(ticker2)s, %(price2)s, %(time)s);
            """, {
                'ticker1': ticker,
                'price1': index_price,
                'ticker2': ticker_2,
                'price2': index_price_2,
                'time': current_time
            })
            
            print(f"💰 Данные успешно вставлены!")
        
        except psycopg2.Error as e:
            print(f"❌ Ошибка при вставке данных: {e}")
            conn.rollback()
            raise
        
    except psycopg2.Error as e:
        print(f"Ошибка при работе с базой данных: {e}")
    
    finally:
        if 'cursor' in locals():
            cursor.close()
            print("Курсор закрыт")
    
        if 'conn' in locals():
            conn.close()
            print("Соединение с базой данных закрыто")

    
