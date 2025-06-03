from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime, timedelta
import os
import csv
from google_integration import update_google_sheet, clear_google_sheet, get_territories_from_sheet
from contextlib import contextmanager
from typing import Generator
import hashlib
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = "MySecretKey2025"  # Тимчасово повернемо старе значення
DATABASE = 'territories.db'
CSV_FILE = 'облік територій.csv'

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_territories_from_csv():
    """Завантаження назв територій з CSV файлу"""
    territories = {}
    encodings = ['utf-8-sig', 'cp1251']  # Змінюємо порядок кодувань
    
    for encoding in encodings:
        try:
            with open(CSV_FILE, 'r', encoding=encoding) as file:
                content = file.read()
                if 'вул.' in content:  # Перевіряємо, чи текст читається правильно
                    file.seek(0)  # Повертаємось на початок файлу
                    csv_reader = csv.reader(file, delimiter=';')
                    next(csv_reader)  # Пропускаємо заголовок
                    for row in csv_reader:
                        if row and len(row) >= 2 and row[0] and row[1]:  # Перевіряємо, що обидва поля не порожні
                            try:
                                # Конвертуємо ID території в ціле число
                                territory_id = row[0].strip().replace(',', '.')
                                # Якщо ID містить крапку, беремо тільки цілу частину
                                territory_id = int(float(territory_id))
                                custom_name = row[1].strip()
                                if custom_name:  # Додаємо тільки якщо назва не порожня
                                    territories[territory_id] = custom_name
                                    logger.info(f"Завантажено територію {territory_id}: {custom_name}")
                            except ValueError as e:
                                logger.error(f"Помилка при обробці рядка CSV {row}: {e}")
                                continue
                    break  # Якщо успішно прочитали файл, виходимо з циклу
                else:
                    continue  # Якщо текст не читається правильно, пробуємо наступне кодування
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            logger.warning(f"Файл {CSV_FILE} не знайдено")
            break
    
    if not territories:
        logger.error("Не вдалося правильно прочитати жодного запису з CSV файлу")
    else:
        logger.info(f"Всього завантажено {len(territories)} територій з CSV файлу")
    
    return territories

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DATABASE)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    logger.info("Починаємо ініціалізацію бази даних...")
    
    with get_db() as conn:
        c = conn.cursor()
        
        # Створюємо таблиці
        logger.info("Створюємо таблиці якщо вони не існують...")
        c.execute('''CREATE TABLE IF NOT EXISTS territories (
            id INTEGER PRIMARY KEY,
            name TEXT,
            custom_name TEXT,
            status TEXT DEFAULT 'Вільна',
            taken_by TEXT DEFAULT '',
            date_taken TEXT DEFAULT '',
            date_due TEXT DEFAULT '',
            notes TEXT DEFAULT ''
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            territory_id INTEGER,
            taken_by TEXT,
            date_taken TEXT,
            date_due TEXT
        )''')
        
        try:
            # Завантажуємо назви територій з CSV
            logger.info("Завантажуємо назви територій з CSV файлу...")
            csv_territories = load_territories_from_csv()
            logger.info(f"Завантажено {len(csv_territories)} назв територій з CSV")
            
            # Додаємо або оновлюємо території
            for territory_id, territory_name in csv_territories.items():
                try:
                    # Перевіряємо чи територія вже існує
                    c.execute("SELECT id FROM territories WHERE id = ?", (territory_id,))
                    exists = c.fetchone()
                    
                    if not exists:
                        logger.info(f"Додаємо нову територію {territory_id}: {territory_name}")
                        c.execute("""
                            INSERT INTO territories (id, name, custom_name)
                            VALUES (?, ?, ?)
                        """, (territory_id, territory_name, territory_name))
                    else:
                        logger.info(f"Оновлюємо існуючу територію {territory_id}: {territory_name}")
                        c.execute("""
                            UPDATE territories
                            SET name = ?, custom_name = ?
                            WHERE id = ?
                        """, (territory_name, territory_name, territory_id))
                except Exception as e:
                    logger.error(f"Помилка при обробці території {territory_id}: {str(e)}")
                    continue
            
            conn.commit()
            logger.info("Ініціалізація бази даних завершена успішно")
            
        except Exception as e:
            logger.error(f"Помилка при ініціалізації бази даних: {str(e)}")
            logger.exception("Деталі помилки:")
            conn.rollback()
            raise

