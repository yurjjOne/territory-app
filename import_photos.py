import os
import sqlite3
from datetime import datetime

# Підключаємося до бази даних
conn = sqlite3.connect('territory.db')
cursor = conn.cursor()

# Перевіряємо чи існує колонка image_url
cursor.execute("PRAGMA table_info(territory)")
columns = cursor.fetchall()
has_image_url = any(col[1] == 'image_url' for col in columns)

# Якщо колонки немає - додаємо її
if not has_image_url:
    cursor.execute("ALTER TABLE territory ADD COLUMN image_url TEXT")
    print("✅ Додано нову колонку image_url")

# Оновлюємо записи для кожної фотографії
photos_dir = "static/uploads/territories"
for filename in os.listdir(photos_dir):
    if filename.endswith(('.jpg', '.jpeg', '.png')):
        try:
            # Отримуємо ID території з імені файлу (наприклад, з "1.jpg" отримуємо "1")
            territory_id = int(filename.split('.')[0])
            
            # Формуємо URL для фотографії
            image_url = f"/static/uploads/territories/{filename}"
            
            # Оновлюємо запис в базі даних
            cursor.execute(
                "UPDATE territory SET image_url = ? WHERE id = ?",
                (image_url, territory_id)
            )
            print(f"✅ Додано фото для території {territory_id}")
            
        except ValueError:
            print(f"❌ Пропускаю файл {filename} - неправильний формат імені")
            continue

# Зберігаємо зміни
conn.commit()
conn.close()

print("✨ Готово! Всі фотографії додано до бази даних.") 