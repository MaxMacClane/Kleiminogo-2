from sqlalchemy.orm import Session
from app import models, schemas
from sqlalchemy.exc import IntegrityError
import random
import string
from datetime import datetime, timedelta

# Получить все вопросы (для фронта)
def get_questions(db: Session):
    """
    Возвращает список всех вопросов из таблицы questions, отсортированных по order.
    """
    return db.query(models.Question).order_by(models.Question.order).all()

# Добавить новый ответ пользователя (response + answers)
def create_response(db: Session, response_data: schemas.ResponseCreateSchema):
    """
    Сохраняет один проход опроса (response) и все ответы (answers) в базе данных.
    """
    # Создаём запись о новом респонденте (response)
    db_response = models.Response()
    db.add(db_response)
    db.commit()
    db.refresh(db_response)

    # Для каждого ответа из формы создаём запись в answers
    for answer in response_data.answers:
        db_answer = models.Answer(
            response_id=db_response.id,
            question_id=answer.question_id,
            value=answer.value
        )
        db.add(db_answer)
    db.commit()
    return db_response

# Получить все ответы (для аналитики)
def get_all_responses(db: Session):
    """
    Возвращает все ответы (responses) с их answers для аналитики.
    """
    return db.query(models.Response).all()

# Получить id вопроса по тексту
def get_question_id_by_text(db: Session, text: str):
    q = db.query(models.Question).filter(models.Question.text == text).first()
    return q.id if q else None

# Проверка уникальности email
def is_email_exists(db: Session, email: str):
    email_qid = get_question_id_by_text(db, 'Email')
    if not email_qid:
        return False
    # Проверяем только завершенные анкеты
    answer = db.query(models.Answer).join(models.Response).filter(
        models.Answer.question_id == email_qid, 
        models.Answer.value == email,
        models.Response.status == 'complete'
    ).first()
    return answer is not None

# Проверка уникальности кадастрового номера
def is_kadastr_exists(db: Session, kadastr: str):
    kadastr_qid = get_question_id_by_text(db, 'Кадастровый номер участка')
    if not kadastr_qid:
        return False
    # Проверяем только завершенные анкеты
    answer = db.query(models.Answer).join(models.Response).filter(
        models.Answer.question_id == kadastr_qid, 
        models.Answer.value == kadastr,
        models.Response.status == 'complete'
    ).first()
    return answer is not None

# Проверка уникальности телефона
def is_phone_exists(db: Session, phone: str):
    phone_qid = get_question_id_by_text(db, 'Телефон для связи')
    if not phone_qid:
        return False
    # Проверяем только завершенные анкеты
    answer = db.query(models.Answer).join(models.Response).filter(
        models.Answer.question_id == phone_qid, 
        models.Answer.value == phone,
        models.Response.status == 'complete'
    ).first()
    return answer is not None

# Получить response по session_id
def get_response_by_session(db: Session, session_id: str):
    resp = db.query(models.Response).filter(models.Response.session_id == session_id).first()
    return resp

# Создать новый response (анкета)
def create_response_base(db: Session, session_id: str, status: str = 'draft'):
    resp = models.Response(session_id=session_id, status=status)
    db.add(resp)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        return None
    db.refresh(resp)
    return resp

# Добавить или обновить answers для response
def upsert_answers(db: Session, response_id: int, answers: list):
    for ans in answers:
        existing = db.query(models.Answer).filter_by(response_id=response_id, question_id=ans['question_id']).first()
        if existing:
            existing.value = ans['value']
            # Обновляем поле модерации, если оно передано
            if 'moderated' in ans:
                existing.moderated = ans['moderated']
        else:
            # При создании нового ответа учитываем поле модерации
            moderated = ans.get('moderated', True)  # По умолчанию True
            db.add(models.Answer(
                response_id=response_id, 
                question_id=ans['question_id'], 
                value=ans['value'],
                moderated=moderated
            ))
    db.commit()

# Обновить статус анкеты
def update_response_status(db: Session, session_id: str, status: str):
    resp = get_response_by_session(db, session_id)
    if resp:
        resp.status = status
        db.commit()
    return resp

