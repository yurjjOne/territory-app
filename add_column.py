from app import db

with db.engine.connect() as conn:
    conn.execute("ALTER TABLE territory ADD COLUMN image_url TEXT;")
    print("✅ Колонку image_url додано!") 