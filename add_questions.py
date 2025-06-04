from app.db import SessionLocal
from app.api.questions import add_all_questions

db = SessionLocal()
add_all_questions(db)
print("Все вопросы успешно добавлены!")