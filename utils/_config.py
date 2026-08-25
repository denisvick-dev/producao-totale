# utils/_config.py
import streamlit as st
from typing import Optional, Dict, Any

USERS_SPREADSHEET_ID: str = "1MolnI0nY4SHWsuqqpa0QTKJ9Phuq1RH5YB2caWKuyVE"
PRODUCAO_SPREADSHEET_ID: str = "11Dp9WdZYUrT_LBvfo07Mi8muKXZykU7v"

WORKSHEET_NAME: int = 0  # Primeira aba de cada planilha

HEADERS_USERS = ["Técnico", "Login", "User", "Pass"]


def get_credentials_dict() -> Optional[Dict[str, Any]]:
    """Retorna credenciais do Streamlit Secrets (se disponível)."""
    if "gcp_service_account" in st.secrets:
        return dict(st.secrets["gcp_service_account"])
    return None