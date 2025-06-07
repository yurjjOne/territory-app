-- Оновлюємо всі URL фотографій на відносні шляхи
UPDATE territory 
SET image_url = '/static/uploads/territories/' || id || '.jpg' 
WHERE image_url IS NOT NULL; 