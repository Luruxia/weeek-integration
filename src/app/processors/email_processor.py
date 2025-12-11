import logging
from datetime import datetime
from utils.task_formatter import TaskFormatter
from utils.email_formatter import EmailFormatter

logger = logging.getLogger(__name__)


class EmailProcessor:
    """Обрабатывает email письма и сохраняет как задачи"""

    def __init__(self, weeek_client):
        self.weeek_client = weeek_client

    def create_email_task(self, contact: dict, email_data: dict) -> dict:
        """
        Создает задачу из письма

        Args:
            contact: словарь с данными контакта
            email_data: словарь с данными письма

        Returns:
            dict с результатом создания задачи
        """
        if not contact or not contact.get('id'):
            logger.error("Нет контакта или ID контакта")
            return {'success': False, 'error': 'No contact ID'}

        # Генерируем название задачи
        task_name = TaskFormatter.generate_task_name(email_data, contact)

        # Форматируем описание
        description = EmailFormatter.format_for_task(email_data, contact)

        # Подготовка данных задачи
        task_data = {
            'name': task_name,
            'description': description,
            'contactId': contact['id'],
            'tags': self._generate_tags(email_data, contact)
        }

        logger.info(f"Создаем задачу: {task_name}")

        # Создаем задачу
        task = self.weeek_client.create_task(task_data)

        if task:
            task_id = task.get('id')
            logger.info(f"✅ Задача создана: ID={task_id}")

            # Обрабатываем вложения
            attachments = []
            if email_data.get('attachments'):
                attachments = self._process_attachments(task_id, email_data, contact)

            return {
                'success': True,
                'task_id': task_id,
                'task_name': task_name,
                'contact_id': contact['id'],
                'attachments': attachments
            }
        else:
            logger.error("❌ Не удалось создать задачу")
            return {'success': False, 'error': 'Failed to create task'}

    def _generate_tags(self, email_data: dict, contact: dict) -> list:
        """Генерирует теги для задачи"""
        tags = ['email', 'входящее', datetime.now().strftime('%Y-%m')]

        # Добавляем тег по домену
        from_email = email_data.get('from_email', '')
        if from_email and '@' in from_email:
            domain = from_email.split('@')[1].split('.')[0]
            if domain and len(domain) <= 15:
                tags.append(domain.lower())

        # Добавляем тег важности
        if self._is_important_email(email_data):
            tags.append('важно')

        return tags

    def _is_important_email(self, email_data: dict) -> bool:
        """Определяет, является ли письмо важным"""
        important_keywords = [
            'запрос', 'вопрос', 'предложение', 'сотрудничество',
            'заказ', 'покупка', 'консультация', 'звонок',
            'срочно', 'важно', 'приоритет'
        ]

        subject = email_data.get('subject', '').lower()
        body = email_data.get('body_text', '').lower()

        for keyword in important_keywords:
            if keyword in subject or keyword in body:
                return True

        return False

    def _process_attachments(self, task_id: str, email_data: dict, contact: dict) -> list:
        """Обрабатывает вложения письма"""
        attachments = email_data.get('attachments', [])
        results = []

        if not attachments:
            return results

        logger.info(f"Обрабатываем {len(attachments)} вложений")

        for attachment in attachments:
            try:
                filename = attachment.get('filename', '')
                file_data = attachment.get('payload', b'')

                if not filename or not file_data:
                    continue

                # Проверяем размер
                if len(file_data) > 10 * 1024 * 1024:  # 10MB
                    logger.warning(f"Файл {filename} слишком большой, пропускаем")
                    continue

                # Загружаем файл
                uploaded = self.weeek_client.upload_file(filename, file_data)
                if uploaded:
                    file_id = uploaded.get('id')

                    # Прикрепляем к задаче (если есть такой метод)
                    # Или к контакту
                    if file_id and contact.get('id'):
                        success = self.weeek_client.attach_file_to_contact(
                            contact['id'],
                            file_id
                        )
                        if success:
                            logger.info(f"Файл {filename} прикреплен к контакту")
                            results.append({
                                'filename': filename,
                                'file_id': file_id,
                                'success': True
                            })

            except Exception as e:
                logger.error(f"Ошибка обработки вложения: {e}")

        return results
