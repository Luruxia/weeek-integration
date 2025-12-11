"""
АВТОМАТИЧЕСКИЙ ДЕМОН ДЛЯ ИНТЕГРАЦИИ WEEEK
Проверяет письма каждые 10 минут, работает 24/7
"""
import time
import schedule
import subprocess
import logging
import sys
import os
import signal
from datetime import datetime
from pathlib import Path

# ========== ИМПОРТ TELEGRAM ==========
import importlib.util

TELEGRAM_TOKEN = None
TELEGRAM_CHAT_ID = None
TelegramNotifier = None

# Пробуем загрузить Telegram конфиг
try:
    # Путь к конфигу Telegram
    telegram_config_path = os.path.join(os.path.dirname(__file__), '..', 'telegram', 'telegram_config.py')

    if os.path.exists(telegram_config_path):
        # Динамически импортируем конфиг
        spec = importlib.util.spec_from_file_location("telegram_config", telegram_config_path)
        tg_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tg_config)

        TELEGRAM_TOKEN = getattr(tg_config, 'TELEGRAM_TOKEN', None)
        TELEGRAM_CHAT_ID = getattr(tg_config, 'TELEGRAM_CHAT_ID', None)

        # Пробуем импортировать notifier
        telegram_dir = os.path.join(os.path.dirname(__file__), '..', 'telegram')
        if telegram_dir not in sys.path:
            sys.path.append(telegram_dir)

        from telegram_notifier import TelegramNotifier
        print(f"✅ Telegram настроен: {TELEGRAM_TOKEN[:10]}...")
    else:
        print("⚠️  telegram_config.py не найден, работаем без Telegram")

except Exception as e:
    print(f"⚠️  Ошибка загрузки Telegram: {e}")
    # Продолжаем без Telegram
# ===================================================

# Настройка логгирования
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_DIR / 'daemon.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('weeek_daemon')

class Config:
    CHECK_INTERVAL_MINUTES = 10  # Проверять каждые 10 минут
    EMAIL_LIMIT = 5              # Обрабатывать по 5 писем за раз
    PROCESS_TIMEOUT = 300        # Таймаут 5 минут

config = Config()

class SignalHandler:
    """Обработчик сигналов для graceful shutdown"""
    def __init__(self):
        self.shutdown_requested = False
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

    def handle_signal(self, signum, frame):
        logger.info(f"Получен сигнал {signum}, завершение...")
        self.shutdown_requested = True

