#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
from openai import OpenAI
from typing import Tuple, Optional
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

class AICommentFilter:
    def __init__(self):
        """Инициализация AI-фильтра комментариев на базе DeepSeek"""
        # Получаем API ключ из переменных окружения
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            logger.warning("DEEPSEEK_API_KEY не найден в переменных окружения")
            self.client = None
            self.use_ai = False
        else:
            # Инициализируем клиент DeepSeek (совместим с OpenAI API)
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )
            self.use_ai = True
        
        # Минимальная длина осмысленного комментария
        self.min_length = 10
        self.max_length = 2000
        
        # Базовые паттерны для быстрой предварительной проверки
        self.basic_patterns = [
            r'(.)\1{4,}',  # Повторение символа более 4 раз подряд
            r'^[0-9]+$',   # Только цифры
            r'^[a-zA-Z]+$', # Только латиница без русских букв
        ]
        
        # Системный промпт для AI модерации
        self.moderation_prompt = """Ты модератор комментариев на сайте российского дачного поселка "Клеймёново-2". 

Отклоняй комментарии ТОЛЬКО если они содержат:
1. Нецензурная лексика (мат, оскорбления)
2. Агрессия, угрозы, призывы к насилию
3. Очевидный спам (повторяющиеся символы, бессмысленный набор букв)

РАЗРЕШАЙ:
- Короткие приветствия ("Здравствуйте", "Как дела")
- Простые вопросы и комментарии
- Любые вежливые обращения
- Краткие мнения и предложения

Ответь ТОЛЬКО в формате JSON:
{
    "approved": true/false,
    "reason": "краткая причина отклонения или 'OK'"
}

Комментарий: """

    def _basic_validation(self, text: str) -> Tuple[bool, str]:
        """Базовая валидация без AI"""
        if not text or not text.strip():
            return False, "Пустой комментарий"
        
        text = text.strip()
        
        # Проверка длины
        if len(text) < self.min_length:
            return False, f"Комментарий слишком короткий (минимум {self.min_length} символов)"
        
        if len(text) > self.max_length:
            return False, f"Комментарий слишком длинный (максимум {self.max_length} символов)"
        
        # Проверка базовых паттернов
        for pattern in self.basic_patterns:
            if re.search(pattern, text):
                if pattern == r'(.)\1{4,}':
                    return False, "Слишком много повторяющихся символов"
                elif pattern == r'^[0-9]+$':
                    return False, "Комментарий состоит только из цифр"
                elif pattern == r'^[a-zA-Z]+$':
                    return False, "Комментарий должен содержать русские буквы"
        
        # Проверка на содержательность
        words = text.split()
        if len(words) < 2:
            return False, "Комментарий должен содержать минимум 2 слова"
        
        # Проверка на наличие русских букв
        if not re.search(r'[а-яёА-ЯЁ]', text):
            return False, "Комментарий должен содержать русские буквы"
        
        return True, "OK"

    def _ai_moderation(self, text: str) -> Tuple[bool, str]:
        """AI модерация через DeepSeek"""
        if not self.use_ai or not self.client:
            # Fallback на базовую проверку если AI недоступен
            logger.warning("AI модерация недоступна, используем базовую проверку")
            return True, "OK"  # Пропускаем если AI недоступен
        
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "user", "content": self.moderation_prompt + text}
                ],
                temperature=0.1,  # Низкая температура для более предсказуемых результатов
                max_tokens=100,
                timeout=10  # Таймаут 10 секунд
            )
            
            result_text = response.choices[0].message.content.strip()
            logger.info(f"AI модерация ответ: {result_text}")
            
            # Убираем markdown блоки если есть
            if result_text.startswith('```json'):
                result_text = result_text.replace('```json', '').replace('```', '').strip()
            elif result_text.startswith('```'):
                result_text = result_text.replace('```', '').strip()
            
            # Парсим JSON ответ
            import json
            try:
                result = json.loads(result_text)
                approved = result.get('approved', True)
                reason = result.get('reason', 'OK')
                
                return approved, reason
                
            except json.JSONDecodeError:
                logger.error(f"Ошибка парсинга JSON от AI: {result_text}")
                # Fallback: ищем ключевые слова в ответе
                if 'false' in result_text.lower() or 'отклонен' in result_text.lower():
                    return False, "Комментарий не прошёл AI модерацию"
                return True, "OK"
                
        except Exception as e:
            logger.error(f"Ошибка AI модерации: {e}")
            # В случае ошибки пропускаем комментарий
            return True, "OK"

    def is_valid_comment(self, text: str) -> Tuple[bool, str]:
        """
        Полная проверка валидности комментария
        
        Returns:
            (is_valid: bool, reason: str)
        """
        # Сначала базовая валидация
        is_valid, reason = self._basic_validation(text)
        if not is_valid:
            return is_valid, reason
        
        # Затем AI модерация
        return self._ai_moderation(text)
    
    def get_toxicity_score(self, text: str) -> float:
        """
        Возвращает уровень токсичности от 0.0 до 1.0
        Пока простая реализация, можно расширить через AI
        """
        if not text:
            return 0.0
        
        score = 0.0
        
        # Проверяем подозрительные паттерны
        for pattern in self.basic_patterns:
            if re.search(pattern, text):
                score += 0.2
        
        # Проверяем длину
        if len(text.strip()) < 10:
            score += 0.3
        
        # Проверяем количество ЗАГЛАВНЫХ БУКВ
        upper_ratio = sum(1 for c in text if c.isupper()) / len(text) if text else 0
        if upper_ratio > 0.5:  # Больше 50% заглавных
            score += 0.3
        
        # TODO: Можно добавить AI оценку токсичности
        
        return min(score, 1.0)

# Глобальный экземпляр фильтра
comment_filter = AICommentFilter()

def validate_comment(text: str) -> Tuple[bool, str]:
    """
    Валидация комментария через AI
    
    Returns:
        (is_valid: bool, message: str)
    """
    return comment_filter.is_valid_comment(text)

def get_comment_toxicity(text: str) -> float:
    """
    Получить уровень токсичности комментария
    """
    return comment_filter.get_toxicity_score(text) 