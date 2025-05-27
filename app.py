from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime, timedelta
import os
from google_integration import update_google_sheet  # 👈 додаємо інтеграцію

app = Flask(__name__)
app.secret_key = "MySecretKey2025"

# Ініціалізація бази даних
def init_db():
    conn = sqlite3.connect('territories.db')
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
    c.execute("SELECT COUNT(*) FROM territories")
    if c.fetchone()[0] == 0:
        for i in range(1, 182):
            c.execute("INSERT INTO territories (id, name, status) VALUES (?, ?, ?)",
                      (i, f"Територія {i}", "Вільна"))
    conn.commit()
    conn.close()

# Логін
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        if password == "Pass123":
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return "Неправильний пароль"
    return render_template('login.html')

# Головна сторінка
@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('territories.db')
    c = conn.cursor()
    c.execute("SELECT * FROM territories ORDER BY status DESC, id ASC")
    territories = c.fetchall()
    conn.close()
    return render_template('index.html', territories=territories)

# Оновлення території
@app.route('/update/<int:territory_id>', methods=['GET', 'POST'])
def update_territory(territory_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = sqlite3.connect('territories.db')
    c = conn.cursor()

    if request.method == 'POST':
        taken_by = request.form['taken_by']

        if taken_by:
            now = datetime.now()
            date_taken = now.strftime('%d.%m.%Y')
            date_due = (now + timedelta(days=120)).strftime('%d.%m.%Y')
            status = "Взято"

            c.execute("UPDATE territories SET status = ?, taken_by = ?, date_taken = ?, date_due = ? WHERE id = ?",
                      (status, taken_by, date_taken, date_due, territory_id))

            c.execute("INSERT INTO history (territory_id, taken_by, date_taken, date_due) VALUES (?, ?, ?, ?)",
                      (territory_id, taken_by, date_taken, date_due))

            c.execute("DELETE FROM history WHERE id NOT IN (SELECT id FROM history WHERE territory_id = ? ORDER BY id DESC LIMIT 5)",
                      (territory_id,))

            # ✅ Google Таблиця — заповнення
            update_google_sheet(
                territory_id=territory_id,
                taken_by=taken_by,
                date_taken=date_taken,
                date_due=date_due,
                returned=False
            )

        else:
            # Скидання
            c.execute("UPDATE territories SET status = ?, taken_by = '', date_taken = '', date_due = '' WHERE id = ?",
                      ("Вільна", territory_id))

            # ✅ Google Таблиця — здача території
            update_google_sheet(
                territory_id=territory_id,
                taken_by="",
                date_taken="",
                date_due=datetime.now().strftime('%d.%m.%Y'),
                returned=True
            )

        conn.commit()

    c.execute("SELECT * FROM territories WHERE id = ?", (territory_id,))
    territory = c.fetchone()

    c.execute("SELECT taken_by, date_taken, date_due FROM history WHERE territory_id = ? ORDER BY id DESC LIMIT 5",
              (territory_id,))
    history = c.fetchall()

    conn.close()
    return render_template('update.html', territory=territory, history=history)

# Запуск
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
