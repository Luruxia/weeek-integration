"""
ПОЛНЫЙ ТЕСТ СИСТЕМЫ - покажет все ошибки
"""
import sys
import os
import traceback

print("🔍 ПОЛНЫЙ ТЕСТ WEEEK INTEGRATION SYSTEM")
print("=" * 60)

# 1. Проверяем Python
print("1. Проверка Python...")
print(f"   Версия: {sys.version}")
print(f"   Папка: {os.getcwd()}")

# 2. Проверяем зависимости
print("\n2. Проверка зависимостей...")
dependencies = ['schedule', 'requests', 'imaplib', 'ssl', 'json', 'logging']

for dep in dependencies:
    try:
        if dep == 'imaplib' or dep == 'ssl':
            __import__(dep)
        else:
            __import__(dep)
        print(f"   ✅ {dep}")
    except ImportError as e:
        print(f"   ❌ {dep}: {e}")

# 3. Проверяем наши модули
print("\n3. Проверка наших модулей...")
modules_to_check = [
    'integration.core.mail_client',
    'integration.core.weeek_client', 
    'integration.config.settings',
    'integration.config.secrets',
    'telegram.telegram_notifier'
]

for module in modules_to_check:
    try:
        __import__(module.replace('/', '.'))
        print(f"   ✅ {module}")
    except ImportError as e:
        print(f"   ❌ {module}: {e}")

# 4. Проверяем главный файл демона
print("\n4. Проверка демона...")
daemon_path = r"C:\weeek1\daemon\weeek_daemon.py"
if os.path.exists(daemon_path):
    print(f"   ✅ Файл демона найден: {daemon_path}")
    
    # Пробуем импортировать
    try:
        # Добавляем путь для импорта
        sys.path.insert(0, r"C:\weeek1\daemon")
        import weeek_daemon
        print("   ✅ Демон может быть импортирован")
    except Exception as e:
        print(f"   ❌ Ошибка импорта демона:")
        print(f"      {traceback.format_exc()}")
else:
    print(f"   ❌ Файл демона не найден!")

# 5. Проверяем конфигурацию
print("\n5. Проверка конфигурации...")
config_files = [
    r"C:\weeek1\config\secrets.py",
    r"C:\weeek1\telegram\telegram_config.py",
    r"C:\weeek1\config\integration_config.json"
]

for config in config_files:
    if os.path.exists(config):
        print(f"   ✅ {os.path.basename(config)}")
    else:
        print(f"   ❌ {os.path.basename(config)} не найден")

print("\n" + "=" * 60)
print("🚀 Запускаю тестовый прогон демона на 30 секунд...")
print("=" * 60)

# Запускаем демона на 30 секунд
try:
    # Импортируем и запускаем
    import subprocess
    import time
    
    # Запускаем демона в отдельном процессе
    process = subprocess.Popen(
        [sys.executable, daemon_path],
        cwd=r"C:\weeek1\daemon",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8'
    )
    
    # Ждем 30 секунд
    print("Демон запущен, жду 30 секунд...")
    time.sleep(30)
    
    # Останавливаем
    process.terminate()
    stdout, stderr = process.communicate(timeout=5)
    
    print("\n📋 ВЫВОД ДЕМОНА:")
    print("-" * 40)
    if stdout:
        print("STDOUT:", stdout[-500:])  # Последние 500 символов
    if stderr:
        print("STDERR:", stderr[-500:])
    
except Exception as e:
    print(f"❌ Ошибка запуска демона: {e}")
    print(traceback.format_exc())

print("\n" + "=" * 60)
print("Тест завершен! Проверьте вывод выше.")
input("Нажмите Enter для выхода...")