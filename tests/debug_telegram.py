"""
ГЛУБОКАЯ ОТЛАДКА TELEGRAM
Запуск: python debug_telegram.py
"""
import requests
import json
import sys
import os

print("=" * 60)
print("🔍 ГЛУБОКАЯ ДИАГНОСТИКА TELEGRAM БОТА")
print("=" * 60)

# 1. Проверяем конфиг
try:
    sys.path.append('telegram')
    from config.telegram_config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
    
    print(f"✅ Конфиг загружен")
    print(f"   Токен: {TELEGRAM_TOKEN}")
    print(f"   Chat ID: {TELEGRAM_CHAT_ID}")
    
    # 2. Проверяем сам токен через API Telegram
    print("\n[1] Проверка токена через getMe...")
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"   Код ответа: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                bot_info = data.get("result", {})
                print(f"   ✅ Бот найден!")
                print(f"      Имя: {bot_info.get('first_name')}")
                print(f"      Username: @{bot_info.get('username')}")
                print(f"      ID: {bot_info.get('id')}")
            else:
                print(f"   ❌ Telegram вернул ошибку:")
                print(f"      {data}")
        else:
            print(f"   ❌ HTTP ошибка: {response.status_code}")
            print(f"      Ответ: {response.text[:200]}")
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Нет интернета или блокируется Telegram")
    except Exception as e:
        print(f"   ❌ Ошибка запроса: {e}")
    
    # 3. Проверяем Chat ID
    print("\n[2] Проверка Chat ID...")
    print(f"   Тип Chat ID: {type(TELEGRAM_CHAT_ID)}")
    print(f"   Значение: '{TELEGRAM_CHAT_ID}'")
    
    # Chat ID должен быть числом или строкой-числом
    try:
        chat_id_int = int(TELEGRAM_CHAT_ID)
        print(f"   ✅ Chat ID корректное число: {chat_id_int}")
    except ValueError:
        print(f"   ⚠️  Chat ID не число: {TELEGRAM_CHAT_ID}")
        print("   Попробуйте использовать числовой ID")
    
    # 4. Пробуем разные форматы отправки
    print("\n[3] Тест разных методов отправки...")
    
    # Метод 1: Без HTML (простой текст)
    print("   Метод 1: Простой текст...")
    url_send = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    # Пробуем без parse_mode
    payload_simple = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": "Простое тестовое сообщение без HTML",
        "disable_notification": False
    }
    
    try:
        resp = requests.post(url_send, json=payload_simple, timeout=10)
        print(f"      Код: {resp.status_code}")
        if resp.status_code == 200:
            print("      ✅ Успешно отправлено!")
        else:
            print(f"      ❌ Ошибка: {resp.text[:200]}")
    except Exception as e:
        print(f"      ❌ Исключение: {e}")
    
    # Метод 2: С HTML (как в вашем коде)
    print("   Метод 2: С HTML тегами...")
    payload_html = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": "<b>Тест HTML</b> и <i>форматирования</i>",
        "parse_mode": "HTML",
        "disable_notification": False
    }
    
    try:
        resp = requests.post(url_send, json=payload_html, timeout=10)
        print(f"      Код: {resp.status_code}")
        if resp.status_code == 200:
            print("      ✅ HTML отправлено!")
        else:
            print(f"      ❌ Ошибка HTML: {resp.text}")
    except Exception as e:
        print(f"      ❌ Исключение: {e}")
    
    # Метод 3: С Markdown
    print("   Метод 3: С Markdown...")
    payload_markdown = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": "*Тест Markdown* и _форматирования_",
        "parse_mode": "Markdown",
        "disable_notification": False
    }
    
    try:
        resp = requests.post(url_send, json=payload_markdown, timeout=10)
        print(f"      Код: {resp.status_code}")
        if resp.status_code == 200:
            print("      ✅ Markdown отправлено!")
        else:
            print(f"      ❌ Ошибка Markdown: {resp.text}")
    except Exception as e:
        print(f"      ❌ Исключение: {e}")
    
    # 5. Проверка getUpdates (для отладки)
    print("\n[4] Проверка обновлений бота...")
    url_updates = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    
    try:
        resp = requests.get(url_updates, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok") and data.get("result"):
                updates = data["result"]
                print(f"   ✅ Есть {len(updates)} обновлений")
                if updates:
                    last = updates[-1]
                    chat = last.get("message", {}).get("chat", {})
                    print(f"      Последний чат ID: {chat.get('id')}")
                    print(f"      Имя: {chat.get('first_name')}")
                    print(f"      Username: {chat.get('username')}")
            else:
                print(f"   ℹ️  Нет обновлений или ошибка: {data}")
        else:
            print(f"   ❌ Ошибка запроса: {resp.status_code}")
    except Exception as e:
        print(f"   ❌ Исключение: {e}")
        
except ImportError as e:
    print(f"❌ Ошибка импорта конфига: {e}")
    print("\nПроверьте файлы:")
    print("1. telegram/config.py существует?")
    print("2. В нем есть TELEGRAM_TOKEN и TELEGRAM_CHAT_ID?")
    
except Exception as e:
    print(f"❌ Неизвестная ошибка: {e}")

print("\n" + "=" * 60)
print("📋 ЧТО ПРОВЕРИТЬ ВРУЧНУЮ:")
print("1. Откройте браузер и перейдите по ссылке:")
print(f"   https://api.telegram.org/bot{TELEGRAM_TOKEN[:10]}.../getMe")
print("2. Если видите информацию о боте - токен правильный")
print("3. Напишите боту /start в Telegram")
print("4. Проверьте Chat ID через getUpdates")
print("=" * 60)

input("\nНажмите Enter для выхода...")