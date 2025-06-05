from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from datetime import datetime

# Базовый класс для всех моделей SQLAlchemy
Base = declarative_base()

class Question(Base):
    """
    Таблица вопросов опроса.
    Каждый вопрос имеет текст, тип и порядок отображения.
    """
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True)  # Уникальный идентификатор вопроса
    text = Column(Text, nullable=False)  # Текст вопроса
    qtype = Column(String, nullable=False)  # Тип вопроса (choice, text, checkbox и т.д.)
    order = Column(Integer, nullable=False)  # Порядок отображения вопроса
    
    # Связь с ответами
    answers = relationship("Answer", back_populates="question")

    def __repr__(self):
        return f"<Question id={self.id} text='{self.text[:50]}...' type={self.qtype} order={self.order}>"

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
    Таблица отдельных ответов на каждый вопрос.
    Каждый ответ связан с конкретным респондентом (response_id) и вопросом (question_id).
    """
    __tablename__ = "answers"
    id = Column(Integer, primary_key=True)  # Уникальный идентификатор ответа
    response_id = Column(Integer, ForeignKey("responses.id"), nullable=False)  # Связь с респондентом
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)  # Связь с вопросом
    value = Column(Text, nullable=False)  # Значение ответа (текст или выбранный вариант)
    moderated = Column(Boolean, default=True, nullable=False)  # Прошёл ли ответ модерацию (False для мата/спама)

    # Связи
    response = relationship("Response", back_populates="answers")
    question = relationship("Question", back_populates="answers")
    
    # Связь с лайками для этого ответа (если это комментарий)
    likes = relationship("CommentLike", back_populates="answer")

    def __repr__(self):
        return f"<Answer id={self.id} response_id={self.response_id} question_id={self.question_id} value='{self.value[:50]}...' moderated={self.moderated}>"

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

class CommentLike(Base):
    """
    Таблица лайков для комментариев.
    Каждый лайк привязан к конкретному ответу (Answer) и IP-адресу для предотвращения повторных лайков.
    """
    __tablename__ = "comment_likes"
    id = Column(Integer, primary_key=True)
    answer_id = Column(Integer, ForeignKey("answers.id"), nullable=False)  # Ответ, который лайкнули
    ip_address = Column(String(45), nullable=False)  # IP-адрес пользователя (IPv4/IPv6)
    created_at = Column(DateTime, server_default=func.now())  # Время лайка

    # Связь с ответом
    answer = relationship("Answer", back_populates="likes")

    # Уникальность: один IP может лайкнуть комментарий только один раз
    __table_args__ = (UniqueConstraint('answer_id', 'ip_address'),)

    def __repr__(self):
        return f"<CommentLike id={self.id} answer_id={self.answer_id} ip={self.ip_address}>"
