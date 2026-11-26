"""Leituras leves usadas pela Visão Geral do portal.

Os módulos das páginas de detalhe (``pages/producao.py``, ``pages/consultivo.py``
e ``pages/indicadores.py``) têm cálculos próprios e mais completos. Aqui a
prioridade é responder rápido ao login com números de prévia; qualquer falha de
fonte é devolvida como ``ok=False`` para que a página mostre um aviso em vez de
quebrar.
"""

from __future__ import annotations

import io
import unicodedata
from typing import Any

import numpy as np
import pandas as pd
import requests
import streamlit as st

from utils._config import (
    ATIVOS_SPREADSHEET_ID,
    PRODUCAO_SPREADSHEET_ID,
    get_indicadores_spreadsheet_id,
)

CONSULTIVO_SPREADSHEET_ID = "1YOWJ0HuGcEP2vJaZwl2kcgrtNgsoMBDs"
META_PRINCIPAL = 400.0
TIMEOUT_REDE = (5, 30)

_IDENTIDADE_COLS = [
    "LOGIN", "MATRICULA", "MATRÍCULA", "RE", "NETSALES", "ID", "CODIGO",
    "CÓDIGO", "USER", "USUARIO", "USUÁRIO", "USERNAME", "CODAUXEQUIP",
    "CODAUXEQUIPE", "CÓDAUXEQUIPE", "COD_AUX_EQUIPE", "LOGIN NETSALES",
    "LOGIN_NETSALES", "LOGIN CONEXÃO DO VENDEDOR", "LOGIN CONEXAO DO VENDEDOR",
    "VENDEDOR", "TECNICO", "TÉCNICO", "NOME", "NOME EQUIPE",
]
_TECNICO_COLS = ["TECNICO", "TÉCNICO", "NOME", "NOME EQUIPE", "VENDEDOR"]
_DATA_COLS = ["DATA", "DATA AGENDAMENTO", "DATA CONCLUSÃO", "DATA_EXECUCAO", "DATE"]
_PONTOS_COLS = ["PONTOS", "PONTO", "PTS", "PONTUACAO", "PREVIA"]


def _norm(valor: Any) -> str:
    """Normaliza texto para comparação tolerante a acento/caixa/separadores."""
    texto = str(valor or "").strip().upper()
    sem_acento = "".join(
        char for char in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(char)
    )
    return (
        sem_acento.replace("_", " ")
        .replace("-", " ")
        .replace(".", " ")
        .strip()
    )


def _encontrar_coluna(df: pd.DataFrame, candidatos: list[str]) -> str | None:
    mapa = {_norm(coluna): coluna for coluna in df.columns}
    for candidato in candidatos:
        encontrada = mapa.get(_norm(candidato))
        if encontrada is not None:
            return str(encontrada)
    return None