def update_territory_names():
    """Update territory names from CSV file"""
    csv_territories = load_territories_from_csv()
    if not csv_territories:
        return
        
    with get_db() as conn:
        c = conn.cursor()
        for territory_id, custom_name in csv_territories.items():
            c.execute("""
                UPDATE territories
                SET custom_name = ?
                WHERE id = ?
            """, (custom_name, territory_id))
        conn.commit()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        role = request.form['role']
        
        # Use environment variable for passwords
        admin_password = os.environ.get('APP_PASSWORD', 'Pass123')  # Default for backwards compatibility
        viewer_password = os.environ.get('VIEWER_PASSWORD', 'View123')  # Default viewer password
        
        is_valid = False
        if role == 'admin' and hashlib.sha256(password.encode()).hexdigest() == hashlib.sha256(admin_password.encode()).hexdigest():
            is_valid = True
            session['role'] = 'admin'
        elif role == 'viewer' and hashlib.sha256(password.encode()).hexdigest() == hashlib.sha256(viewer_password.encode()).hexdigest():
            is_valid = True
            session['role'] = 'viewer'
            
        if is_valid:
            session['logged_in'] = True
            return redirect(url_for('index'))
        return redirect(url_for('login', error=True))
        
    return render_template('login.html')

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    try:
        # Update territory names from CSV before displaying
        update_territory_names()
        
        with get_db() as conn:
            c = conn.cursor()
            
            # Get taken territories with a single query, properly ordered
            c.execute("""
                SELECT t.id, t.custom_name, t.status, t.taken_by, t.date_taken, t.date_due, t.notes,
                       CASE 
                           WHEN date_due != '' AND (
                               julianday(date_due) <= julianday('now') OR  -- дата вже пройшла
                               julianday(date_due) - julianday('now') <= 10  -- або залишилось менше 10 днів
                           )
                           THEN 1 
                           ELSE 0 
                       END as due_flag
                FROM territories t 
                WHERE status='Взято'
                ORDER BY CAST(id AS REAL), date_taken
            """)
            taken = [(row[:-1], bool(row[-1])) for row in c.fetchall()]

            # Get free territories
            c.execute("""
                SELECT id, custom_name, status, notes 
                FROM territories 
                WHERE status='Вільна' 
                ORDER BY CAST(id AS REAL)
            """)
            free = c.fetchall()

        return render_template('index.html', 
                            taken=taken, 
                            free=free, 
                            is_admin=(session.get('role') == 'admin'))
    except sqlite3.Error as e:
        app.logger.error(f"Database error: {e}")
        return "Помилка бази даних", 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        return "Несподівана помилка", 500

