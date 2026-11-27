"""Leitura centralizada e resiliente das bases públicas do Portal TOTALE.

A Visão Geral e a página de Produtividade precisam enxergar exatamente a mesma
base. Antes cada tela tinha um loader próprio: a página inicial só tentava XLSX
e comparava ``_norm(nome_aba)`` (maiúsculo) com ``"prod"``/``"gpon"``
(minúsculo), de modo que um Excel válido era descartado. Este módulo concentra
uma leitura única, com validação do conteúdo, múltiplos formatos de exportação,
nomes de abas tolerantes a acento/caixa e fallback autenticado por service
account quando o link público falha.
"""

from __future__ import annotations

import io
import logging
import unicodedata
from collections.abc import Callable
from typing import Any

import pandas as pd
import requests
import streamlit as st

from utils._config import get_credentials_dict, get_producao_spreadsheet_id

logger = logging.getLogger(__name__)

TIMEOUT_REDE = (5, 30)
CACHE_TTL = 600
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

_COL_CONTRATO = ["CONTRATO", "OS", "O.S.", "ORDEM", "NUM_OS", "ID_OS", "Nº OS"]
_COL_ORIGEM = ["ORIGEM", "__ORIGEM__", "TIPO", "SISTEMA", "FONTE", "TIPO_OS"]

#: Recebe ``(file_id, destino)``; ``destino`` pode ser uma preferência, uma URL
#: ou ``"autenticado"``. Permite que testes injetem uma fonte sem rede.
Baixador = Callable[[str, str], bytes | None]


def normalizar(valor: Any) -> str:
    """Normaliza texto para comparar nomes de abas/colunas sem acento/caixa."""
    texto = str(valor or "").strip().upper()
    sem_acento = "".join(
        char
        for char in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(char)
    )
    return (
        sem_acento.replace("_", " ")
        .replace("-", " ")
        .replace(".", " ")
        .strip()
    )


def encontrar_coluna(df: pd.DataFrame, candidatos: list[str]) -> str | None:
    """Devolve o nome real da primeira coluna equivalente a ``candidatos``."""
    mapa = {normalizar(coluna): coluna for coluna in df.columns}
    for candidato in candidatos:
        encontrada = mapa.get(normalizar(candidato))
        if encontrada is not None:
            return str(encontrada)
    return None


def _parece_html(conteudo: bytes) -> bool:
    """Detecta páginas de login/erro devolvidas com status 200 pelo Google."""
    inicio = conteudo[:1024].lstrip().lower()
    marcadores = (
        b"<!doctype html",
        b"<html",
        b"<head",
        b"<meta",
        b"<script",
        b"<!--",
    )
    return inicio.startswith(marcadores) or b"accounts.google.com" in inicio


def urls_publicas(file_id: str, preferencia: str = "xlsx") -> list[str]:
    """URLs de exportação, ordenadas pela preferência de formato."""
    if not file_id:
        return []

    xlsx = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    csv = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv"
    drive = [
        f"https://drive.usercontent.google.com/download?id={file_id}&export=download",
        f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t",
        f"https://drive.google.com/uc?export=download&id={file_id}",
    ]
    ordem = [xlsx, *drive, csv] if preferencia == "xlsx" else [csv, *drive, xlsx]
    vistas: set[str] = set()
    return [url for url in ordem if not (url in vistas or vistas.add(url))]


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _baixar_url(url: str) -> bytes | None:
    """Baixa uma URL e devolve apenas conteúdo que parece ser planilha."""
    try:
        resposta = requests.get(
            url,
            timeout=TIMEOUT_REDE,
            allow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except requests.RequestException:
        return None
    if resposta.status_code != 200 or len(resposta.content) <= 100:
        return None
    if _parece_html(resposta.content):
        return None
    return resposta.content


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _baixar_autenticado(file_id: str) -> bytes | None:
    """Fallback via Drive API quando os secrets da service account existem."""
    if not file_id:
        return None
    try:
        credenciais_dict = get_credentials_dict()
    except Exception:  # noqa: BLE001 - secrets indisponíveis fora do Streamlit Cloud
        return None
    if not credenciais_dict:
        return None

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.service_account import Credentials

        credenciais = Credentials.from_service_account_info(
            credenciais_dict,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        if not credenciais.valid or not getattr(credenciais, "token", None):
            credenciais.refresh(Request())
        token = getattr(credenciais, "token", None)
        if not token:
            return None
        resposta = requests.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media",
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": USER_AGENT,
            },
            timeout=TIMEOUT_REDE,
        )
        if resposta.status_code != 200 or len(resposta.content) <= 100:
            return None
        if _parece_html(resposta.content):
            return None
        return resposta.content
    except Exception as exc:  # noqa: BLE001 - fallback não pode derrubar a página
        logger.warning("Fallback autenticado do Drive falhou: %s", exc)
        return None


