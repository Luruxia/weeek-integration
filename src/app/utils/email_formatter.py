# utils/email_formatter.py - НОВЫЙ ФАЙЛ

from .name_parser import NameParser


class EmailFormatter:
    @staticmethod
    def format_for_task(email_data: dict, contact: dict = None) -> str:
        """Форматирует письмо для описания задачи"""

        lines = []

        # Заголовок
        lines.append("## 📩 ВХОДЯЩЕЕ ПИСЬМО")
        lines.append("")

        # Информация о контакте
        if contact:
            lines.append("### 👤 КОНТАКТ")
            first_name = contact.get('firstName', '').strip()
            last_name = contact.get('lastName', '').strip()
            contact_email = contact.get('email', '')

            if first_name or last_name:
                lines.append(f"**Имя:** {first_name} {last_name}".strip())

            if contact_email:
                lines.append(f"**Email:** {contact_email}")

            contact_id = contact.get('id', '')
            if contact_id:
                lines.append(f"**ID:** `{contact_id}`")

            lines.append("")

        # Информация о письме
        lines.append("### 📧 ИНФОРМАЦИЯ О ПИСЬМЕ")

        from_name = email_data.get('from_name', '')
        from_email = email_data.get('from_email', '')

        if from_name and from_email:
            lines.append(f"**Отправитель:** {from_name} <{from_email}>")
        elif from_email:
            lines.append(f"**Отправитель:** {from_email}")

        date = email_data.get('date', '')
        if date:
            lines.append(f"**Дата:** {date}")

        subject = email_data.get('subject', '')
        if subject:
            lines.append(f"**Тема:** {subject}")

        message_id = email_data.get('message_id', '')
        if message_id:
            lines.append(f"**ID письма:** `{message_id}`")

        lines.append("")
        lines.append("---")
        lines.append("")

        # Текст письма
        lines.append("### 📄 ТЕКСТ ПИСЬМА")

        body = email_data.get('body_text', '')
        if not body:
            body = email_data.get('body_html', '')

        if body:
            # Очищаем HTML если есть
            import re
            clean_body = re.sub(r'<[^>]+>', '', body)
            clean_body = re.sub(r'\s+', ' ', clean_body).strip()

            # Ограничиваем длину
            max_length = 4000
            if len(clean_body) > max_length:
                clean_body = clean_body[:max_length] + f"\n\n[... текст сокращен, всего {len(body)} символов ...]"

            lines.append(clean_body)
        else:
            lines.append("*(Текст письма отсутствует)*")

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*🤖 Импортировано из Gmail*")

        return "\n".join(lines)
