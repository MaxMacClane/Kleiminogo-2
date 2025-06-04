import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from typing import Optional
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройки SMTP (используем данные из скриншота)
SMTP_SERVER = "smtp.jino.ru"
SMTP_PORT = 465  # SSL
SMTP_USERNAME = "admin@tylermacclane.site"
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")  # Пароль из переменной окружения

def send_verification_code(email: str, code: str, name: str = "") -> bool:
    """
    Отправляет код подтверждения на email
    Возвращает True если отправлено успешно
    """
    try:
        # Создаем сообщение
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Код подтверждения - ДНП "Клеймёново-2"'
        msg['From'] = SMTP_USERNAME
        msg['To'] = email
        
        # HTML содержимое письма
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .code {{ background: #fff; border: 2px solid #667eea; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; color: #667eea; border-radius: 8px; margin: 20px 0; letter-spacing: 3px; }}
                .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>ДНП "Клеймёново-2"</h1>
                    <p>Код подтверждения для продолжения опроса</p>
                </div>
                <div class="content">
                    <p>Здравствуйте{', ' + name if name else ''}!</p>
                    
                    <p>Вы запросили код подтверждения для продолжения заполнения опроса о создании нового СНТ.</p>
                    
                    <div class="code">{code}</div>
                    
                    <div class="warning">
                        <strong>Важно:</strong><br>
                        • Код действует 10 минут с момента отправки<br>
                        • Новый код можно запросить через 2 минуты<br>
                        • Используйте код только на официальном сайте опроса
                    </div>
                    
                    <p>Если вы не запрашивали этот код, просто проигнорируйте это письмо.</p>
                    
                    <p>С уважением,<br>Инициативная группа жителей ДНП "Клеймёново-2"</p>
                </div>
                <div class="footer">
                    <p>Это автоматическое письмо. Не отвечайте на него.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Текстовая версия
        text_body = f"""
        Код подтверждения для ДНП "Клеймёново-2"
        
        Здравствуйте{', ' + name if name else ''}!
        
        Ваш код подтверждения: {code}
        
        Код действует 10 минут с момента отправки.
        Новый код можно запросить через 2 минуты.
        
        Если вы не запрашивали этот код, просто проигнорируйте это письмо.
        
        С уважением,
        Инициативная группа жителей ДНП "Клеймёново-2"
        """
        
        # Добавляем обе версии
        msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        # Отправляем
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        
        return True
        
    except Exception as e:
        print(f"Ошибка отправки email: {e}")
        return False 