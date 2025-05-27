import gspread
from oauth2client.service_account import ServiceAccountCredentials

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
    row_base = 6 + (territory_id - 1)*2
    vis_row, date_row = row_base, row_base + 1
    max_blocks = 5

    if not returned:
        # 1) лише записуємо планову дату (дата отримання)
        for i in range(max_blocks):
            col = 3 + i*2
            if not sheet.cell(vis_row, col).value:
                sheet.update_cell(vis_row, col, taken_by)
                sheet.update_cell(date_row, col, date_taken)
                return
        # 2) якщо всі блоки зайняті — чистимо й починаємо спочатку
        for i in range(max_blocks):
            col = 3 + i*2
            sheet.update_cell(vis_row, col, "")
            sheet.update_cell(date_row, col, "")
            sheet.update_cell(date_row, col+1, "")
        sheet.update_cell(vis_row, 3, taken_by)
        sheet.update_cell(date_row, 3, date_taken)

    else:
        # записуємо фактичну дату здачі (в останній непорожній блок праворуч)
        for i in reversed(range(max_blocks)):
            col = 3 + i*2
            if sheet.cell(vis_row, col).value:
                sheet.update_cell(date_row, col+1, date_due)
                return
        # fallback — перший правий блок
        sheet.update_cell(date_row, 4, date_due)


def clear_google_sheet(territory_id):
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    row_base = 6 + (territory_id - 1)*2
    vis_row, date_row = row_base, row_base + 1
    for i in range(5):
        col = 3 + i*2
        sheet.update_cell(vis_row, col, "")
        sheet.update_cell(date_row, col, "")
        sheet.update_cell(date_row, col+1, "")
