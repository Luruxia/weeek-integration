# send_test_email.py - УПРОЩЕННАЯ ВЕРСИЯ БЕЗ WEEEK
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


def send_test_email():
    """Отправляет тестовое письмо себе"""

    # 1. ЗАГРУЖАЕМ ТОЛЬКО GMAIL ДАННЫЕ
    try:
        # Пробуем загрузить из secrets.py
        from config.secrets import GMAIL_EMAIL, GMAIL_APP_PASSWORD
    except ImportError:
        # Или из переменных окружения
        GMAIL_EMAIL = os.getenv("GMAIL_EMAIL")
        GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

        if not GMAIL_EMAIL or not GMAIL_APP_PASSWORD:
            print("❌ ОШИБКА: Не найдены Gmail данные!")
            print("Добавьте в config/secrets.py:")
            print("GMAIL_EMAIL = 'ваш_email@gmail.com'")
            print("GMAIL_APP_PASSWORD = 'ваш_пароль_приложения'")
            return

    # 2. НАСТРАИВАЕМ ПИСЬМО
    sender_email = GMAIL_EMAIL
    receiver_email = GMAIL_EMAIL  # Отправляем себе
    password = GMAIL_APP_PASSWORD

    # Создаём письмо
    msg = MIMEMultipart()
    msg['From'] = 'Пипа Пупа <Pipa@SeksPiski.ru>'
    msg['To'] = receiver_email
    msg['Subject'] = 'Предложение о сотрудничестве от ООО SeksPiski'

    # Тело письма
    body = """Уважаемый коллега,

Мы, компания ООО "SeksPiski", занимаемся разработкой CRM-систем.
Хотим предложить вам сотрудничество в области интеграции с вашей платформой.

Наши предложения:
1. Интеграция API между нашими системами
2. Совместная разработка модулей
3. Реферальная программа

Бюджет проекта: от 500 000 руб.
Сроки: 3-6 месяцев

Ждём вашего ответа!

С уважением,
Пипа Пупа
CEO ООО 'Секс Письки'
Pipa@seksPiski.ru
+7 (999) 123-45-67
"""

    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    # 3. ОТПРАВЛЯЕМ
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
            server.login(sender_email, password)
            server.send_message(msg)

        print("✅ Тестовое письмо отправлено!")
        print(f"От: {msg['From']}")
        print(f"Кому: {msg['To']}")
        print(f"Тема: {msg['Subject']}")
        print(f"Отправлено через: {sender_email}")

    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        print("\nПроверь:")
        print("1. Gmail пароль приложения (16 знаков)")
        print("2. Разрешения для 'ненадёжных приложений'")
        print("3. Двухфакторную аутентификацию")


if __name__ == "__main__":
    send_test_email()