# Найти незавершенную анкету по данным пользователя
def find_unfinished_survey(db: Session, email: str, phone: str, kadastr: str):
    """
    Ищет незавершенные анкеты (статус draft/consent) по email, телефону или кадастровому номеру
    """
    email_qid = get_question_id_by_text(db, 'Email')
    phone_qid = get_question_id_by_text(db, 'Телефон для связи')
    kadastr_qid = get_question_id_by_text(db, 'Кадастровый номер участка')
    
    # Ищем незавершенные анкеты по email
    if email_qid:
        email_answer = db.query(models.Answer).filter(
            models.Answer.question_id == email_qid, 
            models.Answer.value == email
        ).first()
        if email_answer:
            response = db.query(models.Response).filter(
                models.Response.id == email_answer.response_id,
                models.Response.status.in_(['draft', 'consent'])
            ).first()
            if response:
                return response
    
    # Ищем незавершенные анкеты по телефону
    if phone_qid:
        phone_answer = db.query(models.Answer).filter(
            models.Answer.question_id == phone_qid, 
            models.Answer.value == phone
        ).first()
        if phone_answer:
            response = db.query(models.Response).filter(
                models.Response.id == phone_answer.response_id,
                models.Response.status.in_(['draft', 'consent'])
            ).first()
            if response:
                return response
    
    # Ищем незавершенные анкеты по кадастровому номеру
    if kadastr_qid:
        kadastr_answer = db.query(models.Answer).filter(
            models.Answer.question_id == kadastr_qid, 
            models.Answer.value == kadastr
        ).first()
        if kadastr_answer:
            response = db.query(models.Response).filter(
                models.Response.id == kadastr_answer.response_id,
                models.Response.status.in_(['draft', 'consent'])
            ).first()
            if response:
                return response
    
    return None

# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С КОДАМИ ПОДТВЕРЖДЕНИЯ =====

def generate_verification_code():
    """Генерирует 6-значный код"""
    return ''.join(random.choices(string.digits, k=6))

def create_verification_code(db: Session, email: str, session_id: str):
    """
    Создает новый код подтверждения
    Возвращает (код, можно_ли_отправить, секунд_до_нового_запроса)
    """
    # Проверяем, можно ли запросить новый код (прошло ли 120 секунд)
    last_code = db.query(models.VerificationCode).filter(
        models.VerificationCode.email == email,
        models.VerificationCode.session_id == session_id
    ).order_by(models.VerificationCode.created_at.desc()).first()
    
    if last_code:
        time_since_last = datetime.utcnow() - last_code.last_request_at
        if time_since_last.total_seconds() < 120:  # Меньше 120 секунд
            remaining = 120 - int(time_since_last.total_seconds())
            return None, False, remaining
    
    # Помечаем все старые коды как использованные
    db.query(models.VerificationCode).filter(
        models.VerificationCode.email == email,
        models.VerificationCode.session_id == session_id,
        models.VerificationCode.used == False
    ).update({models.VerificationCode.used: True})
    
    # Создаем новый код
    code = generate_verification_code()
    expires_at = datetime.utcnow() + timedelta(minutes=10)  # 10 минут
    
    verification_code = models.VerificationCode(
        email=email,
        code=code,
        session_id=session_id,
        expires_at=expires_at,
        last_request_at=datetime.utcnow()
    )
    
    db.add(verification_code)
    db.commit()
    
    return code, True, 0

def verify_code(db: Session, email: str, code: str, session_id: str):
    """
    Проверяет код подтверждения
    Возвращает (успех, сообщение)
    """
    verification_code = db.query(models.VerificationCode).filter(
        models.VerificationCode.email == email,
        models.VerificationCode.code == code,
        models.VerificationCode.session_id == session_id,
        models.VerificationCode.used == False
    ).first()
    
    if not verification_code:
        return False, "Неверный код"
    
    if datetime.utcnow() > verification_code.expires_at:
        return False, "Код истек"
    
    # Помечаем код как использованный
    verification_code.used = True
    db.commit()
    
    return True, "Код подтвержден"

def can_request_new_code(db: Session, email: str, session_id: str):
    """
    Проверяет, можно ли запросить новый код
    Возвращает (можно_ли, секунд_до_разрешения)
    """
    last_code = db.query(models.VerificationCode).filter(
        models.VerificationCode.email == email,
        models.VerificationCode.session_id == session_id
    ).order_by(models.VerificationCode.created_at.desc()).first()
    
    if not last_code:
        return True, 0
    
    time_since_last = datetime.utcnow() - last_code.last_request_at
    if time_since_last.total_seconds() >= 120:
        return True, 0
    
    remaining = 120 - int(time_since_last.total_seconds())
    return False, remaining