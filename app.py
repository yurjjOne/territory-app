from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime, timedelta
import os
from google_integration import update_google_sheet, clear_google_sheet
from contextlib import contextmanager
from typing import Generator
import hashlib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = "MySecretKey2025"  # Тимчасово повернемо старе значення
DATABASE = 'territories.db'

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DATABASE)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS territories (
            id INTEGER PRIMARY KEY,
            name TEXT,
            status TEXT,
            taken_by TEXT,
            date_taken TEXT,
            date_due TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            territory_id INTEGER,
            taken_by TEXT,
            date_taken TEXT,
            date_due TEXT
        )''')
        
        # Check if territories need to be initialized
        c.execute("SELECT COUNT(*) FROM territories")
        if c.fetchone()[0] == 0:
            # Use batch insert instead of loop
            territories = [(i, f"Територія {i}", "Вільна") for i in range(1, 182)]
            c.executemany(
                "INSERT INTO territories (id, name, status) VALUES (?, ?, ?)",
                territories
            )
        conn.commit()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        # Use environment variable for password and hash it
        stored_password = os.environ.get('APP_PASSWORD', 'Pass123')  # Default for backwards compatibility
        if hashlib.sha256(password.encode()).hexdigest() == hashlib.sha256(stored_password.encode()).hexdigest():
            session['logged_in'] = True
            return redirect(url_for('index'))
        return "Неправильний пароль"
    return render_template('login.html')

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    try:
        with get_db() as conn:
            c = conn.cursor()
            
            # Get taken territories with a single query, properly ordered
            c.execute("""
                SELECT t.*, 
                       CASE 
                           WHEN julianday(date_due) - julianday('now') <= 10 
                           THEN 1 
                           ELSE 0 
                       END as due_flag
                FROM territories t 
                WHERE status='Взято'
                ORDER BY date_taken
            """)
            taken = [(row[:-1], bool(row[-1])) for row in c.fetchall()]

            # Get free territories
            c.execute("""
                SELECT * 
                FROM territories 
                WHERE status='Вільна' 
                ORDER BY id
            """)
            free = c.fetchall()

        return render_template('index.html', taken=taken, free=free)
    except sqlite3.Error as e:
        app.logger.error(f"Database error: {e}")
        return "Помилка бази даних", 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        return "Несподівана помилка", 500

@app.route('/update/<int:territory_id>', methods=['GET', 'POST'])
def update_territory(territory_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            taken_by = request.form['taken_by'].strip()
            
            with get_db() as conn:
                c = conn.cursor()
                
                if taken_by:
                    now = datetime.now()
                    date_taken = now.strftime('%d.%m.%Y')
                    date_due = (now + timedelta(days=120)).strftime('%d.%m.%Y')

                    # Use transaction for multiple operations
                    c.execute('BEGIN TRANSACTION')
                    try:
                        c.execute("""
                            UPDATE territories
                            SET status=?, taken_by=?, date_taken=?, date_due=?
                            WHERE id=?
                        """, ("Взято", taken_by, date_taken, date_due, territory_id))

                        c.execute("""
                            INSERT INTO history (territory_id, taken_by, date_taken, date_due)
                            VALUES (?, ?, ?, ?)
                        """, (territory_id, taken_by, date_taken, date_due))

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

                        update_google_sheet(
                            territory_id=territory_id,
                            taken_by=taken_by,
                            date_taken=date_taken,
                            date_due=date_due,
                            returned=False
                        )
                    except Exception as e:
                        conn.rollback()
                        raise e
                else:
                    c.execute("""
                        UPDATE territories
                        SET status='Вільна', taken_by='', date_taken='', date_due=''
                        WHERE id=?
                    """, (territory_id,))
                    conn.commit()

                    update_google_sheet(
                        territory_id=territory_id,
                        taken_by="",
                        date_taken="",
                        date_due=datetime.now().strftime('%d.%m.%Y'),
                        returned=True
                    )

            return redirect(url_for('update_territory', territory_id=territory_id))
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

        return render_template('update.html', territory=territory, history=history)
    except Exception as e:
        app.logger.error(f"Error fetching territory {territory_id}: {e}")
        return "Помилка при отриманні даних території", 500

@app.route('/release/<int:territory_id>', methods=['POST'])
def release_territory(territory_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    try:
        with get_db() as conn:
            c = conn.cursor()
            
            # Check if territory exists and is taken
            c.execute("SELECT status FROM territories WHERE id=?", (territory_id,))
            result = c.fetchone()
            if not result:
                return "Територію не знайдено", 404
            if result[0] != 'Взято':
                return "Територія вже вільна", 400

            c.execute("""
                UPDATE territories
                SET status='Вільна', taken_by='', date_taken='', date_due=''
                WHERE id=?
            """, (territory_id,))
            conn.commit()

        update_google_sheet(
            territory_id=territory_id,
            taken_by="",
            date_taken="",
            date_due=datetime.now().strftime('%d.%m.%Y'),
            returned=True
        )

        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Error releasing territory {territory_id}: {e}")
        return "Помилка при звільненні території", 500

@app.route('/clear/<int:territory_id>', methods=['POST'])
def clear_territory(territory_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

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