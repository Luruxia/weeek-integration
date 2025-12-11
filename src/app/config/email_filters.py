"""
Умные фильтры для обработки писем
Режимы: 'strict', 'normal', 'all'
"""

class EmailFilter:
    def __init__(self, mode='normal'):
        """
        Режимы фильтрации:
        - 'strict': только важные письма
        - 'normal': все кроме явного спама (по умолчанию)
        - 'all': обрабатывать все письма
        """
        self.mode = mode

        # Списки для разных режимов
        self.STRICT_SKIP = [
            # Почтовые сервисы
            'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'mail.ru',
            'yandex.ru', 'rambler.ru',

            # Социальные сети
            'facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com',
            'pinterest.com', 'tiktok.com', 'youtube.com',

            # Игровые и развлекательные
            'ubi.com', 'steam.com', 'epicgames.com', 'gamenet.ru',

            # Системные
            'noreply', 'no-reply', 'donotreply', 'support@', 'help@',
            'notification', 'notify', 'alert', 'mailer', 'mailing',
            'newsletter', 'digest', 'unsubscribe', 'отписаться',
            'pinbot', 'accountsupport', 'security',

            # Компании (рассылки)
            'amazon.com', 'ebay.com', 'aliexpress.com', 'wildberries.ru',
            'ozon.ru', 'google.com', 'microsoft.com', 'apple.com',
        ]

        self.NORMAL_SKIP = [
            # Только явный спам и системные уведомления
            'noreply', 'no-reply', 'donotreply', 'pinbot',
            'newsletter', 'digest', 'notification', 'alert',
            'unsubscribe', 'отписаться',
            'accountsupport', 'security@',
        ]

        # Важные домены и ключевые слова
        self.IMPORTANT_DOMAINS = [
            'yourcompany.com',  # Ваш домен
            'client-domain.com',  # Домены клиентов
        ]

        self.IMPORTANT_KEYWORDS = [
            # Русские
            'запрос', 'вопрос', 'предложение', 'сотрудничество',
            'заказ', 'покупка', 'консультация', 'звонок',
            'договор', 'счет', 'оплата', 'доставка',
            'проект', 'встреча', 'переговоры', 'резюме',
            'срочно', 'важно', 'приоритет',

            # Английские
            'request', 'question', 'proposal', 'cooperation',
            'order', 'purchase', 'consultation', 'call',
            'contract', 'invoice', 'payment', 'delivery',
            'project', 'meeting', 'negotiation', 'resume',
            'urgent', 'important', 'asap', 'priority',
        ]

        # Имена отправителей для пропуска
        self.SKIP_NAMES = [
            'YouTube', 'Pinterest', 'Facebook', 'Twitter',
            'Instagram', 'LinkedIn', 'Google', 'Microsoft',
            'Ubisoft', 'Steam', 'Epic Games',
        ]

    def should_process_email(self, email_data: dict) -> tuple:
        """
        Определить, нужно ли обрабатывать письмо
        Возвращает (should_process, reason)
        """
        from_email = email_data.get('from_email', '').lower()
        from_name = email_data.get('from_name', '').lower()
        subject = email_data.get('subject', '').lower()

        # Проверяем режим 'all' - обрабатываем всё
        if self.mode == 'all':
            return True, "Режим 'all': обрабатываем все письма"

        # Проверяем важные домены
        for domain in self.IMPORTANT_DOMAINS:
            if domain in from_email:
                return True, f"Важный домен: {domain}"

        # Проверяем важные ключевые слова
        for keyword in self.IMPORTANT_KEYWORDS:
            if keyword.lower() in subject:
                return True, f"Важное ключевое слово в теме: {keyword}"

        # Проверяем по имени отправителя
        for name in self.SKIP_NAMES:
            if name.lower() in from_name:
                return False, f"Пропускаем отправителя: {name}"

        # В зависимости от режима
        if self.mode == 'strict':
            skip_list = self.STRICT_SKIP
        else:  # normal
            skip_list = self.NORMAL_SKIP

        # Проверяем паттерны для пропуска
        for pattern in skip_list:
            pattern_lower = pattern.lower()

            if (pattern_lower in from_email or
                pattern_lower in from_name or
                pattern_lower in subject):
                return False, f"Паттерн для пропуска: {pattern}"

        # По умолчанию
        if self.mode == 'strict':
            return False, "Строгий режим: письмо не важное"
        else:
            return True, "Нормальный режим: письмо не спам"
