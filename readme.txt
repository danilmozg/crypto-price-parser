Design Decisions
1. Выбор технологий
* FastAPI был выбран из-за всех его основных преимуществ
* Celery + Redis - Периодичность
* PostgreSQL - Надежность, доступность

Требования
Python 3.8+

PostgreSQL 12+

Redis 6+

pip и virtualenv (рекомендуется)

Установка
1. Клонирование репозитория
git clone <your-repository-url>
cd crypto-price-parser

2. Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows

3. Установка зависимостей
pip install -r requirements.txt


4. Установка PostgreSQL (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql

5. Установка Redis (Ubuntu/Debian)
sudo apt install redis-server
sudo systemctl start redis-server

Настройка
1. Создание базы данных
sudo -u postgres psql
В консоли PostgreSQL:

sql
CREATE DATABASE parsing_results;
CREATE USER {DB_USER} WITH PASSWORD {BD_PASSWORD};
GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER};
\q
2. Настройка переменных окружения
Создайте файл .env в корне проекта:

env
# Database Configuration
DB_NAME='your_db_name'
DB_USER=your_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432


🚀 Запуск
Терминал 1 - Запуск Redis (если не запущен)
redis-server

Терминал 2 - Запуск БД
brew services start postgresql@17 - Мак ОС
sudo systemctl start postgresql - Linux (Ubuntu/Debian)
sudo systemctl start postgresql - Linux (CentOS/RHEL/Fedora)
net start postgresql-x64-17 - Windows

Терминал 3 - Запуск Celery Beat (планировщик) и Worker
celery -A parser worker --beat --loglevel=info

Терминал 4 - Запуск FastAPI приложения
uvicorn main:app --reload --host 0.0.0.0 --port 8000



📊 API Endpoints
1. Получение истории цен (/1method/)
text
GET /1method/?ticker=btc_usd&limit=50&offset=0&sort_by=unix_time&sort_order=desc
Параметры:

ticker (обязательный): btc_usd или eth_usd

limit: количество записей (по умолчанию 50)

offset: смещение для пагинации

sort_by: поле для сортировки (id, ticket, price, unix_time)

sort_order: порядок (asc/desc)

2. Последняя цена (/2method/)
text
GET /2method/?ticker=btc_usd
Возвращает самую свежую запись для указанного тикера.

3. Цены за конкретную дату (/3method/)
text
GET /3method/?ticker=btc_usd&date_param=2024-01-15&limit=100
Параметры:

ticker: btc_usd или eth_usd

date_param: дата в формате YYYY-MM-DD

limit: количество записей (по умолчанию 100)

