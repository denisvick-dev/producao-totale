"""pages/indicadores.py
====================================================================
Painel de Qualidade e Indicadores Técnicos — Portal TOTALE
====================================================================

Painel **pessoal**: cruza os seis indicadores operacionais (abas de uma
planilha Excel no Google Drive) com a Lista de Ativos e exibe **somente os
registros do técnico logado** — o login da sessão é aplicado como filtro antes
do merge, então nenhuma visão agrega dados de outros profissionais.

1. **Meus Indicadores** — os seis indicadores, evolução diária e comparativo
   dos últimos 7 dias contra os 7 anteriores.
2. **Painel por Indicador** — recorte por período e evolução diária do
   indicador selecionado.

Contrato de dados
-----------------
* Planilha de indicadores (``indicadores_spreadsheet_id`` nos Secrets ou
  ``INDICADORES_SPREADSHEET_ID`` em ``utils/_config.py``) com as abas
  ``Geoloc_Os``, ``Aderencia_Ura``, ``Nr35``, ``Tec1`` e ``Baixa_Pda``.
  ``OS_Digital`` é calculada sobre a base de ``Geoloc_Os`` (coluna ``GEROU_OS``),
  então não precisa de aba própria.
* Planilha Lista de Ativos com, no mínimo, as colunas ``Login`` e ``Tecnico``
  (``Monitor``, ``Base`` e ``Situação`` são opcionais).

Os nomes de colunas de cada aba são resolvidos de forma flexível (acentos,
espaços, ``_`` e ``-`` são ignorados), então pequenas variações de cabeçalho
não quebram o cálculo.
"""

from __future__ import annotations

import io
import logging
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

import numpy as np
import pandas as pd
import requests
import streamlit as st

logger = logging.getLogger(__name__)

# ====================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ====================================================
st.set_page_config(
    page_title="Indicadores | TOTALE",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ====================================================
# 2. PROTEÇÃO DE ACESSO (AUTENTICAÇÃO)
# ====================================================
if not st.session_state.get("authenticated", False):
    st.switch_page("streamlit_app.py")

info_logado = st.session_state.get("user_info", {}) or {}
nome_logado = str(info_logado.get("tecnico", "")).strip().upper()
login_logado = str(info_logado.get("login", "")).strip().upper()
user_logado = str(info_logado.get("user", "")).strip().upper()
perfil_logado = str(info_logado.get("perfil", "")).strip().upper()

# ====================================================
# 3. DESIGN SYSTEM E CONFIGURAÇÃO COMPARTILHADA
# ====================================================
try:
    from components.componentes import (
        aplicar_estilo,
        aplicar_tema_claro,
        injetar_css_menu_nomes,
        render_empty_state,
        render_hero_totale_1,
        render_insight,
        render_kpi,
        render_kpi_sm,
        render_progress_bar,
        render_section_header,
        render_sidebar_portal,
        render_table_html,
    )
    from utils._config import (
        get_ativos_spreadsheet_id,
        get_indicadores_spreadsheet_id,
    )
except ImportError:
    st.error("⚠️ Módulos do design system não encontrados. Verifique `components/` e `utils/`.")
    st.stop()


def configurar_pagina() -> None:
    aplicar_estilo()
    aplicar_tema_claro()
    injetar_css_menu_nomes()


configurar_pagina()

# ====================================================
# 4. CONSTANTES DO PAINEL
# ====================================================
VERSAO_PAGINA = "1.2.0"
DATA_SISTEMA_STR = datetime.now().strftime("%d/%m/%Y às %H:%M")
SEM_VINCULO = "(Sem vínculo)"
MARGEM_CRITICA = 5.0
TIMEOUT_REDE = (5, 60)  # (conexão, leitura)

INDICADORES_ID = get_indicadores_spreadsheet_id()
ATIVOS_ID = get_ativos_spreadsheet_id()

MergeHowType = Literal["left", "right", "outer", "inner", "cross"]
TemaKPIType = Literal["azul", "verde", "vermelho", "laranja", "cinza"]
TipoInsightType = Literal["ok", "info", "alerta", "critico", "acao"]
TipoTrendType = Literal["up", "down", "neutral", "none"]

SHEET_LOGIN_MAPPING: dict[str, str] = {
    "Geoloc_Os": "LOGIN_TEC",
    "Aderencia_Ura": "CD_LOGIN_TECNICO",
    "Nr35": "LOGIN_FIELD",
    "Baixa_Pda": "LOGIN_TECNICO_DESPACHADO",
    "Tec1": "COD_TECNICO_WFM",
    "OS_Digital": "LOGIN_TEC",
}

METAS_POR_ABA: dict[str, float] = {
    "Geoloc_Os": 95.0,
    "OS_Digital": 95.0,
    "Aderencia_Ura": 95.0,
    "Nr35": 95.0,
    "Tec1": 97.0,
    "Baixa_Pda": 95.0,
}

ORDEM_INDICADORES: list[str] = [
    "Geoloc_Os",
    "OS_Digital",
    "Aderencia_Ura",
    "Nr35",
    "Tec1",
    "Baixa_Pda",
]

NOMES_AMIGAVEIS: dict[str, str] = {
    "Geoloc_Os": "Geolocalização",
    "OS_Digital": "O.S. Digital",
    "Aderencia_Ura": "Aderência URA",
    "Nr35": "NR35",
    "Tec1": "TEC1 - Status Nota",
    "Baixa_Pda": "Baixa PDA",
}

NOMES_CURTOS: dict[str, str] = {
    "Geoloc_Os": "Geoloc",
    "OS_Digital": "O.S. Digital",
    "Aderencia_Ura": "URA",
    "Nr35": "NR35",
    "Tec1": "TEC1",
    "Baixa_Pda": "Baixa PDA",
}

NOMES_ICONES: dict[str, str] = {
    "Geoloc_Os": "📍",
    "OS_Digital": "💻",
    "Aderencia_Ura": "📞",
    "Nr35": "🔰",
    "Tec1": "🔧",
    "Baixa_Pda": "📱",
}

GLOSSARIO: dict[str, str] = {
    "Geoloc_Os": "Com Padrão no menor status de geolocalização, sobre Com Padrão + Sem Padrão. Meta 95%.",
    "OS_Digital": "GEROU_OS = Sim, calculado na base de Geolocalização. Meta 95%.",
    "Aderencia_Ura": "OBJETIVO_URA = Sucesso. Meta 95%.",
    "Nr35": "Campo Subiu preenchido. Meta 95%.",
    "Tec1": "DSC_STATUS_NOTA = Com Padrão. Atualizado até a maior DAT_NOTA da base. Meta 97%.",
    "Baixa_Pda": "STATUS BAIXA = TOA. Meta 95%.",
}

#: Coluna de data de cada base. TEC1 usa DAT_NOTA — a data final da base.
COLUNAS_DATA_POR_ABA: dict[str, list[str]] = {
    "Geoloc_Os": ["DATA", "DT", "DATA_OS", "DT_EXECUCAO"],
    "OS_Digital": ["DATA", "DT", "DATA_OS"],
    "Aderencia_Ura": ["DT_AGENDA", "DATA", "DATA_AGENDA"],
    "Nr35": ["DATA", "DT", "DATA_OS"],
    "Tec1": ["DAT_NOTA", "DATA_NOTA", "DT_NOTA", "DATA"],
    "Baixa_Pda": ["DATA_NET", "DATA", "DT_BAIXA", "DATA_BAIXA"],
}

CRITERIOS_POR_ABA: dict[str, dict[str, Any]] = {
    "Geoloc_Os": {
        "colunas_possiveis_num": [
            "MENOR_STATUS_GEOLOC",
            "MENOR STATUS GEOLOC",
            "MENOR_STATUS_GEO",
        ],
        "colunas_possiveis_den": ["STATUS_GEOLOC", "STATUS GEOLOC", "STATUS_GEO"],
        "tipo": "dual_column_ratio",
        "numerador": ["COM PADRAO", "COM PADRÃO", "COMPADRAO"],
        "denominador": [
            "COM PADRAO",
            "COM PADRÃO",
            "COMPADRAO",
            "SEM PADRAO",
            "SEM PADRÃO",
            "SEMPADRAO",
        ],
        "label": "Atingimento Geoloc Com Padrão",
        "nome_atingido": "Com Padrão",
        "nome_nao_atingido": "Sem Padrão",
    },
    "Nr35": {
        "colunas_possiveis": ["SUBIU", "DS_SUBIU", "STATUS_SUBIU", "SUBIU_ESCADA", "FLG_SUBIU"],
        "tipo": "nao_vazio_total",
        "label": "Aderência NR35 (Subiu)",
        "nome_atingido": "Subiu",
        "nome_nao_atingido": "Não Subiu",
    },
    "Aderencia_Ura": {
        "colunas_possiveis": ["OBJETIVO_URA", "OBJETIVO URA", "OBJETIVO", "STATUS_URA"],
        "tipo": "sucesso_total",
        "numerador": ["SUCESSO"],
        "label": "Aderência URA (Sucesso)",
        "nome_atingido": "Sucesso",
        "nome_nao_atingido": "Insucesso",
    },
    "Baixa_Pda": {
        "colunas_possiveis": ["STATUS BAIXA", "STATUS_BAIXA", "STATUSBAIXA", "DS_STATUS_BAIXA"],
        "tipo": "sucesso_total",
        "numerador": ["TOA"],
        "label": "Baixa PDA (TOA)",
        "nome_atingido": "Baixa TOA",
        "nome_nao_atingido": "Outras Baixas",
    },
    "Tec1": {
        "colunas_possiveis": ["DSC_STATUS_NOTA", "DSC STATUS NOTA", "STATUS_NOTA", "STATUS NOTA"],
        "tipo": "sucesso_total",
        "numerador": ["COM PADRAO", "COM PADRÃO", "COMPADRAO"],
        "label": "Status Nota (Com Padrão)",
        "nome_atingido": "Com Padrão",
        "nome_nao_atingido": "Sem Padrão",
    },
    "OS_Digital": {
        "colunas_possiveis": ["GEROU_OS", "GEROU OS", "GEROUOS", "FLG_GEROU_OS", "STATUS_GEROU_OS"],
        "tipo": "sucesso_total",
        "numerador": ["SIM", "S", "1", "TRUE", "SIM."],
        "label": "Gerou OS Digital (Sim)",
        "nome_atingido": "O.S. Gerada",
        "nome_nao_atingido": "Não Gerada",
    },
}

TEMAS_STATUS: dict[str, TemaKPIType] = {
    "CONCLUIDO": "verde",
    "PENDENTE": "laranja",
    "CANCELADO": "vermelho",
}
TREND_STATUS: dict[str, TipoTrendType] = {
    "CONCLUIDO": "up",
    "PENDENTE": "neutral",
    "CANCELADO": "down",
}
# ====================================================
# 5. FUNÇÕES UTILITÁRIAS
# ====================================================
def remover_acentos_e_padronizar(texto: Any) -> str:
    if not isinstance(texto, str):
        texto = str(texto)
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return sem_acento.lower().strip().replace("_", "").replace(" ", "").replace("-", "")


def normalizar_chave(serie: pd.Series) -> pd.Series:
    return serie.astype(str).str.strip().str.upper()


def encontrar_coluna_flexivel(df: pd.DataFrame, nomes_candidatos: list[str]) -> str | None:
    cols_map: dict[str, str] = {remover_acentos_e_padronizar(c): str(c) for c in df.columns}
    for candidato in nomes_candidatos:
        cand_norm = remover_acentos_e_padronizar(candidato)
        if cand_norm in cols_map:
            return cols_map[cand_norm]
    return None


def classificar_status(pct: float, meta: float) -> str:
    if pct >= meta:
        return "CONCLUIDO"
    if pct >= (meta - MARGEM_CRITICA):
        return "PENDENTE"
    return "CANCELADO"


def tema_kpi_status(status: Any) -> TemaKPIType:
    return TEMAS_STATUS.get(str(status), "vermelho")


def trend_de_status(status: Any) -> TipoTrendType:
    return TREND_STATUS.get(str(status), "down")



def rotulo_categoria(valor: Any) -> str:
    if pd.isna(valor):
        return SEM_VINCULO
    texto = str(valor).strip()
    if texto.upper() in {"", "NAN", "NONE", "NAT", "NULL", "-"}:
        return SEM_VINCULO
    return texto


def fmt_pct(valor: float, sinal: bool = False) -> str:
    numero = f"{valor:+.1f}" if sinal else f"{valor:.1f}"
    return numero.replace(".", ",") + "%"


def fmt_pp(valor: float | None) -> str:
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return "—"
    return f"{valor:+.1f}".replace(".", ",") + " p.p."


def fmt_int(valor: Any) -> str:
    try:
        return f"{int(valor):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def parse_data_texto(texto: Any) -> pd.Timestamp | None:
    if texto is None or (isinstance(texto, float) and np.isnan(texto)):
        return None
    parsed = pd.to_datetime(
        str(texto).replace(" às ", " "), dayfirst=True, errors="coerce"
    )
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed)


