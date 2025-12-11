import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import requests
import json
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from config.settings import settings
from utils.retry import retry_api
from collections import OrderedDict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class WeeekClient:
    """Клиент для работы с Weeek API"""

    def __init__(self):
        self.api_key = settings.WEEEK_API_KEY
        self.workspace_id = settings.WEEEK_WORKSPACE_ID
        self.base_url = "https://api.weeek.net/public/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Кэш для организаций (LRU)
        self.org_cache = OrderedDict()
        self.cache_time = {}
        self.max_cache_size = 200

        logger.debug(f"WeeekClient инициализирован, workspace_id: {self.workspace_id}")

    def _add_to_cache(self, org_name: str, org_data: Dict):
        """Добавить в кэш с очисткой старых записей"""
        org_lower = org_name.lower()

        # 1. Очищаем старые записи (старше 10 минут)
        current_time = time.time()
        to_delete = []
        for key, cache_time in list(self.cache_time.items()):
            if current_time - cache_time > 600:  # 10 минут
                to_delete.append(key)

        for key in to_delete:
            self.org_cache.pop(key, None)
            self.cache_time.pop(key, None)

        # 2. Удаляем лишние записи (LRU)
        while len(self.org_cache) >= self.max_cache_size:
            oldest_key = next(iter(self.org_cache))
            self.org_cache.pop(oldest_key, None)
            self.cache_time.pop(oldest_key, None)

        # 3. Добавляем новую запись
        self.org_cache[org_lower] = org_data
        self.cache_time[org_lower] = current_time

    def add_contact_email(self, contact_id: str, email: str, email_type: str = 'work') -> Optional[Dict]:
        """Добавить email к контакту"""
        try:
            data = {
                'email': email,
                'type': email_type
            }

            result = self._request('POST', f'/crm/contacts/{contact_id}/emails', data=data)

            if result.get('success'):
                email_data = result.get('email')
                logger.info(f"Email добавлен к контакту {contact_id}: {email}")
                return email_data
            else:
                logger.error(f"Не удалось добавить email: {result}")
                return None

        except Exception as e:
            logger.error(f"Исключение при добавлении email: {e}")
            return None

    def _convert_priority_to_int(self, priority):
        """Конвертировать приоритет в число 1-5"""
        if priority is None:
            return 3

        try:
            # Если строка - конвертируем в число
            if isinstance(priority, str):
                priority = int(priority)

            # Ограничиваем диапазон 1-5
            priority = int(priority)
            return max(1, min(5, priority))
        except (ValueError, TypeError):
            return 3  # Значение по умолчанию

    def get_or_create_organization(self, org_name: str) -> Optional[Dict]:
        """Найти или создать организацию (с кэшированием)"""
        org_lower = org_name.lower()

        # ✅ ПРОВЕРЯЕМ КЭШ (действителен 5 минут)
        if org_lower in self.org_cache:
            cache_time = self.cache_time.get(org_lower)
            if cache_time and (datetime.now() - cache_time).seconds < 300:
                print(f"   💾 Используем кэш для организации: {org_name}")
                return self.org_cache[org_lower]

        # Искать по названию
        print(f"   🔍 Поиск организации: {org_name}")
        orgs = self.get_organizations(search=org_name)
        for org in orgs:
            if org.get('name', '').lower() == org_lower:
                # ✅ СОХРАНЯЕМ В КЭШ
                self.org_cache[org_lower] = org
                self.cache_time[org_lower] = datetime.now()
                return org

        # Создать новую
        print(f"   🏢 Создание организации: {org_name}")
        org = self.create_organization({'name': org_name})
        if org:
            # ✅ СОХРАНЯЕМ В КЭШ
            self.org_cache[org_lower] = org
            self.cache_time[org_lower] = datetime.now()

        return org

    def get_or_create_contact(self, contact_data: Dict) -> Optional[Dict]:
        """Найти или создать контакт"""
        # ПОДДЕРЖИВАЕМ ДВА ФОРМАТА ДАННЫХ:
        # 1. Старый формат: {"emails": ["email@example.com"], "firstName": "...", "lastName": "..."}
        # 2. Новый формат: {"from_email": "email@example.com", "from_name": "Имя Фамилия"}

        # Получаем email разными способами
        email = None

        # Способ 1: из массива emails
        emails = contact_data.get('emails', [])
        if emails:
            if isinstance(emails, list) and len(emails) > 0:
                email = emails[0] if isinstance(emails[0], str) else emails[0].get('email', '')

        # Способ 2: из поля from_email
        if not email:
            email = contact_data.get('from_email', '')

        if not email:
            logger.error("❌ Не указан email в contact_data")
            return None

        # 1. Искать по email
        existing = self.search_contact_by_email(email)
        if existing:
            logger.info(f"✅ Контакт уже существует: {existing.get('id')}")
            return existing

        # 2. Создать если не найден
        # Нужно преобразовать данные в правильный формат
        formatted_data = {}

        # Если уже есть firstName и lastName - используем их
        if 'firstName' in contact_data and 'lastName' in contact_data:
            formatted_data = contact_data.copy()
        else:
            # Парсим имя из from_name
            from_name = contact_data.get('from_name', '')
            if from_name:
                parts = from_name.strip().split()
                if len(parts) >= 2:
                    first_name = parts[0]
                    last_name = ' '.join(parts[1:])
                else:
                    first_name = from_name
                    last_name = ""
            else:
                # Из email
                username = email.split('@')[0]
                username = username.replace('.', ' ').replace('_', ' ').title()
                parts = username.split()
                if len(parts) >= 2:
                    first_name = parts[0]
                    last_name = ' '.join(parts[1:])
                else:
                    first_name = username if username else "Клиент"
                    last_name = ""

            formatted_data = {
                'firstName': first_name,
                'lastName': last_name,
                'emails': [email]
            }

        return self.create_contact(formatted_data)

    @retry_api(max_attempts=3, delay=1.0)
    def create_task(self, task_data):
        """Создание задачи в Weeek"""
        logger.info(f"Создание задачи: {task_data.get('title', 'Без названия')}")
        try:
            # КОНВЕРТИРУЕМ ПРИОРИТЕТ ИЗ TASK_DATA
            if 'priority' in task_data:
                task_data['priority'] = self._convert_priority_to_int(task_data['priority'])
            # ДОБАВЬТЕ ПРОВЕРКУ workspaceId
            if 'workspaceId' not in task_data:
                # Используем self.workspace_id который уже загружен из settings
                if self.workspace_id:
                    task_data['workspaceId'] = self.workspace_id
                    logger.info(f"Добавлен workspaceId: {self.workspace_id}")
                else:
                    logger.warning("⚠️ workspaceId не указан в настройках")

            # ЛОГИРУЕМ ДАННЫЕ
            logger.debug(f"Отправка данных задачи в Weeek:")
            logger.debug(json.dumps(task_data, indent=2, ensure_ascii=False))

            result = self._request('POST', '/tm/tasks', data=task_data)

            # ОТЛАДОЧНОЕ ЛОГИРОВАНИЕ
            logger.debug(f"📊 ОТВЕТ WEEEK API ПРИ СОЗДАНИИ ЗАДАЧИ:")
            logger.debug(json.dumps(result, indent=2, ensure_ascii=False))
            logger.debug(f"task_data отправлено: {json.dumps(task_data, indent=2, ensure_ascii=False)}")

            # ЛОГИРУЕМ ОТВЕТ
            logger.debug(f"Ответ от Weeek API: {json.dumps(result, indent=2, ensure_ascii=False)}")

            if result.get('success'):
                task = result.get('task')
                if task:
                    logger.info(f"✅ Задача создана: ID={task.get('id')}, Title={task.get('title')}")
                    return task
            logger.error(f"❌ Создание задачи не удалось: {result}")
            return None
        except Exception as e:
            logger.error(f"❌ Исключение при создании задачи: {e}", exc_info=True)
            return None

    @retry_api(max_attempts=2, delay=2.0)
    def get_projects(self):
        """Получить список проектов"""
        try:
            result = self._request('GET', '/tm/projects')
            if result.get('success'):
                return result.get('projects', [])
            return []
        except Exception as e:
            logger.error(f"Ошибка получения проектов: {e}")
            return []

    def get_tasks_by_contact(self, contact_id: str) -> list:
        """Получить задачи связанные с контактом"""
        try:
            # Используем параметр contactId для фильтрации
            params = {'contactId': contact_id}
            result = self._request('GET', '/tm/tasks', params=params)

            if result.get('success'):
                return result.get('tasks', [])

            logger.warning(f"Не удалось получить задачи для контакта {contact_id}")
            return []

        except Exception as e:
            logger.error(f"Ошибка получения задач контакта: {e}")
            return []

    def task_exists_for_email(self, email_subject: str, contact_id: str, hours_threshold: int = 24) -> bool:
        """Проверить есть ли уже задача для этого письма"""
        logger.debug(f"Проверка дубликатов для письма (contact_id: {contact_id})")

        try:
            # Получаем задачи контакта
            tasks = self.get_tasks_by_contact(contact_id)
            logger.debug(f"Найдено {len(tasks)} задач у контакта {contact_id}")

            # Если у контакта много задач - проверяем только последние
            if len(tasks) > 10:
                logger.debug(f"У контакта много задач, проверяем только последние 5")
                tasks = tasks[:5]

            if not tasks:
                logger.debug(f"У контакта нет задач - можно создавать новую")
                return False

            # Подготавливаем данные для сравнения
            email_lower = str(email_subject).lower().strip()
            logger.debug(f"Тема письма для проверки: '{email_lower[:100]}'")

            # Проверяем есть ли "от ооо " в теме письма
            has_ooo_in_email = "от ооо " in email_lower
            logger.debug(f"Есть 'от ооо ' в теме письма? {has_ooo_in_email}")

            for task in tasks:
                task_id = task.get('id')
                task_title = str(task.get('title', '')).strip()

                if not task_title:
                    logger.debug(f"Задача {task_id}: нет названия, пропускаем")
                    continue

                task_lower = task_title.lower()
                logger.debug(f"Сравниваем с задачей {task_id}: '{task_lower[:100]}'")

                # ПРОВЕРКА 1: Если обе темы содержат "от ооо "
                if has_ooo_in_email and "от ооо " in task_lower:
                    logger.debug(f"Обе темы содержат 'от ооо ' - проверяем компании")

                    # Извлекаем компанию из темы письма
                    email_pos = email_lower.find("от ооо ") + len("от ооо ")
                    task_pos = task_lower.find("от ооо ") + len("от ооо ")

                    email_company = email_lower[email_pos:].split()[0] if email_pos >= len("от ооо ") else ""
                    task_company = task_lower[task_pos:].split()[0] if task_pos >= len("от ооо ") else ""

                    logger.debug(f"Компания в письме: '{email_company}'")
                    logger.debug(f"Компания в задаче: '{task_company}'")

                    # Если компании совпадают - это дубликат!
                    if email_company and task_company:
                        # Убираем возможные окончания
                        email_clean = email_company.rstrip('.,!?')
                        task_clean = task_company.rstrip('.,!?')

                        logger.debug(f"Сравнение очищенных названий: '{email_clean}' vs '{task_clean}'")

                        if email_clean == task_clean:
                            # Проверяем время создания задачи
                            created_str = task.get('createdAt')
                            if created_str:
                                try:
                                    now = datetime.now()
                                    created_date = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                                    hours_diff = (now - created_date).total_seconds() / 3600

                                    logger.debug(f"Задача создана {hours_diff:.1f} часов назад")

                                    if hours_diff < hours_threshold:
                                        logger.info(
                                            f"🚨 Найден дубликат! Задача {task_id} создана {hours_diff:.1f} часов назад")
                                        logger.info(f"   Письмо: '{email_lower[:80]}'")
                                        logger.info(f"   Задача: '{task_lower[:80]}'")
                                        logger.info(f"   Компания: {email_clean}")
                                        return True
                                except Exception as date_error:
                                    logger.warning(f"Ошибка парсинга даты задачи {task_id}: {date_error}")
                                    logger.info(f"Задача {task_id} уже существует (ошибка даты)")
                                    return True
                            else:
                                logger.info(f"Задача {task_id} уже существует (нет даты создания)")
                                return True
                        else:
                            logger.debug(f"Разные компании - не дубликат")
                    else:
                        logger.debug(f"Не удалось извлечь название компании для сравнения")

                # ПРОВЕРКА 2: Если темы начинаются одинаково
                elif email_lower.startswith("предложение о") and task_lower.startswith("предложение о"):
                    logger.debug(f"Обе темы начинаются с 'предложение о'")

                    # Сравниваем первые 30 символов
                    if email_lower[:30] == task_lower[:30]:
                        logger.info(f"🚨 Найден дубликат! Совпадают первые 30 символов")
                        logger.info(f"   Письмо: '{email_lower[:80]}'")
                        logger.info(f"   Задача: '{task_lower[:80]}'")
                        return True

                # ПРОВЕРКА 3: Общая проверка похожести тем
                elif len(email_lower) > 20 and len(task_lower) > 20:
                    # Сравниваем начало тем (первые 20 символов)
                    if email_lower[:20] == task_lower[:20]:
                        logger.debug(f"Начало тем совпадает, проверяем полное совпадение")

                        # Если темы полностью совпадают (с допуском на опечатки)
                        similarity = self._calculate_string_similarity(email_lower, task_lower)
                        if similarity > 0.9:  # 90% похожести
                            logger.info(f"🚨 Найден похожий дубликат! Схожесть: {similarity:.1%}")
                            logger.info(f"   Письмо: '{email_lower[:80]}'")
                            logger.info(f"   Задача: '{task_lower[:80]}'")
                            return True

            logger.debug(f"Дубликатов не найдено для контакта {contact_id}")
            return False

        except Exception as e:
            logger.error(f"❌ Ошибка проверки задач на дубликаты: {e}")
            logger.debug(f"Traceback:", exc_info=True)
            return False  # При ошибке считаем что дубликатов нет

    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Рассчитать схожесть двух строк (0.0 - 1.0)"""
        try:
            # Простая реализация через расстояние Левенштейна
            import numpy as np

            len1, len2 = len(str1), len(str2)
            max_len = max(len1, len2)

            if max_len == 0:
                return 1.0

            # Создаем матрицу
            d = np.zeros((len1 + 1, len2 + 1), dtype=int)

            for i in range(len1 + 1):
                d[i, 0] = i
            for j in range(len2 + 1):
                d[0, j] = j

            # Заполняем матрицу
            for i in range(1, len1 + 1):
                for j in range(1, len2 + 1):
                    if str1[i - 1] == str2[j - 1]:
                        cost = 0
                    else:
                        cost = 1
                    d[i, j] = min(
                        d[i - 1, j] + 1,  # удаление
                        d[i, j - 1] + 1,  # вставка
                        d[i - 1, j - 1] + cost  # замена
                    )

            distance = d[len1, len2]
            similarity = 1 - (distance / max_len)

            logger.debug(f"Схожесть строк: '{str1[:50]}...' и '{str2[:50]}...' = {similarity:.1%}")
            return similarity

        except Exception as e:
            logger.debug(f"Ошибка расчета схожести строк: {e}")
            return 0.0

    def add_contact_comment(self, contact_id: str, comment_text: str) -> bool:
        """Добавить комментарий к контакту"""
        try:
            data = {'text': comment_text}
            result = self._request('POST', f'/crm/contacts/{contact_id}/comments', data=data)

            if result.get('success'):
                logger.info(f"Комментарий добавлен к контакту {contact_id}")
                return True
            else:
                logger.error(f"Ошибка добавления комментария: {result}")
                return False

        except Exception as e:
            logger.error(f"Исключение при добавлении комментария: {e}")
            return False

    def get_contact_comments(self, contact_id: str) -> list:
        """Получить комментарии контакта"""
        try:
            result = self._request('GET', f'/crm/contacts/{contact_id}/comments')
            if result.get('success'):
                return result.get('comments', [])
            return []
        except Exception as e:
            logger.error(f"Ошибка получения комментариев: {e}")
            return []

    def add_contact_note(self, contact_id: str, note_text: str) -> bool:
        """Добавить заметку к контакту (альтернатива комментариям)"""
        try:
            data = {'text': note_text}
            result = self._request('POST', f'/crm/contacts/{contact_id}/notes', data=data)

            if result.get('success'):
                logger.info(f"Заметка добавлена к контакту {contact_id}")
                return True
            else:
                # Пробуем через другой endpoint
                logger.warning(f"Заметки через /notes не работают, пробуем /comments")
                return self.add_contact_comment(contact_id, note_text)

        except Exception as e:
            logger.error(f"Исключение при добавлении заметки: {e}")
            # Пробуем как комментарий
            return self.add_contact_comment(contact_id, note_text)

    # И убедитесь что в create_contact вызывается этот метод:
    def create_contact(self, contact_data: Dict) -> Optional[Dict]:
        """Создать новый контакт с правильным форматом emails"""
        try:
            # Правильный формат для Weeek API
            formatted_data = {
                'firstName': contact_data.get('firstName', ''),
                'lastName': contact_data.get('lastName', ''),
            }

            # Добавляем emails как массив строк
            emails = contact_data.get('emails', [])
            if emails:
                formatted_data['emails'] = emails  # Массив строк или объектов с email полем

            # Добавляем workspaceId если есть
            if hasattr(settings, 'WEEEK_WORKSPACE_ID') and settings.WEEEK_WORKSPACE_ID:
                formatted_data['workspaceId'] = settings.WEEEK_WORKSPACE_ID

            # Добавляем другие поля если есть
            for key in ['middleName', 'about', 'position', 'birthDate', 'country']:
                if key in contact_data:
                    formatted_data[key] = contact_data[key]

            logger.debug(f"Создаем контакт с данными: {formatted_data}")

            # Создаем контакт ОДНИМ запросом
            result = self._request('POST', '/crm/contacts', data=formatted_data)

            if result.get('success'):
                contact = result.get('contact')
                if contact:
                    logger.info(f"Контакт создан: ID={contact.get('id')}")
                    return contact
                else:
                    logger.warning("Создание контакта успешно, но нет данных контакта в ответе")
                    return None
            else:
                logger.error(f"Создание контакта не удалось: {result}")
                return None

        except Exception as e:
            logger.error(f"Исключение при создании контакта: {e}")
            return None

    def _request(self, method: str, endpoint: str,
                 data: Optional[Dict] = None,
                 params: Optional[Dict] = None) -> Dict:
        """Базовый метод для запросов с обработкой ответов"""
        url = f"{self.base_url}{endpoint}"

        # МАСКИРУЕМ URL для безопасного логирования
        safe_url = url
        if 'api_key=' in safe_url.lower() or 'token=' in safe_url.lower():
            import re
            safe_url = re.sub(r'([?&](api_key|token|auth)=)[^&]+', r'\1[MASKED]', safe_url)

        logger.debug(f"Запрос {method} к {safe_url}")

        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=self.headers,
                                        params=params, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=self.headers,
                                         json=data, timeout=30)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=self.headers,
                                        json=data, timeout=30)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=self.headers,
                                           timeout=30)
            else:
                raise ValueError(f"Неподдерживаемый метод: {method}")

            response.raise_for_status()
            result = response.json()

            # Логируем ответ
            logger.debug(f"Ответ от {endpoint}: success={result.get('success')}")

            return result

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP ошибка {e.response.status_code} для {endpoint}")
            if hasattr(e, 'response') and e.response.text:
                logger.error(f"Ответ сервера: {e.response.text[:200]}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса к {url}: {e}")
            raise

    # ==================== USER & WORKSPACE ====================

    @retry_api(max_attempts=3, delay=2.0)
    def test_connection(self):
        """Тестирование подключения к Weeek API"""
        logger.info("Тестирование подключения к Weeek API")
        try:
            result = self._request('GET', '/user/me')
            success = result.get('success', False)
            if success:
                user_email = result.get('user', {}).get('email', 'N/A')
                logger.info(f"Подключение успешно. Пользователь: {user_email}")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            return False

    def get_current_user(self) -> Dict:
        """Получить информацию о текущем пользователе"""
        return self._request('GET', '/user/me')

    def get_workspace(self) -> Dict:
        """Получить информацию о workspace"""
        return self._request('GET', '/ws')

    # ==================== CRM - CONTACTS ====================

    @retry_api(max_attempts=2, delay=1.5)
    def get_contacts(self, limit=100, page=1, search=None):
        """Получение списка контактов"""
        logger.debug("Получение списка контактов")
        params = {'limit': limit, 'page': page}
        if search:
            params['search'] = search

        result = self._request('GET', '/crm/contacts', params=params)
        return result.get('contacts', [])

    def get_contact(self, contact_id: str) -> Optional[Dict]:
        """Получить контакт по ID"""
        try:
            result = self._request('GET', f'/crm/contacts/{contact_id}')
            if result.get('success'):
                return result.get('contact')
            return None
        except Exception as e:
            logger.error(f"Ошибка получения контакта: {e}")
            return None

    def get_or_create_contact_with_company(self, email_data: Dict, company_name: str = None) -> Optional[Dict]:
        """
        Создать или найти контакт С УЧЕТОМ КОМПАНИИ

        Args:
            email_data: Данные письма
            company_name: Название компании

        Returns:
            Словарь с данными контакта или None
        """
        print(f"\n🔍 Создание контакта с учетом компании...")
        print(f"   📧 Email: {email_data.get('from_email')}")
        print(f"   🏢 Компания: {company_name}")

        sender_email = email_data.get('from_email', '')
        sender_name = email_data.get('from_name', '')

        if not sender_email:
            print("❌ Нет email отправителя")
            return None

        # ✅ НОВАЯ ЛОГИКА: Ищем контакт с таким email И компанией
        # 1. Ищем все контакты с этим email
        all_contacts = self._get_all_contacts_by_email(sender_email)
        print(f"   📋 Найдено {len(all_contacts)} контактов с email {sender_email}")

        if company_name:
            # 2. Ищем контакт с нужной компанией
            for contact in all_contacts:
                contact_companies = contact.get('organizations', [])
                # Проверяем если контакт уже привязан к организации с таким именем
                if contact_companies:
                    for org_id in contact_companies:
                        org = self.get_organization(org_id)
                        if org and org.get('name', '').lower() == company_name.lower():
                            print(f"   ✅ Найден существующий контакт с компанией {company_name}")
                            return contact

            # 3. Если не нашли - создаем НОВЫЙ контакт с компанией в имени
            print(f"   📝 Создаем новый контакт для компании {company_name}")

            # Формируем уникальное имя
            if sender_name:
                # Добавляем компанию к имени: "Имя Фамилия (ООО Компания)"
                contact_name = self._extract_name_from_string(sender_name)
                if contact_name:
                    first_name = contact_name.get('first', '')
                    last_name = contact_name.get('last', '')

                    # Если компания - добавляем к фамилии
                    if last_name:
                        last_name = f"{last_name} ({company_name})"
                    else:
                        # Если нет фамилии, добавляем к имени
                        first_name = f"{first_name} ({company_name})"
                else:
                    # Не удалось извлечь имя
                    first_name = company_name
                    last_name = sender_email.split('@')[0]
            else:
                # Нет имени отправителя
                username = sender_email.split('@')[0].replace('.', ' ').title()
                first_name = f"{username} ({company_name})"
                last_name = ""
        else:
            # Без компании - используем старую логику
            print(f"   ℹ️  Компания не указана, создаем простой контакт")
            if sender_name:
                contact_name = self._extract_name_from_string(sender_name)
                if contact_name:
                    first_name = contact_name.get('first', '')
                    last_name = contact_name.get('last', '')
                else:
                    first_name = sender_name
                    last_name = ""
            else:
                username = sender_email.split('@')[0].replace('.', ' ').title()
                first_name = username
                last_name = ""

        # 4. Создаем контакт
        contact_data = {
            'firstName': first_name[:50],  # Ограничиваем длину
            'lastName': last_name[:50],
            'emails': [sender_email]
        }

        # Добавляем workspaceId если есть
        if hasattr(settings, 'WEEEK_WORKSPACE_ID') and settings.WEEEK_WORKSPACE_ID:
            contact_data['workspaceId'] = settings.WEEEK_WORKSPACE_ID

        print(f"   👤 Данные контакта: {contact_data}")
        return self.create_contact(contact_data)

    def _get_all_contacts_by_email(self, email: str) -> List[Dict]:
        """Получить все контакты с указанным email"""
        contacts = []

        try:
            # Ищем через поиск
            params = {'search': email, 'limit': 100}
            result = self._request('GET', '/crm/contacts', params=params)
            found_contacts = result.get('contacts', [])

            # Фильтруем только те, у которых точно есть этот email
            for contact in found_contacts:
                contact_id = contact.get('id')
                if contact_id:
                    detailed = self.get_contact(contact_id)
                    if detailed:
                        contact_emails = detailed.get('emails', [])
                        for email_obj in contact_emails:
                            email_addr = email_obj.get('email', '') if isinstance(email_obj, dict) else email_obj
                            if email_addr.lower() == email.lower():
                                contacts.append(detailed)
                                break

            # Если поиск не нашел, пробуем перебрать все
            if not contacts:
                page = 1
                while True:
                    all_contacts = self.get_contacts(limit=100, page=page)
                    if not all_contacts:
                        break

                    for contact in all_contacts:
                        contact_id = contact.get('id')
                        if contact_id:
                            detailed = self.get_contact(contact_id)
                            if detailed:
                                contact_emails = detailed.get('emails', [])
                                for email_obj in contact_emails:
                                    email_addr = email_obj.get('email', '') if isinstance(email_obj,
                                                                                          dict) else email_obj
                                    if email_addr.lower() == email.lower():
                                        contacts.append(detailed)
                                        break

                    page += 1
                    if page > 3:  # Ограничиваем 300 контактов
                        break

            return contacts

        except Exception as e:
            print(f"   ❌ Ошибка поиска контактов: {e}")
            return []

    def _extract_name_from_string(self, name_string: str) -> Dict[str, str]:
        """Извлечь имя и фамилию из строки"""
        name_string = name_string.strip()

        # Убираем email если есть
        name_string = re.sub(r'<[^>]+>', '', name_string)
        name_string = re.sub(r'\S+@\S+\.\S+', '', name_string)

        parts = name_string.split()
        if len(parts) >= 2:
            return {'first': parts[0], 'last': ' '.join(parts[1:])}
        elif len(parts) == 1:
            return {'first': parts[0], 'last': ''}
        else:
            return None

    def link_contact_to_organization(self, contact_id: str, organization_id: str) -> bool:
        """Привязать контакт к организации через /organizations/{id}/contacts"""
        try:
            data = {'contactId': contact_id}
            result = self._request('POST', f'/crm/organizations/{organization_id}/contacts', data=data)

            if result.get('success'):
                logger.info(f"Контакт {contact_id} привязан к организации {organization_id}")
                return True
            else:
                logger.error(f"Не удалось привязать контакт к организации: {result}")
                return False

        except Exception as e:
            logger.error(f"Ошибка привязки контакта к организации: {e}")
            return False

    def unlink_contact_from_organization(self, contact_id: str, organization_id: str) -> bool:
        """Отвязать контакт от организации"""
        try:
            # Пробуем DELETE запрос
            result = self._request('DELETE', f'/crm/organizations/{organization_id}/contacts/{contact_id}')
            return result.get('success', False)
        except:
            # Если нет такого endpoint, пробуем обновить контакт
            try:
                contact = self.get_contact(contact_id)
                if contact:
                    orgs = contact.get('organizations', [])
                    if organization_id in orgs:
                        orgs.remove(organization_id)
                        # Нужно обновить весь контакт
                        update_data = {
                            'firstName': contact.get('firstName', ''),
                            'lastName': contact.get('lastName', ''),
                            'organizations': orgs
                        }
                        result = self._request('PUT', f'/crm/contacts/{contact_id}', data=update_data)
                        return result.get('success', False)
            except Exception as e:
                logger.error(f"Ошибка отвязки контакта: {e}")
            return False

    def search_contact_by_email(self, email: str) -> Optional[Dict]:
        """Умный поиск контакта по email"""
        if not email:
            return None

        try:
            # 1. Сначала ищем через search (если API поддерживает)
            params = {'search': email, 'limit': 20}
            result = self._request('GET', '/crm/contacts', params=params)

            if result.get('success'):
                contacts = result.get('contacts', [])
                for contact in contacts:
                    # Проверяем emails контакта
                    contact_emails = contact.get('emails', [])
                    for email_obj in contact_emails:
                        email_addr = email_obj.get('email', '') if isinstance(email_obj, dict) else email_obj
                        if email_addr.lower() == email.lower():
                            return contact

            # 2. Если не нашли - возвращаем None
            return None

        except Exception as e:
            logger.error(f"Ошибка поиска контакта по email {email}: {e}")
            return None

    def update_contact(self, contact_id: str, update_data: Dict) -> Optional[Dict]:
        """Обновить контакт"""
        try:
            result = self._request('PUT', f'/crm/contacts/{contact_id}', data=update_data)
            if result.get('success'):
                return result.get('contact')
            return None
        except Exception as e:
            logger.error(f"Ошибка обновления контакта: {e}")
            return None

    def get_contact_emails(self, contact_id: str) -> List[Dict]:
        """Получить emails контакта"""
        contact = self.get_contact(contact_id)
        if contact:
            return contact.get('emails', [])
        return []

    def add_contact_activity(self, contact_id: str, activity_data: Dict) -> bool:
        """Добавить активность контакту"""
        try:
            result = self._request('POST', f'/crm/contacts/{contact_id}/activities',
                                   data=activity_data)
            return result.get('success', False)
        except Exception as e:
            logger.error(f"Ошибка создания активности: {e}")
            return False

    # ==================== CRM - ORGANIZATIONS ====================

    def get_organizations(self, limit: int = 100, page: int = 1,
                          search: Optional[str] = None) -> List[Dict]:
        """Получить список организаций"""
        params = {'limit': limit, 'page': page}
        if search:
            params['search'] = search

        result = self._request('GET', '/crm/organizations', params=params)
        return result.get('organizations', [])

    def get_organization(self, org_id: str) -> Optional[Dict]:
        """Получить организацию по ID"""
        try:
            result = self._request('GET', f'/crm/organizations/{org_id}')
            if result.get('success'):
                return result.get('organization')
            return None
        except Exception as e:
            logger.error(f"Ошибка получения организации: {e}")
            return None

    def search_organization_by_domain(self, domain: str) -> Optional[Dict]:
        """Поиск организации по домену email"""
        if not domain:
            return None

        try:
            # Получаем все организации
            page = 1
            while True:
                organizations = self.get_organizations(limit=100, page=page)
                if not organizations:
                    break

                for org in organizations:
                    # Проверяем website
                    website = org.get('website', '').lower()
                    if website and domain in website:
                        return org

                    # Проверяем email организации
                    org_email = org.get('email', '')
                    if org_email and '@' in org_email:
                        org_domain = org_email.split('@')[-1].lower()
                        if org_domain == domain:
                            return org

                    # Проверяем name (может содержать домен)
                    org_name = org.get('name', '').lower()
                    if domain.split('.')[0] in org_name:
                        return org

                page += 1
                if page > 3:  # Ограничиваем 300 организаций
                    break

            return None

        except Exception as e:
            logger.error(f"Ошибка поиска организации по домену: {e}")
            return None

    def create_organization(self, org_data: Dict) -> Optional[Dict]:
        """Создать новую организацию"""
        try:
            result = self._request('POST', '/crm/organizations', data=org_data)

            if result.get('success'):
                organization = result.get('organization')
                if organization:
                    logger.info(f"Организация создана: ID={organization.get('id')}")
                    return organization
                else:
                    logger.warning("Создание организации успешно, но нет данных в ответе")
                    return None
            else:
                logger.error(f"Создание организации не удалось: {result}")
                return None

        except Exception as e:
            logger.error(f"Исключение при создании организации: {e}")
            return None

    # ==================== CRM - DEALS ====================

    def get_deals(self, limit: int = 100, page: int = 1,
                  contact_id: Optional[str] = None,
                  funnel_id: Optional[str] = None,
                  status_id: Optional[str] = None) -> List[Dict]:
        """Получить список сделок"""
        params = {'limit': limit, 'page': page}
        if contact_id:
            params['contactId'] = contact_id
        if funnel_id:
            params['funnelId'] = funnel_id
        if status_id:
            params['statusId'] = status_id

        result = self._request('GET', '/crm/deals', params=params)
        return result.get('deals', [])

    def create_deal(self, deal_data: Dict) -> Optional[Dict]:
        """Создать новую сделку"""
        try:
            result = self._request('POST', '/crm/deals', data=deal_data)

            if result.get('success'):
                deal = result.get('deal')
                if deal:
                    logger.info(f"Сделка создана: ID={deal.get('id')}")
                    return deal
                else:
                    logger.warning("Создание сделки успешно, но нет данных в ответе")
                    return None
            else:
                logger.error(f"Создание сделки не удалось: {result}")
                return None

        except Exception as e:
            logger.error(f"Исключение при создании сделки: {e}")
            return None

    # ==================== CRM - FUNNELS & STATUSES ====================

    def get_funnels(self) -> List[Dict]:
        """Получить список воронок"""
        result = self._request('GET', '/crm/funnels')
        return result.get('funnels', [])

    def get_funnel_statuses(self, funnel_id: str) -> List[Dict]:
        """Получить статусы воронки"""
        result = self._request('GET', f'/crm/funnels/{funnel_id}/statuses')
        return result.get('statuses', [])

    # ==================== FILES ====================

    def upload_file(self, filename: str, file_data: bytes,
                    content_type: str = "application/octet-stream") -> Optional[Dict]:
        """Загрузить файл в Weeek"""
        try:
            files = {
                'file': (filename, file_data, content_type)
            }

            headers = {
                'Authorization': f'Bearer {self.api_key}'
            }

            response = requests.post(
                f"{self.base_url}/files",
                headers=headers,
                files=files,
                timeout=60
            )

            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                return result.get('file')
            return None

        except Exception as e:
            logger.error(f"Ошибка при загрузке файла {filename}: {e}")
            return None

    def attach_file_to_contact(self, contact_id: str, file_id: str) -> bool:
        """Прикрепить файл к контакту"""
        try:
            data = {'fileId': file_id}
            result = self._request('POST', f'/crm/contacts/{contact_id}/files', data=data)
            return result.get('success', False)

        except Exception as e:
            logger.error(f"Ошибка при прикреплении файла к контакту: {e}")
            return False

        # ==================== CRM - ACTIVITIES ====================

    def create_activity(self, activity_data: dict) -> dict:
        """Создает активность для контакта"""
        contact_id = activity_data.get('contactId')
        if not contact_id:
            logger.error("Не указан contactId в activity_data")
            return None

        # Формируем данные для запроса
        activity_payload = {
            'type': activity_data.get('type', 'email'),
            'title': activity_data.get('title', 'Активность'),
            'description': activity_data.get('description', ''),
        }

        # Добавляем дополнительные поля если есть
        if activity_data.get('date'):
            activity_payload['date'] = activity_data.get('date')

        if activity_data.get('metadata'):
            activity_payload['metadata'] = activity_data.get('metadata')

        try:
            # Используем существующий метод
            success = self.add_contact_activity(contact_id, activity_payload)
            if success:
                # API не возвращает созданную активность, возвращаем переданные данные
                from datetime import datetime
                return {
                    'id': f"temp_{contact_id}_{datetime.now().timestamp()}",
                    'success': True,
                    'contactId': contact_id,
                    'title': activity_payload.get('title'),
                    'description': activity_payload.get('description')
                }
            return None
        except Exception as e:
            logger.error(f"Ошибка создания активности: {e}")
            return None

    def get_contact_activities(self, contact_id: str, limit: int = 50) -> list:
        """Получить активности контакта"""
        try:
            # Проверяем доступность endpoint
            result = self._request('GET', f'/crm/contacts/{contact_id}/activities')
            if result.get('success'):
                return result.get('activities', [])
            return []
        except Exception as e:
            logger.error(f"Ошибка получения активностей: {e}")
            return []
