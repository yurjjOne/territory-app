from migrations_manager import app, db
from flask_migrate import upgrade

def init_migrations():
    """Ініціалізує систему міграцій."""
    with app.app_context():
        db.create_all()
        print("База даних ініціалізована")

def apply_migrations():
    """Застосовує всі очікуючі міграції."""
    with app.app_context():
        upgrade()
        print("Міграції застосовано")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'init':
            init_migrations()
        elif sys.argv[1] == 'migrate':
            apply_migrations()
        else:
            print("Невідома команда. Використовуйте: init або migrate") 