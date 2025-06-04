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
        return SQLiteDB() 