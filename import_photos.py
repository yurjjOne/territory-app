import os
from sqlite_db import SQLiteDB
import sqlite3

# Ініціалізуємо з'єднання з базою даних
db = SQLiteDB()

# Додаємо колонку image_url, якщо її ще немає
conn = sqlite3.connect('territories.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(territories)")
columns = cursor.fetchall()
has_image_url = any(col[1] == 'image_url' for col in columns)

if not has_image_url:
    cursor.execute("ALTER TABLE territories ADD COLUMN image_url TEXT")
    print("✅ Додано нову колонку image_url")
conn.close()

# Оновлюємо записи для кожної фотографії
photos_dir = "static/uploads/territories"
print(f"📂 Шукаю фотографії в папці {photos_dir}")

conn = sqlite3.connect('territories.db')
cursor = conn.cursor()

for filename in os.listdir(photos_dir):
    if filename.endswith(('.jpg', '.jpeg', '.png')):
        try:
            # Отримуємо ID території з імені файлу (наприклад, з "1.jpg" отримуємо "1")
            territory_id = int(filename.split('.')[0])
            
            # Формуємо URL для фотографії
            image_url = f"/static/uploads/territories/{filename}"
            
            # Оновлюємо запис в базі даних
            cursor.execute(
                "UPDATE territories SET image_url = ? WHERE id = ?",
                (image_url, territory_id)
            )
            print(f"✅ Додано фото для території {territory_id}")
            
        except ValueError:
            print(f"❌ Пропускаю файл {filename} - неправильний формат імені")
            continue

conn.commit()
conn.close()

print("\n✨ Готово! Всі фотографії додано до бази даних.") 