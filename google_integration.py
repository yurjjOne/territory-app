import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging
import os
from datetime import datetime, timedelta

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Глобальні змінні
client = None
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
if not SPREADSHEET_ID:
    logger.warning("SPREADSHEET_ID не знайдено в змінних середовища. Використовуємо значення за замовчуванням.")
    SPREADSHEET_ID = "17bGUa7uyxFFJhCTp2UdDuydbFW1UyEN7WoqJ6VlbCig"

CREDS_FILE = "territory-app-461105-e5b14c010a91.json"

def init_google_sheets():
    global client
    try:
        logger.info("Ініціалізація підключення до Google Sheets...")
        
        # Перевіряємо наявність файлу з ключами
        if not os.path.exists(CREDS_FILE):
            error_msg = f"Файл з ключами {CREDS_FILE} не знайдено!"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, scope)
        client = gspread.authorize(creds)
            logger.info("Авторизація успішна")
        except Exception as e:
            logger.error(f"Помилка авторизації: {str(e)}")
            raise
        
        # Перевіряємо доступ до таблиці
        try:
            sheet = client.open_by_key(SPREADSHEET_ID).sheet1
            logger.info(f"Успішно підключено до таблиці {SPREADSHEET_ID}")
            return client
        except gspread.exceptions.APIError as e:
            logger.error(f"Помилка API Google Sheets: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Помилка доступу до таблиці: {str(e)}")
            raise
            
    except Exception as e:
        logger.error(f"Помилка ініціалізації Google Sheets: {str(e)}")
        client = None
        raise

def ensure_client():
    """Ensure we have a valid client, reinitialize if necessary"""
    global client
    if client is None:
        client = init_google_sheets()
    try:
        # Test the connection
        client.open_by_key(SPREADSHEET_ID).sheet1
    except Exception:
        # If any error occurs, try to reinitialize
        client = init_google_sheets()
    return client

def get_territories_from_sheet():
    """Отримання списку всіх територій з Google Sheets"""
    try:
        logger.info("Починаємо отримання територій з Google Sheets...")
        ensure_client()
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        values = sheet.get_values('A6:A200')  # Отримуємо значення з колонки A
        territories = []
        
        for i in range(0, len(values)):
            try:
                if values[i] and values[i][0]:  # Перевіряємо, що значення існує і не порожнє
                    value = values[i][0].strip()  # Видаляємо пробіли
                    if value:  # Перевіряємо ще раз після видалення пробілів
                        try:
                            # Конвертуємо в ціле число
                            territory_id = int(float(value))
                    territories.append(territory_id)
                        except ValueError:
                            logger.warning(f"Неправильний формат ID території: {value}")
            except IndexError:
                continue
                
        territories.sort()  # Сортуємо території за номером
        logger.info(f"Успішно отримано {len(territories)} територій з Google Sheets")
        return territories
    except Exception as e:
        logger.error(f"Помилка при отриманні списку територій: {str(e)}")
        logger.exception("Деталі помилки:")
        raise

