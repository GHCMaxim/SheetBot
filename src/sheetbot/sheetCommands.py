from googleapiclient.discovery import build
from google.oauth2 import service_account

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_service():
    creds = service_account.Credentials.from_service_account_file(
        "credentials.json", scopes=SCOPES
    )
    spreadsheet_service = build("sheets", "v4", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)
    return spreadsheet_service, drive_service


def connect_to_sheet(spreadsheet_service, sheet_id):
    return spreadsheet_service.spreadsheets().get(spreadsheetId=sheet_id).execute()


def get_sheet_values(spreadsheet_service, sheet_id, range):
    return (
        spreadsheet_service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=range)
        .execute()
    )


def write_to_sheet(spreadsheet_service, sheet_id, range, body):
    return (
        spreadsheet_service.spreadsheets()
        .values()
        .update(spreadsheetId=sheet_id, range=range, valueInputOption="RAW", body=body)
        .execute()
    )
