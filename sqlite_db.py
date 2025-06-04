import sqlite3
from typing import List, Dict, Optional
import logging
from datetime import datetime

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SQLiteDB:
    def __init__(self):
        self.db_name = 'territories.db'
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Перевіряє чи існує база даних, якщо ні - створює її"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Створюємо таблицю territories якщо не існує
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS territories (
                id INTEGER PRIMARY KEY,
                name TEXT,
                custom_name TEXT,
                status TEXT DEFAULT 'Вільна',
                taken_by TEXT DEFAULT '',
                date_taken TEXT DEFAULT '',
                date_due TEXT DEFAULT '',
                notes TEXT DEFAULT ''
            )
            ''')
            
            # Створюємо таблицю history якщо не існує
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                territory_id INTEGER,
                taken_by TEXT,
                date_taken TEXT,
                date_due TEXT
            )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Помилка при створенні бази даних: {str(e)}")
            raise

    def get_territory(self, territory_id: int) -> Optional[Dict]:
        """Отримання інформації про територію"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, custom_name as name, status, taken_by, date_taken, date_due, notes
            FROM territories WHERE id = ?
            ''', (territory_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'name': row[1],
                    'status': row[2],
                    'taken_by': row[3],
                    'date_taken': row[4],
                    'date_due': row[5],
                    'notes': row[6]
                }
            return None
        except Exception as e:
            logger.error(f"Помилка отримання території {territory_id}: {str(e)}")
            raise

    def get_all_territories(self) -> List[Dict]:
        """Отримання списку всіх територій"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, custom_name as name, status, taken_by, date_taken, date_due, notes
            FROM territories ORDER BY id
            ''')
            
            territories = []
            for row in cursor.fetchall():
                territories.append({
                    'id': row[0],
                    'name': row[1],
                    'status': row[2],
                    'taken_by': row[3],
                    'date_taken': row[4],
                    'date_due': row[5],
                    'notes': row[6]
                })
            
            conn.close()
            return territories
        except Exception as e:
            logger.error(f"Помилка отримання списку територій: {str(e)}")
            raise

    def update_territory(self, territory_id: int, data: Dict) -> None:
        """Оновлення інформації про територію"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE territories 
            SET status = ?, taken_by = ?, date_taken = ?, date_due = ?, notes = ?
            WHERE id = ?
            ''', (
                data.get('status', 'Вільна'),
                data.get('taken_by', ''),
                data.get('date_taken', ''),
                data.get('date_due', ''),
                data.get('notes', ''),
                territory_id
            ))
            
            conn.commit()
            conn.close()
            
            # Якщо територія взята, додаємо запис в історію
            if data.get('status') == 'Взято':
                self.add_history_record(territory_id, data)
                
        except Exception as e:
            logger.error(f"Помилка оновлення території {territory_id}: {str(e)}")
            raise

    def add_history_record(self, territory_id: int, data: Dict) -> None:
        """Додавання запису в історію"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO history (territory_id, taken_by, date_taken, date_due)
            VALUES (?, ?, ?, ?)
            ''', (
                territory_id,
                data.get('taken_by', ''),
                data.get('date_taken', ''),
                data.get('date_due', '')
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Помилка додавання запису в історію для території {territory_id}: {str(e)}")
            raise

    def get_territory_history(self, territory_id: int, limit: int = 5) -> List[Dict]:
        """Отримання історії території"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT territory_id, taken_by, date_taken, date_due
            FROM history 
            WHERE territory_id = ?
            ORDER BY date_taken DESC
            LIMIT ?
            ''', (territory_id, limit))
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    'territory_id': row[0],
                    'taken_by': row[1],
                    'date_taken': row[2],
                    'date_returned': '',  # В SQLite не зберігаємо дату повернення
                    'notes': ''  # В SQLite не зберігаємо примітки в історії
                })
            
            conn.close()
            return history
        except Exception as e:
            logger.error(f"Помилка отримання історії території {territory_id}: {str(e)}")
            raise

    def clear_territory_history(self, territory_id: int) -> None:
        """Очищення історії території"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM history WHERE territory_id = ?', (territory_id,))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Помилка очищення історії території {territory_id}: {str(e)}")
            raise 