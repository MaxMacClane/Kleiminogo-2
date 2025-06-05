import os

# Корневая директория проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Путь к базе данных SQLite (data/db.sqlite3 в корне проекта)
DB_PATH = os.path.join(BASE_DIR, "data", "db.sqlite3")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# Здесь можно добавить другие константы (секреты, настройки почты и т.д.) 