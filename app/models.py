from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from datetime import datetime

# Базовый класс для всех моделей SQLAlchemy
Base = declarative_base()

class Question(Base):
    """
    Таблица вопросов опроса.
    Каждый вопрос хранится отдельно, чтобы можно было динамически менять структуру опроса.
    """
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True)  # Уникальный идентификатор вопроса
    text = Column(String, nullable=False)   # Текст вопроса (например: "ФИО", "Поддерживаете создание СНТ?")
    qtype = Column(String, nullable=False)  # Тип вопроса (text, choice, number и т.д.)
    order = Column(Integer, nullable=False) # Порядок отображения вопроса в форме

class Response(Base):
    """
    Таблица ответов пользователей.
    Каждый респондент (один проход опроса) — это одна запись в этой таблице.
    """
    __tablename__ = "responses"
    id = Column(Integer, primary_key=True)  # Уникальный идентификатор ответа (респондента)
    session_id = Column(String, unique=True, nullable=False)  # Уникальный идентификатор сессии/анкеты
    status = Column(String, default='draft', nullable=False)  # Статус анкеты: draft/complete
    created_at = Column(DateTime, server_default=func.now())  # Время заполнения

    # Связь: один ответ (response) содержит много отдельных ответов на вопросы (answers)
    answers = relationship("Answer", back_populates="response")

    def __repr__(self):
        return f"<Response id={self.id} session_id={self.session_id} status={self.status} created_at={self.created_at}>"

class Answer(Base):
    """
    Таблица индивидуальных ответов на вопросы.
    Каждый ответ на отдельный вопрос — это отдельная запись.
    """
    __tablename__ = "answers"
    id = Column(Integer, primary_key=True)  # Уникальный идентификатор записи
    response_id = Column(Integer, ForeignKey("responses.id"))   # Ссылка на респондента (response)
    question_id = Column(Integer, ForeignKey("questions.id"))   # Ссылка на вопрос (question)
    value = Column(Text, nullable=False)                        # Значение ответа (текст, число, вариант и т.д.)

    # Связь с таблицей Response (один response — много answers)
    response = relationship("Response", back_populates="answers")
    # Можно добавить связь с Question, если нужно получать текст вопроса из ответа
    # question = relationship("Question")

    def __repr__(self):
        return f"<Answer id={self.id} response_id={self.response_id} question_id={self.question_id} value={self.value[:30] if self.value else ''}>"

class VerificationCode(Base):
    """
    Таблица для хранения кодов подтверждения email
    """
    __tablename__ = "verification_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    code = Column(String(6), nullable=False)  # 6-значный код
    session_id = Column(String(255), nullable=False)  # связь с анкетой
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)  # когда истекает код
    used = Column(Boolean, default=False)  # использован ли код
    last_request_at = Column(DateTime, default=datetime.utcnow)  # когда последний раз запрашивали код
