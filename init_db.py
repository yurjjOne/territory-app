import sqlite3
import pandas as pd
import os

def init_db():
    # Підключаємося до бази даних
    conn = sqlite3.connect('territories.db')
    cursor = conn.cursor()
    
    # Читаємо дані з CSV файлу
    try:
        # Використовуємо крапку з комою як роздільник
        df = pd.read_csv('облік територій.csv', sep=';')
        
        # Підготовка даних для імпорту
        territories = []
        for index, row in df.iterrows():
            territory_id = row['id']
            name = f"Територія {territory_id}"
            custom_name = row['custom_name'].strip()  # Видаляємо зайві пробіли
            
            territories.append((territory_id, name, custom_name))
        
        # Додаємо території
        cursor.executemany('''
        INSERT OR REPLACE INTO territories (id, name, custom_name)
        VALUES (?, ?, ?)
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