def ler_csv(conteudo: bytes) -> pd.DataFrame:
    """Lê CSV com separadores/codificações usados nas exportações do Drive."""
    tentativas: list[dict[str, Any]] = [
        {"sep": None, "engine": "python", "encoding": "utf-8-sig"},
        {"sep": None, "engine": "python", "encoding": "utf-8"},
        {"sep": ";", "encoding": "latin-1"},
        {"sep": ",", "encoding": "utf-8"},
        {"sep": "\t", "encoding": "utf-8"},
    ]
    for kwargs in tentativas:
        try:
            df = pd.read_csv(io.BytesIO(conteudo), **kwargs)
            if not df.empty and df.shape[1] > 1:
                return df.dropna(how="all").reset_index(drop=True)
        except Exception:
            continue
    return pd.DataFrame()


def _classificar_aba(nome: Any) -> str | None:
    nome_norm = normalizar(nome).replace(" ", "")
    if "GPON" in nome_norm:
        return "Gpon"
    if "PROD" in nome_norm or "PRODUCAO" in nome_norm:
        return "Prod"
    return None


def _preparar_aba(df: pd.DataFrame, origem: str | None) -> pd.DataFrame:
    aba = df.dropna(how="all").reset_index(drop=True).copy()
    if aba.empty or aba.shape[1] <= 1:
        return pd.DataFrame()

    # A base Gpon pode repetir a mesma O.S.; a página de Produtividade sempre
    # deduplica pelo contrato. Manter essa regra aqui evita números divergentes.
    if origem == "Gpon":
        col_contrato = encontrar_coluna(aba, _COL_CONTRATO)
        if col_contrato:
            aba = aba.drop_duplicates(subset=[col_contrato], keep="first")

    col_origem = encontrar_coluna(aba, _COL_ORIGEM)
    if not col_origem:
        aba["ORIGEM"] = origem or "Geral"
    aba["__origem__"] = origem or "Geral"
    return aba


def _ler_workbook_producao(conteudo: bytes) -> tuple[pd.DataFrame, int]:
    """Lê as abas Prod/Gpon de um XLSX e pontua a qualidade da fonte."""
    try:
        abas = pd.read_excel(
            io.BytesIO(conteudo), sheet_name=None, engine="openpyxl"
        )
    except Exception:
        return pd.DataFrame(), 0

    alvos: dict[str, pd.DataFrame] = {}
    genericas: list[pd.DataFrame] = []
    for nome_aba, df_aba in abas.items():
        origem = _classificar_aba(nome_aba)
        preparada = _preparar_aba(df_aba, origem)
        if preparada.empty:
            continue
        if origem in {"Prod", "Gpon"}:
            # Se houver mais de uma aba do mesmo tipo, concatena sem perder dados.
            if origem in alvos:
                alvos[origem] = pd.concat(
                    [alvos[origem], preparada], ignore_index=True
                )
            else:
                alvos[origem] = preparada
        else:
            genericas.append(preparada)

    quadros = [alvos["Prod"]] if "Prod" in alvos else []
    quadros += [alvos["Gpon"]] if "Gpon" in alvos else []
    if quadros:
        df = pd.concat(quadros, ignore_index=True)
        return df, (3 if len(quadros) == 2 else 2)

    if genericas:
        return pd.concat(genericas, ignore_index=True), 1
    return pd.DataFrame(), 0


