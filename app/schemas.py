from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# Схема для вопроса (то, что отдаём на фронт)
class QuestionSchema(BaseModel):
    id: int
    text: str
    qtype: str
    order: int

    class Config:
        orm_mode = True  # Позволяет использовать SQLAlchemy-объекты напрямую

# Схема для одного ответа на вопрос (приём с фронта)
class AnswerCreateSchema(BaseModel):
    question_id: int
    value: str

# Схема для всего ответа пользователя (один проход опроса)
class ResponseCreateSchema(BaseModel):
    answers: List[AnswerCreateSchema]
    consent: bool = Field(..., description="Согласие на обработку персональных данных (ФЗ-152)")

# Схема для отображения ответа (например, для аналитики)
class AnswerSchema(BaseModel):
    question_id: int
    value: str

    class Config:
        orm_mode = True

class ResponseSchema(BaseModel):
    id: int
    created_at: str
    answers: List[AnswerSchema]

    class Config:
        orm_mode = True

# --- Поэтапные схемы ---
class BaseStepSchema(BaseModel):
    session_id: str
    answers: List[AnswerCreateSchema]
    consent: bool
    screenshot: Optional[str] = None

class DetailsStepSchema(BaseModel):
    session_id: str
    answers: List[AnswerCreateSchema]

class SendCodeRequest(BaseModel):
    """Запрос на отправку кода подтверждения"""
    email: str
    session_id: str

class VerifyCodeRequest(BaseModel):
    """Запрос на проверку кода"""
    email: str
    code: str
    session_id: str

class CodeResponse(BaseModel):
    """Ответ с информацией о коде"""
    success: bool
    message: str
    can_request_new: bool = False
    seconds_until_new_request: int = 0