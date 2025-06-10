from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify
import os
from datetime import datetime, timedelta
import hashlib
from dotenv import load_dotenv
import logging
from db_factory import DBFactory
from backup_manager import backup_important_data, restore_from_backup
import shutil

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.permanent_session_lifetime = timedelta(minutes=20)  # Встановлюємо час життя сесії 20 хвилин

# Додаємо конфігурацію для базового URL
app.config['BASE_URL'] = os.environ.get('BASE_URL', 'https://territoryapp-production.up.railway.app')

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

# Налаштування шляхів для завантаження
UPLOAD_FOLDER = os.path.join(os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', 'data'), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Копіюємо існуючі фотографії при першому запуску
static_territories = 'static/uploads/territories'
if os.path.exists(static_territories):
    for filename in os.listdir(static_territories):
        src = os.path.join(static_territories, filename)
        dst = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(src) and not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            print(f"Скопійовано фото: {filename}")

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Створюємо функцію для отримання повного URL
def get_full_url(path):
    if app.debug:
        return path  # В режимі розробки використовуємо відносні шляхи
    return app.config['BASE_URL'].rstrip('/') + path

# Додаємо функцію в контекст шаблону
@app.context_processor
def utility_processor():
    return dict(get_full_url=get_full_url)

@app.before_request
def check_session_timeout():
    if 'logged_in' in session:
        # Перевіряємо час останньої активності
        last_activity = session.get('last_activity')
        now = datetime.now()
        
        if last_activity:
            last_activity = datetime.fromisoformat(last_activity)
            if (now - last_activity) > timedelta(minutes=20):
                session.clear()
                return redirect(url_for('login'))
        
        # Оновлюємо час останньої активності
        session['last_activity'] = now.isoformat()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        role = request.form['role']
        
        # Use environment variable for passwords
        admin_password = os.environ.get('APP_PASSWORD', 'Pass123')
        viewer_password = os.environ.get('VIEWER_PASSWORD', 'View123')
        courier_password = os.environ.get('COURIER_PASSWORD', '123')
        
        is_valid = False
        if role == 'admin' and hashlib.sha256(password.encode()).hexdigest() == hashlib.sha256(admin_password.encode()).hexdigest():
            is_valid = True
            session['role'] = 'admin'
        elif role == 'viewer' and hashlib.sha256(password.encode()).hexdigest() == hashlib.sha256(viewer_password.encode()).hexdigest():
            is_valid = True
            session['role'] = 'viewer'
        elif role == 'courier' and hashlib.sha256(password.encode()).hexdigest() == hashlib.sha256(courier_password.encode()).hexdigest():
            is_valid = True
            session['role'] = 'courier'
            
        if is_valid:
            session['logged_in'] = True
            session['last_activity'] = datetime.now().isoformat()  # Додаємо час початку сесії
            if role == 'courier':
                return redirect(url_for('courier_home'))
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
            # Check if image exists for this territory
            image_path = os.path.join(app.static_folder, 'uploads', 'territories', f"{territory['id']}.jpg")
            has_image = os.path.exists(image_path)
            
            territory_tuple = (
                territory['id'],
                territory['name'] or f"Територія {territory['id']}",
                territory['status'],
                territory['taken_by'],
                territory['date_taken'],
                territory['date_due'],
                territory['notes'],
                has_image  # Add has_image as the last element of tuple
            )
            
            if territory['status'] == 'Взято':
                # Перевіряємо чи наближається дата здачі
                due_date = datetime.strptime(territory['date_due'], '%d.%m.%Y') if territory['date_due'] else None
                is_due_soon = False
                if due_date:
                    days_left = (due_date - datetime.now()).days
                    is_due_soon = days_left <= 10
                taken.append((territory_tuple, is_due_soon))
            else:
                free.append(territory_tuple)
        
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

@app.route('/backup', methods=['POST'])
def create_backup():
    """Створює резервну копію важливих даних."""
    backup_important_data()
    return jsonify({'message': 'Резервну копію створено успішно'})

@app.route('/restore/<path:backup_file>', methods=['POST'])
def restore_backup(backup_file):
    """Відновлює дані з резервної копії."""
    restore_from_backup(backup_file)
    return jsonify({'message': 'Дані відновлено успішно'})

@app.route('/courier')
def courier_home():
    if not session.get('logged_in') or session.get('role') != 'courier':
        return redirect(url_for('login'))

    try:
        territories = db.get_all_territories()
        
        # Фільтруємо тільки вільні території
        free = []
        for territory in territories:
            if territory['status'] != 'Взято':
                # Перевіряємо наявність фото
                image_path = os.path.join(app.static_folder, 'uploads', 'territories', f"{territory['id']}.jpg")
                has_image = os.path.exists(image_path)
                
                territory_tuple = (
                    territory['id'],
                    territory['name'] or f"Територія {territory['id']}",
                    territory['status'],
                    territory['notes'],
                    has_image
                )
                free.append(territory_tuple)
        
        return render_template('courier.html', territories=free)
    except Exception as e:
        logger.error(f"Помилка при отриманні даних: {str(e)}")
        return "Помилка при отриманні даних", 500

# Створюємо функцію для отримання повного URL
def get_image_url(territory_id):
    """Повертає URL фотографії території"""
    # Перевіряємо наявність фото в Volume
    volume_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{territory_id}.jpg")
    if os.path.exists(volume_path):
        return f"/uploads/{territory_id}.jpg"
    
    # Якщо немає в Volume, перевіряємо в static
    static_path = os.path.join('static/uploads/territories', f"{territory_id}.jpg")
    if os.path.exists(static_path):
        return f"/static/uploads/territories/{territory_id}.jpg"
    
    return None

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Повертає файл з Volume"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/territory/<int:territory_id>')
def territory(territory_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    try:
        territory_data = db.get_territory(territory_id)
        if territory_data:
            # Перевіряємо фото в Volume
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{territory_id}.jpg")
            if os.path.exists(image_path):
                territory_data['image_url'] = f"/uploads/{territory_id}.jpg"
            else:
                # Перевіряємо фото в static
                static_path = f"uploads/territories/{territory_id}.jpg"
                if os.path.exists(os.path.join('static', static_path)):
                    territory_data['image_url'] = f"/static/{static_path}"
                else:
                    territory_data['image_url'] = None
            
            return render_template('territory.html', territory=territory_data, user_role=session.get('role', ''))
        return "Територію не знайдено", 404
    except Exception as e:
        print(f"Помилка при отриманні території {territory_id}: {str(e)}")
        return "Помилка при отриманні даних", 500

@app.route('/territories')
def territories():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    try:
        territories_data = db.get_all_territories()
        
        # Оновлюємо URL фотографій для кожної території
        for territory in territories_data:
            territory_id = territory['id']
            # Перевіряємо фото в Volume
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{territory_id}.jpg")
            if os.path.exists(image_path):
                territory['image_url'] = f"/uploads/{territory_id}.jpg"
            else:
                # Перевіряємо фото в static
                static_path = f"uploads/territories/{territory_id}.jpg"
                if os.path.exists(os.path.join('static', static_path)):
                    territory['image_url'] = f"/static/{static_path}"
                else:
                    territory['image_url'] = None
        
        return render_template('territories.html', 
                             territories=territories_data,
                             user_role=session.get('role', ''))
    except Exception as e:
        print(f"Помилка при отриманні списку територій: {str(e)}")
        return "Помилка при отриманні даних", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
