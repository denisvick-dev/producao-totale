# utils/_database.py
import os
from typing import Any, Dict, List, Optional
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import streamlit as st

from utils._config import HEADERS, SPREADSHEET_ID, WORKSHEET_NAME, get_credentials_dict


class GoogleSheetsDB:
    def __init__(self) -> None:
        self.client: gspread.Client
        self.spreadsheet: gspread.Spreadsheet
        self.worksheet: gspread.Worksheet
        self._connect()

    def _connect(self) -> None:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        creds_dict = get_credentials_dict()
        if creds_dict:
            credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        else:
            creds_file = "credentials.json"
            if not os.path.exists(creds_file):
                raise FileNotFoundError("❌ Arquivo 'credentials.json' não encontrado!")
            credentials = Credentials.from_service_account_file(creds_file, scopes=scopes)

        self.client = gspread.authorize(credentials)
        self.spreadsheet = self.client.open_by_key(SPREADSHEET_ID)

        ws: Optional[gspread.Worksheet] = None
        if isinstance(WORKSHEET_NAME, int):
            ws = self.spreadsheet.get_worksheet(WORKSHEET_NAME)
        else:
            try:
                ws = self.spreadsheet.worksheet(WORKSHEET_NAME)
            except gspread.WorksheetNotFound:
                ws = None

        if ws is None:
            ws = self.spreadsheet.sheet1

        self.worksheet = ws

    def get_all_records(self) -> List[Dict[str, Any]]:
        """Retorna todas as linhas da planilha como lista de dicionários."""
        try:
            return self.worksheet.get_all_records()
        except Exception:
            return []

    def get_dataframe(self) -> pd.DataFrame:
        """Carrega os dados da planilha diretamente em um DataFrame do Pandas."""
        records = self.get_all_records()
        if records:
            return pd.DataFrame(records)
        return pd.DataFrame(columns=HEADERS)

    def find_user_by_login_or_user(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Busca usuário comparando tanto a coluna 'Login' quanto a 'User'."""
        identifier_clean = identifier.strip().lower()
        records = self.get_all_records()

        for row in records:
            login_val = str(row.get("Login", "")).strip().lower()
            user_val = str(row.get("User", "")).strip().lower()

            if identifier_clean in (login_val, user_val):
                return row
        return None


# Limpa o cache ao recarregar a classe para evitar erros de atributo antigo
@st.cache_resource(ttl=600)
def get_db() -> GoogleSheetsDB:
    return GoogleSheetsDB()