def interpretar_conteudo(conteudo: bytes) -> tuple[pd.DataFrame, int]:
    """Converte XLSX/CSV em DataFrame e devolve uma nota de qualidade."""
    if not conteudo:
        return pd.DataFrame(), 0
    if conteudo.startswith(b"PK"):
        return _ler_workbook_producao(conteudo)

    df = ler_csv(conteudo)
    if not df.empty:
        return _preparar_aba(df, "Geral"), 1

    # Alguns links do Drive respondem XLSX sem o formato solicitado.
    try:
        df_excel = pd.read_excel(io.BytesIO(conteudo), engine="openpyxl")
        return _preparar_aba(df_excel, "Geral"), 1
    except Exception:
        return pd.DataFrame(), 0


def _baixador_padrao(file_id: str, destino: str) -> bytes | None:
    if destino.startswith("http"):
        return _baixar_url(destino)
    if destino == "autenticado":
        return _baixar_autenticado(file_id)
    return None


def _selecionar_melhor_base(file_id: str, baixador: Baixador) -> pd.DataFrame:
    """Escolhe a melhor fonte entre XLSX completo, CSV e Drive autenticado."""
    if not file_id:
        return pd.DataFrame()

    melhor_df = pd.DataFrame()
    melhor_pontuacao = -1
    destinos: list[str] = ["xlsx", *urls_publicas(file_id, "xlsx"), "autenticado"]
    for destino in destinos:
        conteudo = baixador(file_id, destino)
        if not conteudo:
            continue
        df, qualidade = interpretar_conteudo(conteudo)
        if df.empty:
            continue
        # Prefere sempre um workbook com Prod + Gpon a um CSV de uma única aba.
        pontuacao = qualidade * 1_000_000 + min(len(df), 999_999)
        if pontuacao > melhor_pontuacao:
            melhor_df, melhor_pontuacao = df, pontuacao
        if qualidade == 3:
            break
    return melhor_df


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _carregar_base_producao(file_id: str) -> pd.DataFrame:
    return _selecionar_melhor_base(file_id, _baixador_padrao)


def carregar_base_producao(
    file_id: str | None = None,
    baixador: Baixador | None = None,
) -> pd.DataFrame:
    """Base única de produção (Prod + Gpon) usada pela home e por Produtividade.

    O ID pode ser informado (por exemplo, para uma competência anterior) ou lido
    de ``producao_spreadsheet_id`` nos Secrets, com fallback para
    ``PRODUCAO_SPREADSHEET_ID``. ``baixador`` existe para páginas/testes que
    já possuem uma função de download própria e devem reutilizar este parser.
    """
    resolvido = file_id or get_producao_spreadsheet_id()
    if baixador is not None:
        return _selecionar_melhor_base(resolvido, baixador)
    return _carregar_base_producao(resolvido)


def baixar_url(url: str) -> bytes | None:
    """Versão pública do download validado de uma URL."""
    return _baixar_url(url)


def baixar_autenticado(file_id: str) -> bytes | None:
    """Versão pública do fallback autenticado por service account."""
    return _baixar_autenticado(file_id)


def baixar_conteudo(file_id: str, preferencia: str = "xlsx") -> bytes | None:
    """Primeiro conteúdo válido entre exportações públicas e Drive autenticado."""
    if not file_id:
        return None
    for url in urls_publicas(file_id, preferencia):
        conteudo = _baixar_url(url)
        if conteudo:
            return conteudo
    return _baixar_autenticado(file_id)


def limpar_cache_producao() -> None:
    """Invalida downloads e planilhas em cache (útil em um botão Recarregar)."""
    _baixar_url.clear()
    _baixar_autenticado.clear()
    _carregar_base_producao.clear()
