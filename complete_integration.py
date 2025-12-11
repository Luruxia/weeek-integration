"""
ИТОГОВАЯ ИНТЕГРАЦИЯ GMAIL -> WEEEK
Сохраняет важные письма как задачи в Weeek
"""

import re
import sys
import os
import json
import html
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Добавляем правильные пути
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'src/app'))

try:
    # Импортируем из новой структуры
    from core.mail_client import MailClient
    from core.weeek_client import WeeekClient
    from core.telegram_notifier import TelegramNotifier

    # Импортируем настройки
    try:
        from config.settings import Settings

        settings = Settings()
        print("✅ Настройки загружены")
    except ImportError:
        print("⚠️  Настройки не импортированы")
        settings = None

    # Импортируем секреты
    from config.secrets import (
        GMAIL_EMAIL,
        GMAIL_APP_PASSWORD,
        WEEEK_API_KEY,
        WEEEK_WORKSPACE_ID,
        WEEEK_BASE_URL
    )

    # Импортируем телеграм конфиг из отдельного файла
    try:
        from config.telegram_config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

        print("✅ Telegram конфиг загружен")
    except ImportError as e:
        print(f"⚠️  Telegram конфиг не найден: {e}")
        TELEGRAM_BOT_TOKEN = None
        TELEGRAM_CHAT_ID = None

    # Для обратной совместимости со старым кодом
    GMAIL_PASSWORD = GMAIL_APP_PASSWORD

    print("✅ Все импорты успешны")

