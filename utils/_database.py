# utils/_database.py
import os
import io
import requests
import pandas as pd
import streamlit as st
from typing import Any, Dict, List, Optional

import bcrypt
import gspread
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request

# Importa as configurações do seu projeto
from ._config import (
    HEADERS_USERS,
    PRODUCAO_SPREADSHEET_ID,
    USERS_SPREADSHEET_ID,
    WORKSHEET_NAME,
    get_credentials_dict,
)


class GoogleSheetsDB:
    def __init__(self) -> None:
        self.client: gspread.Client
        self.credentials: Credentials
        self._connect()

    def _connect(self) -> None:
        # Escopos necessários para ler Sheets e baixar arquivos do Drive
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/drive"
        ]

        creds_dict = get_credentials_dict()
        if creds_dict:
            self.credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        else:
            creds_file = "credentials.json"
            if not os.path.exists(creds_file):
                raise FileNotFoundError("❌ Arquivo 'credentials.json' não encontrado!")
            self.credentials = Credentials.from_service_account_file(creds_file, scopes=scopes)

        self.client = gspread.authorize(self.credentials)

    def _get_worksheet(self, spreadsheet_id: str):
        """Tenta abrir a planilha como Google Sheets nativo."""
        spreadsheet = self.client.open_by_key(spreadsheet_id)
        ws = spreadsheet.get_worksheet(WORKSHEET_NAME) if isinstance(WORKSHEET_NAME, int) else None
        if ws is None:
            ws = spreadsheet.sheet1
        return ws

    def get_users_dataframe(self) -> pd.DataFrame:
        """Base de usuários (Geralmente é Sheets nativo)."""
        try:
            ws = self._get_worksheet(USERS_SPREADSHEET_ID)
            records = ws.get_all_records()
            return pd.DataFrame(records) if records else pd.DataFrame(columns=HEADERS_USERS)
        except Exception as e:
            st.error(f"Erro na base de usuários: {e}")
            return pd.DataFrame(columns=HEADERS_USERS)

    def save_users_dataframe(self, df: pd.DataFrame) -> bool:
        """Persiste o DataFrame de usuários de volta na planilha Google Sheets."""
        try:
            if df.empty:
                return False

            ws = self._get_worksheet(USERS_SPREADSHEET_ID)
            upload_df = df.copy().fillna("")
            rows: list[list[Any]] = [list(upload_df.columns.astype(str))]
            for _, row in upload_df.iterrows():
                rows.append(["" if pd.isna(value) else value for value in row.tolist()])

            ws.clear()
            ws.update(range_name="A1", values=rows, raw=False)
            return True
        except Exception as e:
            st.error(f"Erro ao salvar base de usuários: {e}")
            return False

    def update_user_password(self, login_real: str, novo_hash_bcrypt: str) -> bool:
        """
        Atualiza o campo 'Pass' do usuário na tabela do banco de dados.
        Retorna True se salvou corretamente.
        """
        try:
            # EXEMPLO SE VOCÊ USA GOOGLE SHEETS:
            df = self.get_users_dataframe()
            df.loc[df["Login"] == login_real, "Pass"] = novo_hash_bcrypt
            return self.save_users_dataframe(df)
            
            # EXEMPLO SE VOCÊ USA SUPABASE CLIENT:
            # response = self.supabase.table("sua_tabela").update({"Pass": novo_hash_bcrypt}).eq("Login", login_real).execute()
            # return len(response.data) > 0

        except Exception as e:
            print(f"Erro no banco: {e}")
            return False
        
        
    def find_user_by_login_or_user(self, identifier: str) -> Optional[Dict[str, Any]]:
        df = self.get_users_dataframe()
        if df.empty: return None
        
        ident = identifier.strip().lower()
        for _, row in df.iterrows():
            if ident in [str(row.get("Login", "")).lower(), str(row.get("User", "")).lower()]:
                return {str(key): value for key, value in row.to_dict().items()}
        return None

    # ========================================================
    # LOGICA ESPECIAL PARA PRODUÇÃO (EXCEL .XLSX)
    # ========================================================
    
    def _download_binary_excel(self, file_id: str) -> pd.DataFrame:
        """
        Faz o download de um arquivo que é EXCEL (.xlsx) dentro do Drive.
        Usa o parâmetro alt=media para baixar o arquivo binário original.
        """
        if not self.credentials.valid:
            self.credentials.refresh(Request())

        # URL para baixar arquivos binários (não-nativos do Google) do Drive
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
        
        headers = {"Authorization": f"Bearer {self.credentials.token}"}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            # Lê o binário .xlsx usando engine openpyxl
            return pd.read_excel(io.BytesIO(response.content), engine='openpyxl')
        else:
            st.error(f"Erro no download binário: {response.status_code} - {response.text}")
            return pd.DataFrame()

    def get_producao_dataframe(self) -> pd.DataFrame:
        """
        Carrega produção unificando as abas Prod + Gpon.
        Mantém coluna auxiliar __origem__ para auditoria.
        """
        df_prod = self._ler_aba_producao("Prod")
        df_gpon = self._ler_aba_producao("Gpon")

        frames = []
        if not df_prod.empty:
            df_prod = df_prod.copy()
            df_prod["__origem__"] = "Prod"
            frames.append(df_prod)
        if not df_gpon.empty:
            df_gpon = df_gpon.copy()
            df_gpon["__origem__"] = "Gpon"
            frames.append(df_gpon)

        if not frames:
            # fallback: primeira aba (comportamento antigo)
            try:
                ws = self._get_worksheet(PRODUCAO_SPREADSHEET_ID)
                if ws is not None:
                    records = ws.get_all_records()
                    df = pd.DataFrame(records) if records else pd.DataFrame()
                    if not df.empty:
                        df["__origem__"] = "Geral"
                    return df
            except Exception:
                pass
            return pd.DataFrame()

        return pd.concat(frames, ignore_index=True)


    def _ler_aba_producao(self, nome_aba: str) -> pd.DataFrame:
        """Lê uma aba específica da planilha de produção (Sheets nativo ou Excel)."""
        try:
            spreadsheet = self.client.open_by_key(PRODUCAO_SPREADSHEET_ID)
            try:
                ws = spreadsheet.worksheet(nome_aba)
                records = ws.get_all_records()
                return pd.DataFrame(records) if records else pd.DataFrame()
            except Exception:
                # Se for arquivo Excel (.xlsx), baixa e lê a aba pelo nome
                return self._download_excel_sheet(PRODUCAO_SPREADSHEET_ID, nome_aba)
        except Exception:
            try:
                return self._download_excel_sheet(PRODUCAO_SPREADSHEET_ID, nome_aba)
            except Exception:
                return pd.DataFrame()


    def _download_excel_sheet(self, file_id: str, sheet_name: str) -> pd.DataFrame:
        """Download binário do Excel e leitura de uma aba específica."""
        import io
        import requests
        from google.auth.transport.requests import Request

        if not self.credentials.valid:
            self.credentials.refresh(Request())

        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
        headers = {"Authorization": f"Bearer {self.credentials.token}"}
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            return pd.DataFrame()

        try:
            return pd.read_excel(
                io.BytesIO(response.content),
                sheet_name=sheet_name,
                engine="openpyxl",
            )
        except Exception:
            # tenta nomes alternativos comuns
            try:
                xl = pd.ExcelFile(io.BytesIO(response.content), engine="openpyxl")
                sheet_name_str = str(sheet_name).strip().lower()
                for name in xl.sheet_names:
                    if str(name).strip().lower() == sheet_name_str:
                        return pd.read_excel(xl, sheet_name=name)
            except Exception:
                return pd.DataFrame()
            return pd.DataFrame()


    def get_producao_by_tecnico(
        self, tecnico: str, login_code: str, user_code: str
    ) -> pd.DataFrame:
        df = self.get_producao_dataframe()
        if df.empty:
            return df

        targets = {
            str(tecnico).strip().lower(),
            str(login_code).strip().lower(),
            str(user_code).strip().lower(),
        }
        targets.discard("")

        mask = pd.Series(False, index=df.index)
        for col in df.columns:
            if col == "__origem__":
                continue
            mask |= df[col].astype(str).str.strip().str.lower().isin(targets)

        return df[mask].reset_index(drop=True)

@st.cache_resource(ttl=300)
def get_db() -> GoogleSheetsDB:
    return GoogleSheetsDB()