from flask import Flask, render_template, request, redirect, url_for, session
import os
from datetime import datetime, timedelta
import hashlib
from dotenv import load_dotenv
import logging
from db_factory import DBFactory

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'MySecretKey2025')

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Замінюємо створення db на використання фабрики
db = DBFactory.get_db()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        role = request.form['role']
        
        # Use environment variable for passwords
        admin_password = os.environ.get('APP_PASSWORD', 'Pass123')
        viewer_password = os.environ.get('VIEWER_PASSWORD', 'View123')
        
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
        territories = db.get_all_territories()
        
        # Розділяємо території на взяті та вільні
        taken = []
        free = []
        
        for territory in territories:
            if territory['status'] == 'Взято':
                # Перевіряємо чи наближається дата здачі
                due_date = datetime.strptime(territory['date_due'], '%d.%m.%Y') if territory['date_due'] else None
                is_due_soon = False
                if due_date:
                    days_left = (due_date - datetime.now()).days
                    is_due_soon = days_left <= 10
                taken.append((territory, is_due_soon))
            else:
                free.append(territory)
        
        return render_template('index.html', 
                            taken=taken, 
                            free=free, 
                            is_admin=(session.get('role') == 'admin'))
    except Exception as e:
        logger.error(f"Помилка при отриманні даних: {str(e)}")
        return "Помилка при отриманні даних", 500

@app.route('/update/<territory_id>', methods=['GET', 'POST'])
def update_territory(territory_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    # Перевіряємо чи користувач має права адміна для редагування
    if request.method == 'POST' and session.get('role') != 'admin':
        return "Немає прав для редагування", 403

    try:
        territory_id = int(territory_id)
    except ValueError:
        return "Неправильний формат номера території", 400

    if request.method == 'POST':
        try:
            taken_by = request.form['taken_by'].strip()
            notes = request.form['notes'].strip()
            
            if taken_by:
                # Використовуємо поточну дату або передану дату
                now = datetime.now()
                if 'date_taken' in request.form and request.form['date_taken']:
                    date_taken = datetime.strptime(request.form['date_taken'], '%Y-%m-%d').strftime('%d.%m.%Y')
                else:
                    date_taken = now.strftime('%d.%m.%Y')

                # Для планової дати повернення
                date_due = (datetime.strptime(date_taken, '%d.%m.%Y') + timedelta(days=120)).strftime('%d.%m.%Y')

                # Оновлюємо дані території
                db.update_territory(territory_id, {
                    'status': 'Взято',
                    'taken_by': taken_by,
                    'date_taken': date_taken,
                    'date_due': date_due,
                    'notes': notes
                })
            else:
                # Звільняємо територію
                db.update_territory(territory_id, {
                    'status': 'Вільна',
                    'taken_by': '',
                    'date_taken': '',
                    'date_due': '',
                    'notes': notes
                })

            return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"Помилка при оновленні території {territory_id}: {str(e)}")
            return f"Помилка при оновленні території: {str(e)}", 500

    # GET request
    try:
        territory = db.get_territory(territory_id)
        if not territory:
            return "Територію не знайдено", 404

        history = db.get_territory_history(territory_id)
        
        # Передаємо поточну дату в шаблон
        now = datetime.now()
        return render_template('update.html', 
                            territory=territory, 
                            history=history, 
                            now=now,
                            is_admin=(session.get('role') == 'admin'))
    except Exception as e:
        logger.error(f"Помилка при отриманні даних території {territory_id}: {str(e)}")
        return f"Помилка при отриманні даних території: {str(e)}", 500

@app.route('/release/<territory_id>', methods=['POST'])
def release_territory(territory_id):
    if not session.get('logged_in') or session.get('role') != 'admin':
        return "Немає прав для цієї дії", 403

    try:
        territory_id = int(territory_id)
    except ValueError:
        return "Неправильний формат номера території", 400

    try:
        territory = db.get_territory(territory_id)
        if not territory:
            return "Територію не знайдено", 404
        if territory['status'] != 'Взято':
            return "Територія вже вільна", 400

        # Оновлюємо територію
        db.update_territory(territory_id, {
            'status': 'Вільна',
            'taken_by': '',
            'date_taken': '',
            'date_due': '',
            'notes': territory['notes']
        })

        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Помилка при звільненні території {territory_id}: {str(e)}")
        return "Помилка при звільненні території", 500

@app.route('/clear_history/<territory_id>', methods=['POST'])
def clear_history(territory_id):
    if not session.get('logged_in') or session.get('role') != 'admin':
        return "Немає прав для цієї дії", 403

    try:
        territory_id = int(territory_id)
    except ValueError:
        return "Неправильний формат номера території", 400

    try:
        db.clear_territory_history(territory_id)
        return redirect(url_for('update_territory', territory_id=territory_id))
    except Exception as e:
        logger.error(f"Помилка при очищенні історії території {territory_id}: {str(e)}")
        return "Помилка при очищенні історії території", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
