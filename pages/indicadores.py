"""pages/indicadores.py
====================================================================
Painel de Qualidade e Indicadores Técnicos — Portal TOTALE
====================================================================

Cruzamento de seis indicadores operacionais (abas de uma planilha Excel no
Google Drive) com a Lista de Ativos, com três leituras:

1. **Visão Consolidada** — os seis indicadores, evolução, matriz por base e
   comparativo dos últimos 7 dias contra os 7 anteriores.
2. **Visão por Técnico** — matriz Técnico × Indicador e drill-down individual
   com plano de ação (registros fora do padrão).
3. **Painéis por Indicador** — recorte por período/base/monitor/técnico,
   ranking, bottom 10, consolidado por monitor e exportações.

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

_ADMIN_IDENTIFIERS = {
    "ADMIN",
    "ADM",
    "ADMINISTRADOR",
    "GESTOR",
    "MANAGER",
    "SUPERVISOR",
    "COORDENADOR",
}
IS_ADMIN = perfil_logado in _ADMIN_IDENTIFIERS or login_logado.startswith("ADM")

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


def injetar_css_navegacao() -> None:
    """Mantém o menu lateral consistente com as demais páginas do portal."""
    esconder_admin = (
        ""
        if IS_ADMIN
        else '[data-testid="stSidebarNav"] a[href*="admin"] { display: none !important; }'
    )
    css = """
    <style>
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] ul {
        display: flex !important;
        flex-direction: column !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:has(a[href*="producao"]) { order: 1 !important; }
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:has(a[href*="consultivo"]) { order: 2 !important; }
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:has(a[href*="indicadores"]) { order: 3 !important; }
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:has(a[href*="admin"]) { order: 4 !important; }
    [data-testid="stSidebarNav"] a[href*="producao"] span,
    [data-testid="stSidebarNav"] a[href*="consultivo"] span { font-size: 0 !important; }
    [data-testid="stSidebarNav"] a[href*="producao"] span::before {
        content: "📊 Produtividade"; font-size: 14px !important;
        font-weight: 700 !important; color: #1E293B !important;
    }
    [data-testid="stSidebarNav"] a[href*="consultivo"] span::before {
        content: "🗣️ Consultivo"; font-size: 14px !important;
        font-weight: 700 !important; color: #1E293B !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
        background: #F8FAFC !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 8px !important;
        margin: 4px 16px !important;
        padding: 10px 14px !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"],
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background: linear-gradient(90deg, #FFF7ED 0%, #FFEDD5 100%) !important;
        border: 1px solid #F97316 !important;
        border-left: 4px solid #F97316 !important;
    }
    __ADMIN__
    </style>
    """
    st.markdown(css.replace("__ADMIN__", esconder_admin), unsafe_allow_html=True)


def configurar_pagina() -> None:
    aplicar_estilo()
    aplicar_tema_claro()
    injetar_css_navegacao()
    injetar_css_menu_nomes({"indicadores": "⚡ Indicadores"})


configurar_pagina()

# ====================================================
# 4. CONSTANTES DO PAINEL
# ====================================================
VERSAO_PAGINA = "1.0.0"
DATA_SISTEMA_STR = datetime.now().strftime("%d/%m/%Y às %H:%M")
SEM_VINCULO = "(Sem vínculo)"
MARGEM_CRITICA = 5.0
MIN_OS_BOTTOM = 3
TIMEOUT_REDE = 60

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

MAPA_PERFORMANCE: dict[str, str | None] = {
    "Todos": None,
    "🟢 Meta Atingida": "CONCLUIDO",
    "🟡 Próximo à Meta": "PENDENTE",
    "🔴 Abaixo da Meta": "CANCELADO",
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
COLUNAS_AUXILIARES = {"_SCORE", "_DATA", "_KEY", "_DIA", "Base_lbl"}


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


def nome_curto(chave: Any, fallback: Any = "") -> str:
    if isinstance(chave, str) and chave in NOMES_CURTOS:
        return NOMES_CURTOS[chave]
    if fallback is None:
        return "" if chave is None else str(chave)
    return str(fallback)


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
        convertida = pd.to_datetime(
            serie.astype(str).str.replace(" às ", " ", regex=False).str.strip(),
            errors="coerce",
            dayfirst=True,
        )
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


def aplicar_filtro_base(df: pd.DataFrame, selecionada: str) -> pd.DataFrame:
    if df is None or selecionada in (None, "Todas") or "Base" not in df.columns:
        return df
    rotulo = df["Base"].map(rotulo_categoria)
    return df.loc[rotulo == selecionada].copy()


def aplicar_filtro_lista(
    df: pd.DataFrame, coluna: str | None, selecionados: list[str]
) -> pd.DataFrame:
    if df is None or not selecionados or not coluna or coluna not in df.columns:
        return df
    rotulo = df[coluna].map(rotulo_categoria)
    return df.loc[rotulo.isin(selecionados)].copy()


def opcoes_categoria(serie: pd.Series) -> list[str]:
    rotulos = serie.map(rotulo_categoria)
    nomes = sorted({r for r in rotulos.unique().tolist() if r != SEM_VINCULO})
    if (rotulos == SEM_VINCULO).any():
        return [SEM_VINCULO] + nomes
    return nomes


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
@dataclass(frozen=True)
class ContextoAtivos:
    df: pd.DataFrame
    col_login: str
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


def montar_resultados(
    excel_sheets: dict[str, pd.DataFrame],
    ativos: ContextoAtivos,
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
            df_merged = merge_aba(df_sheet, ativos, chave_excel, how="left")
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


def dataframe_indicador(resultados: dict[str, dict[str, Any]], chave: str) -> pd.DataFrame | None:
    if chave == "OS_Digital":
        return resultados.get("Geoloc_Os", {}).get("df")
    return resultados.get(chave, {}).get("df")


def resumo_vinculo(df: pd.DataFrame | None) -> dict[str, Any]:
    if df is None or df.empty or "Tecnico" not in df.columns:
        return {"total": 0, "sem": 0, "pct": 0.0}
    rotulo = df["Tecnico"].map(rotulo_categoria)
    sem = int((rotulo == SEM_VINCULO).sum())
    total = len(df)
    pct = ((total - sem) / total * 100.0) if total else 0.0
    return {"total": total, "sem": sem, "pct": pct}


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


def agregar_grupo(
    df: pd.DataFrame,
    col_grupo: str,
    meta: float,
    col_tec: str | None = None,
    com_situacao: bool = False,
    com_monitor: bool = False,
) -> pd.DataFrame:
    if df is None or df.empty or "_SCORE" not in df.columns or col_grupo not in df.columns:
        return pd.DataFrame()

    tmp = df.copy()
    tmp["_GRUPO"] = tmp[col_grupo].map(rotulo_categoria)
    grouped = tmp.groupby("_GRUPO", dropna=False)
    out = pd.DataFrame(
        {
            "Total_OS": grouped["_SCORE"].count(),
            "Atingidos": grouped["_SCORE"].sum(),
        }
    ).reset_index()
    if col_tec and col_tec in tmp.columns:
        qtd = grouped[col_tec].nunique().rename("Qtd_Tecnicos").reset_index()
        out = out.merge(qtd, on="_GRUPO", how="left")
    if com_situacao and "Situacao" in tmp.columns:
        sit = grouped["Situacao"].first().rename("Situacao").reset_index()
        out = out.merge(sit, on="_GRUPO", how="left")
    if com_monitor and "Monitor" in tmp.columns:
        mon = grouped["Monitor"].first().rename("Monitor").reset_index()
        out = out.merge(mon, on="_GRUPO", how="left")

    out = out.rename(columns={"_GRUPO": col_grupo})
    out["Atingidos"] = pd.to_numeric(out["Atingidos"], errors="coerce").fillna(0).astype(int)
    out["Total_OS"] = pd.to_numeric(out["Total_OS"], errors="coerce").fillna(0).astype(int)
    out = out[out["Total_OS"] > 0].copy()
    if out.empty:
        return out
    out["Nao_Atingidos"] = out["Total_OS"] - out["Atingidos"]
    out["Realizado"] = out["Atingidos"] / out["Total_OS"] * 100.0
    out["Meta"] = meta
    out["Desvio"] = out["Realizado"] - meta
    out["Status"] = out["Realizado"].apply(lambda v: classificar_status(float(v), meta))
    return out.sort_values(["Realizado", "Total_OS"], ascending=[False, False])


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


def concentracao_nao_conformes(
    df: pd.DataFrame, col_tec: str | None, n: int = 10
) -> dict[str, Any]:
    vazio = {"qtd": 0, "top": 0, "n": 0, "pct_top": 0.0, "nomes": []}
    if (
        df is None
        or df.empty
        or not col_tec
        or col_tec not in df.columns
        or "_SCORE" not in df.columns
    ):
        return vazio
    fora = df[df["_SCORE"] == 0]
    if fora.empty:
        return vazio
    por = fora.groupby(fora[col_tec].map(rotulo_categoria)).size().sort_values(ascending=False)
    por = por[por.index != SEM_VINCULO]
    if por.empty:
        return {"qtd": len(fora), "top": 0, "n": 0, "pct_top": 0.0, "nomes": []}
    top = int(por.head(n).sum())
    total = int(por.sum())
    return {
        "qtd": len(fora),
        "top": top,
        "n": int(min(n, len(por))),
        "pct_top": (top / total * 100.0) if total else 0.0,
        "nomes": [str(x) for x in por.head(3).index.tolist()],
    }


def filtrar_status(df: pd.DataFrame, selecao: str) -> pd.DataFrame:
    status = MAPA_PERFORMANCE.get(selecao)
    if not status or df is None or df.empty or "Status" not in df.columns:
        return df
    return df[df["Status"] == status].copy()


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


def render_barras_ranking(df: pd.DataFrame, col_nome: str, meta: float) -> None:
    if df is None or df.empty or col_nome not in df.columns:
        return
    plot = df[[col_nome, "Realizado"]].copy()
    ordem = plot[col_nome].astype(str).tolist()
    plot[col_nome] = ordem
    y_min, y_max = escala_percentual(plot["Realizado"].tolist(), [meta])
    try:
        import altair as alt

        barras = (
            alt.Chart(plot)
            .mark_bar()
            .encode(
                x=alt.X(f"{col_nome}:N", sort=ordem, title=""),
                y=alt.Y(
                    "Realizado:Q",
                    title="Aderência (%)",
                    scale=alt.Scale(domain=[y_min, y_max]),
                ),
                color=alt.condition(
                    alt.datum.Realizado >= meta,
                    alt.value("#16745B"),
                    alt.value("#B42318"),
                ),
                tooltip=[
                    alt.Tooltip(f"{col_nome}:N", title="Técnico"),
                    alt.Tooltip("Realizado:Q", format=".1f", title="Realizado (%)"),
                ],
            )
        )
        regra = (
            alt.Chart(pd.DataFrame({"Meta": [meta]}))
            .mark_rule(strokeDash=[6, 4], color="#C66A16")
            .encode(y="Meta:Q")
        )
        st.altair_chart(
            (barras + regra)
            .properties(height=240)
            .configure(background="transparent")
            .configure_view(strokeWidth=0),
            width="stretch",
        )
    except Exception:  # noqa: BLE001 - fallback para o gráfico nativo
        st.bar_chart(plot.set_index(col_nome)[["Realizado"]], height=240)


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
    st.markdown("#### 📈 Evolução diária dos indicadores")
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


def render_ranking_tabela(
    df: pd.DataFrame,
    col_nome: str,
    meta: float,
    titulo: str | None = None,
    height: int | None = None,
    com_qtd_tec: bool = False,
    com_nao: bool = False,
    com_situacao: bool = False,
) -> None:
    if df is None or df.empty:
        st.caption("Nenhuma linha neste recorte.")
        return

    df = df.copy()
    if com_situacao and "Situacao" in df.columns:
        df["Situacao"] = df["Situacao"].map(rotulo_categoria)

    colunas = [col_nome]
    if com_situacao and "Situacao" in df.columns:
        colunas.append("Situacao")
    colunas.extend(["Total_OS", "Atingidos"])
    if com_nao and "Nao_Atingidos" in df.columns:
        colunas.append("Nao_Atingidos")
    if com_qtd_tec and "Qtd_Tecnicos" in df.columns:
        colunas.append("Qtd_Tecnicos")
    colunas.extend(["Realizado", "Desvio", "Status"])

    alinhamentos = {c: "right" for c in colunas}
    alinhamentos[col_nome] = "left"
    alinhamentos["Status"] = "center"
    if "Situacao" in alinhamentos:
        alinhamentos["Situacao"] = "left"

    fmt = {
        "Total_OS": "{:,}",
        "Atingidos": "{:,}",
        "Nao_Atingidos": "{:,}",
        "Qtd_Tecnicos": "{:,}",
        "Realizado": "{:.1f}%",
        "Desvio": "{:+.1f}%",
    }
    kwargs: dict[str, Any] = {
        "colunas": colunas,
        "alinhamentos": alinhamentos,
        "fmt": fmt,
        "color_rules": gerar_regras_cores(
            df, col_realizado="Realizado", col_desvio="Desvio", meta_padrao=meta
        ),
        "mostrar_data": False,
    }
    if titulo:
        kwargs["titulo"] = titulo
    if height:
        kwargs["height"] = height
    render_table_html(df, **kwargs)


def download_csv(df: pd.DataFrame, rotulo: str, nome_arquivo: str, key: str) -> None:
    if df is None or df.empty:
        st.caption(f"Sem linhas para {rotulo.lower()}.")
        return
    cols = [c for c in df.columns if c not in COLUNAS_AUXILIARES]
    csv = df[cols].to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
    st.download_button(
        rotulo,
        data=csv,
        file_name=nome_arquivo,
        mime="text/csv",
        key=key,
    )


def texto_insight_executivo(
    dados: list[dict[str, Any]], vinculo: dict[str, Any]
) -> tuple[str, TipoInsightType]:
    if not dados:
        return "Nenhum indicador disponível neste recorte.", "alerta"

    fora = [d for d in dados if d["Status"] != "CONCLUIDO"]
    tipo: TipoInsightType
    if not fora:
        texto = f"Os {len(dados)} indicadores estão na meta neste recorte."
        tipo = "ok"
    else:
        pior = min(fora, key=lambda d: d["Desvio (%)"])
        criticos = [d for d in fora if d["Status"] == "CANCELADO"]
        margem = [d for d in fora if d["Status"] == "PENDENTE"]
        partes: list[str] = []
        if criticos:
            nomes = ", ".join(nome_curto(d.get("_chave"), d.get("Indicador")) for d in criticos)
            partes.append(f"{len(criticos)} fora do objetivo ({nomes})")
        if margem:
            nomes = ", ".join(nome_curto(d.get("_chave"), d.get("Indicador")) for d in margem)
            partes.append(f"{len(margem)} na margem crítica, até 5 p.p. abaixo ({nomes})")
        texto = f"{' e '.join(partes)}. Maior gap: {pior['Indicador']} ({fmt_pp(pior['Desvio (%)'])})."
        tipo = "critico" if criticos else "alerta"

    quedas = [d for d in dados if d.get("_var7") is not None and d["_var7"] <= -1.0]
    if quedas:
        queda = min(quedas, key=lambda d: d["_var7"])
        texto += (
            f" Queda recente mais forte: {queda['Indicador']} "
            f"({fmt_pp(queda['_var7'])} nos últimos 7 dias)."
        )
        tipo = "alerta"

    if vinculo.get("total", 0) and vinculo.get("pct", 100) < 98:
        texto += (
            f" Vínculo de logins em {fmt_pct(vinculo['pct'])}: "
            f"{fmt_int(vinculo['sem'])} registros sem técnico na lista de ativos."
        )
        tipo = "alerta"
    return texto, tipo


def texto_insight_indicador(
    nome: str,
    pct: float,
    meta: float,
    janela: dict[str, Any],
    pior_base: pd.Series | None,
    concentracao: dict[str, Any],
    vinculo: dict[str, Any],
    volume: int,
) -> tuple[str, TipoInsightType]:
    status = classificar_status(pct, meta)
    tipo: TipoInsightType
    if status == "CONCLUIDO":
        texto = f"{nome} está na meta ({fmt_pct(pct)} contra {fmt_pct(meta)})."
        tipo = "ok"
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

    if pior_base is not None:
        texto += (
            f" Pior base com volume: {pior_base.get('Base', '—')} "
            f"({fmt_pct(float(pior_base['Realizado']))}, {fmt_int(pior_base['Total_OS'])} O.S.)."
        )
    if concentracao.get("qtd", 0) > 0 and concentracao.get("nomes"):
        nomes = ", ".join(concentracao["nomes"])
        texto += (
            f" {fmt_int(concentracao['qtd'])} registros fora do padrão; "
            f"{concentracao['n']} técnicos concentram {fmt_pct(concentracao['pct_top'])}. "
            f"Primeiros nomes: {nomes}."
        )
    if vinculo.get("sem", 0) > 0:
        texto += f" {fmt_int(vinculo['sem'])} registros sem vínculo de técnico."
        tipo = "alerta"
    if 0 < volume < 30:
        texto += " Volume baixo no recorte — leia o percentual com cautela."
        tipo = "alerta"
    return texto, tipo


# ====================================================
# 10. VISÃO EXECUTIVA CONSOLIDADA
# ====================================================
def renderizar_visao_executiva_geral(resultados: dict[str, dict[str, Any]]) -> None:
    frames: list[pd.DataFrame] = []
    for chave in ORDEM_INDICADORES:
        df_chave = dataframe_indicador(resultados, chave)
        if df_chave is not None and not df_chave.empty:
            frames.append(df_chave if "_DATA" in df_chave.columns else anexar_data(df_chave, chave))

    bases: set[str] = set()
    for df_tmp in frames:
        if "Base" in df_tmp.columns:
            bases.update(df_tmp["Base"].map(rotulo_categoria).unique().tolist())

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
        "Visão Executiva Consolidada",
        "Seis indicadores, uma leitura: o que está fora da meta, onde e se a fonte está em dia. "
        f"🕒 Data final da base: {data_final}",
        "🎯",
    )
    st.caption("O detalhe operacional — técnico, monitor e exceção — fica na aba de cada indicador.")

    c1, c2, c3 = st.columns([1.2, 1, 1])
    with c1:
        bases_lista = ["Todas"] + sorted(b for b in bases if b != SEM_VINCULO)
        if SEM_VINCULO in bases:
            bases_lista.append(SEM_VINCULO)
        sel_base = st.selectbox("🏢 Base", bases_lista, key="exec_consolidada_base_filter")

    ini_sel, fim_sel = dmin, dmax
    if dmin and dmax:
        with c2:
            periodo = st.date_input(
                "📅 Período",
                value=(dmin, dmax),
                min_value=dmin,
                max_value=dmax,
                key="exec_periodo",
            )
        ini_sel, fim_sel = normalizar_periodo(periodo, dmin, dmax)
        with c3:
            st.caption("Os percentuais respeitam o período.")
            st.caption("“Atualizado até” é a data final da base, não o fim do filtro.")

    dados: list[dict[str, Any]] = []
    serie_longa: list[pd.DataFrame] = []
    matriz_partes: list[pd.DataFrame] = []
    volume_partes: list[pd.DataFrame] = []

    for chave in ORDEM_INDICADORES:
        df_fonte = dataframe_indicador(resultados, chave)
        if df_fonte is None or df_fonte.empty:
            continue
        df_base = aplicar_filtro_base(df_fonte, sel_base)
        if df_base.empty:
            continue
        dt_fonte = extrair_data_maxima_aba(df_base, chave) or data_final
        df_calc = aplicar_periodo(df_base, ini_sel, fim_sel)
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

        if "Base" in work.columns:
            por_base = agregar_grupo(
                work,
                "Base",
                meta,
                col_tec="Tecnico" if "Tecnico" in work.columns else None,
            )
            if not por_base.empty:
                parte = por_base[["Base", "Realizado", "Total_OS"]].copy()
                parte["Indicador"] = NOMES_CURTOS.get(chave, chave)
                parte["Meta"] = meta
                matriz_partes.append(parte)
                volume_partes.append(parte[["Base", "Indicador", "Total_OS"]])

    if ini_sel and fim_sel:
        st.caption(
            f"Recorte ativo: base {sel_base} • período "
            f"{pd.Timestamp(ini_sel).strftime('%d/%m/%Y')} a {pd.Timestamp(fim_sel).strftime('%d/%m/%Y')}."
        )

    if not dados:
        render_empty_state(
            tipo="dados",
            descricao=f"Nenhum indicador disponível para a base '{sel_base}' neste período.",
        )
        return

    vinculo_total = 0
    vinculo_sem = 0
    bases_contabilizadas: set[int] = set()
    for info_fisica in resultados.values():
        df_fisica = info_fisica.get("df")
        if df_fisica is None or df_fisica.empty or id(df_fisica) in bases_contabilizadas:
            continue
        bases_contabilizadas.add(id(df_fisica))
        df_fisica = aplicar_periodo(aplicar_filtro_base(df_fisica, sel_base), ini_sel, fim_sel)
        vinc_fisica = resumo_vinculo(df_fisica)
        vinculo_total += vinc_fisica["total"]
        vinculo_sem += vinc_fisica["sem"]
    vinculo = {
        "total": vinculo_total,
        "sem": vinculo_sem,
        "pct": (((vinculo_total - vinculo_sem) / vinculo_total * 100.0) if vinculo_total else 0.0),
    }

    texto, tipo_insight = texto_insight_executivo(dados, vinculo)
    if atraso is not None and atraso >= 2:
        texto += f" Fonte desatualizada: a data final da base é {data_final} ({atraso} dias atrás)."
        tipo_insight = "alerta"
    publicar_insight(texto, titulo="Leitura executiva", tipo=tipo_insight)

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
        sub="Contrato de qualidade do recorte",
        tema=tema_meta,
        delta=f"{na_meta - len(dados):+d}" if na_meta < len(dados) else "OK",
        delta_tipo=trend_meta,
        colorida=True,
    )
    render_kpi(
        s2,
        "Maior gap",
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
        "O delta colorido de cada indicador abaixo é o desvio contra a meta. "
        "“7d” é a variação dos últimos 7 dias do recorte contra os 7 dias anteriores."
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

    if matriz_partes:
        bruto = pd.concat(matriz_partes, ignore_index=True)
        pct = bruto.pivot_table(
            index="Base", columns="Indicador", values="Realizado", aggfunc="mean"
        )
        ordem_cols = [NOMES_CURTOS[k] for k in ORDEM_INDICADORES if NOMES_CURTOS[k] in pct.columns]
        pct = pct.reindex(columns=ordem_cols)
        metas_col = {NOMES_CURTOS[k]: METAS_POR_ABA[k] for k in ORDEM_INDICADORES}
        gap = pct.copy()
        for col in gap.columns:
            gap[col] = gap[col] - metas_col.get(col, 95.0)
        pct = pct.loc[gap.mean(axis=1).sort_values(ascending=True).index]

        color_rules: dict[str, dict[str, str]] = {}
        display = pd.DataFrame({"Base": pct.index.astype(str)})
        for col in pct.columns:
            meta_col = metas_col.get(col, 95.0)
            textos: list[str] = []
            regras: dict[str, str] = {}
            for val in pct[col].tolist():
                if pd.isna(val):
                    textos.append("—")
                    continue
                texto = f"{float(val):.1f}%"
                textos.append(texto)
                regras[texto] = "sucesso" if float(val) >= meta_col else "alerta"
            display[col] = textos
            color_rules[col] = regras
        render_table_html(
            display,
            titulo="🏢 Onde agir — aderência por base",
            colunas=["Base"] + ordem_cols,
            alinhamentos={c: ("left" if c == "Base" else "right") for c in ["Base"] + ordem_cols},
            color_rules=color_rules,
            height=360,
            mostrar_data=False,
        )
        st.caption("Bases ordenadas pelo pior desvio médio. Percentual do período selecionado.")

        if volume_partes:
            with st.expander("Ver volume por base (denominador)"):
                vol = pd.concat(volume_partes, ignore_index=True)
                vol_p = vol.pivot_table(
                    index="Base", columns="Indicador", values="Total_OS", aggfunc="sum"
                )
                vol_p = vol_p.reindex(columns=ordem_cols).fillna(0).astype(int).reset_index()
                render_table_html(
                    vol_p,
                    colunas=["Base"] + ordem_cols,
                    alinhamentos={
                        c: ("left" if c == "Base" else "right") for c in ["Base"] + ordem_cols
                    },
                    fmt={c: "{:,}" for c in ordem_cols},
                    mostrar_data=False,
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
        titulo="Tabela consolidada de indicadores",
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
# 11. VISÃO POR TÉCNICO
# ====================================================
def renderizar_visao_tecnicos(
    resultados: dict[str, dict[str, Any]], ativos: ContextoAtivos
) -> None:
    render_cabecalho(
        "Painel Integrado e Drill-Down do Técnico",
        "Visão detalhada do comportamento de cada profissional da operação técnica.",
        "👷",
    )

    frames: list[pd.DataFrame] = []
    for chave in ORDEM_INDICADORES:
        df_chave = dataframe_indicador(resultados, chave)
        if df_chave is not None and not df_chave.empty:
            frames.append(df_chave if "_DATA" in df_chave.columns else anexar_data(df_chave, chave))

    bases: set[str] = set()
    monitores: set[str] = set()
    dmin, dmax = None, None

    for df_tmp in frames:
        if "Base" in df_tmp.columns:
            bases.update(df_tmp["Base"].map(rotulo_categoria).unique().tolist())
        if "Monitor" in df_tmp.columns:
            monitores.update(df_tmp["Monitor"].map(rotulo_categoria).unique().tolist())

        ini, fim = limites_periodo(df_tmp)
        if ini and (dmin is None or ini < dmin):
            dmin = ini
        if fim and (dmax is None or fim > dmax):
            dmax = fim

    c1, c2, c3, c4 = st.columns([1, 1, 1, 1.2])
    with c1:
        bases_lista = ["Todas"] + sorted(b for b in bases if b != SEM_VINCULO)
        sel_base = st.selectbox("🏢 Base (Lotação)", bases_lista, key="tec_view_base_filter")

    ini_sel, fim_sel = dmin, dmax
    if dmin and dmax:
        with c2:
            periodo = st.date_input(
                "📅 Período",
                value=(dmin, dmax),
                min_value=dmin,
                max_value=dmax,
                key="tec_view_periodo",
            )
            ini_sel, fim_sel = normalizar_periodo(periodo, dmin, dmax)

    filtrados_por_estrutura: set[str] = set()
    for df_tmp in frames:
        work_f = df_tmp.copy()
        if sel_base != "Todas":
            work_f = aplicar_filtro_base(work_f, sel_base)
        work_f = aplicar_periodo(work_f, ini_sel, fim_sel)
        if not work_f.empty and "Tecnico" in work_f.columns:
            filtrados_por_estrutura.update(
                work_f["Tecnico"].map(rotulo_categoria).unique().tolist()
            )

    lista_monitores = ["Todos"] + sorted([m for m in monitores if m != SEM_VINCULO])
    with c3:
        sel_monitor = st.selectbox(
            "👥 Filtrar por Monitor", lista_monitores, key="tec_view_mon_filter"
        )

    if sel_monitor != "Todos":
        tecs_do_monitor: set[str] = set()
        for df_tmp in frames:
            work_f = df_tmp.copy()
            if "Monitor" in work_f.columns and "Tecnico" in work_f.columns:
                sub = work_f[work_f["Monitor"].map(rotulo_categoria) == sel_monitor]
                tecs_do_monitor.update(sub["Tecnico"].map(rotulo_categoria).unique().tolist())
        filtrados_por_estrutura = filtrados_por_estrutura.intersection(tecs_do_monitor)

    lista_tecnicos = sorted([t for t in filtrados_por_estrutura if t != SEM_VINCULO])
    if SEM_VINCULO in filtrados_por_estrutura:
        lista_tecnicos.append(SEM_VINCULO)

    with c4:
        sel_tecnico = st.selectbox(
            "👷 Selecionar Técnico (Drill-Down)",
            ["Todos"] + lista_tecnicos,
            key="tec_view_selected",
        )

    matriz_performance_list: list[pd.DataFrame] = []
    lista_erros_individuais: list[pd.DataFrame] = []
    info_cadastral_tecnico = {
        "Monitor": SEM_VINCULO,
        "Base": SEM_VINCULO,
        "Situacao": SEM_VINCULO,
    }

    for chave in ORDEM_INDICADORES:
        df_fonte = dataframe_indicador(resultados, chave)
        if df_fonte is None or df_fonte.empty:
            continue
        df_base = aplicar_filtro_base(df_fonte, sel_base)
        df_calc = aplicar_periodo(df_base, ini_sel, fim_sel)
        if df_calc.empty:
            continue

        work, _ = com_score(df_calc, chave)
        if "_SCORE" not in work.columns:
            continue

        meta = float(METAS_POR_ABA.get(chave, 95.0))

        if sel_monitor != "Todos" and "Monitor" in work.columns:
            work = work[work["Monitor"].map(rotulo_categoria) == sel_monitor].copy()

        if "Tecnico" in work.columns and not work.empty:
            por_tecnico = agregar_grupo(work, "Tecnico", meta, com_situacao=True, com_monitor=True)
            if not por_tecnico.empty:
                parte = por_tecnico[
                    [
                        "Tecnico",
                        "Realizado",
                        "Total_OS",
                        "Atingidos",
                        "Nao_Atingidos",
                        "Situacao",
                        "Monitor",
                    ]
                ].copy()
                parte["Indicador_Chave"] = chave
                parte["Indicador"] = NOMES_CURTOS.get(chave, chave)
                parte["Meta"] = meta
                matriz_performance_list.append(parte)

                if sel_tecnico != "Todos":
                    sub_foco = work[work["Tecnico"].map(rotulo_categoria) == sel_tecnico].copy()
                    if not sub_foco.empty:
                        if "Monitor" in sub_foco.columns:
                            info_cadastral_tecnico["Monitor"] = rotulo_categoria(
                                sub_foco["Monitor"].iloc[0]
                            )
                        if "Base" in sub_foco.columns:
                            info_cadastral_tecnico["Base"] = rotulo_categoria(
                                sub_foco["Base"].iloc[0]
                            )
                        if "Situacao" in sub_foco.columns:
                            info_cadastral_tecnico["Situacao"] = rotulo_categoria(
                                sub_foco["Situacao"].iloc[0]
                            )

                        falhas = sub_foco[sub_foco["_SCORE"] == 0].copy()
                        if not falhas.empty:
                            falhas["Indicador"] = NOMES_AMIGAVEIS.get(chave, chave)
                            lista_erros_individuais.append(falhas)

    if not matriz_performance_list:
        render_empty_state(
            tipo="dados",
            descricao="Nenhum registro encontrado para os técnicos com os filtros informados.",
        )
        return

    df_consolidado_tecnicos = pd.concat(matriz_performance_list, ignore_index=True)

    # --- CASO 1: VISÃO GERAL (MATRIZ TODOS OS TÉCNICOS) ---
    if sel_tecnico == "Todos":
        st.markdown("### 📊 Matriz de Performance: Técnico × Indicadores")
        st.caption(
            "Aderência (%) consolidada por profissional neste recorte temporal. "
            "Células em vermelho representam resultados abaixo da meta correspondente."
        )

        pivot_tec = df_consolidado_tecnicos.pivot_table(
            index="Tecnico", columns="Indicador", values="Realizado", aggfunc="mean"
        ).reset_index()

        ativos_filtro = ativos.df.copy()
        if ativos.col_base and sel_base != "Todas":
            ativos_filtro = ativos_filtro[
                ativos_filtro[ativos.col_base].map(rotulo_categoria) == sel_base
            ]
        if ativos.col_monitor and sel_monitor != "Todos":
            ativos_filtro = ativos_filtro[
                ativos_filtro[ativos.col_monitor].map(rotulo_categoria) == sel_monitor
            ]

        if ativos.col_tecnico and ativos.col_monitor:
            todos_tecs_ativos = (
                ativos_filtro[[ativos.col_tecnico, ativos.col_monitor]].drop_duplicates().copy()
            )
            todos_tecs_ativos.columns = ["Tecnico", "Monitor"]
            todos_tecs_ativos["Tecnico"] = todos_tecs_ativos["Tecnico"].map(rotulo_categoria)
            todos_tecs_ativos["Monitor"] = todos_tecs_ativos["Monitor"].map(rotulo_categoria)
            todos_tecs_ativos = todos_tecs_ativos[todos_tecs_ativos["Tecnico"] != SEM_VINCULO]
        else:
            todos_tecs_ativos = pd.DataFrame(columns=["Tecnico", "Monitor"])

        pivot_tec_completo = pd.merge(todos_tecs_ativos, pivot_tec, on="Tecnico", how="outer")

        if "Monitor" in pivot_tec_completo.columns:
            mapa_mon_ativos: dict[str, str] = {}
            if ativos.col_tecnico and ativos.col_monitor:
                mapa_mon_ativos = (
                    ativos.df.dropna(subset=[ativos.col_tecnico, ativos.col_monitor])
                    .set_index(ativos.col_tecnico)[ativos.col_monitor]
                    .map(rotulo_categoria)
                    .to_dict()
                )
            mapa_mon_calc: dict[str, str] = {}
            if "Monitor" in df_consolidado_tecnicos.columns:
                mapa_mon_calc = (
                    df_consolidado_tecnicos.dropna(subset=["Tecnico", "Monitor"])
                    .set_index("Tecnico")["Monitor"]
                    .to_dict()
                )

            mapa_mon_final = {**mapa_mon_calc, **mapa_mon_ativos}
            pivot_tec_completo["Monitor"] = (
                pivot_tec_completo["Monitor"]
                .fillna(pivot_tec_completo["Tecnico"].map(mapa_mon_final))
                .fillna(SEM_VINCULO)
            )

        pivot_tec_completo = pivot_tec_completo[
            pivot_tec_completo["Tecnico"].notna()
            & (pivot_tec_completo["Tecnico"] != "")
            & (pivot_tec_completo["Tecnico"] != SEM_VINCULO)
        ].copy()

        ordem_cols = [
            NOMES_CURTOS[k]
            for k in ORDEM_INDICADORES
            if NOMES_CURTOS[k] in pivot_tec_completo.columns
        ]

        pivot_tec_completo["Média_Geral"] = pivot_tec_completo[ordem_cols].mean(axis=1)
        pivot_tec_completo = pivot_tec_completo.sort_values(
            by="Média_Geral", ascending=True
        ).drop(columns=["Média_Geral"])

        display_tec = pd.DataFrame(
            {
                "Técnico": pivot_tec_completo["Tecnico"].astype(str),
                "Monitor": pivot_tec_completo["Monitor"].astype(str),
            }
        )

        color_rules_tec: dict[str, dict[str, str]] = {}
        metas_col = {NOMES_CURTOS[k]: METAS_POR_ABA[k] for k in ORDEM_INDICADORES}

        for col in ordem_cols:
            meta_col = metas_col.get(col, 95.0)
            textos: list[str] = []
            regras: dict[str, str] = {}
            for val in pivot_tec_completo[col].tolist():
                if pd.isna(val):
                    textos.append("—")
                    continue
                texto = f"{float(val):.1f}%"
                textos.append(texto)
                regras[texto] = "sucesso" if float(val) >= meta_col else "alerta"
            display_tec[col] = textos
            color_rules_tec[col] = regras

        render_table_html(
            display_tec,
            colunas=["Técnico", "Monitor"] + ordem_cols,
            alinhamentos={
                c: ("left" if c in ["Técnico", "Monitor"] else "right")
                for c in ["Técnico", "Monitor"] + ordem_cols
            },
            color_rules=color_rules_tec,
            height=500,
            mostrar_data=False,
        )

        with st.expander("🔍 Ver volume total de ordens (denominador) por técnico"):
            vol_tec = df_consolidado_tecnicos.pivot_table(
                index="Tecnico", columns="Indicador", values="Total_OS", aggfunc="sum"
            )
            vol_tec = vol_tec.reindex(columns=ordem_cols).fillna(0).astype(int).reset_index()
            render_table_html(
                vol_tec,
                colunas=["Tecnico"] + ordem_cols,
                alinhamentos={
                    c: ("left" if c == "Tecnico" else "right") for c in ["Tecnico"] + ordem_cols
                },
                fmt={c: "{:,}" for c in ordem_cols},
                mostrar_data=False,
            )

    # --- CASO 2: DRILL-DOWN INDIVIDUAL ---
    else:
        df_focado = df_consolidado_tecnicos[df_consolidado_tecnicos["Tecnico"] == sel_tecnico]
        if df_focado.empty:
            render_empty_state(
                tipo="dados",
                descricao=(
                    f"Nenhum registro de OS ativa localizado para o técnico {sel_tecnico} "
                    "no período."
                ),
            )
            return

        st.markdown(f"### 👷 Perfil e Desempenho: {sel_tecnico}")

        inf_c1, inf_c2, inf_c3 = st.columns(3)
        with inf_c1:
            st.markdown(f"**Monitor Integrado:** {info_cadastral_tecnico['Monitor']}")
        with inf_c2:
            st.markdown(f"**Base / Filial:** {info_cadastral_tecnico['Base']}")
        with inf_c3:
            status_text = info_cadastral_tecnico["Situacao"]
            status_color = "🟢" if status_text.upper() == "ATIVO" else "⚠️"
            st.markdown(f"**Situação Cadastral:** {status_color} {status_text}")
        st.markdown("---")

        st.markdown("#### Atingimento dos Indicadores Técnicos")
        cols_kpi = st.columns(6)

        for idx_c, ind_k in enumerate(ORDEM_INDICADORES):
            info_ind = df_focado[df_focado["Indicador_Chave"] == ind_k]
            nome_c = NOMES_CURTOS.get(ind_k, ind_k)
            icon_c = NOMES_ICONES.get(ind_k, "📋")
            meta_val = METAS_POR_ABA.get(ind_k, 95.0)
            with cols_kpi[idx_c]:
                if not info_ind.empty:
                    realizado = float(info_ind["Realizado"].iloc[0])
                    total_os = int(info_ind["Total_OS"].iloc[0])
                    nao_atg = int(info_ind["Nao_Atingidos"].iloc[0])
                    status = classificar_status(realizado, meta_val)
                    desvio = realizado - meta_val

                    render_kpi(
                        cols_kpi[idx_c],
                        f"{icon_c} {nome_c}",
                        f"{realizado:.1f}%",
                        sub=f"Falhas: {nao_atg}/{total_os}",
                        tema=tema_kpi_status(status),
                        delta=f"{desvio:+.1f}%",
                        delta_tipo=trend_de_status(status),
                        colorida=True,
                    )
                else:
                    render_kpi_sm(
                        cols_kpi[idx_c],
                        f"{icon_c} {nome_c}",
                        "—",
                        sub="Sem OS",
                        tema="cinza",
                    )

        st.markdown("---")
        st.markdown("#### 📝 Ocorrências e Plano de Ação")
        st.caption(
            "Detalhamento de cada erro identificado na operação deste profissional. "
            "Use essas informações para feedback específico."
        )

        if lista_erros_individuais:
            df_erros_consol = pd.concat(lista_erros_individuais, ignore_index=True)
            colunas_limpas = [c for c in df_erros_consol.columns if c not in COLUNAS_AUXILIARES]
            df_erros_visualizar = df_erros_consol[colunas_limpas].copy()

            st.dataframe(df_erros_visualizar, width="stretch")

            csv_data = df_erros_visualizar.to_csv(index=False, sep=";", decimal=",").encode(
                "utf-8-sig"
            )
            st.download_button(
                label=f"⬇️ Exportar Ocorrências de {sel_tecnico}",
                data=csv_data,
                file_name=f"plano_acao_{sel_tecnico.lower().replace(' ', '_')}.csv",
                mime="text/csv",
                key="dl_tec_individual_errors",
            )
        else:
            render_insight(
                "**Técnico 100% Conforme** — Operação impecável! Nenhuma falha fora do "
                "padrão registrada para este técnico no recorte selecionado.",
                tipo="ok",
            )


# ====================================================
# 12. PAINEL DO INDICADOR
# ====================================================
def renderizar_painel_executivo_aba(df_indicador: pd.DataFrame | None, nome_kpi: str) -> None:
    nome_amigavel = NOMES_AMIGAVEIS.get(nome_kpi, nome_kpi)
    icone = NOMES_ICONES.get(nome_kpi, "📋")
    meta_kpi = float(METAS_POR_ABA.get(nome_kpi, 95.0))
    data_final = extrair_data_maxima_aba(df_indicador, nome_kpi) or DATA_SISTEMA_STR
    complemento = (
        " (data final da base)" if remover_acentos_e_padronizar(nome_kpi) == "tec1" else ""
    )

    render_cabecalho(
        f"Painel Executivo — {nome_amigavel}",
        f"{GLOSSARIO.get(nome_kpi, nome_amigavel)} • "
        f"🕒 Atualizado até: {data_final}{complemento}",
        icone,
    )

    if df_indicador is None or df_indicador.empty:
        render_empty_state(
            tipo="dados",
            descricao=f"Dados indisponíveis para o indicador {nome_amigavel}.",
        )
        return

    base_df = (
        df_indicador if "_DATA" in df_indicador.columns else anexar_data(df_indicador, nome_kpi)
    )
    dmin, dmax = limites_periodo(base_df)

    st.markdown("### 🔍 Recorte")
    ini_sel, fim_sel = dmin, dmax
    if dmin and dmax:
        periodo = st.date_input(
            "📅 Período",
            value=(dmin, dmax),
            min_value=dmin,
            max_value=dmax,
            key=f"periodo_{nome_kpi}",
        )
        ini_sel, fim_sel = normalizar_periodo(periodo, dmin, dmax)
    df_periodo = aplicar_periodo(base_df, ini_sel, fim_sel)

    fc1, fc2, fc3 = st.columns(3)
    df_view = df_periodo
    with fc1:
        if "Base" in df_periodo.columns:
            bases = ["Todas"] + opcoes_categoria(df_periodo["Base"])
            sel_base = st.selectbox("🏢 Base", bases, key=f"base_filter_{nome_kpi}")
            df_view = aplicar_filtro_base(df_view, sel_base)
    with fc2:
        if "Monitor" in df_view.columns:
            mons = opcoes_categoria(df_view["Monitor"])
            sel_mon = st.multiselect(
                "👥 Monitor", mons, key=f"mon_filter_{nome_kpi}", placeholder="Todos"
            )
            df_view = aplicar_filtro_lista(df_view, "Monitor", sel_mon)
    with fc3:
        if "Tecnico" in df_view.columns:
            tecs = opcoes_categoria(df_view["Tecnico"])
            sel_tec = st.multiselect(
                "👷 Técnico", tecs, key=f"tec_filter_{nome_kpi}", placeholder="Todos"
            )
            df_view = aplicar_filtro_lista(df_view, "Tecnico", sel_tec)

    if df_view.empty:
        render_empty_state(
            tipo="dados",
            descricao="Nenhum registro no recorte. Amplie o período ou limpe os filtros.",
        )
        return

    work, info = com_score(df_view, nome_kpi)
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
    vinculo = resumo_vinculo(work)
    col_tec = "Tecnico" if "Tecnico" in work.columns else None
    col_mon = "Monitor" if "Monitor" in work.columns else None
    col_base = "Base" if "Base" in work.columns else None

    if ini_sel and fim_sel:
        st.caption(
            f"Recorte: {pd.Timestamp(ini_sel).strftime('%d/%m/%Y')} a "
            f"{pd.Timestamp(fim_sel).strftime('%d/%m/%Y')} • "
            f"{fmt_int(total)} registros avaliados. A data do cabeçalho continua sendo a data final da base."
        )

    st.markdown("### 🎯 Resultado do recorte")
    k1, k2, k3, k4, k5 = st.columns(5)
    render_kpi(
        k1,
        "Aderência",
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
        sub="Denominador do recorte",
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
        label=f"Aderência do recorte contra a meta de {meta_kpi:.1f}%",
        tema=tema_kpi_status(status),
    )

    df_base_agg = agregar_grupo(work, col_base, meta_kpi, col_tec) if col_base else pd.DataFrame()
    pior_base = None
    if not df_base_agg.empty:
        # "(Sem vínculo)" não é uma base real — não deve virar o destaque do insight.
        candidatas = df_base_agg[
            df_base_agg[col_base].map(rotulo_categoria) != SEM_VINCULO
        ]
        if candidatas.empty:
            candidatas = df_base_agg
        com_volume = candidatas[candidatas["Total_OS"] >= 10]
        fonte = com_volume if not com_volume.empty else candidatas
        pior_base = fonte.sort_values(["Realizado", "Total_OS"], ascending=[True, False]).iloc[0]
    concentracao = concentracao_nao_conformes(work, col_tec)
    texto, tipo_insight = texto_insight_indicador(
        nome_amigavel, pct, meta_kpi, janela, pior_base, concentracao, vinculo, total
    )
    publicar_insight(texto, titulo="O que fazer com este número", tipo=tipo_insight)

    st.markdown("---")
    render_evolucao(serie_diaria(work), meta_kpi, "📈 Evolução diária vs meta")
    st.markdown("---")

    sel_perf = st.selectbox(
        "🎨 Destacar performance nas tabelas",
        list(MAPA_PERFORMANCE.keys()),
        key=f"perf_filter_{nome_kpi}",
    )

    if col_base and not df_base_agg.empty:
        render_ranking_tabela(
            filtrar_status(df_base_agg, sel_perf),
            col_nome=col_base,
            meta=meta_kpi,
            titulo="🏢 Desempenho por base",
            height=350,
            com_qtd_tec=True,
            com_nao=True,
        )
        st.markdown("---")

    if col_tec and "_SCORE" in work.columns:
        df_tec = agregar_grupo(work, col_tec, meta_kpi, com_situacao=True)
        df_tec = filtrar_status(df_tec, sel_perf)
        if df_tec.empty:
            st.caption("Nenhum técnico no recorte para a performance selecionada.")
        else:
            st.markdown("#### 👷 Desempenho Geral por Técnico (Todos)")
            render_ranking_tabela(
                df_tec.sort_values(["Realizado", "Total_OS"], ascending=[False, False]),
                col_nome=col_tec,
                meta=meta_kpi,
                height=850,
                com_situacao=True,
            )

            st.markdown("#### ⚠️ Bottom 10 — Requer Atenção")
            st.caption(
                f"Técnicos com pelo menos {MIN_OS_BOTTOM} O.S. no recorte, "
                "do pior resultado para o melhor."
            )
            df_bot = (
                df_tec[df_tec["Total_OS"] >= MIN_OS_BOTTOM]
                .sort_values(["Realizado", "Total_OS"], ascending=[True, False])
                .head(10)
            )
            if df_bot.empty:
                df_bot = df_tec.sort_values(
                    ["Realizado", "Total_OS"], ascending=[True, False]
                ).head(10)
            render_barras_ranking(df_bot, col_tec, meta_kpi)
            render_ranking_tabela(
                df_bot,
                col_nome=col_tec,
                meta=meta_kpi,
                height=480,
                com_situacao=True,
            )

            especiais = pd.DataFrame()
            if "Situacao" in df_bot.columns:
                especiais = df_bot[
                    ~df_bot["Situacao"]
                    .map(rotulo_categoria)
                    .str.upper()
                    .isin(["ATIVO", SEM_VINCULO.upper()])
                ]
            if not especiais.empty:
                nomes_esp = ", ".join(
                    f"{r[col_tec]} ({r['Situacao']})" for _, r in especiais.iterrows()
                )
                publicar_insight(
                    f"No Bottom 10 há técnico fora de ATIVO: {nomes_esp}.",
                    titulo="Situação cadastral",
                    tipo="alerta",
                )

            with st.expander("🏆 Top 10 — referência"):
                df_top = df_tec.sort_values(
                    ["Realizado", "Total_OS"], ascending=[False, False]
                ).head(10)
                render_ranking_tabela(
                    df_top,
                    col_nome=col_tec,
                    meta=meta_kpi,
                    com_situacao=True,
                )
        st.markdown("---")
    elif col_tec is None:
        publicar_insight(
            "Ranking por técnico indisponível: o login desta base não foi vinculado à lista de ativos.",
            titulo="Sem vínculo",
            tipo="alerta",
        )

    if col_mon and "_SCORE" in work.columns:
        df_mon = filtrar_status(agregar_grupo(work, col_mon, meta_kpi, col_tec=col_tec), sel_perf)
        render_ranking_tabela(
            df_mon,
            col_nome=col_mon,
            meta=meta_kpi,
            titulo="👥 Consolidado por monitor",
            com_qtd_tec=True,
        )

    with st.expander("Exportar recorte"):
        e1, e2, e3 = st.columns(3)
        with e1:
            download_csv(
                (work[work["_SCORE"] == 0] if "_SCORE" in work.columns else work.iloc[0:0]),
                "⬇️ Fora do padrão",
                f"{nome_kpi}_fora_do_padrao.csv",
                key=f"dl_fora_{nome_kpi}",
            )
        with e2:
            if col_tec:
                download_csv(
                    agregar_grupo(work, col_tec, meta_kpi, com_situacao=True),
                    "⬇️ Ranking de técnicos",
                    f"{nome_kpi}_tecnicos.csv",
                    key=f"dl_tec_{nome_kpi}",
                )
        with e3:
            download_csv(
                work,
                "⬇️ Base filtrada",
                f"{nome_kpi}_recorte.csv",
                key=f"dl_base_{nome_kpi}",
            )


# ====================================================
# 13. CHIPS DE CONTEXTO DO TOPO
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
# 14. EXECUÇÃO PRINCIPAL
# ====================================================
render_sidebar_portal(
    nome=nome_logado,
    login=login_logado,
    user=user_logado,
    pagina_logout="streamlit_app.py",
)

render_hero_totale_1(
    titulo="Painel de Qualidade e Indicadores Técnicos",
    subtitulo=(
        "Seis indicadores operacionais cruzados com a lista de ativos, com "
        "leitura consolidada e drill-down por técnico."
    ),
    icone="monitoring",
    badge=f"PAINEL v{VERSAO_PAGINA}",
    usar_material=True,
)

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

with st.spinner("⏳ Processando e cruzando bases de dados..."):
    excel_sheets = carregar_workbook_indicadores(INDICADORES_ID)
    df_ativos = carregar_lista_ativos(ATIVOS_ID)

if not excel_sheets:
    render_empty_state(
        tipo="erro",
        titulo="Erro ao carregar a planilha de indicadores",
        descricao=(
            "Verifique o ID configurado, a conectividade e a permissão de leitura "
            "(compartilhamento público ou service account)."
        ),
    )
    st.stop()

if df_ativos is None or df_ativos.empty:
    render_empty_state(
        tipo="erro",
        titulo="Erro ao carregar a Lista de Ativos",
        descricao=(
            "A planilha de ativos não retornou dados. Sem ela não é possível vincular "
            "técnico, monitor e base aos indicadores."
        ),
    )
    st.stop()

col_login_ativos = encontrar_coluna_flexivel(df_ativos, ["Login", "LOGIN", "Cd_Login", "LOGIN_TEC"])
col_tec_ativos = encontrar_coluna_flexivel(
    df_ativos, ["Tecnico", "Técnico", "TECNICO", "Nome_Tecnico"]
)
col_mon_ativos = encontrar_coluna_flexivel(df_ativos, ["Monitor", "MONITOR", "Nome_Monitor"])
col_base_ativos = encontrar_coluna_flexivel(df_ativos, ["Base", "BASE", "Filial", "Unidade"])
col_sit_ativos = encontrar_coluna_flexivel(
    df_ativos, ["Situação", "Situacao", "SITUACAO", "Status_Tecnico"]
)

if not col_login_ativos:
    st.error("❌ Coluna 'Login' não encontrada na Lista de Ativos.")
    st.stop()

ativos_ctx = ContextoAtivos(
    df=df_ativos,
    col_login=col_login_ativos,
    col_tecnico=col_tec_ativos,
    col_monitor=col_mon_ativos,
    col_base=col_base_ativos,
    col_situacao=col_sit_ativos,
)

resultados = montar_resultados(excel_sheets, ativos_ctx)

datas_fonte: list[str] = []
datas_inicio: list[str] = []
vinculo_total = 0
vinculo_sem = 0
bases_contabilizadas: set[int] = set()
for res_k, res_v in resultados.items():
    df_res = res_v.get("df")
    if df_res is None or id(df_res) in bases_contabilizadas:
        continue
    bases_contabilizadas.add(id(df_res))
    dt_m = extrair_data_maxima_aba(df_res, res_k)
    if dt_m:
        datas_fonte.append(dt_m)
    if "_DATA" in df_res.columns and df_res["_DATA"].notna().any():
        datas_inicio.append(pd.Timestamp(df_res["_DATA"].min()).strftime("%d/%m/%Y"))
    vinc = resumo_vinculo(df_res)
    vinculo_total += vinc["total"]
    vinculo_sem += vinc["sem"]

data_max_global_str = maior_texto_data(datas_fonte, DATA_SISTEMA_STR)
data_min_global_str = menor_texto_data(datas_inicio, "—")
pct_vinculo = ((vinculo_total - vinculo_sem) / vinculo_total * 100.0) if vinculo_total else 0.0
atraso_global = atraso_em_dias(data_max_global_str)
abas_erro = [aba for aba, info in resultados.items() if info.get("df") is None]

with st.sidebar:
    st.divider()
    st.markdown("#### 🔗 Integração de Dados")
    st.caption(f"Cobertura da fonte: {data_min_global_str} a {data_max_global_str}")
    if atraso_global is not None and atraso_global >= 2:
        st.caption(f"⚠️ Fonte {atraso_global} dias atrás da data de hoje.")
    st.caption(
        f"Vínculo de logins: {fmt_pct(pct_vinculo)} "
        f"({fmt_int(vinculo_total - vinculo_sem)} de {fmt_int(vinculo_total)})"
    )
    if st.button("🔄 Atualizar bases", width="stretch", key="indicadores_refresh"):
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
        "Cobertura": f"{data_min_global_str} a {data_max_global_str}",
        "Vínculo de logins": fmt_pct(pct_vinculo),
        "Abas com erro": str(len(abas_erro)) if abas_erro else "",
    }
)

if abas_erro:
    for aba_err in abas_erro:
        render_insight(
            f"**Erro na aba {aba_err}** — {resultados[aba_err].get('erro', 'Erro desconhecido')}",
            tipo="alerta",
        )

abas_exibicao: list[tuple[str, pd.DataFrame | None]] = []
for chave in ORDEM_INDICADORES:
    df_chave = dataframe_indicador(resultados, chave)
    if df_chave is not None:
        abas_exibicao.append((chave, df_chave))

if not abas_exibicao:
    render_empty_state(
        tipo="erro",
        titulo="Processamento inválido",
        descricao="Nenhuma das abas de indicadores pôde ser mapeada com a lista de ativos.",
    )
    st.stop()

nomes_tabs: list[str] = ["🎯 Visão Consolidada", "👷 Visão por Técnico"] + [
    f"{NOMES_ICONES.get(chave, '📋')} {NOMES_AMIGAVEIS.get(chave, chave)}"
    for chave, _ in abas_exibicao
]

render_cabecalho(
    "Painéis por Indicador",
    "Consolidado, drill-down por técnico e a aba de cada indicador.",
    "📊",
)
tabs = st.tabs(nomes_tabs)

with tabs[0]:
    renderizar_visao_executiva_geral(resultados)

with tabs[1]:
    renderizar_visao_tecnicos(resultados, ativos_ctx)

for idx, (chave_kpi, df_kpi) in enumerate(abas_exibicao):
    with tabs[idx + 2]:
        renderizar_painel_executivo_aba(df_kpi, chave_kpi)

st.markdown("---")
st.caption(
    f"Portal TOTALE · Painel de Indicadores v{VERSAO_PAGINA} · "
    f"Fonte: planilha de indicadores + Lista de Ativos · {DATA_SISTEMA_STR}"
)
