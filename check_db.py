import sqlite3

# Підключаємося до бази даних
conn = sqlite3.connect('territory.db')
cursor = conn.cursor()

# Перевіряємо структуру таблиці
print("Структура таблиці:")
cursor.execute("PRAGMA table_info(territory)")
columns = cursor.fetchall()
for col in columns:
    print(f"- {col[1]} ({col[2]})")

# Перевіряємо кілька записів з фотографіями
print("\nЗаписи з фотографіями:")
cursor.execute("SELECT id, name, image_url FROM territory WHERE image_url IS NOT NULL LIMIT 5")
rows = cursor.fetchall()
for row in rows:
    print(f"ID: {row[0]}, Назва: {row[1]}, Фото: {row[2]}")

conn.close() 