def _normalizar_pontos(serie: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(serie):
        return serie.fillna(0.0).astype(float)
    texto = (
        serie.astype(str)
        .str.strip()
        .str.replace(r"[^\d.,\-]", "", regex=True)
    )
    tem_virgula = texto.str.contains(",", regex=False)
    tem_ponto = texto.str.contains(r"\.", regex=True)
    texto = texto.where(
        ~(tem_virgula & tem_ponto),
        texto.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
    )
    texto = texto.where(
        ~tem_virgula | tem_ponto, texto.str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(texto, errors="coerce").fillna(0.0).astype(float)


def _converter_data(serie: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(serie):
        return serie
    texto = serie.astype(str).str.strip()
    resultado = pd.Series(pd.NaT, index=serie.index, dtype="datetime64[ns]")

    iso = texto.str.match(r"^\d{4}-\d{1,2}-\d{1,2}", na=False)
    if bool(iso.any()):
        resultado.loc[iso] = pd.to_datetime(texto.loc[iso], errors="coerce")
    demais = ~iso & ~texto.str.lower().isin(["", "nan", "nat", "none"])
    if bool(demais.any()):
        resultado.loc[demais] = pd.to_datetime(
            texto.loc[demais], errors="coerce", dayfirst=True
        )
    return resultado


@st.cache_data(ttl=600, show_spinner=False)
def _baixar_arquivo(file_id: str, formato: str) -> bytes | None:
    """Baixa XLSX ou CSV exportado publicamente (com fallback de Drive)."""
    if not file_id:
        return None
    urls = (
        [f"https://docs.google.com/spreadsheets/d/{file_id}/export?format={formato}",
         f"https://drive.google.com/uc?export=download&id={file_id}"]
        if formato == "xlsx"
        else [f"https://drive.google.com/uc?export=download&id={file_id}",
              f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv"]
    )
    for url in urls:
        try:
            resposta = requests.get(url, timeout=TIMEOUT_REDE)
        except requests.RequestException:
            continue
        if resposta.status_code == 200 and len(resposta.content) > 100:
            return resposta.content
    return None


def _ler_csv(conteudo: bytes) -> pd.DataFrame:
    for kwargs in (
        {"sep": None, "engine": "python", "encoding": "utf-8"},
        {"sep": ";", "encoding": "latin-1"},
        {"sep": ",", "encoding": "utf-8"},
    ):
        try:
            df = pd.read_csv(io.BytesIO(conteudo), **kwargs)
            if not df.empty and df.shape[1] > 1:
                return df
        except (ValueError, UnicodeDecodeError, pd.errors.ParserError):
            continue
    return pd.DataFrame()


def _filtrar_tecnico(
    df: pd.DataFrame, nome: str, login: str, user: str
) -> pd.DataFrame:
    alvos = {
        _norm(valor)
        for valor in (nome, login, user)
        if valor and str(valor).strip()
    }
    if not alvos:
        return df.iloc[0:0].copy()

    mask = pd.Series(False, index=df.index)
    for coluna in df.columns:
        if _norm(coluna) not in {_norm(c) for c in _IDENTIDADE_COLS}:
            continue
        serie = df[coluna].astype(str).str.strip().str.upper()
        serie = serie.str.replace(r"\.0$", "", regex=True).map(_norm)
        mask |= serie.isin(alvos)
    return df.loc[mask].copy()


def _dias_uteis_restantes(data_referencia: pd.Timestamp) -> int:
    """Dias de segunda a sábado até o fim do mês da data de referência."""
    ref = pd.Timestamp(data_referencia).normalize()
    fim = ref + pd.offsets.MonthEnd(0)
    if ref >= fim:
        return 0
    dias = pd.date_range(ref + pd.Timedelta(days=1), fim, freq="D")
    return int(sum(dia.weekday() < 6 for dia in dias))


# ====================================================
# PRODUÇÃO
# ====================================================
@st.cache_data(ttl=600, show_spinner=False)
def _carregar_producao() -> pd.DataFrame:
    conteudo = _baixar_arquivo(PRODUCAO_SPREADSHEET_ID, "xlsx")
    if conteudo and conteudo.startswith(b"PK"):
        try:
            abas = pd.read_excel(
                io.BytesIO(conteudo), sheet_name=None, engine="openpyxl"
            )
            quadros = []
            for nome_aba in ("prod", "gpon"):
                aba = next(
                    (df for nome, df in abas.items() if _norm(nome) == nome_aba),
                    None,
                )
                if aba is not None and not aba.empty:
                    aba = aba.copy()
                    aba["__origem__"] = nome_aba.upper()
                    quadros.append(aba)
            if quadros:
                return pd.concat(quadros, ignore_index=True)
        except Exception:
            pass

    if conteudo:
        df = _ler_csv(conteudo)
        if not df.empty:
            return df
    return pd.DataFrame()


def resumo_producao(
    nome: str, login: str, user: str, is_admin: bool = False
) -> dict[str, Any]:
    """Prévia de pontos/O.S. do mês da última data encontrada na base."""
    df = _carregar_producao()
    if df.empty:
        return {"ok": False, "motivo": "base de produção indisponível"}

    col_pontos = _encontrar_coluna(df, _PONTOS_COLS)
    col_data = _encontrar_coluna(df, _DATA_COLS)
    if not col_pontos or not col_data:
        return {"ok": False, "motivo": "colunas de pontos/data não encontradas"}

    df = df.copy()
    df[col_pontos] = _normalizar_pontos(df[col_pontos])
    df["_DATA"] = _converter_data(df[col_data])
    datas = df["_DATA"].dropna()
    if datas.empty:
        return {"ok": False, "motivo": "sem datas válidas na produção"}

    referencia = datas.max().normalize()
    dias_normalizados = df["_DATA"].dt.normalize()
    no_mes = df.loc[
        (dias_normalizados >= referencia.replace(day=1))
        & (dias_normalizados <= referencia),
    ].copy()
    if not is_admin:
        no_mes = _filtrar_tecnico(no_mes, nome, login, user)

    col_tec = _encontrar_coluna(no_mes, _TECNICO_COLS)
    pontos = float(no_mes[col_pontos].sum())
    return {
        "ok": True,
        "pontos": pontos,
        "os": int(len(no_mes)),
        "meta": META_PRINCIPAL,
        "progresso": min(100.0, pontos / META_PRINCIPAL * 100.0),
        "dias_restantes": _dias_uteis_restantes(referencia),
        "data_ref": referencia.date(),
        "tecnicos": int(no_mes[col_tec].nunique()) if col_tec else 0,
    }


# ====================================================
# CONSULTIVO
# ====================================================
@st.cache_data(ttl=600, show_spinner=False)
def _carregar_consultivo() -> pd.DataFrame:
    conteudo = _baixar_arquivo(CONSULTIVO_SPREADSHEET_ID, "csv")
    if not conteudo:
        return pd.DataFrame()

    df = _ler_csv(conteudo)
    if df.empty:
        return pd.DataFrame()

    df.columns = [str(coluna).strip().upper() for coluna in df.columns]
    for coluna in ("PLANO TV", "PLANO INTERNET", "OBSERVACAO"):
        if coluna not in df.columns:
            df[coluna] = ""

    def limpo(serie: pd.Series) -> pd.Series:
        return (
            serie.astype(str)
            .str.strip()
            .replace({"-": "", "N/A": "", "nan": "", "None": "", "null": ""})
            .fillna("")
        )

    tv = limpo(df["PLANO TV"]).replace("SERVIÇOS AVANÇADOS", "CLARO TV+ BOX")
    partes = limpo(df["PLANO INTERNET"]).str.split(".", n=1, expand=True)
    internet = partes[0]
    tv = pd.Series(
        np.where(tv != "", tv, partes[1] if partes.shape[1] > 1 else ""),
        index=df.index,
        dtype=str,
    )
    produtos = (
        df["OBSERVACAO"].fillna("").astype(str).str.findall(r"\b\d{9,12}\b").apply(len)
    )
    df["QTDE_CONSULTIVO"] = (tv != "").astype(int) + (internet != "").astype(int)
    df["QTDE_PRODUTOS"] = produtos.astype(int)
    col_data = _encontrar_coluna(df, _DATA_COLS)
    df["_DATA"] = (
        _converter_data(df[col_data]) if col_data else pd.Series(pd.NaT, index=df.index)
    )
    return df


def resumo_consultivo(
    nome: str, login: str, user: str, is_admin: bool = False
) -> dict[str, Any]:
    """Prévia de consultivos e produtos do mês da última data da base."""
    df = _carregar_consultivo()
    if df.empty:
        return {"ok": False, "motivo": "base de consultivo indisponível"}

    datas = df["_DATA"].dropna()
    if datas.empty:
        return {"ok": False, "motivo": "sem datas válidas no consultivo"}

    referencia = datas.max().normalize()
    inicio = referencia.replace(day=1)
    dias_normalizados = df["_DATA"].dt.normalize()
    no_mes = df.loc[
        (dias_normalizados >= inicio) & (dias_normalizados <= referencia)
    ].copy()
    if not is_admin:
        no_mes = _filtrar_tecnico(no_mes, nome, login, user)

    consultivos = int(no_mes["QTDE_CONSULTIVO"].sum())
    produtos = int(no_mes["QTDE_PRODUTOS"].sum())
    return {
        "ok": True,
        "consultivos": consultivos,
        "produtos": produtos,
        "taxa": (produtos / consultivos) if consultivos else 0.0,
        "data_ref": referencia.date(),
        "registros": int(len(no_mes)),
    }


# ====================================================
# INDICADORES (prévia individual)
# ====================================================
_REGRAS_INDICADORES: dict[str, dict[str, Any]] = {
    "Geoloc_Os": {
        "login": ["LOGIN_TEC", "LOGIN", "LOGIN TECNICO"],
        "num": (["MENOR_STATUS_GEOLOC"], {"COM PADRAO"}),
        "den": (["STATUS_GEOLOC"], {"COM PADRAO", "SEM PADRAO"}),
        "meta": 95.0,
    },
    "OS_Digital": {
        "login": ["LOGIN_TEC", "LOGIN"],
        "num": (["GEROU_OS"], {"SIM"}),
        "den": (["STATUS_GEOLOC"], {"COM PADRAO", "SEM PADRAO"}),
        "meta": 95.0,
    },
    "Aderencia_Ura": {
        "login": ["CD_LOGIN_TECNICO", "LOGIN"],
        "num": (["OBJETIVO_URA"], {"SUCESSO"}),
        "meta": 95.0,
    },
    "Nr35": {
        "login": ["LOGIN_FIELD", "LOGIN"],
        "num": (["SUBIU"], None),
        "meta": 95.0,
    },
    "Tec1": {
        "login": ["COD_TECNICO_WFM", "LOGIN"],
        "num": (["DSC_STATUS_NOTA"], {"COM PADRAO"}),
        "meta": 97.0,
    },
    "Baixa_Pda": {
        "login": ["LOGIN_TECNICO_DESPACHADO", "LOGIN"],
        "num": (["STATUS BAIXA"], {"TOA"}),
        "meta": 95.0,
    },
}


@st.cache_data(ttl=3600, show_spinner=False)
def _carregar_indicadores() -> dict[str, pd.DataFrame]:
    conteudo = _baixar_arquivo(get_indicadores_spreadsheet_id(), "xlsx")
    if not conteudo or not conteudo.startswith(b"PK"):
        return {}
    try:
        abas = pd.read_excel(
            io.BytesIO(conteudo), sheet_name=None, engine="openpyxl"
        )
    except Exception:
        return {}
    return {
        str(nome).strip(): df.dropna(how="all").reset_index(drop=True)
        for nome, df in abas.items()
        if isinstance(df, pd.DataFrame) and not df.empty
    }


def resumo_indicadores(login: str, user: str) -> dict[str, Any]:
    """Prévia de quantos indicadores estão na meta para o técnico logado."""
    abas = _carregar_indicadores()
    if not abas:
        return {"ok": False, "motivo": "planilha de indicadores indisponível"}

    alvos = {
        _norm(valor).replace(" ", "")
        for valor in (login, user)
        if valor and str(valor).strip()
    }
    resultados: list[dict[str, Any]] = []
    for nome_aba, regra in _REGRAS_INDICADORES.items():
        aba = next(
            (df for nome, df in abas.items() if _norm(nome) == _norm(nome_aba)),
            None,
        )
        # O.S. Digital é derivada de Geoloc_Os na planilha oficial.
        if aba is None and nome_aba == "OS_Digital":
            aba = next(
                (df for nome, df in abas.items() if _norm(nome) == "GEOLOC OS"),
                None,
            )
        if aba is None:
            resultados.append({"nome": nome_aba, "pct": None, "meta": regra["meta"]})
            continue

        col_login = _encontrar_coluna(aba, regra["login"])
        if not col_login:
            resultados.append({"nome": nome_aba, "pct": None, "meta": regra["meta"]})
            continue
        chaves = (
            aba[col_login]
            .astype(str)
            .str.strip()
            .str.upper()
            .str.replace(r"\.0$", "", regex=True)
            .map(lambda valor: _norm(valor).replace(" ", ""))
        )
        recorte = aba.loc[chaves.isin(alvos)].copy()
        if recorte.empty:
            resultados.append({"nome": nome_aba, "pct": None, "meta": regra["meta"]})
            continue

        col_num, valores_num = regra["num"]
        nome_col_num = _encontrar_coluna(recorte, col_num)
        if not nome_col_num:
            resultados.append({"nome": nome_aba, "pct": None, "meta": regra["meta"]})
            continue
        serie_num = recorte[nome_col_num].map(_norm)

        denominador = len(recorte)
        if "den" in regra:
            col_den, valores_den = regra["den"]
            nome_col_den = _encontrar_coluna(recorte, col_den)
            if not nome_col_den:
                resultados.append({"nome": nome_aba, "pct": None, "meta": regra["meta"]})
                continue
            serie_den = recorte[nome_col_den].map(_norm)
            aptos = serie_den.isin(valores_den)
            denominador = int(aptos.sum())
            atingidos = int((aptos & serie_num.isin(valores_num)).sum())
        elif valores_num is None:
            atingidos = int((serie_num != "").sum())
        else:
            atingidos = int(serie_num.isin(valores_num).sum())

        pct = (atingidos / denominador * 100.0) if denominador else None
        resultados.append(
            {"nome": nome_aba, "pct": pct, "meta": regra["meta"]}
        )

    avaliaveis = [item for item in resultados if item["pct"] is not None]
    na_meta = sum(
        1 for item in avaliaveis if item["pct"] is not None and item["pct"] >= item["meta"]
    )
    return {
        "ok": bool(avaliaveis),
        "na_meta": na_meta,
        "total": len(avaliaveis),
        "itens": resultados,
        "motivo": "" if avaliaveis else "nenhuma aba com registros do login",
    }
