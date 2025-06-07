import sqlite3
import pandas as pd
import os

def init_db():
    # Підключаємося до бази даних
    conn = sqlite3.connect('territories.db')
    cursor = conn.cursor()
    
    # Створюємо таблиці якщо вони не існують
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS territories (
        id INTEGER PRIMARY KEY,
        name TEXT,
        custom_name TEXT,
        status TEXT DEFAULT 'Вільна',
        taken_by TEXT DEFAULT '',
        date_taken TEXT DEFAULT '',
        date_due TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS territory_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        territory_id INTEGER,
        taken_by TEXT,
        date_taken TEXT,
        date_returned TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (territory_id) REFERENCES territories(id)
    )
    ''')
    
    # Читаємо дані з CSV файлу
    try:
        # Використовуємо кому як роздільник
        df = pd.read_csv('облік територій.csv')
        
        # Підготовка даних для імпорту
        territories = []
        for index, row in df.iterrows():
            territory_id = row['id']
            custom_name = row['custom_name'].strip() if pd.notna(row['custom_name']) else ''
            name = f"Територія {territory_id}"
            
            territories.append((territory_id, name, custom_name, 'Вільна'))
        
        # Додаємо території
        cursor.executemany('''
        INSERT OR REPLACE INTO territories (id, name, custom_name, status)
        VALUES (?, ?, ?, ?)
        ''', territories)
        
        # Зберігаємо зміни
        conn.commit()
        print(f"База даних успішно ініціалізована! Додано {len(territories)} територій.")
        
    except Exception as e:
        print(f"Помилка при читанні файлу CSV: {str(e)}")
    finally:
        conn.close()

if __name__ == '__main__':
    init_db() 