def atraso_em_dias(texto: str) -> int | None:
    parsed = parse_data_texto(texto)
    if parsed is None:
        return None
    return int((pd.Timestamp.now().normalize() - parsed.normalize()).days)


def _tokens_coluna(nome_coluna: str) -> list[str]:
    bruto = str(nome_coluna).replace("-", " ").replace("_", " ").replace(".", " ")
    return [remover_acentos_e_padronizar(t) for t in bruto.split() if str(t).strip()]


def _coluna_e_data(nome_coluna: str) -> bool:
    """Reconhece DATA, DT_AGENDA, DATA_NET e também DAT_NOTA (TEC1)."""
    tokens = _tokens_coluna(nome_coluna)
    prefixos = ("dt", "data", "date", "dat")
    if any(tok == pref or tok.startswith(pref) for tok in tokens for pref in prefixos):
        return True
    c_norm = remover_acentos_e_padronizar(nome_coluna)
    return any(
        k in c_norm for k in ["created", "fechamento", "execucao", "abertura", "notificacao"]
    )


def _serie_para_datetime(serie: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(serie):
        return pd.to_datetime(serie, errors="coerce")

    try:
        texto = serie.astype(str).str.replace(" às ", " ", regex=False).str.strip()
        try:
            # format="mixed" evita perder linhas quando a coluna tem datas com e
            # sem hora (o pandas inferiria o formato apenas pela primeira linha).
            convertida = pd.to_datetime(
                texto, errors="coerce", dayfirst=True, format="mixed"
            )
        except (ValueError, TypeError):
            convertida = pd.to_datetime(texto, errors="coerce", dayfirst=True)
        if int(convertida.notna().sum()) > 0:
            return convertida
    except (ValueError, TypeError, OverflowError):
        logger.debug("Conversão de datas falhou; seguindo com a série original.", exc_info=True)

    numeric = pd.to_numeric(serie, errors="coerce")
    numeric_ok = numeric.dropna()
    if not numeric_ok.empty and float(numeric_ok.between(20000, 80000).mean()) > 0.8:
        return pd.to_datetime(numeric, unit="D", origin="1899-12-30", errors="coerce")

    return pd.to_datetime(serie, errors="coerce")


def _formatar_data_maxima(max_dt: Any) -> str:
    if hasattr(max_dt, "hour") and (
        int(getattr(max_dt, "hour", 0) or 0) != 0
        or int(getattr(max_dt, "minute", 0) or 0) != 0
    ):
        return max_dt.strftime("%d/%m/%Y às %H:%M")
    if hasattr(max_dt, "strftime"):
        return max_dt.strftime("%d/%m/%Y")
    return str(max_dt)


def maior_texto_data(datas: list[str], fallback: str) -> str:
    validas = [d for d in (parse_data_texto(t) for t in datas) if d is not None]
    if not validas:
        return fallback
    return _formatar_data_maxima(max(validas))


def menor_texto_data(datas: list[str], fallback: str) -> str:
    validas = [d for d in (parse_data_texto(t) for t in datas) if d is not None]
    if not validas:
        return fallback
    return _formatar_data_maxima(min(validas))


def resolver_coluna_data(df: pd.DataFrame, aba: str | None = None) -> str | None:
    if df is None or df.empty:
        return None
    if aba:
        for k_aba, candidatas in COLUNAS_DATA_POR_ABA.items():
            if remover_acentos_e_padronizar(k_aba) == remover_acentos_e_padronizar(aba):
                for cand in candidatas:
                    encontrada = encontrar_coluna_flexivel(df, [cand])
                    if encontrada:
                        return encontrada
                break
    for col in df.columns:
        if _coluna_e_data(str(col)):
            return str(col)
    return None


def anexar_data(df: pd.DataFrame, aba: str | None = None) -> pd.DataFrame:
    out = df.copy()
    if "_DATA" in out.columns:
        return out
    col = resolver_coluna_data(out, aba)
    if col is None:
        out["_DATA"] = pd.NaT
        return out
    out["_DATA"] = _serie_para_datetime(out[col]).dt.normalize()
    return out


def extrair_data_maxima_aba(df: pd.DataFrame | None, aba: str | None = None) -> str | None:
    """Maior data válida da base. No TEC1 a referência é DAT_NOTA, não o relógio."""
    if df is None or df.empty:
        return None

    col = resolver_coluna_data(df, aba)
    if col is None:
        return None

    limite_futuro = pd.Timestamp.now() + pd.Timedelta(days=2)
    limite_passado = pd.Timestamp("2000-01-01")
    try:
        s_dt = _serie_para_datetime(df[col]).dropna()
        s_dt = s_dt[(s_dt <= limite_futuro) & (s_dt >= limite_passado)]
        if s_dt.empty:
            return None
        return _formatar_data_maxima(pd.Timestamp(s_dt.max()))
    except (ValueError, TypeError, AttributeError):
        logger.debug("Detecção de coluna de data falhou para valor.", exc_info=True)
        return None


def limites_periodo(df: pd.DataFrame | None) -> tuple[Any, Any]:
    if df is None or df.empty or "_DATA" not in df.columns:
        return None, None
    validas = df["_DATA"].dropna()
    if validas.empty:
        return None, None
    return validas.min().date(), validas.max().date()


def normalizar_periodo(valor: Any, padrao_ini: Any, padrao_fim: Any) -> tuple[Any, Any]:
    if isinstance(valor, (tuple, list)):
        if len(valor) >= 2 and valor[0] is not None and valor[1] is not None:
            return valor[0], valor[1]
        if len(valor) == 1 and valor[0] is not None:
            return valor[0], valor[0]
        return padrao_ini, padrao_fim
    if valor is None:
        return padrao_ini, padrao_fim
    return valor, valor


def aplicar_periodo(df: pd.DataFrame, inicio: Any, fim: Any) -> pd.DataFrame:
    if df is None or df.empty or "_DATA" not in df.columns or inicio is None or fim is None:
        return df
    if int(df["_DATA"].notna().sum()) == 0:
        return df
    ini = pd.Timestamp(inicio)
    end = pd.Timestamp(fim)
    mascara = df["_DATA"].notna() & (df["_DATA"] >= ini) & (df["_DATA"] <= end)
    return df.loc[mascara].copy()





def gerar_regras_cores(
    df_data: pd.DataFrame,
    col_realizado: str | None = None,
    col_desvio: str | None = None,
    col_meta: str | None = None,
    meta_padrao: float = 95.0,
) -> dict[str, dict[str, str]]:
    """Mapeia valores numéricos para as cores do design system."""
    color_rules: dict[str, dict[str, str]] = {}
    if df_data is None or df_data.empty:
        return color_rules

    if col_realizado and col_realizado in df_data.columns:
        regras_realizado: dict[str, str] = {}
        for _, row in df_data.iterrows():
            val_real = row[col_realizado]
            meta_val = row[col_meta] if (col_meta and col_meta in df_data.columns) else meta_padrao
            try:
                if pd.isna(val_real):
                    continue
                v = float(val_real)
                m = float(meta_val)
                regras_realizado[str(val_real)] = "sucesso" if v >= m else "alerta"
            except (ValueError, TypeError):
                logger.debug("Normalização numérica falhou; usando fallback.", exc_info=True)
        color_rules[col_realizado] = regras_realizado

    if col_desvio and col_desvio in df_data.columns:
        regras_desvio: dict[str, str] = {}
        for _, row in df_data.iterrows():
            val_desv = row[col_desvio]
            try:
                if pd.isna(val_desv):
                    continue
                d = float(val_desv)
                regras_desvio[str(val_desv)] = "sucesso" if d >= 0 else "alerta"
            except (ValueError, TypeError):
                continue
        color_rules[col_desvio] = regras_desvio

    return color_rules


def regras_texto_pp(valores: pd.Series) -> dict[str, str]:
    regras: dict[str, str] = {}
    for valor in valores.dropna().unique().tolist():
        texto = str(valor)
        if texto == "—":
            continue
        regras[texto] = "alerta" if texto.strip().startswith("-") else "sucesso"
    return regras


# ====================================================
# 6. CARREGAMENTO DAS BASES
# ====================================================
def _urls_xlsx(sheet_id: str) -> list[str]:
    return [
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx",
        f"https://drive.google.com/uc?export=download&id={sheet_id}",
    ]


def _baixar_xlsx(sheet_id: str) -> bytes | None:
    """Baixa o XLSX exportado publicamente. Retorna ``None`` se indisponível."""
    for url in _urls_xlsx(sheet_id):
        try:
            resp = requests.get(url, timeout=TIMEOUT_REDE)
        except requests.RequestException:
            logger.warning("Falha ao baixar planilha %s", sheet_id, exc_info=True)
            continue
        if resp.status_code != 200 or len(resp.content) <= 100:
            continue
        # Exportações restritas devolvem HTML (tela de login), não o ZIP do XLSX.
        if not resp.content.startswith(b"PK"):
            continue
        return resp.content
    return None


def _abrir_planilha_autenticada(sheet_id: str) -> Any:
    """Fallback autenticado via service account (``gcp_service_account``)."""
    try:
        from utils._config import get_credentials_dict

        credenciais = get_credentials_dict()
        if not credenciais:
            return None
        import gspread

        cliente = gspread.service_account_from_dict(credenciais)
        return cliente.open_by_key(sheet_id)
    except Exception:
        logger.warning("Não foi possível abrir a planilha %s via gspread.", sheet_id, exc_info=True)
        return None


def _normalizar_abas(abas: dict[str, Any]) -> dict[str, pd.DataFrame]:
    normalizadas: dict[str, pd.DataFrame] = {}
    for nome, df in abas.items():
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            continue
        limpo = df.dropna(how="all").dropna(axis=1, how="all").copy()
        limpo.columns = [str(c).strip() for c in limpo.columns]
        if limpo.empty:
            continue
        normalizadas[str(nome).strip()] = limpo.reset_index(drop=True)
    return normalizadas


@st.cache_data(ttl=3600, show_spinner=False)
def carregar_workbook_indicadores(sheet_id: str) -> dict[str, pd.DataFrame] | None:
    """Carrega todas as abas da planilha de indicadores (Drive → gspread)."""
    if not sheet_id:
        return None

    conteudo = _baixar_xlsx(sheet_id)
    if conteudo:
        try:
            abas = pd.read_excel(io.BytesIO(conteudo), sheet_name=None, engine="openpyxl")
        except Exception:
            logger.warning("XLSX inválido para %s; tentando gspread.", sheet_id, exc_info=True)
            abas = {}
        normalizadas = _normalizar_abas(abas)
        if normalizadas:
            return normalizadas

    planilha = _abrir_planilha_autenticada(sheet_id)
    if planilha is None:
        return None

    normalizadas = {}
    for worksheet in planilha.worksheets():
        try:
            registros = worksheet.get_all_records()
        except Exception:
            logger.warning("Aba %s ilegível.", worksheet.title, exc_info=True)
            continue
        if registros:
            normalizadas[worksheet.title.strip()] = pd.DataFrame(registros)
    return normalizadas or None


@st.cache_data(ttl=3600, show_spinner=False)
def carregar_lista_ativos(sheet_id: str) -> pd.DataFrame | None:
    """Carrega a Lista de Ativos (primeira aba com dados)."""
    if not sheet_id:
        return None

    conteudo = _baixar_xlsx(sheet_id)
    if conteudo:
        try:
            abas = pd.read_excel(io.BytesIO(conteudo), sheet_name=None, engine="openpyxl")
        except Exception:
            logger.warning("XLSX de ativos inválido; tentando gspread.", exc_info=True)
            abas = {}
        for df_aba in abas.values():
            if df_aba is None or df_aba.empty or df_aba.shape[1] <= 1:
                continue
            df_aba = df_aba.dropna(how="all").dropna(axis=1, how="all").copy()
            df_aba.columns = [str(c).strip() for c in df_aba.columns]
            if not df_aba.empty:
                return df_aba.reset_index(drop=True)

    planilha = _abrir_planilha_autenticada(sheet_id)
    if planilha is None:
        return None
    try:
        registros = planilha.sheet1.get_all_records()
    except Exception:
        logger.warning("Lista de ativos ilegível via gspread.", exc_info=True)
        return None
    return pd.DataFrame(registros) if registros else None


def localizar_aba(abas: dict[str, pd.DataFrame], chave: str) -> pd.DataFrame | None:
    alvo = remover_acentos_e_padronizar(chave)
    for nome, df in abas.items():
        if remover_acentos_e_padronizar(nome) == alvo:
            return df
    return None


def resolver_chave_excel(sheet_name: str, df_sheet: pd.DataFrame) -> str | None:
    sheet_name_norm = remover_acentos_e_padronizar(sheet_name)

    for aba_config, col_esperada in SHEET_LOGIN_MAPPING.items():
        if remover_acentos_e_padronizar(aba_config) == sheet_name_norm:
            col_encontrada = encontrar_coluna_flexivel(df_sheet, [col_esperada, aba_config])
            if col_encontrada:
                return col_encontrada

    todas_cols: list[str] = list(SHEET_LOGIN_MAPPING.values()) + list(SHEET_LOGIN_MAPPING.keys())
    col_encontrada = encontrar_coluna_flexivel(df_sheet, todas_cols)
    if col_encontrada:
        return col_encontrada

    for col in df_sheet.columns:
        c_norm = remover_acentos_e_padronizar(col)
        if any(termo in c_norm for termo in ["login", "codtec", "cdtec", "matricula", "tecnico"]):
            return str(col)
    return None


# ====================================================
# 7. CRUZAMENTO COM A LISTA DE ATIVOS
# ====================================================
def montar_contexto_ativos(
    df_ativos: pd.DataFrame | None,
) -> tuple[ContextoAtivos | None, str]:
    """Detecta as colunas da Lista de Ativos e monta o contexto de cruzamento."""
    if df_ativos is None or df_ativos.empty:
        return None, "planilha não retornou dados."

    col_login = encontrar_coluna_flexivel(
        df_ativos, ["Login", "LOGIN", "Cd_Login", "LOGIN_TEC"]
    )
    if not col_login:
        return None, "coluna 'Login' não encontrada."

    return (
        ContextoAtivos(
            df=df_ativos,
            col_login=col_login,
            col_user=encontrar_coluna_flexivel(
                df_ativos, ["User", "Usuário", "Usuario", "LOGIN_USER", "USERNAME"]
            ),
            col_tecnico=encontrar_coluna_flexivel(
                df_ativos, ["Tecnico", "Técnico", "TECNICO", "Nome_Tecnico"]
            ),
            col_monitor=encontrar_coluna_flexivel(
                df_ativos, ["Monitor", "MONITOR", "Nome_Monitor"]
            ),
            col_base=encontrar_coluna_flexivel(
                df_ativos, ["Base", "BASE", "Filial", "Unidade"]
            ),
            col_situacao=encontrar_coluna_flexivel(
                df_ativos, ["Situação", "Situacao", "SITUACAO", "Status_Tecnico"]
            ),
        ),
        "",
    )


@dataclass(frozen=True)
class ContextoAtivos:
    df: pd.DataFrame
    col_login: str
    col_user: str | None = None
    col_tecnico: str | None = None
    col_monitor: str | None = None
    col_base: str | None = None
    col_situacao: str | None = None

    @property
    def colunas_importar(self) -> list[str]:
        return [
            c
            for c in (self.col_tecnico, self.col_monitor, self.col_base, self.col_situacao)
            if c is not None
        ]


def merge_aba(
    df_sheet: pd.DataFrame,
    ativos: ContextoAtivos,
    chave_excel: str,
    how: MergeHowType = "left",
) -> pd.DataFrame:
    cols_right: list[str] = [ativos.col_login] + ativos.colunas_importar

    left = df_sheet.copy()
    right = ativos.df[cols_right].drop_duplicates(subset=[ativos.col_login]).copy()

    left["_KEY"] = normalizar_chave(left[chave_excel])
    right["_KEY"] = normalizar_chave(right[ativos.col_login])
    right = right.drop(columns=[ativos.col_login])

    merged = pd.merge(left, right, on="_KEY", how=how, suffixes=("", "_ativos"))

    renomear: dict[str, str] = {}
    for origem, destino in (
        (ativos.col_tecnico, "Tecnico"),
        (ativos.col_monitor, "Monitor"),
        (ativos.col_base, "Base"),
        (ativos.col_situacao, "Situacao"),
    ):
        if origem and origem in merged.columns and origem != destino:
            renomear[origem] = destino
    if renomear:
        merged = merged.rename(columns=renomear)

    # Garante a existência das colunas canônicas mesmo quando opcionais.
    for canonica in ("Tecnico", "Monitor", "Base", "Situacao"):
        if canonica not in merged.columns:
            merged[canonica] = SEM_VINCULO
    return merged.drop(columns=["_KEY"])


#: Abas físicas da planilha. O.S. Digital é calculada sobre Geoloc_Os (GEROU_OS).
ABAS_FISICAS: list[str] = [k for k in ORDEM_INDICADORES if k != "OS_Digital"]


def _filtrar_por_login(
    df_sheet: pd.DataFrame, coluna_login: str, logins: set[str] | None
) -> pd.DataFrame:
    """Mantém apenas as linhas do login logado. Sem logins, não retorna nada."""
    if logins is None:
        return df_sheet
    if not logins or coluna_login not in df_sheet.columns:
        return df_sheet.iloc[0:0].copy()
    chaves = normalizar_chave(df_sheet[coluna_login])
    alvos = {str(valor).strip().upper() for valor in logins if str(valor).strip()}
    return df_sheet.loc[chaves.isin(alvos)].copy()


def montar_resultados(
    excel_sheets: dict[str, pd.DataFrame],
    ativos: ContextoAtivos,
    logins_permitidos: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    resultados: dict[str, dict[str, Any]] = {}
    for aba in ABAS_FISICAS:
        df_sheet = localizar_aba(excel_sheets, aba)
        if df_sheet is None:
            resultados[aba] = {
                "df": None,
                "erro": "Aba não encontrada no arquivo de indicadores.",
                "chave_excel": None,
            }
            continue
        chave_excel = resolver_chave_excel(aba, df_sheet)
        if not chave_excel:
            resultados[aba] = {
                "df": None,
                "erro": "Coluna de login não detectada.",
                "chave_excel": None,
            }
            continue
        try:
            df_sheet_logado = _filtrar_por_login(df_sheet, chave_excel, logins_permitidos)
            df_merged = merge_aba(df_sheet_logado, ativos, chave_excel, how="left")
            resultados[aba] = {
                "df": anexar_data(df_merged, aba),
                "erro": None,
                "chave_excel": chave_excel,
            }
        except Exception as exc:  # pragma: no cover - depende da base externa
            logger.exception("Falha ao mesclar a aba %s.", aba)
            resultados[aba] = {"df": None, "erro": str(exc), "chave_excel": chave_excel}

    geoloc = resultados.get("Geoloc_Os", {})
    if geoloc.get("df") is not None:
        resultados["OS_Digital"] = {
            "df": geoloc["df"],
            "erro": None,
            "chave_excel": geoloc.get("chave_excel"),
        }
    else:
        resultados["OS_Digital"] = {
            "df": None,
            "erro": "Depende da aba Geoloc_Os, que não pôde ser processada.",
            "chave_excel": None,
        }
    return resultados


@st.cache_resource(ttl=3600, show_spinner=False)
def preparar_dados_indicadores(
    sheet_id: str,
    ativos_sheet_id: str,
    logins: tuple[str, ...],
) -> tuple[dict[str, dict[str, Any]] | None, ContextoAtivos | None, str]:
    """Carrega, cruza e mantém o recorte do técnico em cache entre reruns.

    O cruzamento das seis abas com a Lista de Ativos é a etapa mais cara da
    página. Sem cache ele era refeito a cada interação (inclusive ao trocar
    apenas o período de um gráfico). ``cache_resource`` devolve os mesmos
    objetos, sem copiar DataFrames a cada rerun.
    """
    excel = carregar_workbook_indicadores(sheet_id)
    if not excel:
        return (
            None,
            None,
            "Planilha de indicadores indisponível. Verifique o ID configurado, "
            "a conectividade e a permissão de leitura (compartilhamento público "
            "ou service account).",
        )

    df_ativos = carregar_lista_ativos(ativos_sheet_id)
    ativos_ctx, erro_ativos = montar_contexto_ativos(df_ativos)
    if ativos_ctx is None:
        return None, None, f"Lista de Ativos: {erro_ativos}"

    resultados = montar_resultados(excel, ativos_ctx, logins_permitidos=set(logins))
    return resultados, ativos_ctx, ""


def dataframe_indicador(resultados: dict[str, dict[str, Any]], chave: str) -> pd.DataFrame | None:
    if chave == "OS_Digital":
        return resultados.get("Geoloc_Os", {}).get("df")
    return resultados.get(chave, {}).get("df")


@dataclass(frozen=True)
class IdentidadeTecnico:
    nome: str
    login: str
    monitor: str = SEM_VINCULO
    base: str = SEM_VINCULO
    situacao: str = SEM_VINCULO
    encontrado: bool = False


def _valor_cadastral(linha: pd.Series, coluna: str | None) -> str:
    if not coluna or coluna not in linha.index:
        return SEM_VINCULO
    return rotulo_categoria(linha[coluna])


def resolver_identidade(
    ativos: ContextoAtivos,
    login: str,
    user: str,
    nome: str,
) -> IdentidadeTecnico:
    """Localiza o técnico logado na Lista de Ativos pelo login, user ou nome."""
    df = ativos.df
    logins = {str(valor).strip().upper() for valor in (login, user) if str(valor).strip()}
    linha: pd.Series | None = None

    for coluna in (ativos.col_login, ativos.col_user):
        if linha is not None or not coluna or coluna not in df.columns or not logins:
            continue
        mascara = normalizar_chave(df[coluna]).isin(logins)
        if bool(mascara.any()):
            linha = df.loc[mascara].iloc[0]

    if linha is None and ativos.col_tecnico and nome and ativos.col_tecnico in df.columns:
        alvo = remover_acentos_e_padronizar(nome)
        mascara = df[ativos.col_tecnico].map(remover_acentos_e_padronizar) == alvo
        if bool(mascara.any()):
            linha = df.loc[mascara].iloc[0]

    if linha is not None:
        nome_cadastro = _valor_cadastral(linha, ativos.col_tecnico)
        if nome_cadastro == SEM_VINCULO:
            nome_cadastro = nome or login or user
        return IdentidadeTecnico(
            nome=nome_cadastro,
            login=login or user,
            monitor=_valor_cadastral(linha, ativos.col_monitor),
            base=_valor_cadastral(linha, ativos.col_base),
            situacao=_valor_cadastral(linha, ativos.col_situacao),
            encontrado=True,
        )

    return IdentidadeTecnico(
        nome=nome or login or user,
        login=login or user,
        encontrado=False,
    )



# ====================================================
# 8. MOTOR DE CÁLCULO
# ====================================================
def _norm_regra(valores: list[Any]) -> set[str]:
    return {remover_acentos_e_padronizar(v) for v in valores}


def _serie_norm_regra(serie: pd.Series) -> pd.Series:
    return serie.map(remover_acentos_e_padronizar)


def calcular_aderencia_criterio(
    df: pd.DataFrame, aba: str
) -> tuple[str | None, pd.Series | None, dict[str, Any]]:
    regra: dict[str, Any] | None = None
    for k_aba, v_regra in CRITERIOS_POR_ABA.items():
        if remover_acentos_e_padronizar(k_aba) == remover_acentos_e_padronizar(aba):
            regra = v_regra
            break
    if not regra or df is None or df.empty:
        return None, None, {"erro": "Sem regra ou sem dados para o recorte."}

    tipo = regra["tipo"]
    if tipo == "dual_column_ratio":
        col_num = encontrar_coluna_flexivel(df, regra["colunas_possiveis_num"])
        col_den = encontrar_coluna_flexivel(df, regra["colunas_possiveis_den"])
        if not col_num or not col_den:
            return None, None, {"erro": "Colunas Geoloc não encontradas."}

        serie_num = _serie_norm_regra(df[col_num])
        serie_den = _serie_norm_regra(df[col_den])
        num_norm = _norm_regra(regra["numerador"])
        den_norm = _norm_regra(regra["denominador"])

        serie_score = pd.Series(np.nan, index=df.index, dtype=float)
        mask_den = serie_den.isin(den_norm)
        mask_num = serie_num.isin(num_norm)
        serie_score.loc[mask_den & mask_num] = 1.0
        serie_score.loc[mask_den & ~mask_num] = 0.0
        coluna = col_den
    elif tipo == "nao_vazio_total":
        col_avaliada = encontrar_coluna_flexivel(df, regra["colunas_possiveis"])
        if not col_avaliada:
            return None, None, {"erro": "Coluna não encontrada."}
        serie_raw = df[col_avaliada]
        serie_str = serie_raw.astype(str).str.strip().str.upper()
        invalidos = ["", "NAN", "NAT", "NULL", "NONE", "-"]
        mask_vazio = serie_raw.isna() | serie_str.isin(invalidos)
        serie_score = pd.Series(0.0, index=df.index, dtype=float)
        serie_score.loc[~mask_vazio] = 1.0
        coluna = col_avaliada
    else:
        col_avaliada = encontrar_coluna_flexivel(df, regra["colunas_possiveis"])
        if not col_avaliada:
            return None, None, {"erro": "Coluna não encontrada."}
        serie_norm = _serie_norm_regra(df[col_avaliada])
        num_norm = _norm_regra(regra["numerador"])
        serie_score = pd.Series(0.0, index=df.index, dtype=float)
        serie_score.loc[serie_norm.isin(num_norm)] = 1.0
        coluna = col_avaliada

    qtd_num = int((serie_score == 1.0).sum())
    qtd_den = int(serie_score.notna().sum()) if tipo == "dual_column_ratio" else len(df)
    pct = (qtd_num / qtd_den * 100.0) if qtd_den > 0 else 0.0
    return (
        coluna,
        serie_score,
        {
            "coluna": coluna,
            "label": regra["label"],
            "nome_atingido": regra.get("nome_atingido", "Atingidos"),
            "nome_nao_atingido": regra.get("nome_nao_atingido", "Não Atingidos"),
            "numerador": qtd_num,
            "denominador": qtd_den,
            "pct": pct,
        },
    )


def com_score(df: pd.DataFrame, aba: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    work = df.copy()
    _, serie, info = calcular_aderencia_criterio(work, aba)
    if serie is not None:
        work["_SCORE"] = serie
    return work, info



def serie_diaria(df: pd.DataFrame) -> pd.DataFrame:
    vazio = pd.DataFrame(columns=["Data", "Realizado", "Total", "Atingidos"])
    if df is None or df.empty or "_DATA" not in df.columns or "_SCORE" not in df.columns:
        return vazio
    valid = df[df["_DATA"].notna() & df["_SCORE"].notna()].copy()
    if valid.empty:
        return vazio
    valid["_DIA"] = valid["_DATA"].dt.normalize()
    out = (
        valid.groupby("_DIA", as_index=False)
        .agg(Atingidos=("_SCORE", "sum"), Total=("_SCORE", "count"))
        .rename(columns={"_DIA": "Data"})
    )
    out["Realizado"] = out["Atingidos"] / out["Total"] * 100.0
    return out.sort_values("Data")


def comparativo_7d(df: pd.DataFrame) -> dict[str, Any]:
    vazio: dict[str, Any] = {
        "pct": None,
        "pct_ant": None,
        "var": None,
        "n": 0,
        "n_ant": 0,
        "ini": None,
        "fim": None,
    }
    if df is None or df.empty or "_DATA" not in df.columns or "_SCORE" not in df.columns:
        return vazio
    datas = df["_DATA"].dropna()
    if datas.empty:
        return vazio
    fim = pd.Timestamp(datas.max()).normalize()
    ini = fim - pd.Timedelta(days=6)
    ant_fim = ini - pd.Timedelta(days=1)
    ant_ini = ant_fim - pd.Timedelta(days=6)

    def pack(inicio: pd.Timestamp, final: pd.Timestamp) -> tuple[float | None, int]:
        sub = df[
            df["_DATA"].notna()
            & df["_SCORE"].notna()
            & (df["_DATA"] >= inicio)
            & (df["_DATA"] <= final)
        ]
        den = int(sub["_SCORE"].count())
        if den == 0:
            return None, 0
        return float(sub["_SCORE"].sum()) / den * 100.0, den

    pct, n = pack(ini, fim)
    pct_ant, n_ant = pack(ant_ini, ant_fim)
    var = (pct - pct_ant) if pct is not None and pct_ant is not None else None
    return {
        "pct": pct,
        "pct_ant": pct_ant,
        "var": var,
        "n": n,
        "n_ant": n_ant,
        "ini": ini,
        "fim": fim,
        "ant_ini": ant_ini,
        "ant_fim": ant_fim,
    }




def escala_percentual(valores: list[float], metas: list[float]) -> tuple[float, float]:
    numeros = [float(v) for v in valores if v is not None and not pd.isna(v)]
    metas_ok = [float(m) for m in metas if m is not None]
    if not numeros and not metas_ok:
        return 0.0, 100.0
    baixo = min(numeros + metas_ok) - 3.0
    alto = max(numeros + metas_ok + [100.0])
    return max(0.0, baixo), min(100.0, max(alto, baixo + 5.0))

# ====================================================
# 9. APRESENTAÇÃO
# ====================================================
def publicar_insight(texto: str, titulo: str, tipo: TipoInsightType = "alerta") -> None:
    render_insight(f"**{titulo}** — {texto}", tipo)


def render_cabecalho(titulo: str, subtitulo: str, icone: str) -> None:
    render_section_header(icon=icone, title=titulo)
    if subtitulo:
        st.caption(subtitulo)


def render_evolucao(df_daily: pd.DataFrame, meta: float, titulo: str) -> None:
    if df_daily is None or df_daily.empty or len(df_daily) < 2:
        st.caption("Período curto demais para mostrar tendência.")
        return
    st.markdown(f"#### {titulo}")
    st.caption(
        f"Linha de meta em {meta:.1f}%. A escala aproxima o desvio — não começa em zero para não esconder o gap."
    )
    plot = df_daily.copy()
    plot["Data"] = pd.to_datetime(plot["Data"])
    y_min, y_max = escala_percentual(plot["Realizado"].tolist(), [meta])
    try:
        import altair as alt

        linha = (
            alt.Chart(plot)
            .mark_line(point=True, color="#12304A")
            .encode(
                x=alt.X("Data:T", title="Data", axis=alt.Axis(format="%d/%m")),
                y=alt.Y(
                    "Realizado:Q",
                    title="Aderência (%)",
                    scale=alt.Scale(domain=[y_min, y_max]),
                ),
                tooltip=[
                    alt.Tooltip("Data:T", format="%d/%m/%Y", title="Data"),
                    alt.Tooltip("Realizado:Q", format=".1f", title="Realizado (%)"),
                    alt.Tooltip("Total:Q", format=",.0f", title="Volume"),
                ],
            )
        )
        regra = (
            alt.Chart(pd.DataFrame({"Meta": [meta]}))
            .mark_rule(strokeDash=[6, 4], color="#B42318")
            .encode(y="Meta:Q")
        )
        st.altair_chart(
            (linha + regra)
            .properties(height=280)
            .configure(background="transparent")
            .configure_view(strokeWidth=0),
            width="stretch",
        )
    except Exception:  # noqa: BLE001 - fallback para o gráfico nativo
        st.line_chart(plot.set_index("Data")[["Realizado"]], height=280)


def render_evolucao_consolidada(long_df: pd.DataFrame, metas: list[float]) -> None:
    if long_df is None or long_df.empty or long_df["Data"].nunique() < 2:
        st.caption("Período curto demais para a tendência consolidada.")
        return
    st.markdown("#### 📈 Evolução diária dos meus indicadores")
    st.caption(
        "Referência visual em 95%. TEC1 tem meta de 97% — o valor da meta vai no detalhe de cada ponto. "
        "Escala aproximada para evidenciar desvio."
    )
    plot = long_df.copy()
    plot["Data"] = pd.to_datetime(plot["Data"])
    y_min, y_max = escala_percentual(plot["Realizado"].tolist(), metas or [95.0])
    try:
        import altair as alt

        linhas = (
            alt.Chart(plot)
            .mark_line(point=True)
            .encode(
                x=alt.X("Data:T", title="Data", axis=alt.Axis(format="%d/%m")),
                y=alt.Y(
                    "Realizado:Q",
                    title="Aderência (%)",
                    scale=alt.Scale(domain=[y_min, y_max]),
                ),
                color=alt.Color("Indicador:N", title=""),
                tooltip=[
                    alt.Tooltip("Data:T", format="%d/%m/%Y"),
                    alt.Tooltip("Indicador:N"),
                    alt.Tooltip("Realizado:Q", format=".1f", title="Realizado (%)"),
                    alt.Tooltip("Meta:Q", format=".0f", title="Meta (%)"),
                    alt.Tooltip("Total:Q", format=",.0f", title="Volume"),
                ],
            )
        )
        regra = (
            alt.Chart(pd.DataFrame({"Meta": [95.0]}))
            .mark_rule(strokeDash=[6, 4], color="#B42318")
            .encode(y="Meta:Q")
        )
        st.altair_chart(
            (linhas + regra)
            .properties(height=320)
            .configure(background="transparent")
            .configure_view(strokeWidth=0)
            .configure_legend(orient="bottom"),
            width="stretch",
        )
    except Exception:  # noqa: BLE001 - fallback para o gráfico nativo
        pivot = plot.pivot_table(
            index="Data", columns="Indicador", values="Realizado", aggfunc="mean"
        )
        st.line_chart(pivot, height=320)


def texto_resumo_pessoal(dados: list[dict[str, Any]]) -> tuple[str, TipoInsightType]:
    if not dados:
        return "Nenhum indicador com registros seus neste recorte.", "alerta"

    total = len(dados)
    fora = [d for d in dados if d["Status"] != "CONCLUIDO"]
    if not fora:
        texto = f"Você está na meta nos {total} indicadores avaliados neste recorte."
        tipo: TipoInsightType = "ok"
    else:
        pior = min(fora, key=lambda d: d["Desvio (%)"])
        criticos = [d for d in fora if d["Status"] == "CANCELADO"]
        margem = [d for d in fora if d["Status"] == "PENDENTE"]
        texto = f"Você está na meta em {total - len(fora)} de {total} indicadores."
        if criticos:
            nomes = ", ".join(NOMES_CURTOS.get(d["_chave"], d["Indicador"]) for d in criticos)
            texto += f" Fora do objetivo: {nomes}."
        if margem:
            nomes = ", ".join(NOMES_CURTOS.get(d["_chave"], d["Indicador"]) for d in margem)
            texto += f" Na margem crítica (até 5 p.p. abaixo): {nomes}."
        texto += (
            f" Seu maior gap é {NOMES_CURTOS.get(pior['_chave'], pior['Indicador'])} "
            f"({fmt_pp(pior['Desvio (%)'])})."
        )
        tipo = "critico" if criticos else "alerta"

    quedas = [d for d in dados if d.get("_var7") is not None and d["_var7"] <= -1.0]
    if quedas:
        queda = min(quedas, key=lambda d: d["_var7"])
        texto += (
            f" Atenção à queda recente em {NOMES_CURTOS.get(queda['_chave'], queda['Indicador'])}: "
            f"{fmt_pp(queda['_var7'])} nos últimos 7 dias."
        )
        tipo = "alerta"
    return texto, tipo


def texto_insight_indicador_pessoal(
    nome: str,
    pct: float,
    meta: float,
    janela: dict[str, Any],
    volume: int,
) -> tuple[str, TipoInsightType]:
    status = classificar_status(pct, meta)
    if status == "CONCLUIDO":
        texto = f"Você está na meta em {nome}: {fmt_pct(pct)} contra {fmt_pct(meta)}."
        tipo: TipoInsightType = "ok"
    elif status == "PENDENTE":
        texto = (
            f"{nome} está na margem crítica: {fmt_pct(pct)} contra a meta de {fmt_pct(meta)} "
            f"({fmt_pp(pct - meta)})."
        )
        tipo = "alerta"
    else:
        texto = (
            f"{nome} está fora do objetivo: {fmt_pct(pct)} contra a meta de {fmt_pct(meta)} "
            f"({fmt_pp(pct - meta)})."
        )
        tipo = "critico"

    if janela.get("var") is not None and janela.get("ini") is not None:
        texto += (
            f" Últimos 7 dias ({janela['ini'].strftime('%d/%m')} a {janela['fim'].strftime('%d/%m')}): "
            f"{fmt_pct(janela['pct'])}, contra {fmt_pct(janela['pct_ant'])} nos 7 dias anteriores "
            f"({fmt_pp(janela['var'])})."
        )
        if janela["var"] <= -1:
            tipo = "alerta"

    if 0 < volume < 30:
        texto += " Volume baixo no recorte — leia o percentual com cautela."
        tipo = "alerta"
    return texto, tipo


# 10. VISÃO CONSOLIDADA PESSOAL
# ====================================================
def renderizar_meus_indicadores(
    resultados: dict[str, dict[str, Any]], identidade: IdentidadeTecnico
) -> None:
    frames: list[pd.DataFrame] = []
    vistos: set[int] = set()
    for chave in ORDEM_INDICADORES:
        df_chave = dataframe_indicador(resultados, chave)
        if df_chave is None or df_chave.empty or id(df_chave) in vistos:
            continue
        vistos.add(id(df_chave))
        frames.append(df_chave if "_DATA" in df_chave.columns else anexar_data(df_chave, chave))

    dmin, dmax = None, None
    for df_tmp in frames:
        ini, fim = limites_periodo(df_tmp)
        if ini and (dmin is None or ini < dmin):
            dmin = ini
        if fim and (dmax is None or fim > dmax):
            dmax = fim

    datas_fonte: list[str] = []
    for chave in ORDEM_INDICADORES:
        dt = extrair_data_maxima_aba(dataframe_indicador(resultados, chave), chave)
        if dt:
            datas_fonte.append(dt)
    data_final = maior_texto_data(datas_fonte, DATA_SISTEMA_STR)
    atraso = atraso_em_dias(data_final)

    render_cabecalho(
        "Visão Consolidada dos Meus Indicadores",
        f"Seus seis indicadores em uma leitura. 🕒 Data final da base: {data_final}",
        "🎯",
    )
    st.caption(
        f"Olá, {identidade.nome.title()}. O detalhe operacional de cada indicador "
        "fica nas abas abaixo."
    )

    ini_sel, fim_sel = dmin, dmax
    if dmin and dmax:
        c1, c2 = st.columns([1.2, 2])
        with c1:
            periodo = st.date_input(
                "📅 Período",
                value=(dmin, dmax),
                min_value=dmin,
                max_value=dmax,
                key="meus_indicadores_periodo",
            )
            ini_sel, fim_sel = normalizar_periodo(periodo, dmin, dmax)
        with c2:
            st.caption(
                f"Recorte: {pd.Timestamp(ini_sel).strftime('%d/%m/%Y')} a "
                f"{pd.Timestamp(fim_sel).strftime('%d/%m/%Y')}."
            )
            st.caption("“Atualizado até” é a data final da base, não o fim do filtro.")

    dados: list[dict[str, Any]] = []
    serie_longa: list[pd.DataFrame] = []

    for chave in ORDEM_INDICADORES:
        df_fonte = dataframe_indicador(resultados, chave)
        if df_fonte is None or df_fonte.empty:
            continue
        dt_fonte = extrair_data_maxima_aba(df_fonte, chave) or data_final
        df_calc = aplicar_periodo(df_fonte, ini_sel, fim_sel)
        if df_calc.empty:
            continue
        work, info = com_score(df_calc, chave)
        if "pct" not in info or int(info.get("denominador", 0)) == 0:
            continue

        meta = float(METAS_POR_ABA.get(chave, 95.0))
        janela = comparativo_7d(work)
        status = classificar_status(float(info["pct"]), meta)
        dados.append(
            {
                "_chave": chave,
                "_var7": janela.get("var"),
                "Indicador": f"{NOMES_ICONES.get(chave, '')} {NOMES_AMIGAVEIS.get(chave, chave)}",
                "Realizado (%)": float(info["pct"]),
                "Meta (%)": meta,
                "Desvio (%)": float(info["pct"]) - meta,
                "7 dias (%)": janela.get("pct"),
                "Var. 7d": fmt_pp(janela.get("var")),
                "Atingidos": int(info["numerador"]),
                "Total": int(info["denominador"]),
                "Atualizado até": dt_fonte,
                "Status": status,
            }
        )

        diaria = serie_diaria(work)
        if not diaria.empty:
            diaria = diaria.copy()
            diaria["Indicador"] = NOMES_CURTOS.get(chave, chave)
            diaria["Meta"] = meta
            serie_longa.append(diaria)

    if not dados:
        render_empty_state(
            tipo="dados",
            descricao="Você não tem registros avaliáveis neste período.",
        )
        return

    texto, tipo_insight = texto_resumo_pessoal(dados)
    if atraso is not None and atraso >= 2:
        texto += f" A fonte está {atraso} dias atrás da data de hoje ({data_final})."
        tipo_insight = "alerta"
    publicar_insight(texto, titulo="Seu resumo", tipo=tipo_insight)

    na_meta = sum(1 for d in dados if d["Status"] == "CONCLUIDO")
    pior = min(dados, key=lambda d: d["Desvio (%)"])
    tema_meta: TemaKPIType = (
        "verde"
        if na_meta == len(dados)
        else ("laranja" if na_meta >= len(dados) - 1 else "vermelho")
    )
    trend_meta: TipoTrendType = "up" if na_meta == len(dados) else "down"

    s1, s2, s3 = st.columns(3)
    render_kpi(
        s1,
        "Indicadores na meta",
        f"{na_meta} de {len(dados)}",
        sub="Seu contrato de qualidade no recorte",
        tema=tema_meta,
        delta=f"{na_meta - len(dados):+d}" if na_meta < len(dados) else "OK",
        delta_tipo=trend_meta,
        colorida=True,
    )
    render_kpi(
        s2,
        "Seu maior gap",
        fmt_pp(pior["Desvio (%)"]),
        sub=str(pior["Indicador"]),
        tema=tema_kpi_status(pior["Status"]),
        delta=f"{pior['Realizado (%)']:.1f}%",
        delta_tipo=trend_de_status(pior["Status"]),
        colorida=True,
    )
    tema_fonte: TemaKPIType = (
        "verde"
        if atraso is not None and atraso <= 1
        else ("laranja" if atraso == 2 else "vermelho")
    )
    trend_fonte: TipoTrendType = "up" if atraso is not None and atraso <= 1 else "down"
    render_kpi(
        s3,
        "Data final da base",
        data_final,
        sub=(
            "Há 0 dias"
            if atraso == 0
            else (f"Há {atraso} dias" if atraso is not None else "Fonte")
        ),
        tema=tema_fonte,
        delta="em dia" if atraso is not None and atraso <= 1 else "atrasada",
        delta_tipo=trend_fonte,
        colorida=True,
    )
    st.caption(
        "O delta colorido de cada indicador é o seu desvio contra a meta. "
        "“7d” compara seus últimos 7 dias com os 7 dias anteriores."
    )

    for inicio in range(0, len(dados), 3):
        grupo = dados[inicio : inicio + 3]
        cols = st.columns(3)
        for col, dado in zip(cols, grupo):
            with col:
                sub = (
                    f"Meta: {dado['Meta (%)']:.0f}% | "
                    f"{fmt_int(dado['Atingidos'])}/{fmt_int(dado['Total'])} | "
                    f"7d: {fmt_pp(dado['_var7'])}"
                )
                render_kpi(
                    col,
                    str(dado["Indicador"]),
                    f"{dado['Realizado (%)']:.1f}%",
                    sub=sub,
                    tema=tema_kpi_status(dado["Status"]),
                    delta=f"{dado['Desvio (%)']:+.1f}%",
                    delta_tipo=trend_de_status(dado["Status"]),
                    colorida=True,
                )
                render_progress_bar(
                    valor=dado["Realizado (%)"],
                    maximo=100.0,
                    mostrar_valor=False,
                    tema=tema_kpi_status(dado["Status"]),
                    altura="pequeno",
                )

    st.markdown("---")
    if serie_longa:
        render_evolucao_consolidada(
            pd.concat(serie_longa, ignore_index=True),
            [float(d["Meta (%)"]) for d in dados],
        )
        st.markdown("---")

    df_exec = pd.DataFrame(dados)
    df_exec["7 dias"] = df_exec["7 dias (%)"].apply(
        lambda v: "—" if v is None or pd.isna(v) else f"{float(v):.1f}%"
    )
    color_rules_exec = gerar_regras_cores(
        df_exec,
        col_realizado="Realizado (%)",
        col_desvio="Desvio (%)",
        col_meta="Meta (%)",
    )
    color_rules_exec["Var. 7d"] = regras_texto_pp(df_exec["Var. 7d"])
    regras_7d: dict[str, str] = {}
    for _, row in df_exec.iterrows():
        texto_7d = str(row["7 dias"])
        if texto_7d == "—":
            continue
        try:
            regras_7d[texto_7d] = (
                "sucesso" if float(row["7 dias (%)"]) >= float(row["Meta (%)"]) else "alerta"
            )
        except (TypeError, ValueError):
            logger.debug("Valor inválido ignorado na consolidação.", exc_info=True)
            continue
    color_rules_exec["7 dias"] = regras_7d
    render_table_html(
        df_exec,
        titulo="Tabela consolidada dos meus indicadores",
        colunas=[
            "Indicador",
            "Realizado (%)",
            "Meta (%)",
            "Desvio (%)",
            "7 dias",
            "Var. 7d",
            "Atingidos",
            "Total",
            "Atualizado até",
            "Status",
        ],
        alinhamentos={
            "Indicador": "left",
            "Realizado (%)": "right",
            "Meta (%)": "right",
            "Desvio (%)": "right",
            "7 dias": "right",
            "Var. 7d": "right",
            "Atingidos": "right",
            "Total": "right",
            "Atualizado até": "center",
            "Status": "center",
        },
        fmt={
            "Realizado (%)": "{:.1f}%",
            "Meta (%)": "{:.1f}%",
            "Desvio (%)": "{:+.1f}%",
            "Atingidos": "{:,}",
            "Total": "{:,}",
        },
        color_rules=color_rules_exec,
        mostrar_data=False,
    )


# ====================================================
# 11. PAINEL PESSOAL DO INDICADOR
# ====================================================
def renderizar_painel_pessoal(
    df_indicador: pd.DataFrame | None, nome_kpi: str, identidade: IdentidadeTecnico
) -> None:
    nome_amigavel = NOMES_AMIGAVEIS.get(nome_kpi, nome_kpi)
    icone = NOMES_ICONES.get(nome_kpi, "📋")
    meta_kpi = float(METAS_POR_ABA.get(nome_kpi, 95.0))
    data_final = extrair_data_maxima_aba(df_indicador, nome_kpi) or DATA_SISTEMA_STR
    complemento = (
        " (data final da base)" if remover_acentos_e_padronizar(nome_kpi) == "tec1" else ""
    )

    render_cabecalho(
        f"Meu painel — {nome_amigavel}",
        f"{GLOSSARIO.get(nome_kpi, nome_amigavel)} • 🕒 Atualizado até: {data_final}{complemento}",
        icone,
    )

    if df_indicador is None or df_indicador.empty:
        render_empty_state(
            tipo="dados",
            descricao=(
                f"Você não tem registros de {nome_amigavel} na base. "
                "Se isso não for esperado, confira seu login na Lista de Ativos."
            ),
        )
        return

    base_df = (
        df_indicador if "_DATA" in df_indicador.columns else anexar_data(df_indicador, nome_kpi)
    )
    dmin, dmax = limites_periodo(base_df)

    st.markdown("### 🔍 Meu recorte")
    ini_sel, fim_sel = dmin, dmax
    if dmin and dmax:
        periodo = st.date_input(
            "📅 Período",
            value=(dmin, dmax),
            min_value=dmin,
            max_value=dmax,
            key=f"periodo_pessoal_{nome_kpi}",
        )
        ini_sel, fim_sel = normalizar_periodo(periodo, dmin, dmax)
    df_periodo = aplicar_periodo(base_df, ini_sel, fim_sel)

    if df_periodo.empty:
        render_empty_state(
            tipo="dados",
            descricao="Você não tem registros neste período. Amplie o intervalo.",
        )
        return

    work, info = com_score(df_periodo, nome_kpi)
    if "erro" in info or "pct" not in info:
        st.error(f"❌ {info.get('erro', 'Não foi possível calcular o indicador.')}")
        return
    if int(info.get("denominador", 0)) == 0:
        render_empty_state(
            tipo="dados",
            descricao="O recorte não tem registros avaliáveis para este indicador.",
        )
        return

    pct = float(info["pct"])
    total = int(info["denominador"])
    atingidos = int(info["numerador"])
    nao_atingidos = total - atingidos
    desvio = pct - meta_kpi
    status = classificar_status(pct, meta_kpi)
    janela = comparativo_7d(work)

    if ini_sel and fim_sel:
        st.caption(
            f"Recorte: {pd.Timestamp(ini_sel).strftime('%d/%m/%Y')} a "
            f"{pd.Timestamp(fim_sel).strftime('%d/%m/%Y')} • "
            f"{fmt_int(total)} registros seus avaliados."
        )

    st.markdown("### 🎯 Resultado do meu recorte")
    k1, k2, k3, k4, k5 = st.columns(5)
    render_kpi(
        k1,
        "Minha aderência",
        f"{pct:.1f}%",
        sub=f"{info.get('label', nome_amigavel)} | 7d: {fmt_pp(janela.get('var'))}",
        tema=tema_kpi_status(status),
        delta=f"{desvio:+.1f}%",
        delta_tipo=trend_de_status(status),
        colorida=True,
    )
    render_kpi_sm(
        k2,
        info.get("nome_atingido", "Atingidos"),
        fmt_int(atingidos),
        sub="Registros conformes",
        tema="verde",
    )
    render_kpi_sm(
        k3,
        info.get("nome_nao_atingido", "Não Atingidos"),
        fmt_int(nao_atingidos),
        sub="Fora do padrão",
        tema="vermelho",
    )
    render_kpi_sm(
        k4,
        "Volume avaliado",
        fmt_int(total),
        sub="Seus registros no recorte",
        tema="azul",
    )
    render_kpi_sm(
        k5,
        "Meta",
        f"{meta_kpi:.0f}%",
        sub="Objetivo do indicador",
        tema="cinza",
    )
    render_progress_bar(
        valor=pct,
        maximo=100.0,
        label=f"Sua aderência contra a meta de {meta_kpi:.1f}%",
        tema=tema_kpi_status(status),
    )

    texto, tipo_insight = texto_insight_indicador_pessoal(
        nome_amigavel, pct, meta_kpi, janela, total
    )
    publicar_insight(texto, titulo="O que fazer com este número", tipo=tipo_insight)

    st.markdown("---")
    render_evolucao(serie_diaria(work), meta_kpi, "📈 Minha evolução diária vs meta")


# ====================================================
# 12. CHIPS DE CONTEXTO DO TOPO
# ====================================================
def render_chips(chips: dict[str, str]) -> None:
    itens = "".join(
        f'<div style="display:flex;flex-direction:column;gap:2px;padding:8px 14px;'
        f'background:#FFFFFF;border:1px solid #D9E2E8;border-left:3px solid #C66A16;'
        f'border-radius:6px;min-width:150px;">'
        f'<span style="font-family:IBM Plex Sans,sans-serif;font-size:9px;'
        f'font-weight:800;letter-spacing:0.08em;text-transform:uppercase;'
        f'color:#6B7C89;">{chave}</span>'
        f'<span style="font-family:IBM Plex Sans,sans-serif;font-size:13px;'
        f'font-weight:700;color:#172B3A;">{valor}</span></div>'
        for chave, valor in chips.items()
        if valor
    )
    if not itens:
        return
    st.markdown(
        f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin:0 0 18px 0;">{itens}</div>',
        unsafe_allow_html=True,
    )


# ====================================================
# 13. EXECUÇÃO PRINCIPAL
# ====================================================
render_sidebar_portal(
    nome=nome_logado,
    login=login_logado,
    user=user_logado,
    pagina_logout="streamlit_app.py",
    perfil=perfil_logado,
)

render_hero_totale_1(
    titulo="Meus Indicadores de Qualidade",
    subtitulo=(
        "Seus seis indicadores operacionais e a evolução diária — somente os "
        "seus registros."
    ),
    icone="monitoring",
    badge=f"PAINEL PESSOAL v{VERSAO_PAGINA}",
    usar_material=True,
)

if not (login_logado or user_logado):
    render_empty_state(
        tipo="erro",
        titulo="Sessão sem identificação de técnico",
        descricao=(
            "O usuário logado não tem login/user na sessão. Entre novamente no portal "
            "para carregar seus indicadores."
        ),
    )
    st.stop()

if not INDICADORES_ID:
    render_insight(
        "**Configuração pendente** — informe o ID da planilha de indicadores nos Secrets "
        "do Streamlit com a chave `indicadores_spreadsheet_id` ou em "
        "`INDICADORES_SPREADSHEET_ID` (utils/_config.py). A planilha deve conter as abas "
        "Geoloc_Os, Aderencia_Ura, Nr35, Tec1 e Baixa_Pda (O.S. Digital é derivada "
        "de Geoloc_Os).",
        tipo="alerta",
    )
    st.stop()

logins_permitidos = tuple(
    sorted({valor for valor in (login_logado, user_logado) if valor})
)

with st.spinner("⏳ Processando e cruzando suas bases..."):
    resultados, ativos_ctx, erro_carga = preparar_dados_indicadores(
        INDICADORES_ID, ATIVOS_ID, logins_permitidos
    )

if resultados is None or ativos_ctx is None:
    render_empty_state(
        tipo="erro",
        titulo="Erro ao carregar as bases de indicadores",
        descricao=(
            f"{erro_carga} Sem a Lista de Ativos não é possível vincular técnico, "
            "monitor e base aos seus indicadores."
        ),
    )
    st.stop()

identidade = resolver_identidade(ativos_ctx, login_logado, user_logado, nome_logado)

frames_pessoais: list[pd.DataFrame] = []
vistos: set[int] = set()
for chave in ORDEM_INDICADORES:
    df_pessoal = dataframe_indicador(resultados, chave)
    if df_pessoal is None or df_pessoal.empty or id(df_pessoal) in vistos:
        continue
    vistos.add(id(df_pessoal))
    frames_pessoais.append(
        df_pessoal if "_DATA" in df_pessoal.columns else anexar_data(df_pessoal, chave)
    )

datas_fonte: list[str] = []
datas_inicio: list[str] = []
for chave in ORDEM_INDICADORES:
    df_pessoal = dataframe_indicador(resultados, chave)
    if df_pessoal is None or df_pessoal.empty:
        continue
    dt_m = extrair_data_maxima_aba(df_pessoal, chave)
    if dt_m:
        datas_fonte.append(dt_m)
    if "_DATA" in df_pessoal.columns and df_pessoal["_DATA"].notna().any():
        datas_inicio.append(pd.Timestamp(df_pessoal["_DATA"].min()).strftime("%d/%m/%Y"))

data_max_global_str = maior_texto_data(datas_fonte, DATA_SISTEMA_STR)
data_min_global_str = menor_texto_data(datas_inicio, "—")
atraso_global = atraso_em_dias(data_max_global_str)

with st.sidebar:
    st.divider()
    st.markdown("#### 👤 Meu cadastro")
    st.markdown(f"**Técnico:** {identidade.nome.title()}")
    st.markdown(f"**Login:** `{identidade.login or '—'}`")
    st.markdown(f"**Base:** {identidade.base}")
    st.markdown(f"**Monitor:** {identidade.monitor}")
    st.markdown(f"**Situação:** {identidade.situacao}")
    if not identidade.encontrado:
        st.caption("⚠️ Seu login não foi localizado na Lista de Ativos.")

    st.divider()
    st.markdown("#### 🔗 Fonte de dados")
    st.caption(f"Sua cobertura na fonte: {data_min_global_str} a {data_max_global_str}")
    if atraso_global is not None and atraso_global >= 2:
        st.caption(f"⚠️ Fonte {atraso_global} dias atrás da data de hoje.")
    if st.button("🔄 Atualizar bases", width="stretch", key="indicadores_refresh"):
        preparar_dados_indicadores.clear()
        carregar_workbook_indicadores.clear()
        carregar_lista_ativos.clear()
        st.rerun()

    st.divider()
    st.markdown("#### 🎨 Legenda")
    st.markdown("🟢 **CONCLUÍDO**: meta atingida")
    st.markdown("🟡 **PENDENTE**: margem crítica (até 5 p.p. abaixo)")
    st.markdown("🔴 **CANCELADO**: fora do objetivo")
    st.caption("O delta colorido mede desvio da meta, não a variação de 7 dias.")

    st.divider()
    st.markdown("#### 🎯 Metas")
    for aba_name_side in ORDEM_INDICADORES:
        st.markdown(
            f"- **{NOMES_AMIGAVEIS.get(aba_name_side, aba_name_side)}**: "
            f"{METAS_POR_ABA[aba_name_side]:.0f}%"
        )

    with st.expander("Como cada indicador é calculado"):
        for aba_name_side in ORDEM_INDICADORES:
            st.markdown(f"**{NOMES_AMIGAVEIS[aba_name_side]}**")
            st.caption(GLOSSARIO[aba_name_side])

render_chips(
    {
        "Técnico": identidade.nome.title(),
        "Base": identidade.base,
        "Monitor": identidade.monitor,
        "Minha cobertura": (
            f"{data_min_global_str} a {data_max_global_str}" if datas_fonte else ""
        ),
    }
)

if not frames_pessoais:
    render_empty_state(
        tipo="dados",
        titulo="Nenhum registro seu encontrado",
        descricao=(
            f"Não localizamos registros com o login **{identidade.login or login_logado}** "
            "nas abas de indicadores. Confira seu cadastro na Lista de Ativos ou fale "
            "com o seu monitor."
        ),
    )
    st.stop()

abas_exibicao: list[tuple[str, pd.DataFrame | None]] = []
for chave in ORDEM_INDICADORES:
    df_chave = dataframe_indicador(resultados, chave)
    if df_chave is not None:
        abas_exibicao.append((chave, df_chave))

if not abas_exibicao:
    render_empty_state(
        tipo="erro",
        titulo="Processamento inválido",
        descricao="Nenhuma das abas de indicadores pôde ser mapeada para o seu login.",
    )
    st.stop()

nomes_tabs: list[str] = ["🎯 Meus Indicadores"] + [
    f"{NOMES_ICONES.get(chave, '📋')} {NOMES_AMIGAVEIS.get(chave, chave)}"
    for chave, _ in abas_exibicao
]

render_cabecalho(
    "Detalhe por Indicador",
    "Selecione uma aba para ver seu recorte e sua evolução diária.",
    "📊",
)
tabs = st.tabs(nomes_tabs)

with tabs[0]:
    renderizar_meus_indicadores(resultados, identidade)

for idx, (chave_kpi, df_kpi) in enumerate(abas_exibicao):
    with tabs[idx + 1]:
        renderizar_painel_pessoal(df_kpi, chave_kpi, identidade)

st.markdown("---")
st.caption(
    f"Portal TOTALE · Painel pessoal de indicadores v{VERSAO_PAGINA} · "
    f"{identidade.nome.title()} · Fonte: planilha de indicadores + Lista de Ativos"
)
