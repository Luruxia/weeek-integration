# core/mail_sender.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

class MailSender:
    """Простой класс для отправки emails через SMTP"""

    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.username = settings.IMAP_USERNAME
        self.password = settings.IMAP_PASSWORD
        self.use_ssl = settings.SMTP_USE_SSL

    def send_email(self, to_email: str, subject: str, body: str,
                   in_reply_to: str = None) -> bool:
        """Отправить простой email (без вложений)"""
        try:
            # Создаем сообщение
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = to_email
            msg['Subject'] = subject

            # Добавляем headers для ответа
            if in_reply_to:
                msg['In-Reply-To'] = in_reply_to
                msg['References'] = in_reply_to

            # Текст письма
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # Подключаемся и отправляем
            if self.use_ssl:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as smtp:
                    smtp.login(self.username, self.password)
                    smtp.send_message(msg)
            else:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as smtp:
                    smtp.starttls()
                    smtp.login(self.username, self.password)
                    smtp.send_message(msg)

            logger.info(f"✅ Email отправлен на {to_email}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка отправки email: {e}")
            return False

    def send_reply(self, original_email: dict, reply_text: str) -> bool:
        """Отправить ответ на оригинальное письмо"""
        subject = f"Re: {original_email.get('subject', '')}"

        return self.send_email(
            to_email=original_email.get('from_email'),
            subject=subject,
            body=reply_text,
            in_reply_to=original_email.get('message_id')
        )
