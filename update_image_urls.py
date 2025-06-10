import sqlite3

def update_image_urls():
    conn = sqlite3.connect('territories.db')
    cursor = conn.cursor()
    
    # Оновлюємо URL для територій 183-190
    for territory_id in range(183, 191):
        image_url = f"/static/uploads/territories/{territory_id}.jpg"
        cursor.execute("""
            UPDATE territories 
            SET image_url = ?
            WHERE id = ?
        """, (image_url, territory_id))
        print(f"Оновлено URL для території {territory_id}")
    
    conn.commit()
    conn.close()
    print("Готово! URLs оновлено.")

if __name__ == "__main__":
    update_image_urls() 