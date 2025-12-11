"""
Инициализация конфигурации
"""

import sys
from .settings import settings

__all__ = ['settings']

# Проверка обязательных настроек
def validate_config():
    """Проверить обязательные настройки"""
    required = [
        ('WEEEK_API_KEY', settings.WEEEK_API_KEY),
        ('GMAIL_EMAIL', settings.GMAIL_EMAIL),
        ('GMAIL_APP_PASSWORD', settings.GMAIL_APP_PASSWORD),
    ]

    missing = []
    for name, value in required:
        if not value:
            missing.append(name)

    if missing:
        print(f"❌ Отсутствуют обязательные настройки: {', '.join(missing)}")
        print("Создайте config/secrets.py с этими настройками")
        sys.exit(1)

# Автоматическая проверка при импорте
validate_config()
