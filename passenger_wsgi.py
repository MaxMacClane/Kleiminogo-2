#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(__file__))

# Импортируем приложение FastAPI
from app.main import app

# Для Джино хостинга - используем asgiref для конвертации ASGI в WSGI
try:
    from asgiref.wsgi import WsgiToAsgi
    # Создаем WSGI приложение из FastAPI (ASGI)
    application = WsgiToAsgi(app)
except ImportError:
    # Если asgiref не установлен, простая заглушка
    def application(environ, start_response):
        start_response('200 OK', [('Content-Type', 'text/plain; charset=utf-8')])
        return [b"FastAPI app error: asgiref not installed"] 