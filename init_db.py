from sqlalchemy import create_engine
from app.models import Base

# Создаём подключение к базе данных SQLite (файл db.sqlite3)
engine = create_engine("sqlite:///db.sqlite3")

# Создаём все таблицы, описанные в models.py (если их ещё нет)
Base.metadata.create_all(engine)

print("Таблицы успешно созданы!")