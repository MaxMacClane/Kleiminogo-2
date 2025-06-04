from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from sqlalchemy.orm import Session
from app.db import get_db
from app import crud, schemas
from app.email_service import send_verification_code
import os
import base64
from datetime import datetime
from pydantic import BaseModel
from uuid import uuid4

router = APIRouter(
    prefix="/survey",
    tags=["survey"]
)

class ConsentData(BaseModel):
    fio: str
    kadastr: str
    phone: str
    email: str
    operator: str
    operator_email: str
    consent: bool
    consent_datetime: str
    screenshot: str  # base64 PNG

class UniqueCheckRequest(BaseModel):
    email: str = None
    kadastr: str = None
    phone: str = None

@router.get("/questions", response_model=list[schemas.QuestionSchema])
def read_questions(db: Session = Depends(get_db)):
    """
    Получить список всех вопросов для опроса.
    """
    return crud.get_questions(db)

@router.post("/responses", status_code=status.HTTP_201_CREATED)
def submit_response(response: schemas.ResponseCreateSchema, db: Session = Depends(get_db)):
    """
    Принять и сохранить ответы пользователя на опрос.
    """
    # Проверяем согласие на обработку персональных данных
    if not response.consent:
        raise HTTPException(status_code=400, detail="Необходимо согласие на обработку персональных данных")
    crud.create_response(db, response)
    return {"message": "Ответ успешно сохранён"}

@router.post('/consent')
async def save_consent(data: ConsentData):
    os.makedirs('consents', exist_ok=True)
    if data.screenshot.startswith('data:image/png;base64,'):
        img_data = base64.b64decode(data.screenshot.split(',')[1])
        filename = f"consents/consent_{data.email}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        with open(filename, 'wb') as f:
            f.write(img_data)
    return {"status": "ok"}

@router.post("/check_unique")
def check_unique(data: UniqueCheckRequest = Body(...), db: Session = Depends(get_db)):
    result = {}
    if data.email:
        result['email_exists'] = crud.is_email_exists(db, data.email)
    if data.kadastr:
        result['kadastr_exists'] = crud.is_kadastr_exists(db, data.kadastr)
    if data.phone:
        result['phone_exists'] = crud.is_phone_exists(db, data.phone)
    return result

@router.post("/check_unfinished")
def check_unfinished(data: UniqueCheckRequest = Body(...), db: Session = Depends(get_db)):
    """
    Проверяет есть ли незавершенная анкета с такими данными
    """
    unfinished = crud.find_unfinished_survey(db, data.email, data.phone, data.kadastr)
    if unfinished:
        return {
            "has_unfinished": True,
            "session_id": unfinished.session_id,
            "created_at": unfinished.created_at.isoformat()
        }
    return {"has_unfinished": False}

@router.post("/send_code", response_model=schemas.CodeResponse)
def send_verification_code_endpoint(data: schemas.SendCodeRequest, db: Session = Depends(get_db)):
    """
    Отправляет код подтверждения на email
    """
    # Создаем код
    code, can_send, seconds_remaining = crud.create_verification_code(db, data.email, data.session_id)
    
    if not can_send:
        return schemas.CodeResponse(
            success=False,
            message=f"Можно запросить новый код через {seconds_remaining} секунд",
            can_request_new=False,
            seconds_until_new_request=seconds_remaining
        )
    
    # Получаем имя пользователя для письма
    response = crud.get_response_by_session(db, data.session_id)
    name = ""
    if response:
        # Ищем ответ с ФИО (question_id = 1)
        fio_answer = db.query(crud.models.Answer).filter(
            crud.models.Answer.response_id == response.id,
            crud.models.Answer.question_id == 1
        ).first()
        if fio_answer:
            name = fio_answer.value.split()[0] if fio_answer.value else ""
    
    # Отправляем email
    email_sent = send_verification_code(data.email, code, name)
    
    if email_sent:
        return schemas.CodeResponse(
            success=True,
            message="Код отправлен на вашу почту"
        )
    else:
        return schemas.CodeResponse(
            success=False,
            message="Ошибка отправки письма. Попробуйте позже."
        )

@router.post("/verify_code", response_model=schemas.CodeResponse)
def verify_verification_code(data: schemas.VerifyCodeRequest, db: Session = Depends(get_db)):
    """
    Проверяет код подтверждения
    """
    success, message = crud.verify_code(db, data.email, data.code, data.session_id)
    
    can_request_new, seconds_remaining = crud.can_request_new_code(db, data.email, data.session_id)
    
    return schemas.CodeResponse(
        success=success,
        message=message,
        can_request_new=can_request_new,
        seconds_until_new_request=seconds_remaining
    )

@router.post("/base")
def save_base(data: schemas.BaseStepSchema, db: Session = Depends(get_db)):
    resp = crud.get_response_by_session(db, data.session_id)
    if not resp:
        resp = crud.create_response_base(db, data.session_id)
    crud.upsert_answers(db, resp.id, [a.dict() for a in data.answers])
    if data.consent:
        crud.update_response_status(db, data.session_id, "consent")
    if data.screenshot:
        os.makedirs('consents', exist_ok=True)
        filename = f"consents/consent_{data.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        with open(filename, 'wb') as f:
            f.write(base64.b64decode(data.screenshot.split(',')[1]))
    return {"status": "ok", "session_id": data.session_id}

@router.post("/details")
def save_details(data: schemas.DetailsStepSchema, db: Session = Depends(get_db)):
    resp = crud.get_response_by_session(db, data.session_id)
    if not resp:
        raise HTTPException(404, "Анкета не найдена")
    crud.upsert_answers(db, resp.id, [a.dict() for a in data.answers])
    crud.update_response_status(db, data.session_id, "complete")
    return {"status": "ok"}