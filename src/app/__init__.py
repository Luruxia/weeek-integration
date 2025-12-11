# src/app/__init__.py
"""
Пакет Weeek Integration
"""

import os
import sys

# Автоматически экспортируем основные классы
try:
    from .core.mail_client import MailClient
    from .core.weeek_client import WeeekClient
    from .core.telegram_notifier import TelegramNotifier
    from .config.settings import get_settings
    from .utils.logger import setup_logger
    from .processors.email_processor import EmailProcessor
except ImportError as e:
    print(f"Warning: {e}")