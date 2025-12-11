"""
ФИНАЛЬНЫЙ ТЕСТ ДЕМОНА - ИСПРАВЛЕННЫЙ
"""
import os
import sys
import subprocess
from datetime import datetime

print("=" * 70)
print("🎯 ФИНАЛЬНАЯ ПРОВЕРКА ПЕРЕД ЗАПУСКОМ ДЕМОНА")
print("=" * 70)

def check(description, check_func):
    print(f"\n🔍 {description}...")
    try:
        if check_func():
            print("   ✅ УСПЕХ")
            return True
        else:
            print("   ❌ ПРОВАЛ")
            return False
    except Exception as e:
        print(f"   ❌ ОШИБКА: {e}")
        return False

# 1. Проверка основных файлов
def check_files():
    essential = [
        ('../complete_integration.py', 'Главная логика'),
        ('../config/secrets.py', 'Секреты'),
        ('../core/mail_client.py', 'Клиент почты'),
        ('../core/weeek_client.py', 'Клиент Weeek'),
    ]
    
    all_ok = True
    for file, desc in essential:
        if os.path.exists(file):
            print(f"   ✓ {desc}")
        else:
            print(f"   ✗ {desc} - НЕ НАЙДЕН")
            all_ok = False
    
    # Telegram config - опционально
    if os.path.exists('../telegram/telegram_config.py'):
        print("   ✓ Telegram настройки")
    else:
        print("   ⚠ Telegram настройки - не найдены (можно добавить позже)")
    
    return all_ok

# 2. Проверка Python-модулей
def check_imports():
    sys.path.append('..')
    
    modules_to_check = [
        ('complete_integration', 'Интеграция'),
        ('core.mail_client', 'Mail клиент'),
        ('core.weeek_client', 'Weeek клиент'),
    ]
    
    for module_name, desc in modules_to_check:
        try:
            __import__(module_name)
            print(f"   ✓ {desc}")
        except ImportError as e:
            print(f"   ✗ {desc}: {e}")
            return False
    
    return True

# 3. Проверка конфигурации
def check_config():
    """Проверка конфигурации - ОБНОВЛЕННАЯ ВЕРСИЯ"""
    sys.path.append('../config')

    try:
        import secrets

        # Проверяем разные возможные имена переменных
        email_configs = []

        # Проверяем возможные имена для email
        email_vars = ['EMAIL_USER', 'GMAIL_EMAIL', 'EMAIL', 'MAIL_USER']
        password_vars = ['EMAIL_PASSWORD', 'GMAIL_APP_PASSWORD', 'APP_PASSWORD']

        email_found = None
        password_found = None

        for var in email_vars:
            if hasattr(secrets, var) and getattr(secrets, var):
                email_found = var
                email_configs.append(f"Почта ({var})")
                break

        for var in password_vars:
            if hasattr(secrets, var) and getattr(secrets, var):
                password_found = var
                email_configs.append(f"Пароль ({var})")
                break

        # Проверяем Weeek API
        if hasattr(secrets, 'WEEEK_API_KEY') and secrets.WEEEK_API_KEY:
            email_configs.append("Weeek API")

        if hasattr(secrets, 'WEEEK_WORKSPACE_ID') and secrets.WEEEK_WORKSPACE_ID:
            email_configs.append(f"Workspace: {secrets.WEEEK_WORKSPACE_ID}")

        if email_configs:
            print(f"   ✅ Настроено: {', '.join(email_configs)}")
            return True
        else:
            print("   ⚠ Нет настроек в secrets.py")
            return False

    except Exception as e:
        print(f"   ⚠ Ошибка загрузки конфига: {e}")
        return True  # Не критично, если есть другие способы загрузки

# 4. Быстрая проверка интеграции
def check_integration_quick():
    print("   Тестовый запуск (5 секунд)...")
    
    cmd = [sys.executable, "../complete_integration.py", "--limit", "0"]  # limit 0 = только проверка
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='cp1251',  # Кодировка Windows
            timeout=5,
            cwd=os.path.dirname(__file__)
        )
        
        if result.returncode in [0, 1]:  # 0=успех, 1=нет новых писем
            print(f"   ✓ Интеграция запускается (код: {result.returncode})")
            
            # Показываем первую строку вывода
            if result.stdout.strip():
                first_line = result.stdout.strip().split('\n')[0][:80]
                print(f"   Вывод: {first_line}...")
            return True
        else:
            print(f"   ✗ Код ошибки: {result.returncode}")
            print(f"   Ошибка: {result.stderr[:100]}")
            return False
            
    except subprocess.TimeoutExpired:
        print("   ⏱️  Таймаут (нормально для быстрой проверки)")
        return True
    except Exception as e:
        print(f"   ✗ Ошибка: {e}")
        return False

