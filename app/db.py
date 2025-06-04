import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Путь к базе данных - используем переменную окружения или дефолтный путь
DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/survey.db")

# Создаем директорию если её нет
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Создаём движок SQLAlchemy (engine) — объект, который управляет соединением с БД
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # Для SQLite обязательно!
)

# Создаём фабрику сессий — через неё будем работать с БД в каждом запросе
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Функция для получения сессии (используется в зависимостях FastAPI)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()