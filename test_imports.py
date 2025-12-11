# test_imports.py
"""
Тестирование всех импортов
"""

import sys
import os

print("🔍 Тестирование импортов новой структуры")
print("=" * 60)

# Добавляем путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src/app'))

modules_to_test = [
    ("config.settings", "Настройки"),
    ("config.secrets", "Секреты"),
    ("core.mail_client", "Почтовый клиент"),
    ("core.weeek_client", "Weeek клиент"),
    ("core.telegram_notifier", "Telegram"),
    ("utils.logger", "Логирование"),
    ("processors.email_processor", "Процессор писем"),
]

success = True
for module, description in modules_to_test:
    try:
        __import__(module)
        print(f"✅ {description} ({module})")
    except ImportError as e:
        print(f"❌ {description} ({module}): {e}")
        success = False

print("\n" + "=" * 60)
if success:
    print("✨ Все импорты работают! Система готова.")
else:
    print("⚠️  Есть проблемы с импортами. См. выше.")
    
# Тестируем полный импорт
print("\n🔄 Тестирование полного импорта WeeekIntegration...")
try:
    # Возвращаемся к корню для импорта complete_integration.py
    sys.path.insert(0, os.path.dirname(__file__))
    from complete_integration import CompleteIntegration as WeeekIntegration
    print("✅ WeeekIntegration импортирован успешно!")
    
    # Создаём экземпляр
    integration = WeeekIntegration()
    print("✅ Объект WeeekIntegration создан!")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()