@app.route('/update/<territory_id>', methods=['GET', 'POST'])
def update_territory(territory_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    # Перевіряємо чи користувач має права адміна для редагування
    if request.method == 'POST' and session.get('role') != 'admin':
        return "Немає прав для редагування", 403

    try:
        territory_id = float(territory_id)
    except ValueError:
        return "Неправильний формат номера території", 400

    if request.method == 'POST':
        try:
            taken_by = request.form['taken_by'].strip()
            notes = request.form['notes'].strip()
            
            with get_db() as conn:
                c = conn.cursor()
                
                if taken_by:
                    # Отримуємо поточний стан території
                    c.execute("SELECT taken_by, status FROM territories WHERE id=?", (territory_id,))
                    current_state = c.fetchone()
                    current_taken_by = current_state[0] if current_state else None
                    is_new_user = current_taken_by != taken_by

                    # Використовуємо поточну дату або передану дату
                    now = datetime.now()
                    if 'date_taken' in request.form and request.form['date_taken']:
                        date_taken_obj = datetime.strptime(request.form['date_taken'], '%Y-%m-%d')
                        date_taken = date_taken_obj.strftime('%d.%m.%Y')
                    else:
                        date_taken = now.strftime('%d.%m.%Y')

                    # Для Google Sheets розраховуємо планову дату повернення
                    date_due_planned = (datetime.strptime(date_taken, '%d.%m.%Y') + timedelta(days=120)).strftime('%d.%m.%Y')

                    # Use transaction for multiple operations
                    c.execute('BEGIN TRANSACTION')
                    try:
                        # Оновлюємо дані території
                        c.execute("""
                            UPDATE territories
                            SET status=?, taken_by=?, date_taken=?, date_due=?, notes=?
                            WHERE id=?
                        """, ("Взято", taken_by, date_taken, date_due_planned, notes, territory_id))

                        # Додаємо новий запис в історію тільки якщо змінився користувач
                        if is_new_user:
                            c.execute("""
                                INSERT INTO history (territory_id, taken_by, date_taken, date_due)
                                VALUES (?, ?, ?, ?)
                            """, (territory_id, taken_by, date_taken, ""))  # Порожня дата здачі, буде заповнена при поверненні

                            # Keep only last 5 history records
                            c.execute("""
                                DELETE FROM history
                                WHERE id NOT IN (
                                    SELECT id FROM history
                                    WHERE territory_id=?
                                    ORDER BY id DESC
                                    LIMIT 5
                                )
                            """, (territory_id,))

                        conn.commit()

                        try:
                            update_google_sheet(
                                territory_id=territory_id,
                                taken_by=taken_by,
                                date_taken=date_taken,
                                date_due=date_due_planned,
                                returned=False
                            )
                        except Exception as e:
                            app.logger.error(f"Google Sheets error: {e}")
                            # Continue even if Google Sheets update fails
                            pass

                    except Exception as e:
                        conn.rollback()
                        raise e
                else:
                    c.execute("""
                        UPDATE territories
                        SET status='Вільна', taken_by='', date_taken='', date_due='', notes=?
                        WHERE id=?
                    """, (notes, territory_id,))
                    conn.commit()

                    try:
                        update_google_sheet(
                            territory_id=territory_id,
                            taken_by="",
                            date_taken="",
                            date_due=datetime.now().strftime('%d.%m.%Y'),
                            returned=True
                        )
                    except Exception as e:
                        app.logger.error(f"Google Sheets error: {e}")
                        # Continue even if Google Sheets update fails
                        pass

            return redirect(url_for('index'))
        except Exception as e:
            app.logger.error(f"Error updating territory {territory_id}: {e}")
            return f"Помилка при оновленні території: {str(e)}", 500

    # GET request
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM territories WHERE id=?", (territory_id,))
            territory = c.fetchone()
            
            if not territory:
                return "Територію не знайдено", 404

            c.execute("""
                SELECT taken_by, date_taken, date_due
                FROM history
                WHERE territory_id=?
                ORDER BY id DESC
                LIMIT 5
            """, (territory_id,))
            history = c.fetchall()

            # Передаємо поточну дату в шаблон
            now = datetime.now()
            return render_template('update.html', territory=territory, history=history, now=now)
    except Exception as e:
        app.logger.error(f"Error fetching territory {territory_id}: {e}")
        return f"Помилка при отриманні даних території: {str(e)}", 500

@app.route('/release/<territory_id>', methods=['POST'])
def release_territory(territory_id):
    if not session.get('logged_in') or session.get('role') != 'admin':
        return "Немає прав для цієї дії", 403

    try:
        territory_id = float(territory_id)
    except ValueError:
        return "Неправильний формат номера території", 400

    try:
        with get_db() as conn:
            c = conn.cursor()
            
            # Check if territory exists and get current data
            c.execute("SELECT status, taken_by, date_taken FROM territories WHERE id=?", (territory_id,))
            result = c.fetchone()
            if not result:
                return "Територію не знайдено", 404
            if result[0] != 'Взято':
                return "Територія вже вільна", 400

            current_status, current_taken_by, current_date_taken = result

            # Get current date for return
            return_date = datetime.now().strftime('%d.%m.%Y')

            # Start transaction
            c.execute('BEGIN TRANSACTION')
            try:
                # Update territory status
                c.execute("""
                    UPDATE territories
                    SET status='Вільна', taken_by='', date_taken='', date_due=''
                    WHERE id=?
                """, (territory_id,))

                # Update the last history record with the return date
                c.execute("""
                    UPDATE history 
                    SET date_due=? 
                    WHERE territory_id=? 
                    AND taken_by=? 
                    AND date_taken=? 
                    AND (date_due IS NULL OR date_due = '')
                """, (return_date, territory_id, current_taken_by, current_date_taken))

                # Update Google Sheet before committing
                try:
                    update_google_sheet(
                        territory_id=territory_id,
                        taken_by="",
                        date_taken=current_date_taken if current_date_taken else "",
                        date_due=return_date,
                        returned=True
                    )
                except Exception as e:
                    app.logger.error(f"Google Sheets error: {e}")
                    conn.rollback()
                    return "Помилка при оновленні Google Sheets", 500

                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e

        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Error releasing territory {territory_id}: {e}")
        return "Помилка при звільненні території", 500

@app.route('/clear/<territory_id>', methods=['POST'])
def clear_territory(territory_id):
    if not session.get('logged_in') or session.get('role') != 'admin':
        return "Немає прав для цієї дії", 403

    try:
        territory_id = float(territory_id)
    except ValueError:
        return "Неправильний формат номера території", 400

    try:
        with get_db() as conn:
            c = conn.cursor()
            
            # Check if territory exists
            c.execute("SELECT 1 FROM territories WHERE id=?", (territory_id,))
            if not c.fetchone():
                return "Територію не знайдено", 404

            # Use transaction for multiple operations
            c.execute('BEGIN TRANSACTION')
            try:
                c.execute("""
                    UPDATE territories
                    SET status='Вільна', taken_by='', date_taken='', date_due=''
                    WHERE id=?
                """, (territory_id,))
                c.execute("DELETE FROM history WHERE territory_id=?", (territory_id,))
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e

        clear_google_sheet(territory_id)
        return redirect(url_for('update_territory', territory_id=territory_id))
    except Exception as e:
        app.logger.error(f"Error clearing territory {territory_id}: {e}")
        return "Помилка при очищенні історії території", 500

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
