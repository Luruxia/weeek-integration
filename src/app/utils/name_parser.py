import re
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class NameParser:
    """Универсальный парсер имен из email заголовков"""

    @staticmethod
    def parse_email_header(header: str) -> Dict[str, str]:
        """
        Парсит строку вида:
        - "Иван Иванов <ivan@example.com>"
        - "ivan@example.com"
        - "\"Иван Иванов\" <ivan@example.com>"
        - "Ivan Ivanov <ivan@example.com>"

        Возвращает: {"name": "", "email": "", "domain": ""}
        """
        if not header:
            return {"name": "", "email": "", "domain": ""}

        header = header.strip()

        # 1. Ищем email в угловых скобках
        email_match = re.search(r'<(.+?)>', header)
        if email_match:
            email = email_match.group(1).strip()
            name = re.sub(r'<.+?>', '', header).strip()
        else:
            # 2. Ищем email без скобок
            email_match = re.search(r'(\S+@\S+\.\S+)', header)
            if email_match:
                email = email_match.group(1)
                name = header.replace(email, '').strip()
            else:
                # 3. Нет email - возможно это просто имя
                email = ""
                name = header

        # Очистка кавычек
        name = name.strip('"\' ')

        # Извлекаем домен
        domain = ""
        if email and '@' in email:
            domain_parts = email.split('@')[1].lower().split('.')
            domain = domain_parts[0] if domain_parts else ""

        return {
            "name": name,
            "email": email,
            "domain": domain
        }

    @staticmethod
    def extract_name_from_email(email: str) -> str:
        """
        Извлекает имя из email адреса:
        vasily.pupkin@company.com → "Vasily Pupkin"
        """
        if not email or '@' not in email:
            return ""

        username = email.split('@')[0]

        # Заменяем разделители пробелами
        name_parts = re.split(r'[\._\-+]', username)

        # Капитализируем каждую часть
        name_parts = [part.capitalize() for part in name_parts if part]

        return " ".join(name_parts).strip()

    @staticmethod
    def normalize_name(name: str) -> Dict[str, str]:
        """
        Нормализует имя в first/last name
        "Иванов Иван Иванович" → {"first": "Иван", "last": "Иванов", "middle": "Иванович"}
        """
        if not name:
            return {"first": "", "last": "", "middle": ""}

        parts = name.split()

        if len(parts) == 1:
            return {"first": parts[0], "last": "", "middle": ""}
        elif len(parts) == 2:
            return {"first": parts[1], "last": parts[0], "middle": ""}
        elif len(parts) >= 3:
            return {"first": parts[1], "last": parts[0], "middle": " ".join(parts[2:])}

        return {"first": "", "last": "", "middle": ""}

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Проверяет валидность email адреса"""
        if not email:
            return False

        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def parse_full_from_header(from_header: str) -> Dict[str, str]:
        """
        Полный парсинг from заголовка с нормализацией имени
        """
        # Парсим заголовок
        parsed = NameParser.parse_email_header(from_header)

        # Если нет имени, пытаемся извлечь из email
        if not parsed["name"] and parsed["email"]:
            parsed["name"] = NameParser.extract_name_from_email(parsed["email"])

        # Нормализуем имя
        normalized = NameParser.normalize_name(parsed["name"])

        return {
            **parsed,
            **normalized,
            "first_name": normalized["first"],
            "last_name": normalized["last"]
        }
