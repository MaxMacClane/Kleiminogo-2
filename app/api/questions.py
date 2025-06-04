from app import models
from sqlalchemy.orm import Session

def add_all_questions(db: Session):
    """
    Добавляет все вопросы для обеих частей опроса (основные и детальные), как в Google Forms.
    """
    questions = [
        # Первая часть (основная)
        models.Question(text='ФИО', qtype='text', order=1),
        models.Question(text='Кадастровый номер участка', qtype='text', order=2),
        models.Question(text='Телефон для связи', qtype='text', order=3),
        models.Question(text='Поддерживаете ли вы создание нового СНТ?', qtype='choice', order=4),
        models.Question(text='Готовы ли вы нести финансовые обязательства в рамках СНТ?', qtype='choice', order=5),
        # Вторая часть (детальное мнение)
        models.Question(text='Какие у вас основные опасения или вопросы?', qtype='checkbox', order=6),
        models.Question(text='Какой максимальный ежемесячный взнос вы считаете приемлемым?', qtype='choice', order=7),
        models.Question(text='Готовы ли вы лично участвовать в управлении СНТ?', qtype='choice', order=8),
        models.Question(text='Содержание дорог в хорошем состоянии (приоритет)', qtype='priority', order=9),
        models.Question(text='Организация вывоза мусора (приоритет)', qtype='priority', order=10),
        models.Question(text='Благоустройство территории (приоритет)', qtype='priority', order=11),
        models.Question(text='Безопасность и охрана (приоритет)', qtype='priority', order=12),
        models.Question(text='Обслуживание электросетей (приоритет)', qtype='priority', order=13),
        models.Question(text='Прозрачная отчётность (приоритет)', qtype='priority', order=14),
        models.Question(text='Минимальные взносы (приоритет)', qtype='priority', order=15),
        models.Question(text='Ваши предложения и комментарии', qtype='text', order=16),
        models.Question(text='Предпочитаемый способ коммуникации', qtype='choice', order=17),
        models.Question(text='Email', qtype='text', order=18),
    ]
    db.add_all(questions)
    db.commit()
    return questions 