# config/secrets.py
# ЗАПОЛНИТЕ ЭТОТ ФАЙЛ СВОИМИ ДАННЫМИ!
# secrets.py - НИКОГДА НЕ КОММИТИТЬ В GIT!
# Добавьте в .gitignore: config/secrets.py

# Weeek API (у вас уже есть)
WEEEK_API_KEY = "" # Берется в самом приложении
WEEEK_WORKSPACE_ID = ""  # Когда заходите в weeek в ссылке увидеть ID WorkSpace


# IMAP для Gmail (НУЖНО ЗАПОЛНИТЬ!)
GMAIL_EMAIL = ""  # Например: your-email@gmail.com
GMAIL_APP_PASSWORD =  ""  # App Password (16 символов)

# 3. ОПЦИОНАЛЬНО (можно оставить None)
WEEEK_BASE_URL = "https://api.weeek.net/public/v1"  # Обычно этот
WEEEK_CONTACT_LIST_ID = None  # Если нужно в конкретный список