except ImportError as e:
    print(f"❌ Критическая ошибка импорта: {e}")
    import traceback

    traceback.print_exc()

    # Проверяем что есть в telegram_config.py
    print("\n🔍 Проверка telegram_config.py:")
    try:
        import config.telegram_config

        print("Файл найден. Переменные:")
        for attr in dir(config.telegram_config):
            if not attr.startswith('_') and attr.isupper():
                print(f"  - {attr}")
    except ImportError:
        print("❌ Файл не найден")

    raise

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CompleteIntegration:
    """Полная интеграция Gmail с Weeek"""

    def __init__(self):
        self.mail_client = MailClient()
        self.weeek_client = WeeekClient()
        self.setup_workspace()
        self.company_cache = {}

    def setup_workspace(self):
        """Настроить рабочее пространство"""
        # Создаем структуру папок
        folders = [
            'logs/daily',
            'data/processed',
            'data/contacts',
            'data/attachments',
            'reports',
            'logs/errors'
        ]

        for folder in folders:
            os.makedirs(folder, exist_ok=True)

        # Создаем файл конфигурации
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Загрузить конфигурацию"""
        config_path = 'config/integration_config.json'
        default_config = {
            'processing': {
                'daily_limit': 50,
                'auto_mark_read': True,
                'skip_patterns': [
                    'noreply', 'no-reply', 'donotreply',
                    'notification', 'notify', 'alert',
                    'newsletter', 'digest', 'mailing',
                    'unsubscribe', 'отписаться',
                    'facebook.com', 'twitter.com', 'linkedin.com',
                    'instagram.com', 'pinterest.com', 'youtube.com',
                    'vk.com', 'tiktok.com', 'reddit.com',
                    'netease.com', 'ubi.com', 'steam.com',
                    'gamenet.ru','info@info.sportmaster.ru',
                    'inform@emails.tinkoff.ru', 'info@service.'
                ],
                'important_patterns': [
                    'запрос', 'вопрос', 'предложение', 'сотрудничество',
                    'заказ', 'покупка', 'консультация', 'звонок',
                    'договор', 'счет', 'оплата', 'доставка',
                    'проект', 'встреча', 'переговоры', 'резюме',
                    'срочно', 'важно', 'приоритет',
                    'request', 'question', 'proposal', 'cooperation',
                    'order', 'purchase', 'consultation', 'call',
                    'contract', 'invoice', 'payment', 'delivery',
                    'urgent', 'important', 'asap', 'отчет', 'report', 'задача', 'task',
                    'подготовить', 'prepare', 'совещание', 'meeting'
                ],
                'client_domains': []  # Здесь добавьте домены клиентов
            },
            'weeek': {
                'default_project': None,
                'email_tag': 'EMAIL',
                'inbox_tag': 'ВХОДЯЩЕЕ'
            },
            'backup': {
                'keep_days': 30,
                'compress_old': True
            }
        }

        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    # Объединяем с дефолтными настройками
                    default_config.update(user_config)
            except:
                logger.warning("Не удалось загрузить конфиг, использую по умолчанию")

        return default_config

    def run_daily_processing(self, limit: int = None):
        """Ежедневная обработка писем"""
        logger.info("=" * 80)
        logger.info("🔄 ЕЖЕДНЕВНАЯ ОБРАБОТКА ПИСЕМ GMAIL -> WEEEK")
        logger.info("=" * 80)

        # Статистика
        stats = {
            'start_time': datetime.now(),
            'total_processed': 0,
            'tasks_created': 0,
            'contacts_created': 0,
            'emails_skipped': 0,
            'errors': 0
        }

        # Подключаемся
        if not self.mail_client.connect():
            logger.error("❌ Не удалось подключиться к почтовому серверу")
            return

        # Определяем лимит
        process_limit = limit or self.config['processing']['daily_limit']
        logger.info(f"📧 Лимит обработки: {process_limit} писем")

        # Получаем письма
        emails = self.mail_client.get_unread_emails(limit=process_limit)

        if not emails:
            logger.info("✅ Новых непрочитанных писем нет")
            self.mail_client.disconnect()
            self._save_daily_report(stats)
            return

        logger.info(f"📫 Найдено {len(emails)} непрочитанных писем")
        logger.info("-" * 80)

        # Обрабатываем каждое письмо
        for i, email in enumerate(emails, 1):
            logger.info(f"\n📧 Письмо {i}:")
            logger.info(f"   From заголовок: '{email.get('from', '')}'")
            logger.info(f"   From email: '{email.get('from_email', '')}'")
            logger.info(f"   From name: '{email.get('from_name', '')}'")

            # Решаем что делать с письмом
            decision, reason = self._decide_email_action(email)
            stats['total_processed'] += 1

            if decision == 'skip':
                logger.info(f"⏭️  Пропускаем: {reason}")
                if self.config['processing']['auto_mark_read']:
                    self.mail_client.mark_as_read(email.get('uid'))
                stats['emails_skipped'] += 1
                continue

            elif decision == 'process':
                logger.info(f"✅ Обрабатываем: {reason}")

                try:
                    # Обрабатываем письмо
                    task_created, contact_created = self._process_important_email(email)

                    if task_created:
                        stats['tasks_created'] += 1
                        logger.info(f"   📋 Задача создана")

                    if contact_created:
                        stats['contacts_created'] += 1
                        logger.info(f"   👤 Контакт создан")

                    # Помечаем прочитанным
                    if self.config['processing']['auto_mark_read']:
                        self.mail_client.mark_as_read(email.get('uid'))

                except Exception as e:
                    logger.error(f"Ошибка обработки письма: {e}")
                    stats['errors'] += 1
                    self._save_error(email, str(e))

            elif decision == 'ask':
                # В авто-режиме всегда пропускаем непонятные письма
                logger.info(f"🤖 Авто-режим: пропускаем неопределенное письмо")
                logger.info(f"   Причина: {reason}")
                logger.info(f"   От: {email.get('from_email')}")
                logger.info(f"   Тема: {email.get('subject', '')[:60]}...")

                if self.config['processing']['auto_mark_read']:
                    self.mail_client.mark_as_read(email.get('uid'))
                stats['emails_skipped'] += 1

    def _log_uncertain_email(self, email: Dict, reason: str):
        """Записать непонятное письмо в лог для ручной проверки"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'from_email': email.get('from_email'),
                'from_name': email.get('from_name'),
                'subject': email.get('subject'),
                'date': str(email.get('date')),
                'reason': reason,
                'message_id': email.get('message_id')
            }

            log_file = 'logs/uncertain_emails.json'

            # Читаем существующие записи
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = []

            # Добавляем новую запись
            data.append(log_entry)

            # Сохраняем (максимум 1000 записей)
            if len(data) > 1000:
                data = data[-1000:]

            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Ошибка записи непонятного письма: {e}")


    def _decide_email_action(self, email: Dict) -> Tuple[str, str]:
        """Решить что делать с письмом - СПЕЦИАЛЬНО ДЛЯ АКУСТИЧЕСКИХ КАБИН"""
        from_email = email.get('from_email', '').lower()
        subject = email.get('subject', '').lower()
        body = email.get('body_text', '').lower()
        search_text = subject + " " + body[:500]
    
        # 🔴 ЖЕСТКИЙ ПРОПУСК (100% не релевантно)
        hard_skip = [
            # Авто-рассылки
            'no-reply@', 'noreply@', 'donotreply@', 'notification@',
            'newsletter@', 'digest@', 'mailing@', 'alert@',
    
            # Массовые рассылки (абсолютно не релевантно)
            '@tinkoff.ru', '@sportmaster.ru', '@hh.ru',
            '@redditmail.com', '@discord.com', '@twitch.tv',
            '@steam.com', '@hoyoverse.com', '@gosuslugi.ru',
    
            # Соцсети и развлечения
            'facebook.com', 'twitter.com', 'instagram.com',
            'vk.com', 'tiktok.com', 'pinterest.com',
            'youtube.com', 'linkedin.com', 'telegram.org',
    
            # Технические/служебные
            '@emails.', '@info.', '@service.', '@offers.',
    
            # Игровые/крипто
            'crypto', 'bitcoin', 'forex', 'gambling', 'casino',
            'gamenet.ru', 'drweb.com', '1-ofd.ru', 'eduface.ru'
        ]
    
        for pattern in hard_skip:
            if pattern in from_email:
                return 'skip', f"автоспам: {pattern}"
    
        # 🟡 МЯГКИЙ ПРОПУСК (скорее всего не релевантно)
        soft_skip = [
            # Маркетинг/рассылки
            'акция', 'скидка', 'распродажа', 'рассылка', 'newsletter',
            'ваканси', 'резюме', 'hh.ru', 'опрос', 'survey', 'feedback',
            'разыгрываем', 'приз', 'лотерея', 'вебинар', 'конференция',
            'уведомление', 'notification', 'unsubscribe', 'отписаться',  
        ]
    
        for keyword in soft_skip:
            if keyword in search_text:
                # НО! Если есть и ваши ключевые слова - все равно обрабатывать
                pass  # Пропускаем проверку - дальше проверим ваши ключевые слова
    
        # 🟢 ВАЖНЫЕ СЛОВА ДЛЯ АКУСТИЧЕСКИХ КАБИН (ОБРАБАТЫВАТЬ!)
        acoustic_keywords = [
            # Бренд и продукция
            'quiet store', 'quietstore', 'куайет стор',
            'акустическ', 'звукоизоляц', 'шумопоглощен',
            'переговорн', 'переговорка', 'кабин', 'кабина',
            'телефонная кабин', 'звуковая кабин',
    
            # Технические термины
            'дб ', 'децибел', 'звукоизоляция', 'шумоизоляция',
            'акустика', 'реверберация', 'эхоподавление',
            'вентиляц', 'кондицион', 'освещен',
            'эргономик', 'эргономичн',
    
            # Применение
            'офис', 'коворкинг', 'бизнес-центр', 'open space',
            'call-центр', 'колл-центр', 'звонок', 'телефон',
            'конференц', 'совещан', 'митинг', 'переговоры',
            'фокусировка', 'концентрац', 'privacy', 'приватность',
    
            # Производство и материалы
            'стекло', 'панел', 'мдф', 'дсп', 'двп', 'гипсокартон',
            'минеральная вата', 'базальт', 'пробка', 'пена',
            'завод', 'производство', 'изготовление', 'сборка',
            'монтаж', 'установк', 'доставк', 'срок',
    
            # Запросы клиентов
            'запрос', 'вопрос', 'предложение', 'сотрудничество',
            'заказ', 'покупка', 'консультация', 'звонок',
            'договор', 'счет', 'оплата', 'доставка',
            'проект', 'встреча', 'переговоры', 'измерение',
            'коммерческое предложение', 'кп', 'прайс', 'каталог',
            'образец', 'материал', 'размер', 'габарит',
    
            # Срочность
            'срочно', 'важно', 'приоритет', 'дедлайн',
            'urgent', 'important', 'asap', 'deadline',
    
            # Клиентские фразы
            'хочу', 'интересует', 'интересно', 'уточнить',
            'согласовать', 'обсудить', 'проконсультировать',
            'нужно', 'необходимо', 'требуется',
    
            # Деловая переписка
            'ответ', 'reply', 're:', 'fwd:', 'fw:', 'добрый день',
            'здравствуйте', 'уважаем'
        ]
    
        for keyword in acoustic_keywords:
            if keyword in search_text:
                return 'process', f"релевантно: '{keyword}'"
    
        # 🔵 ЛИЧНЫЕ И КОРПОРАТИВНЫЕ ПОЧТЫ (ВСЕГДА ПРОВЕРЯТЬ!)
        # Любое деловое письмо может быть клиентом!
    
        if '@' in from_email:
            # Проверяем не спам ли по содержимому
            if any(spam_word in search_text for spam_word in ['акция', 'скидка', 'рассылка']):
                return 'skip', "маркетинговая рассылка"
    
            # Если письмо выглядит деловым
            business_indicators = [
                'добрый день', 'здравствуйте', 'уважаемый',
                'прошу', 'просим', 'обращаюсь', 'обращаемся',
                'с уважением', 'best regards', 'искренне ваш'
            ]
    
            if any(indicator in search_text for indicator in business_indicators):
                return 'process', f"деловое письмо от {from_email}"
    
        # ⚪ ВСЕ ОСТАЛЬНОЕ - ПРОПУСК (но безопасно)
        return 'skip', f"нерелевантное: {from_email[:30]}..."

    def _process_important_email(self, email: Dict) -> Tuple[bool, bool]:
        """Обработать важное письмо"""
        logger.info(f"\n{'=' * 60}")
        logger.info("🔍 ОБРАБОТКА ВАЖНОГО ПИСЬМА")
        logger.info(f"   📧 Тема: {email.get('subject')}")
        logger.info(f"   👤 От: {email.get('from_email')}")
        logger.info(f"   📅 Дата: {email.get('date')}")

        # ✅ ДОБАВЛЕНО: Показываем откуда письмо (спам, рассылка или важное)
        from_email = email.get('from_email', '').lower()
        if 'no-reply' in from_email or 'noreply' in from_email:
            logger.info(f"   ⚠️  Источник: Рассылка (no-reply)")
        elif any(domain in from_email for domain in ['gmail.com', 'yandex.ru', 'mail.ru']):
            logger.info(f"   👤 Источник: Личная почта")
        else:
            logger.info(f"   🏢 Источник: Корпоративная почта")

        contact_created = False
        task_created = False

        # ✅ 1. ИЗВЛЕКАЕМ КОМПАНИЮ ПЕРВЫМ ДЕЛОМ
        company_name = self._extract_company_name(email)

        if company_name:
            logger.info(f"   🏢 КОМПАНИЯ ДЛЯ ОБРАБОТКИ: {company_name}")
        else:
            logger.info(f"   ℹ️  Компания не найдена, обрабатываем как общий контакт")

        # ✅ 2. СОЗДАЕМ/НАХОДИМ КОНТАКТ С УЧЕТОМ КОМПАНИИ
        contact = self._get_or_create_contact(email, company_name)
        if not contact:
            raise Exception("Не удалось создать/найти контакт")

        contact_id = contact.get('id')
        logger.info(f"   👤 Контакт ID: {contact_id}")

        # ✅ 3. СОЗДАНИЕ/ПОИСК ОРГАНИЗАЦИИ
        if company_name:
            logger.info(f"   🔍 Поиск/создание организации: {company_name}")
            organization = self.weeek_client.get_or_create_organization(company_name)
            if organization:
                logger.info(f"   🔗 Привязываем контакт к организации ID: {organization.get('id')}")
                # Проверяем не привязан ли уже контакт
                contact_orgs = contact.get('organizations', [])
                if organization['id'] not in contact_orgs:
                    success = self.weeek_client.link_contact_to_organization(contact['id'], organization['id'])
                    if success:
                        logger.info(f"   ✅ Контакт привязан к организации")
                    else:
                        logger.warning(f"   ⚠️  Не удалось привязать контакт к организации")
                else:
                    logger.info(f"   ℹ️  Контакт уже привязан к этой организации")
            else:
                logger.error(f"   ❌ Не удалось создать/найти организацию")

        # ✅ 4. ПОДГОТОВКА ДАННЫХ ЗАДАЧИ
        logger.info(f"\n   🛠️  Подготовка данных задачи...")
        task_data = self._prepare_task_data(email, contact)

        # ✅ 5. ПРОВЕРКА И ИСПРАВЛЕНИЕ НАЗВАНИЯ
        current_title = task_data.get('title', '')
        logger.info(f"   📝 Текущее название задачи: {current_title}")

        if company_name:
            # Ищем и заменяем любые упоминания "ТехноЛогика" на правильную компанию
            wrong_names = ['ТехноЛогика', 'технологика', 'ООО ТехноЛогика', 'ооо технологика']
            for wrong_name in wrong_names:
                if wrong_name.lower() in current_title.lower():
                    new_title = current_title.replace(wrong_name, f"ООО {company_name}")
                    new_title = new_title.replace(wrong_name.title(), f"ООО {company_name}")
                    new_title = new_title.replace(wrong_name.lower(), company_name.lower())
                    task_data['title'] = new_title
                    logger.info(f"   ✏️  Исправлено название: {new_title[:60]}...")
                    break

        # ✅ ПРОВЕРКА workspaceId
        if 'workspaceId' not in task_data:
            logger.warning(f"   ⚠️  ВНИМАНИЕ: workspaceId не указан в task_data!")
            if self.weeek_client.workspace_id:
                task_data['workspaceId'] = self.weeek_client.workspace_id
                logger.info(f"   📍 Добавлен workspaceId: {self.weeek_client.workspace_id}")
            else:
                logger.error(f"   ❌ КРИТИЧЕСКАЯ ОШИБКА: workspaceId не найден!")
                logger.info(f"   ℹ️  Проверьте config/secrets.py")

        # ✅ 6. СОЗДАНИЕ ЗАДАЧИ
        logger.info(f"\n   🚀 Отправка задачи в Weeek...")

        task = self.weeek_client.create_task(task_data)

        if task:
            task_created = True
            logger.info(f"\n   ✅ ЗАДАЧА СОЗДАНА!")
            logger.info(f"   📋 ID: {task.get('id')}")
            logger.info(f"   🏷️  Название: {task.get('title', '')[:70]}")

            # Сохраняем вложения если есть
            if email.get('attachments'):
                self._handle_attachments(email, contact, task)

            # Сохраняем результат
            self._save_processing_result(email, contact, task)

            logger.info(f"\n   📍 Проверить задачу:")
            logger.info(f"   🔗 https://app.weeek.net/ws/{task_data.get('workspaceId', '')}/tm/tasks/{task.get('id')}")
        else:
            logger.error(f"   ❌ НЕ УДАЛОСЬ создать задачу!")
            logger.warning(f"   ⚠️  Проверьте логи Weeek API")

        return task_created, True  # contact_created всегда True если контакт создан/найден

    def _extract_company_name(self, email: Dict) -> Optional[str]:
        """ИЗВЛЕЧЬ НАЗВАНИЕ КОМПАНИИ из письма разными способами"""
        email_id = email.get('message_id') or email.get('uid')
        if email_id and email_id in self.company_cache:
            logger.debug(f"Используем кэш для компании из письма {email_id[:20]}")
            return self.company_cache[email_id]

        try:
            subject = email.get('subject', '').lower()
            body = email.get('body_text', '').lower()
            from_email = email.get('from_email', '').lower()
            from_name = email.get('from_name', '')

            logger.debug(f"ИЗВЛЕЧЕНИЕ КОМПАНИИ:")
            logger.debug(f"   Тема: {subject[:80]}...")
            logger.debug(f"   От: {from_name} <{from_email}>")

            # ✅ ОЧИЩАЕМ HTML ENTITIES
            subject = html.unescape(subject)
            body = html.unescape(body)

            # ✅ СПОСОБ 1: Ищем в теме "от ООО Название"
            if "от ооо " in subject:
                start_pos = subject.find("от ооо ") + len("от ооо ")
                rest_text = subject[start_pos:]

                # Ищем название до знака препинания или конца
                match = re.match(r'([а-яёa-z0-9\-&\.\s]+?)(?:[\.,!\?]|$)', rest_text)
                if match:
                    company_name = match.group(1).strip()
                    if len(company_name) > 2:
                        # Убираем стоп-слова
                        stop_words = ['письмо', 'запрос', 'предложение', 'сотрудничество', 'о', 'об']
                        for word in stop_words:
                            if company_name.lower().startswith(word):
                                company_name = company_name[len(word):].strip()

                        if company_name and len(company_name) > 2:
                            logger.info(f"   🏢 КОМПАНИЯ из 'от ООО': {company_name.title()}")
                            if email_id:
                                self.company_cache[email_id] = company_name.title()
                            return company_name.title()

            # ✅ СПОСОБ 2: Ищем "от ОАО" (Акционерное общество)
            if "от оао " in subject:
                start_pos = subject.find("от оао ") + len("от оао ")
                rest_text = subject[start_pos:]
                match = re.match(r'([а-яёa-z0-9\-&\.\s]+?)(?:[\.,!\?]|$)', rest_text)
                if match:
                    company_name = match.group(1).strip()
                    if len(company_name) > 2:
                        logger.info(f"   🏢 КОМПАНИЯ из 'от ОАО': {company_name.title()}")
                        if email_id:
                            self.company_cache[email_id] = company_name.title()
                        return company_name.title()

            # ✅ СПОСОБ 3: Ищем "от ИП"
            if "от ип " in subject:
                start_pos = subject.find("от ип ") + len("от ип ")
                rest_text = subject[start_pos:]
                match = re.match(r'([а-яёa-z0-9\-&\.\s]+?)(?:[\.,!\?]|$)', rest_text)
                if match:
                    company_name = f"ИП {match.group(1).strip().title()}"
                    logger.info(f"   🏢 КОМПАНИЯ из 'от ИП': {company_name}")
                    if email_id:
                        self.company_cache[email_id] = company_name
                    return company_name

            # ✅ СПОСОБ 4: Ищем "от ЗАО" (Закрытое акционерное общество)
            if "от зао " in subject:
                start_pos = subject.find("от зао ") + len("от зао ")
                rest_text = subject[start_pos:]
                match = re.match(r'([а-яёa-z0-9\-&\.\s]+?)(?:[\.,!\?]|$)', rest_text)
                if match:
                    company_name = match.group(1).strip()
                    if len(company_name) > 2:
                        logger.info(f"   🏢 КОМПАНИЯ из 'от ЗАО': {company_name.title()}")
                        if email_id:
                            self.company_cache[email_id] = company_name.title()
                        return company_name.title()

            # ✅ СПОСОБ 5: Ищем просто "ООО", "ОАО", "ЗАО"
            company_patterns = [
                (r'ооо\s+["«]?([а-яёa-z0-9\-&\.\s]+?)["»]?', "ООО"),
                (r'оао\s+["«]?([а-яёa-z0-9\-&\.\s]+?)["»]?', "ОАО"),
                (r'зао\s+["«]?([а-яёa-z0-9\-&\.\s]+?)["»]?', "ЗАО"),
                (r'компани(?:я|и|ей)?\s+["«]?([а-яёa-z0-9\-&\.\s]+?)["»]?', "Компания"),
                (r'фирм(?:а|ы|е)?\s+["«]?([а-яёa-z0-9\-&\.\s]+?)["»]?', "Фирма"),
                (r'предприяти(?:е|я|ю)?\s+["«]?([а-яёa-z0-9\-&\.\s]+?)["»]?', "Предприятие"),
            ]

            for pattern, company_type in company_patterns:
                match = re.search(pattern, subject, re.IGNORECASE)
                if match:
                    company_name = match.group(1).strip('.,!?«»"\'')
                    if len(company_name) > 2:
                        logger.info(f"   🏢 КОМПАНИЯ из '{company_type}': {company_name.title()}")
                        if email_id:
                            self.company_cache[email_id] = company_name.title()
                        return company_name.title()

            # ✅ СПОСОБ 6: Извлекаем из имени отправителя (если не похоже на имя человека)
            if from_name:
                from_name_lower = from_name.lower()

                # Проверяем что это не обычное имя человека
                common_names = [
                    'alex', 'alexander', 'john', 'peter', 'michael', 'david',
                    'максим', 'иван', 'анна', 'мария', 'ольга', 'елена', 'наталья',
                    'sasha', 'alexey', 'sergey', 'dmitry', 'andrey', 'vladimir'
                ]

                is_person_name = any(name in from_name_lower for name in common_names)

                if not is_person_name and len(from_name.strip()) > 3:
                    # Проверяем на признаки компании
                    company_indicators = ['ооо', 'зао', 'ао', 'company', 'corp', 'inc', 'ltd', 'группа', 'про', 'техно']
                    if any(indicator in from_name_lower for indicator in company_indicators):
                        logger.info(f"   🏢 КОМПАНИЯ из имени отправителя: {from_name}")
                        if email_id:
                            self.company_cache[email_id] = from_name
                        return from_name
                    else:
                        # Если имя содержит пробелы или длинное - может быть компанией
                        if ' ' in from_name or len(from_name) > 10:
                            logger.info(f"   🏢 КОМПАНИЯ (предположительно из имени): {from_name}")
                            if email_id:
                                self.company_cache[email_id] = from_name
                            return from_name

            # ✅ СПОСОБ 7: Извлекаем из домена email
            if '@' in from_email:
                domain = from_email.split('@')[1]

                # Игнорируем общие почтовые сервисы
                common_domains = [
                    'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com',
                    'mail.ru', 'yandex.ru', 'rambler.ru', 'bk.ru', 'list.ru',
                    'inbox.ru', 'redditmail.com', 'tinkoff.ru', 'sportmaster.ru'
                ]

                if domain not in common_domains:
                    # Извлекаем название компании из домена
                    company_from_domain = domain.split('.')[0]

                    # Преобразуем: lemanapro -> ЛеманаПРО, system-pbo -> SystemPBO
                    if company_from_domain and len(company_from_domain) > 2:
                        # Убираем цифры и спецсимволы
                        clean_name = re.sub(r'[0-9\-_]', ' ', company_from_domain)
                        clean_name = ' '.join(word.title() for word in clean_name.split())

                        if clean_name and len(clean_name) > 2:
                            logger.info(f"   🏢 КОМПАНИЯ из домена: {clean_name}")
                            if email_id:
                                self.company_cache[email_id] = clean_name
                            return clean_name

            logger.info(f"   ❌ Компания не найдена")
            return None

        except Exception as e:
            logger.error(f"Ошибка извлечения названия компании: {e}")
            return None

    def _get_or_create_contact(self, email: Dict, company_name: str = None) -> Optional[Dict]:
        """Создать или найти контакт С УЧЕТОМ КОМПАНИИ"""
        logger.info(f"\n👤 ОБРАБОТКА КОНТАКТА (с компанией: {company_name})")

        # ✅ ИСПОЛЬЗУЕМ НОВЫЙ МЕТОД с учетом компании
        if company_name:
            contact = self.weeek_client.get_or_create_contact_with_company(email, company_name)
        else:
            # Старая логика для писем без компании
            from_email = email.get('from_email', '')
            from_name = email.get('from_name', '')

            if not from_email:
                logger.warning("Не удалось извлечь email отправителя")
                return None

            contact_data = {
                'emails': [from_email],
                'firstName': '',
                'lastName': ''
            }

            if from_name:
                parts = from_name.strip().split()
                if len(parts) >= 2:
                    contact_data['firstName'] = parts[0]
                    contact_data['lastName'] = ' '.join(parts[1:])
                else:
                    contact_data['firstName'] = from_name

            if not contact_data['firstName']:
                username = from_email.split('@')[0]
                username = username.replace('.', ' ').replace('_', ' ').title()
                parts = username.split()
                if len(parts) >= 2:
                    contact_data['firstName'] = parts[0]
                    contact_data['lastName'] = ' '.join(parts[1:])
                else:
                    contact_data['firstName'] = username if username else "Клиент"

            contact = self.weeek_client.get_or_create_contact(contact_data)

        return contact

    def _prepare_task_data(self, email: Dict, contact: Dict) -> Dict:
        workspace_id = None
        sources = []

        # Проверяем все возможные источники workspaceId
        if contact.get('workspaceId'):
            workspace_id = contact.get('workspaceId')
            sources.append('contact')
        elif hasattr(settings, 'WEEEK_WORKSPACE_ID') and settings.WEEEK_WORKSPACE_ID:
            workspace_id = settings.WEEEK_WORKSPACE_ID
            sources.append('settings')
        elif self.weeek_client.workspace_id:
            workspace_id = self.weeek_client.workspace_id
            sources.append('client')

        if workspace_id:
            logger.debug(f"Используем workspaceId: {workspace_id} (источник: {', '.join(sources)})")
        else:
            logger.error("❌ workspaceId не найден ни в одном источнике!")
            raise ValueError("workspaceId обязателен для создания задачи")

        # Форматируем описание
        desc = self._format_task_description(email, contact)

        # Теги
        tags = [
            self.config['weeek']['email_tag'],
            self.config['weeek']['inbox_tag'],
            datetime.now().strftime('%Y-%m')
        ]

        # Добавляем тег по домену
        if '@' in email.get('from_email', ''):
            domain = email.get('from_email', '').split('@')[1].split('.')[0]
            if len(domain) <= 15 and domain.isalpha():
                tags.append(domain.upper())

        # ИСПРАВЛЕННАЯ ГЕНЕРАЦИЯ НАЗВАНИЯ:
        subject = email.get('subject', '').strip()

        # Если тема пустая или "Без темы"
        if not subject or subject.lower() == 'без темы':
            # Пробуем взять имя из контакта
            first_name = str(contact.get('firstName', '')).strip()
            last_name = str(contact.get('lastName', '')).strip()

            if first_name or last_name:
                contact_name = f"{first_name} {last_name}".strip()
                subject = f"Письмо от {contact_name}"
            else:
                # Пробуем из email
                from_email = email.get('from_email', '')
                if from_email and '@' in from_email:
                    username = from_email.split('@')[0]
                    # Преобразуем user.name -> User Name
                    username = username.replace('.', ' ').replace('_', ' ').title()
                    subject = f"Письмо от {username}"
                else:
                    subject = "Новое письмо"

        # Очищаем тему от лишних пробелов и переносов
        subject = ' '.join(subject.split())  # Убирает множественные пробелы
        subject = subject.replace('\n', ' ').replace('\r', ' ')

        # Ограничиваем длину
        if len(subject) > 70:
            subject = subject[:67] + "..."

        # Добавляем эмодзи если его еще нет
        if not subject.startswith('📧'):
            task_name = f"📧 {subject}"
        else:
            task_name = subject

        # ИСПРАВЛЕННАЯ СТРУКТУРА TASK_DATA:
        task_data = {
            'title': task_name,
            'description': desc,
            'contactIds': [contact.get('id')],
            'tags': tags,

            # ОБЯЗАТЕЛЬНЫЕ ПОЛЯ:
            'workspaceId': workspace_id,

            # Важные поля для правильного отображения:
            'priority': 2,
            'type': 'action',
            'dueDate': (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
        }

        # Добавляем проект если указан
        project_id = self.config['weeek'].get('default_project')
        if project_id:
            task_data['projectId'] = project_id

        # Если нет projectId, проверяем есть ли у контакта связанный проект
        elif contact.get('projectId'):
            task_data['projectId'] = contact.get('projectId')

        task_data = {k: v for k, v in task_data.items() if v is not None}

        return task_data

    def _format_task_description(self, email: Dict, contact: Dict) -> str:
        """Форматировать описание задачи"""
        lines = [
            "# 📧 ВХОДЯЩЕЕ ПИСЬМО",
            "",
            "## 👤 ИНФОРМАЦИЯ О КОНТАКТЕ",
            f"- **Имя:** {contact.get('firstName', '')} {contact.get('lastName', '')}",
            f"- **Email:** {self._get_email_from_contact(contact)}",
            f"- **ID контакта:** `{contact.get('id')}`",
            "",
            "## 📩 ИНФОРМАЦИЯ О ПИСЬМЕ",
            f"- **Отправитель:** {email.get('from_name', '')} <{email.get('from_email', '')}>",
            f"- **Дата получения:** {email.get('date')}",
            f"- **Тема:** {email.get('subject', 'Без темы')}",
            "",
            "## 📄 ТЕКСТ ПИСЬМА",
            "---",
        ]

        # Тело письма
        body = email.get('body_text', '')
        if body:
            # Очищаем текст до совершенного вида
            clean_body = self._clean_email_text_perfectly(body)
            if not clean_body or clean_body == "(Текст письма не содержит значимого содержания)":
                lines.append(clean_body)
            else:
                lines.append(clean_body)
        else:
            lines.append("(Текст письма отсутствует или не удалось извлечь)")

        # Вложения
        attachments = email.get('attachments', [])
        if attachments:
            lines.append("")
            lines.append("## 📎 ВЛОЖЕНИЯ")
            for i, att in enumerate(attachments, 1):
                lines.append(f"{i}. **{att.get('filename', 'Файл')}** ({att.get('size', 0)} байт)")

        lines.append("")
        lines.append("---")
        lines.append(f"*🤖 Обработано автоматически: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        # ОГРАНИЧЕНИЕ ДЛЯ WEEEK API
        max_length = 10000
        description = "\n".join(lines)

        if len(description) > max_length:
            logger.warning(f"Описание слишком длинное ({len(description)} > {max_length}), обрезаем")
            description = description[:max_length] + f"\n\n[... текст сокращен ...]"

        return description

    def _clean_email_text_perfectly(self, text: str) -> str:
        """СОВЕРШЕННАЯ очистка текста писем - удаляет всё лишнее, оставляет красоту"""
        if not text:
            return ""

        import re
        from html import unescape

        # 🔥 ЭТАП 1: УДАЛЯЕМ ВСЮ ТЕХНИЧЕСКУЮ ЕРУНДУ

        # 1. Удаляем ВЕСЬ CSS код (рекурсивно, включая вложенные {})
        while True:
            new_text = re.sub(r'\{[^{}]*\}', '', text)
            if new_text == text:
                break
            text = new_text

        # 2. Удаляем HTML теги с сохранением структуры
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<p[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<div[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)

        # 3. Удаляем остальные HTML теги
        text = re.sub(r'<[^>]+>', '', text)

        # 4. Удаляем CSS классы и селекторы
        text = re.sub(r'\.\w+[^{]*', '', text)
        text = re.sub(r'#[^{]*', '', text)
        text = re.sub(r'style="[^"]*"', '', text)

        # 5. Удаляем медиа-запросы и импорты
        text = re.sub(r'@media[^{]+\{[^}]*\}', '', text, flags=re.DOTALL)
        text = re.sub(r'@import[^;]+;', '', text)

        # 6. Убираем HTML entities
        text = unescape(text)

        # 7. Удаляем URL encoded пробелы и спецсимволы
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
        text = text.replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'")

        # 🔥 ЭТАП 2: УДАЛЯЕМ СЛУЖЕБНЫЕ СИМВОЛЫ И КОД

        # 8. Удаляем невидимые символы (zero-width, мягкие переносы)
        text = re.sub(r'[\u200B\u200C\u200D\uFEFF\u00AD]', '', text)

        # 9. Удаляем символы-заполнители (часто в спаме)
        text = text.replace('⠀⠀', '').replace('▪', '').replace('•', '')
        text = text.replace('▫', '').replace('◼', '').replace('⬤', '')

        # 10. Удаляем строки с только CSS/HTML кодом
        css_keywords = [
            'width:', 'height:', 'margin:', 'padding:', 'background:',
            'color:', 'font-family:', 'font-size:', 'display:', 'position:',
            'float:', 'clear:', 'border:', 'text-align:', 'line-height:',
            'webkit-', 'moz-', 'ms-', 'o-', '!important', 'transparent',
            'inherit', 'initial', 'unset', 'sans-serif', 'serif', 'monospace',
            'linear-gradient', 'radial-gradient', 'rgba(', 'hsl(',
            'max-width', 'min-width', 'max-height', 'min-height',
            'cursor:', 'opacity:', 'visibility:', 'z-index:', 'box-sizing:'
        ]

        for keyword in css_keywords:
            text = text.replace(keyword, '')

        # 🔥 ЭТАП 3: ОЧИЩАЕМ ПОСТРОЧНО

        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()

            # Пропускаем если:
            # - пустая строка
            # - только спецсимволы
            # - выглядит как код
            # - слишком короткая (кроме маркеров списка)
            if (not line or
                    len(line) < 2 or
                    re.match(r'^[\s\-*.,:;]+$', line) or
                    re.match(r'^[{}.#@]', line) or
                    (';' in line[:20] and '://' not in line) or
                    (':' in line[:10] and '//' not in line)):
                continue

            # Убираем множественные пробелы
            line = re.sub(r'\s+', ' ', line)

            # Убираем пробелы в начале списков
            if line.startswith('- ') or line.startswith('* '):
                line = line[2:].strip()
                line = f"- {line}"

            # Убираем лишние точки
            line = re.sub(r'\.{3,}', '...', line)

            cleaned_lines.append(line)

        if not cleaned_lines:
            return "(Текст письма не содержит значимого содержания)"

        # 🔥 ЭТАП 4: ФОРМАТИРУЕМ КРАСИВО

        # Собираем с умными абзацами
        result = []
        current_block = []

        for line in cleaned_lines:
            # Определяем тип строки
            is_list_item = line.startswith('-')
            is_short = len(line) < 50
            is_signature = any(word in line.lower() for word in
                               ['с уважением', 'best regards', 'спасибо', 'thanks', 'искренне'])

            # Если это новая мысль - начинаем новый блок
            if (current_block and
                    ((is_short and not is_list_item) or
                     (is_list_item and not current_block[-1].startswith('-')) or
                     is_signature)):
                if current_block:
                    result.append(' '.join(current_block))
                    current_block = []

            current_block.append(line)

        # Добавляем последний блок
        if current_block:
            result.append(' '.join(current_block))

        # Создаем красивые абзацы
        beautiful_text = '\n\n'.join(result)

        # 🔥 ЭТАП 5: ФИНАЛЬНАЯ ПОЛИРОВКА

        # Исправляем подписи
        beautiful_text = re.sub(r'С уважением,(\w)', r'С уважением, \1', beautiful_text, flags=re.IGNORECASE)
        beautiful_text = re.sub(r'Best regards,(\w)', r'Best regards, \1', beautiful_text, flags=re.IGNORECASE)

        # Добавляем абзацы после заголовков
        headings = ['СРОЧНО!', 'URGENT!', 'ВАЖНО!', 'IMPORTANT!']
        for heading in headings:
            if heading in beautiful_text:
                beautiful_text = beautiful_text.replace(heading, heading + '\n')

        # Убираем множественные переносы
        beautiful_text = re.sub(r'\n{3,}', '\n\n', beautiful_text)

        # Обрезаем если слишком длинное
        if len(beautiful_text) > 6000:
            beautiful_text = beautiful_text[:6000] + "\n\n[... текст сокращен ...]"

        return beautiful_text.strip()

    def _get_email_from_contact(self, contact: Dict) -> str:
        """Получить email из контакта Weeek"""
        emails = contact.get('emails', [])
        if emails:
            for email_item in emails:
                if isinstance(email_item, dict):
                    email = email_item.get('email', '')
                    if email:
                        return email
                elif isinstance(email_item, str) and '@' in email_item:
                    return email_item
        return ''

    def _handle_attachments(self, email: Dict, contact: Dict, task: Dict):
        """Обработать вложения"""
        attachments_processed = 0
        for attachment in email.get('attachments', []):
            try:
                filename = attachment.get('filename', 'attachment.bin')
                filepath = f"data/attachments/{task.get('id')}_{filename}"

                # Проверяем размер файла
                file_size = len(attachment.get('payload', b''))
                if file_size > 10 * 1024 * 1024:  # 10 MB лимит
                    logger.warning(f"Пропускаем большое вложение {filename} ({file_size} байт)")
                    continue

                with open(filepath, 'wb') as f:
                    f.write(attachment.get('payload', b''))

                attachments_processed += 1
                logger.info(f"Вложение сохранено: {filename} ({file_size} байт)")

            except Exception as e:
                logger.error(f"Ошибка сохранения вложения {filename}: {e}")

        if attachments_processed:
            logger.info(f"Сохранено {attachments_processed} вложений для задачи {task.get('id')}")

    def _save_processing_result(self, email: Dict, contact: Dict, task: Dict):
        """Сохранить результат обработки"""
        try:
            result = {
                'task': {
                    'id': task.get('id'),
                    'title': task.get('title'),
                    'createdAt': task.get('createdAt'),
                },
                'contact': {
                    'id': contact.get('id'),
                    'name': f"{contact.get('firstName', '')} {contact.get('lastName', '')}",
                    'email': self._get_email_from_contact(contact),
                },
                'email': {
                    'from': email.get('from_email'),
                    'subject': email.get('subject'),
                    'date': str(email.get('date')),
                    'message_id': email.get('message_id'),
                },
                'processing': {
                    'timestamp': datetime.now().isoformat(),
                    'version': '1.0'
                }
            }

            filename = f"data/processed/{task.get('id')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            logger.debug(f"Результат сохранен: {filename}")

        except Exception as e:
            logger.error(f"Ошибка сохранения результата: {e}")

    def _save_contact_locally(self, contact: Dict):
        """Сохранить контакт локально"""
        try:
            filename = f"data/contacts/{contact.get('id')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(contact, f, indent=2, ensure_ascii=False)
        except:
            pass

    def _save_error(self, email: Dict, error_msg: str):
        """Сохранить ошибку"""
        try:
            error_data = {
                'email': {
                    'from': email.get('from_email'),
                    'subject': email.get('subject'),
                    'date': str(email.get('date')),
                },
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            }

            filename = f"logs/errors/error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(error_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Ошибка сохранения ошибки: {e}")

    def _add_to_skip_list(self, domain: str):
        """Добавить домен в список пропуска"""
        try:
            if domain not in self.config['processing']['skip_patterns']:
                self.config['processing']['skip_patterns'].append(domain)

                # Сохраняем обновленный конфиг
                config_path = 'config/integration_config.json'
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=2, ensure_ascii=False)

                logger.info(f"   ✅ Домен {domain} добавлен в список пропуска")

        except Exception as e:
            logger.error(f"   ⚠️  Не удалось добавить домен в список пропуска: {e}")

    def _show_results(self, stats: Dict):
        """Показать результаты обработки"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 РЕЗУЛЬТАТЫ ОБРАБОТКИ")
        logger.info("=" * 80)
        logger.info(f"   Всего писем: {stats['total_processed']}")
        logger.info(f"   Создано задач: {stats['tasks_created']}")
        logger.info(f"   Создано контактов: {stats['contacts_created']}")
        logger.info(f"   Пропущено писем: {stats['emails_skipped']}")
        logger.info(f"   Ошибок: {stats['errors']}")
        logger.info(f"   Время обработки: {stats['duration']:.1f} секунд")

        if stats['tasks_created'] > 0:
            logger.info(f"\n💡 Проверьте созданные задачи:")
            logger.info(f"   🔗 https://app.weeek.net/ws")
            logger.info(f"   📋 Раздел 'Задачи'")
            logger.info(f"   🏷️  Ищите по тегу '{self.config['weeek']['email_tag']}'")

        logger.info("=" * 80)

    def _save_daily_report(self, stats: Dict):
        """Сохранить ежедневный отчет"""
        try:
            # Преобразуем datetime в строки
            serializable_stats = {}
            for key, value in stats.items():
                if isinstance(value, datetime):
                    serializable_stats[key] = value.isoformat()
                else:
                    serializable_stats[key] = value

            report = {
                'date': datetime.now().isoformat(),
                'stats': serializable_stats,
                'config_used': {
                    'daily_limit': self.config['processing']['daily_limit'],
                    'skip_patterns_count': len(self.config['processing']['skip_patterns']),
                    'important_patterns_count': len(self.config['processing']['important_patterns'])
                }
            }

            filename = f"logs/daily/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            logger.info(f"\n📝 Отчет сохранен: {filename}")

        except Exception as e:
            logger.error(f"Ошибка сохранения отчета: {e}")

    def show_stats(self):
        """Показать статистику системы"""
        logger.info("=" * 80)
        logger.info("📈 СТАТИСТИКА СИСТЕМЫ")
        logger.info("=" * 80)

        # Подсчитываем обработанные задачи
        processed_dir = 'data/processed'
        if os.path.exists(processed_dir):
            task_files = [f for f in os.listdir(processed_dir) if f.endswith('.json')]
            logger.info(f"📋 Обработано задач: {len(task_files)}")

            # Группируем по месяцам
            from collections import defaultdict
            monthly_stats = defaultdict(int)

            for filename in task_files:
                try:
                    with open(os.path.join(processed_dir, filename), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        date_str = data.get('processing', {}).get('timestamp', '')
                        if date_str:
                            month = date_str[:7]  # Год-месяц
                            monthly_stats[month] += 1
                except:
                    pass

            if monthly_stats:
                logger.info("\n📅 По месяцам:")
                for month, count in sorted(monthly_stats.items()):
                    logger.info(f"   {month}: {count} задач")

        # Контакты
        contacts_dir = 'data/contacts'
        if os.path.exists(contacts_dir):
            contact_files = [f for f in os.listdir(contacts_dir) if f.endswith('.json')]
            logger.info(f"\n👤 Контактов сохранено: {len(contact_files)}")

        # Настройки
        logger.info(f"\n⚙️  НАСТРОЙКИ:")
        logger.info(f"   Паттернов пропуска: {len(self.config['processing']['skip_patterns'])}")
        logger.info(f"   Важных ключевых слов: {len(self.config['processing']['important_patterns'])}")
        logger.info(f"   Домены клиентов: {len(self.config['processing']['client_domains'])}")

        logger.info("=" * 80)

def main():
    """Главная функция"""
    import argparse

    parser = argparse.ArgumentParser(description='Полная интеграция Gmail с Weeek')
    parser.add_argument('--limit', type=int, help='Лимит обработки писем')
    parser.add_argument('--stats', action='store_true', help='Показать статистику')
    parser.add_argument('--config', action='store_true', help='Показать конфигурацию')
    parser.add_argument('--auto-mode', action='store_true',
                        help='Автоматический режим (не спрашивать подтверждения)')

    args = parser.parse_args()

    integration = CompleteIntegration()

    if args.stats:
        integration.show_stats()
    elif args.config:
        print(json.dumps(integration.config, indent=2, ensure_ascii=False))
    else:
        integration.run_daily_processing(limit=args.limit)

if __name__ == "__main__":
    main()