class WeeekDaemon:
    """Основной демон интеграции"""
    def __init__(self):
        logger.info("Инициализация демона...")
        self.signal_handler = SignalHandler()
        self.stats = {
            'runs': 0,
            'successful': 0,
            'failed': 0,
            'last_run': None,
            'total_emails_processed': 0
        }

        # Инициализация Telegram
        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID and TelegramNotifier:
            try:
                self.notifier = TelegramNotifier(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
                logger.info("Telegram нотификатор инициализирован")

                # Отправляем уведомление о запуске
                self.notifier.send_message(
                    "🤖 <b>Weeek Integration Daemon запущен</b>\n"
                    f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                    "🔄 Проверка каждые 10 минут\n"
                    "━━━━━━━━━━━━━━━━\n"
                    "✅ Система мониторинга активна",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Ошибка инициализации Telegram: {e}")
                self.notifier = None
        else:
            logger.info("Telegram не настроен, работаем без уведомлений")
            self.notifier = None

        self.setup_directories()

    def setup_directories(self):
        """Создание необходимых директорий"""
        dirs = ['logs', '../data/processed', '../data/contacts', '../data/attachments']
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        logger.info("Директории созданы")

    def run_integration(self):
        """Запуск одной проверки интеграции"""
        run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        logger.info(f"Запуск #{self.stats['runs'] + 1} (ID: {run_id})")

        # Уведомление о начале проверки
        if self.notifier:
            self.notifier.send_message(
                f"🔍 <b>Начало проверки #{self.stats['runs'] + 1}</b>\n"
                f"🆔 {run_id}\n"
                f"⏰ {datetime.now().strftime('%H:%M:%S')}",
                parse_mode="HTML"
            )

        try:
            # Запускаем основную интеграцию
            cmd = [
                sys.executable,
                "../complete_integration.py",
                "--limit", str(config.EMAIL_LIMIT)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='cp1251',
                timeout=config.PROCESS_TIMEOUT,
                cwd=os.path.dirname(__file__)
            )

            # ДОБАВЬ ЭТО ДЛЯ ДЕБАГА:
            print("=" * 50)
            print("DEBUG - STDOUT:")
            print(result.stdout[:500] if result.stdout else "пусто")
            print("\nDEBUG - STDERR:")
            print(result.stderr[:500] if result.stderr else "пусто")
            print("=" * 50)

            # И также запиши в лог:
            logger.error(f"STDOUT: {result.stdout[:200] if result.stdout else 'пусто'}")
            logger.error(f"STDERR: {result.stderr[:200] if result.stderr else 'пусто'}")

            # Анализируем результат
            if result.returncode == 0:
                self.stats['successful'] += 1
                logger.info(f"Запуск #{self.stats['runs'] + 1} успешен")

                # Проверяем были ли созданы задачи
                if "Задача создана" in result.stdout or "Task created" in result.stdout:
                    if self.notifier:
                        self.notifier.send_message(
                            f"✅ <b>Новые задачи созданы</b>\n"
                            f"🆔 {run_id}\n"
                            f"📧 Проверка успешно завершена",
                            parse_mode="HTML"
                        )
                elif self.notifier:
                    # Просто успешная проверка без новых задач
                    self.notifier.send_message(
                        f"✅ <b>Проверка завершена</b>\n"
                        f"🆔 {run_id}\n"
                        f"📭 Новых писем не найдено",
                        parse_mode="HTML"
                    )

            else:
                self.stats['failed'] += 1
                logger.error(f"Запуск #{self.stats['runs'] + 1} с ошибкой")

                # Уведомление об ошибке
                if self.notifier:
                    error_msg = result.stderr[:150] if result.stderr else "Неизвестная ошибка"
                    self.notifier.send_message(
                        f"🚨 <b>Ошибка в проверке #{self.stats['runs'] + 1}</b>\n"
                        f"🆔 {run_id}\n"
                        f"❌ {error_msg}\n"
                        f"⏰ {datetime.now().strftime('%H:%M:%S')}",
                        parse_mode="HTML"
                    )

            self.stats['runs'] += 1
            self.stats['last_run'] = datetime.now()

            # Считаем обработанные письма (примерно)
            if "обработано" in result.stdout.lower() or "processed" in result.stdout.lower():
                import re
                match = re.search(r'(\d+)\s+(письм|письма|emails?)', result.stdout, re.IGNORECASE)
                if match:
                    self.stats['total_emails_processed'] += int(match.group(1))

        except subprocess.TimeoutExpired:
            self.stats['failed'] += 1
            self.stats['runs'] += 1
            logger.error(f"Таймаут! Более {config.PROCESS_TIMEOUT} сек")

            if self.notifier:
                self.notifier.send_message(
                    f"⏱️ <b>Таймаут выполнения!</b>\n"
                    f"Запуск #{self.stats['runs']} превысил {config.PROCESS_TIMEOUT} сек\n"
                    f"Проверка будет повторена через {config.CHECK_INTERVAL_MINUTES} мин",
                    parse_mode="HTML"
                )

        except Exception as e:
            self.stats['failed'] += 1
            self.stats['runs'] += 1
            logger.error(f"Неизвестная ошибка: {e}")

            if self.notifier:
                self.notifier.send_message(
                    f"🚨 <b>Критическая ошибка!</b>\n"
                    f"Запуск #{self.stats['runs']}\n"
                    f"❌ {str(e)[:150]}\n"
                    f"⏰ {datetime.now().strftime('%H:%M:%S')}",
                    parse_mode="HTML"
                )

    def print_stats(self):
        """Вывод статистики"""
        logger.info("=" * 60)
        logger.info("СТАТИСТИКА ДЕМОНА")
        logger.info(f"   Всего запусков: {self.stats['runs']}")
        logger.info(f"   Успешных: {self.stats['successful']}")
        logger.info(f"   Неудачных: {self.stats['failed']}")
        logger.info(f"   Обработано писем: {self.stats['total_emails_processed']}")
        logger.info(f"   Последний запуск: {self.stats['last_run']}")
        logger.info("=" * 60)

        # Ежедневный отчет в 19:00
        if self.notifier and datetime.now().hour == 19 and datetime.now().minute < 5:
            report = (
                f"📊 <b>Ежедневный отчет Weeek Integration</b>\n"
                f"📅 {datetime.now().strftime('%Y-%m-%d')}\n"
                f"🔄 Запусков: {self.stats['runs']}\n"
                f"✅ Успешно: {self.stats['successful']}\n"
                f"❌ Ошибок: {self.stats['failed']}\n"
                f"📧 Обработано писем: {self.stats['total_emails_processed']}\n"
                f"⏰ Последний запуск: {self.stats['last_run'].strftime('%H:%M:%S') if self.stats['last_run'] else 'никогда'}"
            )
            self.notifier.send_message(report, parse_mode="HTML")

    def run(self):
        """Основной цикл демона"""
        logger.info("Запуск демона интеграции Weeek")
        logger.info(f"Проверка каждые {config.CHECK_INTERVAL_MINUTES} минут")

        # Настраиваем расписание
        schedule.every(config.CHECK_INTERVAL_MINUTES).minutes.do(self.run_integration)

        # Первый запуск сразу
        logger.info("Первый запуск...")
        self.run_integration()

        logger.info(f"Демон запущен. Следующая проверка через {config.CHECK_INTERVAL_MINUTES} минут")
        self.print_stats()

        # Основной цикл
        while not self.signal_handler.shutdown_requested:
            try:
                schedule.run_pending()
                time.sleep(30)  # Проверяем каждые 30 секунд

                # Раз в час выводим статистику
                if datetime.now().minute == 0 and datetime.now().second < 30:
                    self.print_stats()

            except Exception as e:
                logger.error(f"Ошибка в основном цикле: {e}")
                time.sleep(60)

        logger.info("Завершение демона...")
        if self.notifier:
            self.notifier.send_message(
                "🛑 <b>Weeek Integration Daemon остановлен</b>\n"
                f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                "━━━━━━━━━━━━━━━━\n"
                f"Всего запусков: {self.stats['runs']}\n"
                f"Обработано писем: {self.stats['total_emails_processed']}",
                parse_mode="HTML"
            )
        self.print_stats()

def main():
    """Главная функция"""
    try:
        daemon = WeeekDaemon()
        daemon.run()
    except KeyboardInterrupt:
        logger.info("Демон остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        return 1
    return 0

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 WEEEK INTEGRATION DAEMON")
    print("=" * 50)
    print(f"Версия: Python {sys.version}")
    print(f"Запуск: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Папка: {os.getcwd()}")
    print("=" * 50)

    exit_code = main()
    print(f"\nДемон завершил работу с кодом: {exit_code}")
    sys.exit(exit_code)