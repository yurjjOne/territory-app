from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

# Ініціалізуємо Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///territories.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Ініціалізуємо SQLAlchemy та Flask-Migrate
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Реєструємо моделі для міграцій
class TerritoryModel(db.Model):
    __tablename__ = 'territories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    custom_name = db.Column(db.String)
    status = db.Column(db.String)
    taken_by = db.Column(db.String)
    date_taken = db.Column(db.String)
    date_due = db.Column(db.String)
    notes = db.Column(db.String)
    last_updated = db.Column(db.DateTime, default=db.func.current_timestamp())

class TerritoryHistoryModel(db.Model):
    __tablename__ = 'territory_history'
    
    id = db.Column(db.Integer, primary_key=True)
    territory_id = db.Column(db.Integer, db.ForeignKey('territories.id'))
    action = db.Column(db.String)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

if __name__ == '__main__':
    # Створюємо директорію для міграцій, якщо її немає
    if not os.path.exists('migrations'):
        os.makedirs('migrations')
    
    # Ініціалізуємо міграції, якщо це перший запуск
    if not os.path.exists('migrations/versions'):
        os.system('flask db init')
        print("Міграції ініціалізовано")
    
    app.run() 