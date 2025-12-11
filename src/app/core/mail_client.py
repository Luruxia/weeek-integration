import imaplib
import email
import re
import logging
import os
from typing import List, Dict, Optional
from datetime import datetime
from utils.retry import retry_imap
from email.header import decode_header


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class MailClient:
    """Клиент для работы с IMAP почтой"""

    def __init__(self):
        self.mail = None
        self.selected_folder = None
        self.is_connected = False

    @retry_imap(max_attempts=3, delay=3.0)
    def connect(self):
        """Подключение к IMAP серверу"""
        try:
            from config.settings import settings

            logger.info(f"Подключение к IMAP: {settings.IMAP_SERVER}:{settings.IMAP_PORT}")

            if settings.IMAP_USE_SSL:
                self.mail = imaplib.IMAP4_SSL(settings.IMAP_SERVER, settings.IMAP_PORT)
            else:
                self.mail = imaplib.IMAP4(settings.IMAP_SERVER, settings.IMAP_PORT)

            self.mail.login(settings.IMAP_USERNAME, settings.IMAP_PASSWORD)
            self.is_connected = True
            logger.info("Успешное подключение к почте")
            return True

        except Exception as e:
            logger.error(f"Ошибка подключения к почте: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """Отключиться от почтового сервера"""
        try:
            if self.mail:
                self.mail.logout()
                self.mail = None
                self.selected_folder = None
                self.is_connected = False
                logger.info("Отключились от почты")
        except:
            pass

    def select_folder(self, folder: str = 'INBOX') -> bool:
        """Выбрать папку"""
        try:
            if not self.is_connected or not self.mail:
                return False

            status, messages = self.mail.select(folder)
            if status == 'OK':
                self.selected_folder = folder
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка выбора папки {folder}: {e}")
            return False

    def get_unread_emails(self, limit: int = 10) -> List[Dict]:
        """Получить непрочитанные письма"""
        emails = []

        try:
            if not self.is_connected or not self.mail:
                if not self.connect():
                    return emails

            # Выбираем папку INBOX
            self.select_folder('INBOX')

            # Ищем непрочитанные письма
            status, messages = self.mail.search(None, 'UNSEEN')

            if status != 'OK':
                logger.warning("Не удалось найти письма")
                return emails

            message_ids = messages[0].split()
            logger.info(f"Найдено {len(message_ids)} непрочитанных писем")

            # Ограничиваем количество
            if limit > 0:
                message_ids = message_ids[-limit:]  # Берем самые новые

            for msg_id in message_ids:
                email_data = self._fetch_email(msg_id)
                if email_data:
                    emails.append(email_data)

        except Exception as e:
            logger.error(f"Ошибка получения писем: {e}")

        return emails

    def _fetch_email(self, msg_id) -> Optional[Dict]:
        """Получить конкретное письмо по ID"""
        try:
            status, msg_data = self.mail.fetch(msg_id, '(RFC822)')

            if status != 'OK':
                return None

            # Парсим письмо
            msg = email.message_from_bytes(msg_data[0][1])

            # Получаем заголовки
            subject, encoding = decode_header(msg.get("Subject") or "")[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or 'utf-8', errors='ignore')

            from_header = msg.get("From", "")
            from_name, from_email = self._parse_email_address(from_header)

            # ДЛЯ ОТЛАДКИ
            logger.debug(f"Парсинг From: '{from_header}' -> name='{from_name}', email='{from_email}'")

            date_str = msg.get("Date", "")
            date_obj = self._parse_date(date_str)

            # Получаем тело письма
            body_text = self._get_email_body(msg)

            # Получаем вложения
            attachments = self._get_attachments(msg)

            # Message ID
            message_id = msg.get("Message-ID", "").strip("<>")

            return {
                'uid': msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id),
                'message_id': message_id,
                'subject': subject or "",
                'from_name': from_name,
                'from_email': from_email,
                'date': date_obj,
                'body_text': body_text,
                'attachments': attachments,
                'raw_message': msg
            }

        except Exception as e:
            logger.error(f"Ошибка парсинга письма {msg_id}: {e}")
            return None

    def _decode_header(self, header):
        """Декодировать email заголовок"""
        from email.header import decode_header
        decoded_parts = decode_header(header)
        result = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                result += part.decode(encoding or 'utf-8', errors='ignore')
            else:
                result += part
        return result

    def _parse_email_address(self, address_str: str):
        """Парсить email адрес с валидацией"""
        try:
            from email.utils import parseaddr

            if not address_str:
                return "", ""

            decoded_header = self._decode_header(address_str)
            name, addr = parseaddr(decoded_header)

            # ВАЛИДАЦИЯ EMAIL
            if addr and not self._is_valid_email(addr):
                logger.warning(f"Некорректный email адрес: {addr}")
                addr = ""

            if name:
                name = self._decode_header(name)
                name = re.sub(r'\s*<[^>]+>', '', name)
                name = re.sub(r'\S+@\S+\.\S+', '', name)
                name = name.strip().strip('"\'')

            return name.strip(), addr.strip()

        except Exception as e:
            logger.error(f"Ошибка парсинга email адреса: {e}")
            return "", ""

    def _is_valid_email(self, email: str) -> bool:
        """Проверка валидности email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def _parse_date(self, date_str: str):
        """Парсить дату письма"""
        try:
            # Пробуем разные форматы
            date_tuple = email.utils.parsedate_tz(date_str)
            if date_tuple:
                timestamp = email.utils.mktime_tz(date_tuple)
                return datetime.fromtimestamp(timestamp)
        except:
            pass

        try:
            # Пробуем свой парсинг
            date_str_clean = re.sub(r'\(.*?\)', '', date_str).strip()
            return datetime.strptime(date_str_clean, '%a, %d %b %Y %H:%M:%S %z')
        except:
            pass

        return datetime.now()

    def _get_email_body(self, msg) -> str:
        """Получить текстовое тело письма (предпочитаем plain text)"""
        body = ""

        if msg.is_multipart():
            # Сначала ищем plain text
            plain_text = ""
            html_text = ""

            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                if "attachment" in content_disposition:
                    continue

                if content_type == "text/plain":
                    plain_text = self._decode_part(part)
                    if plain_text:
                        break  # Предпочитаем plain text

                elif content_type == "text/html":
                    html_text = self._decode_part(part)

            # Используем plain text или конвертируем HTML
            if plain_text:
                body = plain_text
            elif html_text:
                # Простая конвертация HTML в текст
                from html import unescape
                import re
                clean_html = re.sub(r'<[^>]+>', ' ', html_text)
                body = unescape(clean_html).strip()

        else:
            body = self._decode_part(msg)

        return body.strip()

    def _decode_part(self, part):
        """Декодировать часть письма"""
        try:
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset() or 'utf-8'
            return payload.decode(charset, errors='ignore')
        except:
            return ""

    def _get_attachments(self, msg) -> List[Dict]:
        """Получить вложения с корректной обработкой имен файлов"""
        attachments = []

        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = str(part.get("Content-Disposition", ""))

                if "attachment" in content_disposition.lower():
                    try:
                        filename = part.get_filename()
                        if filename:
                            # ИСПРАВЛЕННАЯ обработка имени файла
                            safe_filename = self._safe_decode_filename(filename)

                            # Получаем содержимое файла
                            payload = part.get_payload(decode=True)

                            # Проверяем что файл не пустой
                            if payload and len(payload) > 0:
                                attachments.append({
                                    'filename': safe_filename,
                                    'size': len(payload),
                                    'payload': payload,
                                    'content_type': part.get_content_type() or 'application/octet-stream'
                                })
                                logger.debug(f"Вложение сохранено: {safe_filename} ({len(payload)} байт)")
                            else:
                                logger.warning(f"Пустое вложение: {safe_filename}")

                    except Exception as e:
                        logger.error(f"Ошибка получения вложения: {e}")
                        # Продолжаем обработку других вложений

        return attachments

    def _safe_decode_filename(self, filename: str) -> str:
        """
        Безопасная декодировка имени файла с поддержкой кириллицы
        и обработкой всех возможных форматов
        """
        if not filename:
            return "attachment.bin"

        try:
            from email.header import decode_header

            # Разбираем заголовок с именем файла
            decoded_parts = decode_header(filename)

            decoded_filename = ""

            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    # Пробуем разные кодировки для кириллицы
                    possible_encodings = []

                    # 1. Кодировка из заголовка (если указана)
                    if encoding:
                        possible_encodings.append(encoding)

                    # 2. UTF-8 (самый распространенный)
                    possible_encodings.append('utf-8')

                    # 3. Кодировки для кириллицы
                    possible_encodings.extend([
                        'cp1251',  # Windows Cyrillic
                        'koi8-r',  # KOI8-R
                        'windows-1251',  # Windows Cyrillic
                        'iso-8859-5',  # ISO Cyrillic
                        'cp866',  # DOS Cyrillic
                        'maccyrillic'  # Mac Cyrillic
                    ])

                    # 4. Дополнительные кодировки
                    possible_encodings.extend(['latin-1', 'ascii'])

                    # Пробуем декодировать
                    decoded = None
                    for enc in possible_encodings:
                        try:
                            decoded = part.decode(enc, errors='strict')
                            # Проверяем что декодирование дало осмысленный результат
                            if decoded and any(c.isalnum() for c in decoded):
                                decoded_filename += decoded
                                logger.debug(f"Файл декодирован в {enc}: {decoded[:50]}")
                                break
                        except (UnicodeDecodeError, LookupError):
                            continue

                    # Если ни одна кодировка не подошла - используем замену символов
                    if decoded is None:
                        decoded_filename += part.decode('utf-8', errors='replace')
                        logger.warning(f"Файл декодирован с заменой символов: {filename[:50]}")

                else:
                    # Часть уже в виде строки
                    decoded_filename += str(part)

            # Очищаем имя файла от опасных символов
            clean_filename = self._sanitize_filename(decoded_filename.strip())

            # Если имя файла пустое после очистки
            if not clean_filename:
                clean_filename = "attachment.bin"

            # Обрезаем слишком длинные имена файлов
            if len(clean_filename) > 200:
                name, ext = os.path.splitext(clean_filename)
                clean_filename = name[:150] + "..." + ext

            logger.debug(f"Исходное имя: {filename[:50]}, очищенное: {clean_filename}")
            return clean_filename

        except Exception as e:
            logger.error(f"Критическая ошибка декодирования имени файла '{filename[:50]}': {e}")
            return "attachment.bin"

    def _sanitize_filename(self, filename: str) -> str:
        """
        Очистка имени файла от опасных символов и путей
        """
        if not filename:
            return "attachment.bin"

        # Удаляем путь, оставляем только имя файла
        filename = os.path.basename(filename)

        # Заменяем опасные символы
        dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')

        # Удаляем управляющие символы
        import string
        filename = ''.join(c for c in filename if c in string.printable)

        # Убираем лишние пробелы
        filename = ' '.join(filename.split())

        # Если имя начинается с точки - добавляем префикс
        if filename.startswith('.'):
            filename = 'file' + filename

        # Проверяем расширение
        if '.' not in filename:
            # Пытаемся определить расширение из имени
            common_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg',
                                 '.png', '.gif', '.zip', '.rar', '.txt', '.rtf']
            for ext in common_extensions:
                if ext in filename.lower():
                    return filename

        # Добавляем расширение .bin если его нет
        if '.' not in filename:
            filename += '.bin'

        return filename

    def mark_as_read(self, msg_id) -> bool:
        """Пометить письмо как прочитанное"""
        try:
            if not self.is_connected or not self.mail:
                logger.error("Нет подключения к почте")
                return False

            # Убедимся что папка выбрана
            if not self.selected_folder:
                self.select_folder('INBOX')

            # Помечаем как прочитанное
            self.mail.store(msg_id, '+FLAGS', '\\Seen')
            logger.info(f"Письмо {msg_id} помечено как прочитанное")
            return True

        except Exception as e:
            logger.error(f"Ошибка пометки письма как прочитанного: {e}")
            return False

    def mark_as_unread(self, msg_id) -> bool:
        """Пометить письмо как непрочитанное"""
        try:
            if not self.is_connected or not self.mail:
                return False

            if not self.selected_folder:
                self.select_folder('INBOX')

            self.mail.store(msg_id, '-FLAGS', '\\Seen')
            logger.info(f"Письмо {msg_id} помечено как непрочитанное")
            return True

        except Exception as e:
            logger.error(f"Ошибка пометки письма как непрочитанного: {e}")
            return False
