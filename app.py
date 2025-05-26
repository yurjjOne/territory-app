from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "MySecretKey2025"  # Змініть на унікальний ключ, наприклад, "MySecretKey2025"

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
    # Додаємо 181 територію
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
        if password == "Pass123":  # Змініть на ваш пароль, наприклад, "Pass123"
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
    c.execute("SELECT * FROM territories")
    territories = c.fetchall()
    conn.close()
    return render_template('index.html', territories=territories)

# Взяти/оновити територію
@app.route('/update/<int:territory_id>', methods=['GET', 'POST'])
def update_territory(territory_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('territories.db')
    c = conn.cursor()
    if request.method == 'POST':
        taken_by = request.form['taken_by']
        date_due = request.form['date_due']
        date_taken = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = "Взято" if taken_by else "Вільна"
        c.execute("UPDATE territories SET status = ?, taken_by = ?, date_taken = ?, date_due = ? WHERE id = ?",
                  (status, taken_by, date_taken if status == "Взято" else "", date_due if status == "Взято" else "", territory_id))
        conn.commit()
    c.execute("SELECT * FROM territories WHERE id = ?", (territory_id,))
    territory = c.fetchone()
    conn.close()
    return render_template('update.html', territory=territory)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
