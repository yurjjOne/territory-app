import os
import shutil
from typing import Union
from sqlite_db import SQLiteDB
import time

class DBFactory:
    @staticmethod
    def get_db() -> SQLiteDB:
        """
        Повертає об'єкт для роботи з базою даних.
        За замовчуванням використовує SQLite.
        """
        # Визначаємо шлях до папки з даними
        data_dir = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', 'data')
        
        # Створюємо папку, якщо її немає
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        # Шлях до файлу бази даних
        db_path = os.path.join(data_dir, 'territories.db')
        root_db_path = 'territories.db'
        
        # Перевіряємо наявність баз даних
        volume_db_exists = os.path.exists(db_path)
        root_db_exists = os.path.exists(root_db_path)
        
        if root_db_exists:
            if not volume_db_exists:
                # Якщо в Volume немає бази - копіюємо з кореня
                print("Копіюємо базу даних в Volume...")
                shutil.copy2(root_db_path, db_path)
            else:
                # Якщо обидві бази існують - порівнюємо дати модифікації
                root_mtime = os.path.getmtime(root_db_path)
                volume_mtime = os.path.getmtime(db_path)
                
                if root_mtime > volume_mtime:
                    print("Знайдено новішу версію бази даних, оновлюємо...")
                    # Створюємо бекап поточної бази в Volume
                    backup_path = f"{db_path}.backup.{int(time.time())}"
                    if os.path.exists(db_path):
                        shutil.copy2(db_path, backup_path)
                    # Копіюємо нову версію
                    shutil.copy2(root_db_path, db_path)
        
        return SQLiteDB(db_path) 