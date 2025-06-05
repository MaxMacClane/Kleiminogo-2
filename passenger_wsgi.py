#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# Активируем виртуальное окружение
venv_path = '/home/users/j/j01384090/miniconda3/envs/kleymenovo'
if os.path.exists(venv_path):
    sys.path.insert(0, os.path.join(venv_path, 'lib', 'python3.11', 'site-packages'))

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(__file__))

# Импортируем приложение FastAPI
from app.main import app

# Для Джино хостинга - используем a2wsgi для конвертации ASGI в WSGI
from a2wsgi import ASGIMiddleware
application = ASGIMiddleware(app) 