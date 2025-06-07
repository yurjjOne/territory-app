import sqlite3

# Підключаємося до бази даних
conn = sqlite3.connect('territories.db')
cursor = conn.cursor()

# Перевіряємо структуру таблиці
print("Структура таблиці territories:")
cursor.execute("PRAGMA table_info(territories)")
columns = cursor.fetchall()
for col in columns:
    print(f"- {col[1]} ({col[2]})")

# Перевіряємо записи з фотографіями
print("\nПерші 5 записів з фотографіями:")
cursor.execute("SELECT id, custom_name, image_url FROM territories WHERE image_url IS NOT NULL LIMIT 5")
rows = cursor.fetchall()
for row in rows:
    print(f"ID: {row[0]}, Назва: {row[1]}, Фото: {row[2]}")

# Рахуємо кількість територій з фотографіями
cursor.execute("SELECT COUNT(*) FROM territories WHERE image_url IS NOT NULL")
count = cursor.fetchone()[0]
print(f"\nВсього територій з фотографіями: {count}")

conn.close() 