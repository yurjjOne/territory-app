import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging
import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SheetsDB:
    def __init__(self):
        self.client = None
        self.spreadsheet_id = os.environ.get('SPREADSHEET_ID')
        self.territories_sheet_name = "Territories"  # Основний лист з територіями
        self.history_sheet_name = "History"  # Лист з історією
        self.initialize()

    def get_credentials(self) -> dict:
        """Отримання credentials з змінної середовища або файлу"""
        try:
            google_creds = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
            if google_creds:
                return json.loads(google_creds)
            else:
                creds_file = "territory-app-461105-e5b14c010a91.json"
                if os.path.exists(creds_file):
                    with open(creds_file, 'r') as f:
                        return json.load(f)
                raise FileNotFoundError(f"Файл з ключами {creds_file} не знайдено!")
        except Exception as e:
            logger.error(f"Помилка отримання credentials: {str(e)}")
            raise

    def initialize(self):
        """Ініціалізація підключення до Google Sheets"""
        try:
            creds_dict = self.get_credentials()
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            self.client = gspread.authorize(creds)
            
            # Відкриваємо або створюємо необхідні листи
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            
            try:
                self.territories_sheet = spreadsheet.worksheet(self.territories_sheet_name)
            except gspread.exceptions.WorksheetNotFound:
                self.territories_sheet = spreadsheet.add_worksheet(self.territories_sheet_name, 1000, 10)
                self._initialize_territories_sheet()
            
            try:
                self.history_sheet = spreadsheet.worksheet(self.history_sheet_name)
            except gspread.exceptions.WorksheetNotFound:
                self.history_sheet = spreadsheet.add_worksheet(self.history_sheet_name, 1000, 5)
                self._initialize_history_sheet()
                
        except Exception as e:
            logger.error(f"Помилка ініціалізації Google Sheets: {str(e)}")
            raise

    def _initialize_territories_sheet(self):
        """Ініціалізація структури листа з територіями"""
        headers = [
            ["ID", "Назва", "Статус", "Хто взяв", "Дата видачі", "Планова дата здачі", "Примітки"]
        ]
        self.territories_sheet.update('A1:G1', headers)
        self.territories_sheet.format('A1:G1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
        })

    def _initialize_history_sheet(self):
        """Ініціалізація структури листа з історією"""
        headers = [
            ["Territory ID", "Хто взяв", "Дата видачі", "Дата повернення", "Примітки"]
        ]
        self.history_sheet.update('A1:E1', headers)
        self.history_sheet.format('A1:E1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
        })

    def get_territory(self, territory_id: int) -> Optional[Dict]:
        """Отримання інформації про територію"""
        try:
            values = self.territories_sheet.get_all_values()
            for row in values[1:]:  # Пропускаємо заголовки
                if row and row[0] and int(float(row[0])) == territory_id:
                    return {
                        'id': int(float(row[0])),
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
            values = self.territories_sheet.get_all_values()
            territories = []
            for row in values[1:]:  # Пропускаємо заголовки
                if row and row[0]:  # Перевіряємо що рядок не порожній
                    territories.append({
                        'id': int(float(row[0])),
                        'name': row[1],
                        'status': row[2],
                        'taken_by': row[3],
                        'date_taken': row[4],
                        'date_due': row[5],
                        'notes': row[6]
                    })
            return sorted(territories, key=lambda x: x['id'])
        except Exception as e:
            logger.error(f"Помилка отримання списку територій: {str(e)}")
            raise

    def update_territory(self, territory_id: int, data: Dict) -> None:
        """Оновлення інформації про територію"""
        try:
            values = self.territories_sheet.get_all_values()
            row_idx = None
            
            # Шукаємо рядок з потрібною територією
            for idx, row in enumerate(values):
                if row and row[0] and int(float(row[0])) == territory_id:
                    row_idx = idx + 1  # +1 бо gspread використовує 1-based індексацію
                    break
            
            if row_idx is None:
                # Якщо територія не знайдена, додаємо новий рядок
                row_idx = len(values) + 1
            
            # Оновлюємо дані
            update_data = [
                territory_id,
                data.get('name', ''),
                data.get('status', ''),
                data.get('taken_by', ''),
                data.get('date_taken', ''),
                data.get('date_due', ''),
                data.get('notes', '')
            ]
            
            self.territories_sheet.update(f'A{row_idx}:G{row_idx}', [update_data])
            
            # Якщо територія взята, додаємо запис в історію
            if data.get('status') == 'Взято':
                self.add_history_record(territory_id, data)
                
        except Exception as e:
            logger.error(f"Помилка оновлення території {territory_id}: {str(e)}")
            raise

    def add_history_record(self, territory_id: int, data: Dict) -> None:
        """Додавання запису в історію"""
        try:
            record = [
                territory_id,
                data.get('taken_by', ''),
                data.get('date_taken', ''),
                '',  # Дата повернення буде додана пізніше
                data.get('notes', '')
            ]
            self.history_sheet.append_row(record)
        except Exception as e:
            logger.error(f"Помилка додавання запису в історію для території {territory_id}: {str(e)}")
            raise

    def get_territory_history(self, territory_id: int, limit: int = 5) -> List[Dict]:
        """Отримання історії території"""
        try:
            values = self.history_sheet.get_all_values()
            history = []
            
            # Фільтруємо записи для конкретної території
            for row in values[1:]:  # Пропускаємо заголовки
                if row and row[0] and int(float(row[0])) == territory_id:
                    history.append({
                        'territory_id': int(float(row[0])),
                        'taken_by': row[1],
                        'date_taken': row[2],
                        'date_returned': row[3],
                        'notes': row[4]
                    })
            
            # Повертаємо останні N записів
            return sorted(history, key=lambda x: x['date_taken'], reverse=True)[:limit]
        except Exception as e:
            logger.error(f"Помилка отримання історії території {territory_id}: {str(e)}")
            raise

    def clear_territory_history(self, territory_id: int) -> None:
        """Очищення історії території"""
        try:
            values = self.history_sheet.get_all_values()
            rows_to_delete = []
            
            # Знаходимо всі рядки для видалення
            for idx, row in enumerate(values):
                if row and row[0] and int(float(row[0])) == territory_id:
                    rows_to_delete.append(idx + 1)  # +1 бо gspread використовує 1-based індексацію
            
            # Видаляємо рядки в зворотному порядку
            for row_idx in sorted(rows_to_delete, reverse=True):
                self.history_sheet.delete_rows(row_idx)
                
        except Exception as e:
            logger.error(f"Помилка очищення історії території {territory_id}: {str(e)}")
            raise 