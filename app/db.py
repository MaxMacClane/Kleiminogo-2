import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Корректный путь к базе данных (data/db.sqlite3 в корне проекта)
DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join("data", "db.sqlite3"))

# Создаём директорию, если её нет (только если путь не в корне)
dirname = os.path.dirname(DATABASE_PATH)
if dirname and not os.path.exists(dirname):
    os.makedirs(dirname, exist_ok=True)

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