import pandas as pd
import sqlite3
from datetime import datetime
from backup_manager import backup_important_data

def import_from_csv():
    """Імпортує території з CSV файлу, зберігаючи існуючі дані."""
    print("Починаємо безпечний імпорт даних...")
    
    # Створюємо резервну копію
    backup_important_data()
    
    try:
        # Читаємо CSV файл
        try:
            df = pd.read_csv('облік територій.csv', encoding='utf-8', sep=';')
        except:
            df = pd.read_csv('облік територій.csv', encoding='cp1251', sep=';')
        print(f"Успішно прочитано CSV файл. Знайдено {len(df)} територій.")
        
        # Підключаємося до бази даних
        conn = sqlite3.connect('territories.db')
        cursor = conn.cursor()
        
        # Отримуємо поточний стан територій
        cursor.execute("""
            SELECT id, status, taken_by, date_taken, date_due, notes 
            FROM territories
        """)
        current_territories = {row[0]: row[1:] for row in cursor.fetchall()}
        
        # Створюємо тимчасову таблицю
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS temp_territories (
                id INTEGER PRIMARY KEY,
                name TEXT,
                custom_name TEXT,
                status TEXT,
                taken_by TEXT,
                date_taken TEXT,
                date_due TEXT,
                notes TEXT
            )
        """)
        
        # Імпортуємо нові дані, зберігаючи поточний стан
        for index, row in df.iterrows():
            territory_id = row['id']
            custom_name = row['custom_name'] if 'custom_name' in row else ''
            
            # Якщо територія існує, зберігаємо її поточний стан
            if territory_id in current_territories:
                status, taken_by, date_taken, date_due, notes = current_territories[territory_id]
            else:
                status, taken_by, date_taken, date_due, notes = 'Вільна', '', '', '', ''
            
            cursor.execute('''
            INSERT INTO temp_territories (id, name, custom_name, status, taken_by, date_taken, date_due, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                territory_id,
                f"Територія {territory_id}",
                custom_name,
                status,
                taken_by,
                date_taken,
                date_due,
                notes
            ))
        
        # Замінюємо стару таблицю на нову
        cursor.execute("DROP TABLE territories")
        cursor.execute("ALTER TABLE temp_territories RENAME TO territories")
        
        # Зберігаємо зміни
        conn.commit()
        print("Дані успішно оновлено!")
        
    except Exception as e:
        print(f"Помилка при імпорті даних: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == '__main__':
    import_from_csv() 