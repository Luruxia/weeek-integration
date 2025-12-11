# Создайте check_secrets.py
import re
import os

def check_file_for_secrets(filename):
    """Проверить файл на наличие секретов"""
    dangerous_patterns = [
        (r'cf28c39b-44e7-4155-af56-bc4eb97c526c', 'СТАРЫЙ API КЛЮЧ'),
        (r'ouih iubi xvzc qwhr', 'СТАРЫЙ ПАРОЛЬ'),
        (r'test\.debug\.api@gmail\.com', 'СТАРЫЙ EMAIL'),
        (r'password\s*=\s*["\'][^"\']{8,}["\']', 'ЗАХАРДКОЖЕННЫЙ ПАРОЛЬ'),
        (r'api_key\s*=\s*["\'][^"\']{20,}["\']', 'ЗАХАРДКОЖЕННЫЙ API КЛЮЧ'),
    ]
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        for pattern, description in dangerous_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append(f"  🚨 {description}")
        
        if issues:
            print(f"\n🔍 {filename}:")
            for issue in issues:
                print(issue)
            return True
        else:
            print(f"✅ {filename}: безопасно")
            return False
    
    except Exception as e:
        print(f"⚠️  {filename}: ошибка чтения - {e}")
        return False

# Проверяем основные файлы
files_to_check = [
    'complete_integration.py',
    'main_integration_fixed.py', 
    'core/mail_client.py',
    'core/weeek_client.py',
    'core/mail_sender.py',
    'config/settings.py'
]

print("=" * 60)
print("🔒 ПРОВЕРКА НА СЕКРЕТЫ В КОДЕ")
print("=" * 60)

found_issues = False
for file in files_to_check:
    if os.path.exists(file):
        if check_file_for_secrets(file):
            found_issues = True

print("\n" + "=" * 60)
if found_issues:
    print("🚨 НАЙДЕНЫ ПРОБЛЕМЫ! Исправьте перед коммитом.")
else:
    print("✅ ВСЕ ФАЙЛЫ БЕЗОПАСНЫ!")
print("=" * 60)