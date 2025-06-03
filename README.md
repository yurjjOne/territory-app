# Територіальний облік

Веб-додаток для обліку та управління територіями.

## Функціонал

- Облік взятих та вільних територій
- Система ролей (адміністратор та переглядач)
- Відстеження дат видачі та повернення
- Примітки до територій
- Історія змін
- Інтеграція з Google Sheets

## Технології

- Python 3.8+
- Flask
- SQLite
- Google Sheets API

## Встановлення

1. Клонуйте репозиторій:
```bash
git clone https://github.com/your-username/territory-app.git
cd territory-app
```

2. Створіть віртуальне середовище та активуйте його:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
venv\Scripts\activate     # для Windows
```

3. Встановіть залежності:
```bash
pip install -r requirements.txt
```

4. Налаштуйте змінні середовища:
Створіть файл `.env` з наступними змінними:
```
APP_PASSWORD=your_admin_password
VIEWER_PASSWORD=your_viewer_password
FLASK_DEBUG=False
```

5. Запустіть додаток:
```bash
python app.py
```

## Розгортання на Render

1. Створіть безкоштовний акаунт на [Render](https://render.com)
2. Підключіть ваш GitHub репозиторій
3. Створіть новий Web Service
4. Налаштуйте змінні середовища в Render
5. Розгорніть додаток

## Ролі користувачів

- **Адміністратор**: повний доступ до управління територіями
- **Переглядач**: може тільки переглядати інформацію

## Ліцензія

MIT 