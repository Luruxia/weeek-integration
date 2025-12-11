"""
ПРОСТОЙ ТЕСТ TELEGRAM
"""
import sys
sys.path.append('telegram')

try:
    from telegram_notifier import TelegramNotifier
    from config.telegram_config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
    
    print("=" * 40)
    print("Тестируем новую версию notifier...")
    print("=" * 40)
    
    notifier = TelegramNotifier(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    
    # Тест 1: Простой текст
    print("1. Отправляем простое сообщение...")
    success1 = notifier.send_message("✅ Тест 1: Простое сообщение", parse_mode=None)
    print(f"   Результат: {'✅' if success1 else '❌'}")
    
    # Тест 2: С HTML
    print("2. Отправляем HTML...")
    success2 = notifier.send_message("<b>✅ Тест 2</b>: HTML <i>работает</i>", parse_mode="HTML")
    print(f"   Результат: {'✅' if success2 else '❌'}")
    
    # Тест 3: Ошибка
    print("3. Отправляем ошибку...")
    success3 = notifier.send_error_alert("Тестовая ошибка для проверки")
    print(f"   Результат: {'✅' if success3 else '❌'}")
    
    print("\n" + "=" * 40)
    if all([success1, success2, success3]):
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("Telegram готов к работе с демоном!")
    else:
        print("⚠️  Есть проблемы с отправкой")
        print("Проверьте сообщения выше")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

input("\nНажмите Enter...")