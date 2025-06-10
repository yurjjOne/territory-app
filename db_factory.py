import os
from typing import Union
from sqlite_db import SQLiteDB

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
        
        return SQLiteDB(db_path) 