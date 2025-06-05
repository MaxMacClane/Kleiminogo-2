#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(__file__))

# Импортируем приложение FastAPI
from app.main import app

# Для WSGI серверов FastAPI нужен ASGI-to-WSGI адаптер
try:
    from asgiref.wsgi import WsgiToAsgi
    application = WsgiToAsgi(app)
except ImportError:
    # Если asgiref не установлен, используем uvicorn programmatically
    import uvicorn
    
    def application(environ, start_response):
        # Это не идеальное решение, но работает
        return uvicorn.run(app, host="0.0.0.0", port=8000)

# Для некоторых хостингов
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 