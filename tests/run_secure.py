#!/usr/bin/env python3
"""Безопасный запуск интеграции с retry и логированием"""
import sys
import os
from utils.logging_config import setup_logging, get_logger

# Настройка логирования
setup_logging(
    level='INFO',
    log_file='logs/integration.log',
    json_format=False
)
logger = get_logger(__name__)

def main():
    """Основная функция"""
    logger.info("=" * 60)
    logger.info("ЗАПУСК ИНТЕГРАЦИИ GMAIL-WEEEK С RETRY МЕХАНИЗМОМ")
    logger.info("=" * 60)

    try:
        # Импортируем основную логику
        from complete_integration import main as integration_main

        # Запускаем
        integration_main()

        logger.info("✅ Интеграция успешно завершена")

    except KeyboardInterrupt:
        logger.warning("⏹️  Интеграция прервана пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в интеграции: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    # Создаем папку для логов если её нет
    os.makedirs('logs', exist_ok=True)
    main()
