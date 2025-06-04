import pandas as pd
import sqlite3
from datetime import datetime

def import_from_csv():
    print("Починаємо імпорт даних з CSV...")
    
    # Читаємо CSV файл
    try:
        df = pd.read_csv('облік територій.csv', encoding='utf-8', sep=';')
        print(f"Успішно прочитано CSV файл. Знайдено {len(df)} рядків.")
    except Exception as e:
        try:
            # Спробуємо інше кодування, якщо перше не спрацювало
            df = pd.read_csv('облік територій.csv', encoding='cp1251', sep=';')
            print(f"Успішно прочитано CSV файл. Знайдено {len(df)} рядків.")
        except Exception as e:
            print(f"Помилка при читанні CSV файлу: {str(e)}")
            return

    # Підключаємося до бази даних
    try:
        conn = sqlite3.connect('territories.db')
        cursor = conn.cursor()
        print("Підключено до бази даних SQLite")
    except Exception as e:
        print(f"Помилка підключення до бази даних: {str(e)}")
        return

    try:
        # Очищаємо таблицю territories
        cursor.execute('DELETE FROM territories')
        
        # Для кожного рядка в CSV
        for index, row in df.iterrows():
            territory_id = row['id']  # Беремо ID з CSV
            custom_name = row['custom_name']  # Беремо назву з CSV
            
            # Отримуємо значення з CSV
            status = 'Вільна'  # За замовчуванням територія вільна
            taken_by = ''
            date_taken = ''
            date_due = ''
            
            # Додаємо запис в базу даних
            cursor.execute('''
            INSERT INTO territories (id, name, custom_name, status, taken_by, date_taken, date_due, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                territory_id,
                f"Територія {territory_id}",
                custom_name,  # Використовуємо назву з CSV
                status,
                taken_by,
                date_taken,
                date_due,
                ''
            ))
        
        # Зберігаємо зміни
        conn.commit()
        print("Дані успішно імпортовано в базу даних")
        
    except Exception as e:
        print(f"Помилка при імпорті даних: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    import_from_csv() 