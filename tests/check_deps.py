# check_deps.py - проверяет зависимости между файлами
import os

print("📋 Проверка зависимостей...")
print("=" * 50)

# Кто кого импортирует
dependencies = {
    'daemon/weeek_daemon.py': ['complete_integration.py', 'telegram/telegram_notifier.py'],
    'complete_integration.py': ['core/mail_client.py', 'core/weeek_client.py', 'config/settings.py'],
    'telegram/telegram_notifier.py': ['config/telegram_config.py'],
}

for file, deps in dependencies.items():
    if os.path.exists(file):
        print(f"✅ {file}")
        for dep in deps:
            if os.path.exists(dep):
                print(f"   └─✅ {dep}")
            else:
                print(f"   └─❌ {dep} - НЕ НАЙДЕН!")
    else:
        print(f"❌ {file} - НЕ НАЙДЕН!")

print("\n🎯 Готово! Если все ✅ - система цела.")