
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Авторизація до Google Sheets
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# Основна функція інтеграції
def update_google_sheet(territory_id, taken_by, date_taken, date_due, returned=False):
    # Відкриваємо таблицю
    sheet = client.open_by_key("17bGUa7uyxFFJhCTp2UdDuydbFW1UyEN7WoqJ6VlbCig").sheet1

    # Вираховуємо базовий рядок для території
    row_base = 6 + ((territory_id - 1) * 2)
    visnyk_row = row_base
    date_row = row_base + 1

    max_blocks = 5
    written = False

    # Проходимо по 5 блоках (C:D, E:F, G:H, I:J, K:L)
    for i in range(max_blocks):
        col = 3 + i * 2  # C=3, E=5, ...
        visnyk = sheet.cell(visnyk_row, col).value
        if not visnyk:
            if not returned:
                sheet.update_cell(visnyk_row, col, taken_by)
                sheet.update_cell(date_row, col, date_taken)
            else:
                sheet.update_cell(date_row, col + 1, date_due)
            written = True
            break

    # Якщо всі 5 блоків зайняті — очищаємо й записуємо з початку
    if not written:
        for i in range(max_blocks):
            col = 3 + i * 2
            sheet.update_cell(visnyk_row, col, "")
            sheet.update_cell(date_row, col, "")
            sheet.update_cell(date_row, col + 1, "")
        # Записуємо у перший блок
        sheet.update_cell(visnyk_row, 3, taken_by)
        sheet.update_cell(date_row, 3, date_taken)
