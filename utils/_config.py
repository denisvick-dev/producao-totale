# utils/_config.py
from typing import Any

import streamlit as st

USERS_SPREADSHEET_ID: str = "1MolnI0nY4SHWsuqqpa0QTKJ9Phuq1RH5YB2caWKuyVE"
PRODUCAO_SPREADSHEET_ID: str = "11Dp9WdZYUrT_LBvfo07Mi8muKXZykU7v"
ATIVOS_SPREADSHEET_ID: str = "1LQKDcLshC6XSXLBVWaEYSpxrro6uydyU9pwDLc38pEg"

# Planilha (Excel/Google Sheets) com as abas operacionais de indicadores:
# Geoloc_Os, OS_Digital, Aderencia_Ura, Nr35, Tec1 e Baixa_Pda.
# Informe o ID aqui ou, preferencialmente, nos Secrets do Streamlit com a
# chave "indicadores_spreadsheet_id".
INDICADORES_SPREADSHEET_ID: str = ""

WORKSHEET_NAME: int = 0  # Primeira aba de cada planilha

HEADERS_USERS = ["Técnico", "Login", "User", "Pass", "Perfil"]


def get_credentials_dict() -> dict[str, Any] | None:
    """Retorna credenciais do Streamlit Secrets (se disponível)."""
    if "gcp_service_account" in st.secrets:
        return dict(st.secrets["gcp_service_account"])
    return None


def _segredo(chave: str) -> str:
    """Lê uma chave de ``st.secrets`` sem quebrar quando não há secrets.toml."""
    try:
        valor = st.secrets.get(chave, "")
    except Exception:  # noqa: BLE001 - sem secrets.toml em ambiente local
        return ""
    return str(valor or "").strip()


def get_indicadores_spreadsheet_id() -> str:
    """ID da planilha de indicadores (Secret > ``utils/_config.py``)."""
    return _segredo("indicadores_spreadsheet_id") or INDICADORES_SPREADSHEET_ID


def get_ativos_spreadsheet_id() -> str:
    """ID da planilha Lista Ativos (Secret > ``utils/_config.py``)."""
    return _segredo("ativos_spreadsheet_id") or ATIVOS_SPREADSHEET_ID
