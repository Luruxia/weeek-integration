# utils/task_formatter.py - НОВЫЙ ФАЙЛ

from .name_parser import NameParser

class TaskFormatter:
    @staticmethod
    def generate_task_name(email_data: dict, contact: dict = None) -> str:
        """Генерирует понятное название задачи из письма"""

        subject = email_data.get('subject', '').strip()

        # Если тема есть и не пустая
        if subject and subject != 'Без темы':
            # Очищаем тему
            subject = ' '.join(subject.split())
            subject = subject.replace('\n', ' ').replace('\r', ' ')

            # Ограничиваем длину
            if len(subject) > 60:
                subject = subject[:57] + "..."

            return f"📧 {subject}"

        # Если темы нет, генерируем из контакта
        if contact:
            first_name = contact.get('firstName', '').strip()
            last_name = contact.get('lastName', '').strip()

            if first_name or last_name:
                name = f"{first_name} {last_name}".strip()
                return f"📧 Письмо от {name}"

        # Если нет контакта, извлекаем из email
        from_email = email_data.get('from_email', '')
        if from_email:
            username = NameParser.extract_username_from_email(from_email)
            if username:
                return f"📧 Письмо от {username}"

        return "📧 Новое письмо"
