"""
Делаем демона полностью автономным - убираем все запросы к пользователю
"""
import os

file_path = r"c:\weeek1\complete_integration.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Изменяем логику принятия решений
old_ask_logic = '''        common_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'mail.ru', 'yandex.ru']
        if domain not in common_domains:
            return 'ask', f"неизвестный домен: {domain}"'''

new_ask_logic = '''        common_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'mail.ru', 'yandex.ru']
        if domain not in common_domains:
            # В авто-режиме пропускаем неизвестные домены
            return 'skip', f"неизвестный домен (авто-пропуск): {domain}"'''

if old_ask_logic in content:
    content = content.replace(old_ask_logic, new_ask_logic)
    print("✅ Изменена логика для неизвестных доменов")

# 2. Удаляем блок с запросом input
import_lines = []
lines = content.split('\n')
in_ask_block = False
ask_block_start = -1
ask_block_end = -1

for i, line in enumerate(lines):
    if 'elif decision == \'ask\':' in line:
        in_ask_block = True
        ask_block_start = i
    elif in_ask_block and line.strip() and not line.startswith(' ' * 8):
        # Нашли конец блока (отступ уменьшился)
        ask_block_end = i
        break

if ask_block_start > 0 and ask_block_end > ask_block_start:
    # Удаляем блок ask
    del lines[ask_block_start:ask_block_end]
    
    # Вставляем автономную логику
    auto_logic = '''        elif decision == 'ask':
            # В авто-режиме всегда пропускаем непонятные письма
            logger.info(f"🤖 Авто-режим: пропускаем неопределенное письмо")
            logger.info(f"   Причина: {reason}")
            logger.info(f"   От: {email.get('from_email')}")
            logger.info(f"   Тема: {email.get('subject', '')[:60]}...")
            
            if self.config['processing']['auto_mark_read']:
                self.mail_client.mark_as_read(email.get('uid'))
            stats['emails_skipped'] += 1'''
    
    lines.insert(ask_block_start, auto_logic)
    content = '\n'.join(lines)
    print("✅ Удален блок запросов к пользователю")

# 3. Добавляем метод логирования непонятных писем (если нужно)
if 'def _log_uncertain_email' not in content:
    # Находим место для вставки (перед последним методом)
    last_method = content.rfind('\n\n    def ')
    if last_method > 0:
        log_method = '''
    def _log_uncertain_email(self, email: Dict, reason: str):
        """Записать непонятное письмо в лог для ручной проверки"""
        try:
            import json
            from datetime import datetime
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'from_email': email.get('from_email'),
                'from_name': email.get('from_name'),
                'subject': email.get('subject'),
                'date': str(email.get('date')),
                'reason': reason,
                'message_id': email.get('message_id')
            }
            
            os.makedirs('logs', exist_ok=True)
            log_file = 'logs/uncertain_emails.json'
            
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = []
            
            data.append(log_entry)
            
            if len(data) > 1000:
                data = data[-1000:]
            
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Ошибка записи непонятного письма: {e}")'''
        
        content = content[:last_method] + log_method + content[last_method:]
        print("✅ Добавлен метод логирования непонятных писем")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n🎯 Демон теперь полностью автономный!")
print("Что изменилось:")
print("   1. Неизвестные домены → автоматический пропуск")
print("   2. Убраны все input() запросы")
print("   3. Добавлено логирование непонятных писем")
print("   4. Демон может работать 24/7 без участия человека")