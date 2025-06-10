import sqlite3
import os
from datetime import datetime
import shutil

def get_db_path():
    """Повертає шлях до файлу бази даних."""
    data_dir = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', 'data')
    return os.path.join(data_dir, 'territories.db')

def backup_important_data():
    """Створює резервну копію важливих даних з бази даних."""
    # Підключення до основної бази даних
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"Основну базу даних не знайдено: {db_path}")
        return

    # Створюємо папку для резервних копій
    backup_dir = os.path.join(os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', 'data'), 'backups')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # Створюємо нову резервну копію
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f'backup_{timestamp}.db')
    
    try:
        # Копіюємо файл бази даних
        shutil.copy2(db_path, backup_file)
        print(f"Резервну копію створено успішно: {backup_file}")
        
        # Видаляємо старі бекапи (залишаємо тільки 5 останніх)
        backups = sorted([f for f in os.listdir(backup_dir) if f.startswith('backup_')])
        if len(backups) > 5:
            for old_backup in backups[:-5]:
                os.remove(os.path.join(backup_dir, old_backup))
                print(f"Видалено стару резервну копію: {old_backup}")
        
    except Exception as e:
        print(f"Помилка при створенні резервної копії: {str(e)}")

def restore_from_backup(backup_file):
    """Відновлює дані з резервної копії."""
    if not os.path.exists(backup_file):
        print(f"Файл резервної копії не знайдено: {backup_file}")
        return
    
    db_path = get_db_path()
    try:
        # Створюємо резервну копію поточної бази перед відновленням
        if os.path.exists(db_path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            current_backup = f"{db_path}.before_restore_{timestamp}"
            shutil.copy2(db_path, current_backup)
            print(f"Створено резервну копію поточної бази: {current_backup}")
        
        # Відновлюємо базу з бекапу
        shutil.copy2(backup_file, db_path)
        print("Дані успішно відновлено з резервної копії")
        
    except Exception as e:
        print(f"Помилка при відновленні даних: {str(e)}")

if __name__ == "__main__":
    backup_important_data() 