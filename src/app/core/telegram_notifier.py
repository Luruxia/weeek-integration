"""
УВЕДОМЛЕНИЯ В TELEGRAM - ИСПРАВЛЕННАЯ ВЕРСИЯ
"""
import requests
import logging
from datetime import datetime

class TelegramNotifier:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = str(chat_id)  # Убедимся что это строка
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.logger = logging.getLogger(__name__)

    def send_message(self, text, parse_mode="HTML"):
        """Отправить сообщение в Telegram - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        try:
            url = f"{self.base_url}/sendMessage"

            # Очищаем текст от возможных проблем
            clean_text = text.replace('\\', '')  # Убираем обратные слеши

            data = {
                "chat_id": self.chat_id,
                "text": clean_text,
                "parse_mode": parse_mode if parse_mode in ["HTML", "Markdown"] else None,
                "disable_web_page_preview": True
            }

            # Убираем parse_mode если он None
            if data["parse_mode"] is None:
                del data["parse_mode"]

            response = requests.post(url, json=data, timeout=10)

            if response.status_code == 200:
                return True
            else:
                error_msg = f"Telegram error {response.status_code}: {response.text}"
                self.logger.error(error_msg)
                print(f"❌ Telegram error: {response.text}")
                return False

        except Exception as e:
            error_msg = f"Ошибка отправки в Telegram: {e}"
            self.logger.error(error_msg)
            print(f"❌ Exception: {e}")
            return False

    def send_daily_report(self, stats):
        """Отправить ежедневный отчет - УПРОЩЕННАЯ ВЕРСИЯ"""
        report = (
            f"📊 Ежедневный отчет Weeek Integration\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d')}\n"
            f"🔄 Запусков: {stats.get('runs', 0)}\n"
            f"✅ Успешно: {stats.get('successful', 0)}\n"
            f"❌ Ошибок: {stats.get('failed', 0)}\n"
            f"📧 Обработано писем: {stats.get('total_emails', 0)}\n"
            f"⏰ Последний запуск: {stats.get('last_run', 'никогда')}"
        )
        return self.send_message(report, parse_mode=None)  # Без HTML

    def send_error_alert(self, error_msg):
        """Отправить сообщение об ошибке - УПРОЩЕННАЯ ВЕРСИЯ"""
        alert = (
            f"🚨 Ошибка в Weeek Integration!\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}\n"
            f"❌ {error_msg[:200]}"
        )
        return self.send_message(alert, parse_mode=None)  # Без HTML

# Простой тест
if __name__ == "__main__":
    # Твои данные - убедись они в telegram_config.py
    TOKEN = "8537795653:AAEZn1hnSq7hPq2s0tfSeShOxN9xd_iZMvw"
    CHAT_ID = "1702558019"

    notifier = TelegramNotifier(TOKEN, CHAT_ID)

    print("Тестируем отправку...")

    # Тест 1: Простое сообщение
    print("1. Простое сообщение...")
    notifier.send_message("🤖 Тест: Weeek Integration работает!", parse_mode=None)

    # Тест 2: С HTML
    print("2. Сообщение с HTML...")
    notifier.send_message("<b>HTML тест</b> успешен!", parse_mode="HTML")

    print("✅ Проверьте Telegram!")