def update_google_sheet(territory_id, taken_by, date_taken, date_due, returned=False):
    try:
        logger.info(f"Починаємо оновлення Google Sheet для території {territory_id}")
        logger.info(f"Параметри: taken_by={taken_by}, date_taken={date_taken}, returned={returned}")
        
        ensure_client()
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        
        # Конвертуємо в ціле число для розрахунку рядка
        try:
            territory_id = int(territory_id)
            row_base = 6 + (territory_id - 1)*2
        vis_row, date_row = row_base, row_base + 1
        except ValueError as e:
            logger.error(f"Помилка конвертації territory_id: {e}")
            raise
        
        logger.info(f"Рядки для оновлення: vis_row={vis_row}, date_row={date_row}")
        
        try:
            # Отримуємо поточні дані
            range_name = f'C{vis_row}:L{date_row}'
            current_data = sheet.get_values(range_name)
            
            logger.info(f"Отримані поточні дані: {current_data}")
            
            # Перевіряємо та ініціалізуємо дані якщо вони порожні
            if not current_data:
                current_data = [[''] * 10, [''] * 10]
            elif len(current_data) < 2:
                current_data.append([''] * 10)
            
            # Переконуємося що у нас достатньо стовпців
            current_data[0] = (current_data[0] + [''] * 10)[:10]
            current_data[1] = (current_data[1] + [''] * 10)[:10]
            
            if returned:
                logger.info("Додавання дати повернення")
                # Шукаємо останній непорожній блок без дати повернення
                last_block = -1
                for i in range(0, 10, 2):
                    if i < len(current_data[0]) and current_data[0][i] and (i+1 >= len(current_data[1]) or not current_data[1][i+1]):
                        last_block = i // 2
                        break
                
                if last_block != -1:
                    # Додаємо дату повернення у відповідну колонку
                    col_start = chr(ord('C') + last_block*2)
                    col_end = chr(ord('C') + last_block*2 + 1)
                    range_name = f'{col_start}{vis_row}:{col_end}{date_row}'
                    values = [
                        [current_data[0][last_block*2], ''],  # Зберігаємо ім'я
                        [current_data[1][last_block*2], date_due]  # Додаємо дату повернення
                    ]
                    sheet.update(range_name, values, raw=False)
                    logger.info(f"Додано дату повернення в діапазон {range_name}")
                return

            # Для нового призначення території
            # Шукаємо перший порожній блок або блок після останнього з датою повернення
            empty_block = -1
            for i in range(0, 10, 2):
                if i >= len(current_data[0]) or not current_data[0][i] or (
                    i > 0 and
                    i-1 < len(current_data[1]) and
                    current_data[1][i-1] and
                    (i >= len(current_data[0]) or not current_data[0][i])
                ):
                    empty_block = i // 2
                    break

            if empty_block == -1:
                # Якщо немає порожніх блоків, зсуваємо все вліво і використовуємо останній блок
                new_data = [[''] * 10, [''] * 10]
                for i in range(2, 10, 2):
                    if i+1 < len(current_data[0]):
                    new_data[0][i-2] = current_data[0][i]
                        new_data[0][i-1] = current_data[0][i+1] if i+1 < len(current_data[0]) else ''
                    if i+1 < len(current_data[1]):
                    new_data[1][i-2] = current_data[1][i]
                        new_data[1][i-1] = current_data[1][i+1] if i+1 < len(current_data[1]) else ''
                sheet.update(range_name, new_data, raw=False)
                empty_block = 4  # Використовуємо останній блок

            logger.info(f"Знайдено порожній блок: {empty_block}")

            # Оновлюємо порожній блок
            col_start = chr(ord('C') + empty_block*2)
            range_name = f'{col_start}{vis_row}:{chr(ord(col_start)+1)}{date_row}'
            values = [[taken_by, ''], [date_taken, '']]
            sheet.update(range_name, values, raw=False)
            logger.info(f"Дані успішно записано в діапазон {range_name}")

        except gspread.exceptions.APIError as e:
            logger.error(f"Помилка API Google Sheets: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Помилка при роботі з діапазоном: {str(e)}")
            raise
            
    except Exception as e:
        logger.error(f"Помилка при оновленні Google Sheet для території {territory_id}: {str(e)}")
        logger.exception("Деталі помилки:")
        raise

def clear_google_sheet(territory_id):
    try:
        ensure_client()
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        
        # Convert to integer for range calculation
        row_base = 6 + (int(territory_id) - 1)*2
        vis_row, date_row = row_base, row_base + 1
        
        updates = []
        for i in range(5):
            col = 3 + i*2
            updates.extend([
                gspread.Cell(row=vis_row, col=col, value=""),
                gspread.Cell(row=date_row, col=col, value=""),
                gspread.Cell(row=date_row, col=col+1, value="")
            ])
        
        sheet.update_cells(updates)
        logger.info(f"Успішно очищено дані для території {territory_id}")
    except Exception as e:
        logger.error(f"Помилка при очищенні даних території {territory_id}: {e}")
        raise

# Ініціалізуємо клієнт при імпорті модуля
try:
    client = init_google_sheets()
except Exception as e:
    logger.error(f"Не вдалося ініціалізувати Google Sheets: {e}")
    client = None  # Встановлюємо client як None, спробуємо ініціалізувати при першому використанні
