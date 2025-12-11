from utils.name_parser import NameParser
import logging

logger = logging.getLogger(__name__)


class ContactProcessor:
    def __init__(self, weeek_client):
        self.weeek_client = weeek_client

    def process(self, email_data: dict) -> dict:
        from_string = email_data.get('from', '')
        from_name = email_data.get('from_name', '')
        from_email = email_data.get('from_email', '')

        # Если from_email не заполнен, парсим из from_string
        if not from_email and from_string:
            name, email, domain = NameParser.parse_from_string(from_string)
            if not from_name and name:
                from_name = name
            if not from_email and email:
                from_email = email

        if not from_email:
            logger.error("Не удалось извлечь email")
            return None

        # Ищем существующий контакт
        existing = self.weeek_client.search_contact_by_email(from_email)
        if existing:
            logger.info(f"Найден существующий контакт: {from_email}")
            return existing

        # Создаем новый контакт
        return self._create_contact(from_name, from_email)

    def _create_contact(self, name: str, email: str) -> dict:
        first_name, last_name = NameParser.split_full_name(name)

        # Если нет имени, создаем из email
        if not first_name:
            first_name = NameParser.extract_username_from_email(email) or "Клиент"

        contact_data = {
            'email': email,
            'firstName': first_name[:50],
            'lastName': last_name[:50]
        }

        logger.info(f"Создаем контакт: {first_name} {last_name} ({email})")
        contact = self.weeek_client.create_contact(contact_data)

        if contact:
            logger.info(f"✅ Контакт создан: ID={contact.get('id')}")

        return contact
