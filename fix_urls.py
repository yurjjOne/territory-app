import sqlite3
import re

def fix_image_urls():
    conn = sqlite3.connect('territories.db')
    cursor = conn.cursor()
    
    # Отримуємо всі записи з image_url
    cursor.execute("SELECT id, image_url FROM territory WHERE image_url IS NOT NULL")
    records = cursor.fetchall()
    
    for record in records:
        territory_id, image_url = record
        if image_url:
            # Видаляємо будь-який домен та залишаємо тільки шлях
            new_url = re.sub(r'^https?://[^/]+', '', image_url)
            # Переконуємось що шлях починається з /
            if not new_url.startswith('/'):
                new_url = '/' + new_url
            
            # Оновлюємо запис
            cursor.execute(
                "UPDATE territory SET image_url = ? WHERE id = ?",
                (f"/static/uploads/territories/{territory_id}.jpg", territory_id)
            )
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    fix_image_urls()
    print("URLs fixed successfully!") 