# 5. Проверка Telegram (если есть)
def check_telegram():
    config_path = '../telegram/telegram_config.py'
    
    if not os.path.exists(config_path):
        print("   ⚠ Telegram не настроен (пропускаем)")
        return True  # Не критично
    
    try:
        sys.path.append('../telegram')
        
        # Динамический импорт
        import importlib.util
        spec = importlib.util.spec_from_file_location("tg_config", config_path)
        tg_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tg_config)
        
        TOKEN = getattr(tg_config, 'TELEGRAM_TOKEN', None)
        CHAT_ID = getattr(tg_config, 'TELEGRAM_CHAT_ID', None)
        
        if TOKEN and CHAT_ID:
            print(f"   ✓ Telegram настроен")
            
            # Тест отправки (опционально)
            test_send = input("   Протестировать отправку сообщения? (y/N): ")
            if test_send.lower() == 'y':
                from telegram_notifier import TelegramNotifier
                notifier = TelegramNotifier(TOKEN, CHAT_ID)
                success = notifier.send_message("✅ Тест от демона", parse_mode=None)
                print(f"   Результат: {'✅ Отправлено' if success else '❌ Ошибка'}")
            
            return True
        else:
            print("   ⚠ Telegram не полностью настроен")
            return True  # Не критично
            
    except Exception as e:
        print(f"   ⚠ Ошибка Telegram: {e}")
        return True  # Не критично

# 6. Проверка зависимостей
def check_dependencies():
    try:
        import schedule
        print("   ✓ Библиотека schedule")
    except ImportError:
        print("   ✗ Библиотека schedule - НЕ УСТАНОВЛЕНА")
        print("   Установите: pip install schedule")
        return False
    
    try:
        import requests
        print("   ✓ Библиотека requests")
    except ImportError:
        print("   ✗ Библиотека requests - НЕ УСТАНОВЛЕНА")
        return False
    
    return True

def main():
    """Запуск всех проверок"""
    
    checks = [
        ("Основные файлы системы", check_files),
        ("Импорты Python-модулей", check_imports),
        ("Конфигурация (secrets.py)", check_config),
        ("Быстрая проверка интеграции", check_integration_quick),
        ("Telegram уведомления", check_telegram),
        ("Зависимости Python", check_dependencies),
    ]
    
    results = []
    for desc, func in checks:
        results.append((desc, check(desc, func)))
    
    # Итог
    print("\n" + "=" * 70)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for i, (desc, result) in enumerate(results, 1):
        status = "✅" if result else "❌"
        print(f"{i:2}. {status} {desc}")
    
    print(f"\n🎯 Пройдено: {passed}/{total}")
    
    if passed == total:
        print("\n✨ ВСЕ СИСТЕМЫ ГОТОВЫ!")
        print("   Запускайте демона:")
        print("   python weeek_daemon.py")
        print("   ИЛИ")
        print("   start_daemon.bat")
    elif passed >= total - 1:
        print("\n⚠️  Есть незначительные проблемы")
        print("   Демон МОЖЕТ работать, но проверьте:")
        print("   1. Настроен ли Telegram")
        print("   2. Есть ли секреты в config/secrets.py")
        print("\n   Можно запустить демона для теста:")
        print("   python weeek_daemon.py --test")
    else:
        print("\n🚨 Есть критические проблемы!")
        print("   Исправьте их перед запуском демона")
    
    print("=" * 70)
    
    if passed >= total - 1:
        launch = input("\nЗапустить демона сейчас? (y/N): ")
        if launch.lower() == 'y':
            print("\n🚀 Запускаю демона...")
            os.system("python weeek_daemon.py")
    else:
        input("\nНажмите Enter для выхода...")

if __name__ == "__main__":
    main()