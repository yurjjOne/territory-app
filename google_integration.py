
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Авторизація до Google Sheets
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_name(
    "territory-app-461105-e5b14c010a91.json", scope
)
client = gspread.authorize(creds)

SPREADSHEET_ID = "17bGUa7uyxFFJhCTp2UdDuydbFW1UyEN7WoqJ6VlbCig"

def update_google_sheet(territory_id, taken_by, date_taken, date_due, returned=False):
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    row_base = 6 + (territory_id - 1) * 2
    visnyk_row = row_base
    date_row = row_base + 1
    max_blocks = 5

    if not returned:
        # запис нового вісника в перший вільний блок
        for i in range(max_blocks):
            col = 3 + i * 2
            if not sheet.cell(visnyk_row, col).value:
                sheet.update_cell(visnyk_row, col, taken_by)
                sheet.update_cell(date_row, col, date_taken)
                sheet.update_cell(date_row, col + 1, date_due)
                return
        # якщо всі блоки зайняті — очищаємо й записуємо в перший
        for i in range(max_blocks):
            col = 3 + i * 2
            sheet.update_cell(visnyk_row, col, "")
            sheet.update_cell(date_row, col, "")
            sheet.update_cell(date_row, col + 1, "")
        sheet.update_cell(visnyk_row, 3, taken_by)
        sheet.update_cell(date_row, 3, date_taken)
        sheet.update_cell(date_row, 4, date_due)
    else:
        # запис дати здачі в останній непорожній блок
        for i in reversed(range(max_blocks)):
            col = 3 + i * 2
            if sheet.cell(visnyk_row, col).value:
                sheet.update_cell(date_row, col + 1, date_due)
                return
        # якщо не знайдений — записуємо дату здачі в перший правий блок
        sheet.update_cell(date_row, 4, date_due)

def clear_google_sheet(territory_id):
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    row_base = 6 + (territory_id - 1) * 2
    visnyk_row = row_base
    date_row = row_base + 1
    # очищаємо усі 5 блоків
    for i in range(5):
        col = 3 + i * 2
        sheet.update_cell(visnyk_row, col, "")
        sheet.update_cell(date_row, col, "")
        sheet.update_cell(date_row, col + 1, "")
