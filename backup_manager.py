import sqlite3
import os
from datetime import datetime

def backup_important_data():
    """Створює резервну копію важливих даних з бази даних."""
    # Підключення до основної бази даних
    conn = sqlite3.connect('territories.db')
    cursor = conn.cursor()
    
    # Створюємо папку для резервних копій, якщо її немає
    if not os.path.exists('backups'):
        os.makedirs('backups')
    
    # Створюємо нову базу даних для резервної копії
    backup_file = f'backups/backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    backup_conn = sqlite3.connect(backup_file)
    backup_cursor = backup_conn.cursor()
    
    try:
        # Копіюємо структуру та дані з territory_history
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='territory_history'")
        create_table_sql = cursor.fetchone()[0]
        backup_cursor.execute(create_table_sql)
        
        cursor.execute("SELECT * FROM territory_history")
        history_data = cursor.fetchall()
        for row in history_data:
            backup_cursor.execute("INSERT INTO territory_history VALUES (?,?,?,?,?,?)", row)
        
        # Зберігаємо зміни
        backup_conn.commit()
        print(f"Резервну копію створено успішно: {backup_file}")
        
    except Exception as e:
        print(f"Помилка при створенні резервної копії: {str(e)}")
        
    finally:
        backup_conn.close()
        conn.close()

def restore_from_backup(backup_file):
    """Відновлює дані з резервної копії."""
    if not os.path.exists(backup_file):
        print(f"Файл резервної копії не знайдено: {backup_file}")
        return
    
    # Підключення до баз даних
    backup_conn = sqlite3.connect(backup_file)
    main_conn = sqlite3.connect('territories.db')
    
    try:
        # Копіюємо дані з резервної копії в основну базу
        backup_cursor = backup_conn.cursor()
        main_cursor = main_conn.cursor()
        
        # Відновлюємо дані territory_history
        backup_cursor.execute("SELECT * FROM territory_history")
        history_data = backup_cursor.fetchall()
        
        main_cursor.execute("DELETE FROM territory_history")
        for row in history_data:
            main_cursor.execute("INSERT INTO territory_history VALUES (?,?,?,?,?,?)", row)
        
        main_conn.commit()
        print("Дані успішно відновлено з резервної копії")
        
    except Exception as e:
        print(f"Помилка при відновленні даних: {str(e)}")
        
    finally:
        backup_conn.close()
        main_conn.close()

if __name__ == "__main__":
    backup_important_data() 