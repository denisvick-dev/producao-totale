# utils/_config.py
import streamlit as st

# ID da sua planilha extraído do link
SPREADSHEET_ID = "1MolnI0nY4SHWsuqqpa0QTKJ9Phuq1RH5YB2caWKuyVE"
WORKSHEET_NAME = 0  # Pega a primeira aba

# Colunas exatas da sua planilha
HEADERS = ["Técnico", "Login", "User", "Pass"]

def get_credentials_dict():
    """Retorna credenciais do Streamlit Secrets (se disponível)."""
    if "gcp_service_account" in st.secrets:
        return dict(st.secrets["gcp_service_account"])
    return None