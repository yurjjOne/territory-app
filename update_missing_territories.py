import sqlite3
import os

def add_missing_territories():
    conn = sqlite3.connect('territories.db')
    cursor = conn.cursor()
    
    # Перевіряємо існуючі території
    cursor.execute("SELECT id FROM territories")
    existing_ids = set(row[0] for row in cursor.fetchall())
    
    # Перевіряємо фотографії в папці
    photos_dir = "static/uploads/territories"
    for filename in os.listdir(photos_dir):
        if filename.endswith('.jpg'):
            try:
                territory_id = int(filename.split('.')[0])
                
                # Якщо території немає в базі, додаємо її
                if territory_id not in existing_ids:
                    print(f"Додаю територію {territory_id}")
                    cursor.execute("""
                        INSERT INTO territories 
                        (id, status, image_url) 
                        VALUES (?, 'Вільна', ?)
                    """, (territory_id, f"/static/uploads/territories/{filename}"))
            except ValueError:
                continue
    
    conn.commit()
    conn.close()
    print("Готово! Всі відсутні території додано.")

if __name__ == "__main__":
    add_missing_territories() 