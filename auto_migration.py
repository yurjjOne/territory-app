import sqlite3
import os
from datetime import datetime
from backup_manager import backup_important_data
import pandas as pd
import shutil

def safe_update_database():
    """
    Безпечне оновлення бази даних з автоматичним бекапом та збереженням історії.
    """
    print("Починаємо безпечне оновлення бази даних...")
    
    # 1. Створюємо резервну копію
    print("Створення резервної копії...")
    backup_important_data()
    
    # 2. Створюємо тимчасову базу даних для нових даних
    temp_db = 'temp_territories.db'
    if os.path.exists(temp_db):
        os.remove(temp_db)
    
    # 3. Копіюємо структуру основної бази даних
    print("Копіювання структури бази даних...")
    conn = sqlite3.connect('territories.db')
    temp_conn = sqlite3.connect(temp_db)
    
    try:
        # Копіюємо схему бази даних
        for line in conn.iterdump():
            if line.startswith('CREATE TABLE'):
                temp_conn.execute(line)
        
        # 4. Зберігаємо поточні дані історії та приміток
        print("Збереження історії та приміток...")
        cursor = conn.cursor()
        temp_cursor = temp_conn.cursor()
        
        # Копіюємо дані з territory_history
        cursor.execute("SELECT * FROM territory_history")
        history_data = cursor.fetchall()
        for row in history_data:
            temp_cursor.execute("INSERT INTO territory_history VALUES (?,?,?,?,?,?)", row)
        
        # 5. Імпортуємо нові дані з CSV
        print("Імпорт нових даних з CSV...")
        try:
            df = pd.read_csv('облік територій.csv', encoding='utf-8', sep=';')
        except:
            df = pd.read_csv('облік територій.csv', encoding='cp1251', sep=';')
        
        # Отримуємо поточний стан територій
        cursor.execute("SELECT id, status, taken_by, date_taken, date_due, notes FROM territories")
        current_territories = {row[0]: row[1:] for row in cursor.fetchall()}
        
        # Імпортуємо нові дані, зберігаючи поточний стан
        for index, row in df.iterrows():
            territory_id = row['id']
            custom_name = row['custom_name']
            
            # Якщо територія існує, зберігаємо її поточний стан
            if territory_id in current_territories:
                status, taken_by, date_taken, date_due, notes = current_territories[territory_id]
            else:
                status, taken_by, date_taken, date_due, notes = 'Вільна', '', '', '', ''
            
            temp_cursor.execute('''
            INSERT INTO territories (id, name, custom_name, status, taken_by, date_taken, date_due, notes)
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
        
        # 6. Зберігаємо зміни в тимчасовій базі
        temp_conn.commit()
        
        # 7. Замінюємо стару базу даних на нову
        conn.close()
        temp_conn.close()
        
        print("Оновлення бази даних...")
        os.remove('territories.db')
        shutil.move(temp_db, 'territories.db')
        
        print("База даних успішно оновлена!")
        return True
        
    except Exception as e:
        print(f"Помилка при оновленні бази даних: {str(e)}")
        temp_conn.close()
        if os.path.exists(temp_db):
            os.remove(temp_db)
        return False
    finally:
        if conn:
            conn.close()
        if temp_conn:
            temp_conn.close()

if __name__ == '__main__':
    safe_update_database() 