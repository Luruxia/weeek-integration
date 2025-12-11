# config/settings.py - БЕЗОПАСНАЯ ВЕРСИЯ
import os
import sys
from pathlib import Path
from typing import Optional

# Путь к корню проекта
BASE_DIR = Path(__file__).parent.parent


class ConfigError(Exception):
    """Ошибка конфигурации"""
    pass


def load_secrets() -> dict:
    """
    БЕЗОПАСНАЯ загрузка секретов.
    Либо из secrets.py, либо из env, но НИКОГДА не создаём dummy файлы!
    """
    secrets = {}

    # 1. Попробовать загрузить из secrets.py
    try:
        from .secrets import (
            WEEEK_API_KEY,
            GMAIL_EMAIL,
            GMAIL_APP_PASSWORD,
            WEEEK_BASE_URL,
            WEEEK_CONTACT_LIST_ID,
            WEEEK_WORKSPACE_ID
        )
        secrets.update({
            'WEEEK_API_KEY': WEEEK_API_KEY,
            'GMAIL_EMAIL': GMAIL_EMAIL,
            'GMAIL_APP_PASSWORD': GMAIL_APP_PASSWORD,
            'WEEEK_BASE_URL': WEEEK_BASE_URL,
            'WEEEK_CONTACT_LIST_ID': WEEEK_CONTACT_LIST_ID,
            'WEEEK_WORKSPACE_ID': WEEEK_WORKSPACE_ID
        })
        return secrets

    except ImportError as e:
        # 2. Загрузить из переменных окружения
        secrets['WEEEK_API_KEY'] = os.getenv('WEEEK_API_KEY')
        secrets['GMAIL_EMAIL'] = os.getenv('GMAIL_EMAIL')
        secrets['GMAIL_APP_PASSWORD'] = os.getenv('GMAIL_APP_PASSWORD')
        secrets['WEEEK_BASE_URL'] = os.getenv('WEEEK_BASE_URL', 'https://api.weeek.net/public/v1')
        secrets['WEEEK_CONTACT_LIST_ID'] = os.getenv('WEEEK_CONTACT_LIST_ID')
        secrets['WEEEK_WORKSPACE_ID'] = os.getenv('WEEEK_WORKSPACE_ID')

        # 3. ПРОВЕРИТЬ что хотя бы API ключ есть
        if not secrets['WEEEK_API_KEY']:
            raise ConfigError(
                "❌ WEEEK_API_KEY не найден!\n"
                "Создайте config/secrets.py или установите переменную окружения WEEEK_API_KEY\n"
                "Смотрите config/secrets_example.py для примера"
            )

        return secrets


# Загружаем секреты
try:
    SECRETS = load_secrets()
except ConfigError as e:
    print(f"ОШИБКА КОНФИГУРАЦИИ: {e}")
    sys.exit(1)


# Настройки приложения
class Settings:
    # Weeek API
    WEEEK_API_KEY: str = SECRETS['WEEEK_API_KEY']
    WEEEK_BASE_URL: str = SECRETS.get('WEEEK_BASE_URL', 'https://api.weeek.net/public/v1')
    WEEEK_CONTACT_LIST_ID: Optional[str] = SECRETS.get('WEEEK_CONTACT_LIST_ID')

    WEEEK_WORKSPACE_ID: Optional[str] = SECRETS.get('WEEEK_WORKSPACE_ID')

    # Gmail
    GMAIL_EMAIL: str = SECRETS['GMAIL_EMAIL']
    GMAIL_APP_PASSWORD: str = SECRETS['GMAIL_APP_PASSWORD']
    IMAP_SERVER: str = 'imap.gmail.com'
    IMAP_PORT: int = 993
    IMAP_USE_SSL: bool = True

    IMAP_USERNAME: str = SECRETS['GMAIL_EMAIL']
    IMAP_PASSWORD: str = SECRETS['GMAIL_APP_PASSWORD']

    # Обработка писем
    PROCESS_LIMIT: int = 50  # Максимум писем за один запуск
    RETRY_ATTEMPTS: int = 3  # Количество попыток retry

    # Логирование
    LOG_LEVEL: str = 'INFO'
    LOG_FILE: str = str(BASE_DIR / 'logs' / 'integration.log')

    # Паузы между запросами (секунды)
    REQUEST_DELAY: float = 0.5

    # Игнорируемые отправители
    IGNORE_PATTERNS: list = [
        'no-reply', 'noreply', 'donotreply',
        'notification', 'notifications',
        'auto', 'automatic', 'mailer'
    ]


# Экспортируем настройки
settings = Settings()
