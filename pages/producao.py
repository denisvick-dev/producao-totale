# pages/producao.py
import io
import calendar
import datetime
import locale
import requests
import textwrap
from datetime import timedelta
from io import BytesIO
from typing import Any, Dict, List, Optional, cast
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# ====================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ====================================================
st.set_page_config(
    page_title="Visão Produção | TOTALE",
    page_icon="📊",
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

# ====================================================
# 3. IMPORTAÇÃO DO DESIGN SYSTEM CORPORATIVO
# ====================================================
try:
    from components.componentes import (
        aplicar_estilo,
        aplicar_tema_claro,
        render_hero_totale_1,
        render_insight,
        render_section_header,
        injetar_css_menu_nomes,  # noqa: F401
    )
except ImportError:
    st.error("⚠️ Módulo 'componentes.py' não encontrado.")
    st.stop()


def configurar_locale() -> None:
    for loc in ("pt_BR.UTF-8", "Portuguese_Brazil.1252", "pt_BR"):
        try:
            locale.setlocale(locale.LC_TIME, loc)
            return
        except locale.Error:
            continue


configurar_locale()


# ====================================================
# 4. CSS DO MENU E SIDEBAR UNIFICADO
# ====================================================
def injetar_css_menu_sidebar() -> None:
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #F4F5F7 0%, #FFFFFF 100%) !important;
            border-right: 1px solid #E2E8F0 !important;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:first-child { display: none !important; }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] ul {
            display: flex !important;
            flex-direction: column !important;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:has(a[href*="producao"]) { order: 1 !important; }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:has(a[href*="consultivo"]) { order: 2 !important; }

        [data-testid="stSidebarNav"] a[href*="consultivo"] span { font-size: 0 !important; }
        [data-testid="stSidebarNav"] a[href*="consultivo"] span::before { content: "🗣️ Consultivo" !important; font-size: 14px !important; font-weight: 700 !important; color: #1E293B !important; }

        [data-testid="stSidebarNav"] a[href*="producao"] span { font-size: 0 !important; }
        [data-testid="stSidebarNav"] a[href*="producao"] span::before { content: "📊 Produtividade" !important; font-size: 14px !important; font-weight: 700 !important; color: #1E293B !important; }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
            background: #F8FAFC !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 8px !important;
            margin: 4px 16px !important;
            padding: 10px 14px !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
            transition: all 0.2s ease;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"],
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-selected="true"] {
            background: linear-gradient(90deg, #FFF7ED 0%, #FFEDD5 100%) !important;
            border: 1px solid #F97316 !important;
            border-left: 4px solid #F97316 !important;
            box-shadow: 0 4px 10px rgba(249, 115, 22, 0.1) !important;
        }
        .btn-logout button {
            background: linear-gradient(180deg, #E2E8F0 0%, #CBD5E1 100%) !important;
            border: 1px solid #94A3B8 !important;
            color: #1E293B !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            margin-top: 10px !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.5), 0 2px 4px rgba(0,0,0,0.05) !important;
        }
        .btn-logout button:hover {
            background: #F1F5F9 !important;
            border-color: #64748B !important;
        }
        .card-premium { position: relative; cursor: help; }
        .tooltip-premium {
            visibility: hidden; background-color: #1E293B; color: #F8FAFC;
            text-align: center; border-radius: 8px; padding: 8px 12px;
            position: absolute; z-index: 999; bottom: 115%; left: 50%;
            transform: translateX(-50%); opacity: 0;
            transition: opacity 0.3s ease, bottom 0.3s ease;
            font-size: 11px; font-weight: 500; min-width: 180px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2); pointer-events: none;
        }
        .tooltip-premium::after {
            content: ""; position: absolute; top: 100%; left: 50%;
            margin-left: -6px; border-width: 6px; border-style: solid;
            border-color: #1E293B transparent transparent transparent;
        }
        .card-premium:hover .tooltip-premium { visibility: visible; opacity: 1; bottom: 105%; }

        [data-testid="stMain"] [data-baseweb="input"],
        [data-testid="stMain"] [data-testid="stDateInput"] > div > div,
        [data-testid="stMain"] div[data-baseweb="select"] > div {
            background-color: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
        }
        [data-testid="stMain"] input {
            color: #0F172A !important;
            font-weight: 600 !important;
            font-size: 14px !important;
            background-color: #FFFFFF !important;
        }
        .loading-totale {
            background: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid #F37C04;
            padding: 16px 20px; border-radius: 10px; margin-bottom: 20px;
            display: flex; align-items: center; justify-content: space-between;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_perfil() -> None:
    partes_nome = nome_logado.split()
    if len(partes_nome) >= 2:
        iniciais = partes_nome[0][0] + partes_nome[1][0]
    elif len(partes_nome) == 1:
        iniciais = partes_nome[0][:2]
    else:
        iniciais = "US"

    with st.sidebar:
        st.html(
            textwrap.dedent(f"""
            <div style="background: linear-gradient(145deg, #F8FAFC 0%, #E2E8F0 100%);
                        border: 1px solid #CBD5E1; border-left: 4px solid #F97316;
                        border-radius: 12px; padding: 16px; margin: 16px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
                <div style="font-size: 11px; font-weight: 800; letter-spacing: 1.5px; color: #F97316; margin-bottom: 12px;">
                    ⚡ TOTALE · PORTAL
                </div>
                <div style="width: 52px; height: 52px; border-radius: 50%;
                            background: linear-gradient(135deg, #012869 0%, #F97316 100%);
                            color: #FFFFFF !important; display: flex; align-items: center; justify-content: center;
                            font-size: 18px; font-weight: 800; margin-bottom: 12px;
                            box-shadow: 0 4px 10px rgba(0,0,0,0.2);">
                    {iniciais}
                </div>
                <p style="color: #012869; font-weight: 800; font-size: 14px; margin: 0 0 12px 0; line-height: 1.2;">
                    {nome_logado or 'TÉCNICO NÃO IDENTIFICADO'}
                </p>
                <div style="display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px;">
                    <div style="font-size: 12px; color: #475569;">
                        Login: <span style="background: #E2E8F0; border: 1px solid #CBD5E1; color: #0F172A; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-weight: 600;">{login_logado or 'N/A'}</span>
                    </div>
                    <div style="font-size: 12px; color: #475569;">
                        User: <span style="background: #E2E8F0; border: 1px solid #CBD5E1; color: #0F172A; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-weight: 600;">{user_logado or 'N/A'}</span>
                    </div>
                </div>
                <div style="background: #D1FAE5; border: 1px solid #6EE7B7; color: #065F46;
                            padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700;
                            display: inline-flex; align-items: center; gap: 6px;">
                    <div style="width: 6px; height: 6px; background: #10B981; border-radius: 50%;"></div>
                    Online
                </div>
            </div>
                """),
        )
        st.markdown('<div class="btn-logout">', unsafe_allow_html=True)
        if st.button("🚪 Encerrar Sessão", use_container_width=True):
            st.session_state["authenticated"] = False
            st.switch_page("streamlit_app.py")
        st.markdown("</div>", unsafe_allow_html=True)


# ====================================================
# 5. CARREGAMENTO DAS BASES (GOOGLE SHEETS)
# ====================================================
SPREADSHEET_ID_PRODUCAO = "11Dp9WdZYUrT_LBvfo07Mi8muKXZykU7v"
SPREADSHEET_ID_ATIVOS = "1LQKDcLshC6XSXLBVWaEYSpxrro6uydyU9pwDLc38pEg"


@st.cache_data(ttl=600, show_spinner=False)
def carregar_base_producao() -> pd.DataFrame:
    urls = [
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID_PRODUCAO}/export?format=xlsx",
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID_PRODUCAO}/export?format=csv",
        f"https://drive.google.com/uc?export=download&id={SPREADSHEET_ID_PRODUCAO}",
    ]
    for url in urls:
        try:
            resp = requests.get(url, timeout=30)
        except requests.RequestException:
            continue
        if resp.status_code != 200 or len(resp.content) <= 100:
            continue

        content = resp.content
        if url.endswith("format=xlsx"):
            try:
                abas = pd.read_excel(
                    io.BytesIO(content), sheet_name=None, engine="openpyxl"
                )
                abas_alvo = {
                    str(nome).strip().lower(): df
                    for nome, df in abas.items()
                    if str(nome).strip().lower() in ("prod", "gpon") and not df.empty
                }
                if abas_alvo:
                    frames = []
                    for nome_aba in ("prod", "gpon"):
                        df_aba = abas_alvo.get(nome_aba)
                        if df_aba is not None:
                            df_aba = df_aba.copy()
                            df_aba["__origem__"] = nome_aba.title()
                            if nome_aba == "gpon":
                                col_contrato = Utilitarios.buscar_coluna(
                                    df_aba, ["CONTRATO", "OS", "O.S."]
                                )
                                if col_contrato:
                                    df_aba = df_aba.drop_duplicates(
                                        subset=[col_contrato], keep="first"
                                    )
                            frames.append(df_aba)
                    if frames:
                        return pd.concat(frames, ignore_index=True)
            except Exception:
                pass

        for csv_kwargs in (
            {"sep": None, "engine": "python", "encoding": "utf-8"},
            {"sep": ";", "encoding": "latin-1"},
            {"sep": ",", "encoding": "utf-8"},
        ):
            csv_kwargs: Dict[str, Any] = dict(csv_kwargs)
            try:
                df = pd.read_csv(io.BytesIO(content), **csv_kwargs)
                if not df.empty and df.shape[1] > 1:
                    return df
            except Exception:
                continue
        try:
            df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
            if not df.empty and df.shape[1] > 1:
                return df
        except Exception:
            continue
    return pd.DataFrame()


@st.cache_data(ttl=600, show_spinner=False)
def carregar_base_ativos() -> pd.DataFrame:
    """Carrega a planilha Lista Ativos."""
    urls = [
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID_ATIVOS}/export?format=xlsx",
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID_ATIVOS}/export?format=csv",
        f"https://drive.google.com/uc?export=download&id={SPREADSHEET_ID_ATIVOS}",
    ]
    for url in urls:
        try:
            resp = requests.get(url, timeout=30)
        except requests.RequestException:
            continue
        if resp.status_code != 200 or len(resp.content) <= 100:
            continue

        content = resp.content
        if url.endswith("format=xlsx"):
            try:
                abas = pd.read_excel(
                    io.BytesIO(content), sheet_name=None, engine="openpyxl"
                )
                for _, df_aba in abas.items():
                    if not df_aba.empty and df_aba.shape[1] > 1:
                        return df_aba
            except Exception:
                pass

        for csv_kwargs in (
            {"sep": None, "engine": "python", "encoding": "utf-8"},
            {"sep": ";", "encoding": "latin-1"},
            {"sep": ",", "encoding": "utf-8"},
        ):
            csv_kwargs: Dict[str, Any] = dict(csv_kwargs)
            try:
                df = pd.read_csv(io.BytesIO(content), **csv_kwargs)
                if not df.empty and df.shape[1] > 1:
                    return df
            except Exception:
                continue

        try:
            df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
            if not df.empty and df.shape[1] > 1:
                return df
        except Exception:
            continue
    return pd.DataFrame()


# ====================================================
# 6. UTILITÁRIOS
# ====================================================
class Utilitarios:
    @staticmethod
    def buscar_coluna(df: pd.DataFrame, palavras_chave: List[str]) -> Optional[str]:
        cols_upper = {str(c).upper().strip(): str(c) for c in df.columns}
        for palavra in palavras_chave:
            key = palavra.upper().strip()
            if key in cols_upper:
                return cols_upper[key]
        return None

    @staticmethod
    def encontrar_coluna_data(df: pd.DataFrame) -> Optional[str]:
        return Utilitarios.buscar_coluna(
            df,
            ["Data Agendamento", "Data Conclusão", "Data", "Date", "Data_Execucao"],
        )

    @staticmethod
    def normalizar_chave_string(series: pd.Series) -> pd.Series:
        """Limpa floats (.0), tira espaços extras e coloca em caixa alta para dar match exato."""
        return (
            series.astype(str)
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
            .str.upper()
        )

    @staticmethod
    def calcular_variacao(vf: float, vg: float) -> tuple[str, str]:
        if vg == 0 or pd.isna(vg):
            return "neutra", "S/D"
        if abs(vf - vg) < 0.0001:
            return "neutra", "Visão Geral"
        p = ((vf - vg) / vg) * 100
        if p > 0:
            return "positiva", f"+{Utilitarios.formatar_numero(p, 1)}%"
        if p < 0:
            return "negativa", f"{Utilitarios.formatar_numero(p, 1)}%"
        return "neutra", "0%"

    @staticmethod
    def calcular_share(vf: float, vg: float) -> tuple[str, str]:
        if vg == 0 or pd.isna(vg):
            return "neutra", "0% do Total"
        if abs(vf - vg) < 0.0001:
            return "neutra", "Visão Geral"
        share = (vf / vg) * 100
        return "share", f"{Utilitarios.formatar_numero(share, 1)}% do Total"

    @staticmethod
    def formatar_numero(v: float, casas_decimais: int = 0) -> str:
        if pd.isna(v):
            return "0," + "0" * casas_decimais if casas_decimais else "0"
        return (
            f"{v:,.{casas_decimais}f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    @staticmethod
    def formatar_posicao(valor: Any) -> str:
        try:
            v = int(valor)
            return {1: f"🥇 {v}º", 2: f"🥈 {v}º", 3: f"🥉 {v}º"}.get(v, f"{v}º")
        except (ValueError, TypeError):
            return str(valor)

    @staticmethod
    def colorir_metas(valor: Any) -> str:
        try:
            v = float(valor)
        except (ValueError, TypeError):
            return ""
        if v >= 400:
            return (
                "background-color:#1E3A8A;color:#FFFFFF;font-weight:800;"
                "border-left:3px solid #0F172A;text-align:center;"
            )
        if v >= 300:
            return (
                "background-color:#DCFCE7;color:#166534;font-weight:700;"
                "border-left:3px solid #22C55E;text-align:center;"
            )
        if v >= 275:
            return (
                "background-color:#FEF9C3;color:#854D0E;font-weight:700;"
                "border-left:3px solid #EAB308;text-align:center;"
            )
        return "font-weight:700;border-left:3px solid #EF4444;text-align:center;"

    @staticmethod
    def calcular_dias_uteis(
        df: pd.DataFrame, col_data: Optional[str] = None
    ) -> tuple[int, int, Any, int]:
        col = col_data or Utilitarios.encontrar_coluna_data(df)
        data_max: Any = (
            pd.to_datetime(df[col].max()).date()
            if col and pd.notna(df[col].max())
            else datetime.date.today()
        )
        ano, mes = data_max.year, data_max.month
        primeiro = datetime.date(ano, mes, 1)
        _, ult = calendar.monthrange(ano, mes)
        ultimo = datetime.date(ano, mes, ult)

        p_np = np.datetime64(primeiro)
        m_np = np.datetime64(data_max)
        u_np = np.datetime64(ultimo)

        weekmask = "1111110"  # seg-sáb = 1 | dom = 0
        total = int(
            np.busday_count(p_np, u_np + np.timedelta64(1, "D"), weekmask=weekmask)
        )
        passados = int(
            np.busday_count(p_np, m_np + np.timedelta64(1, "D"), weekmask=weekmask)
        )
        brutos = max(0, total - passados)
        seguros = max(1, brutos)
        return brutos, seguros, data_max, passados

    @staticmethod
    def converter_data(series: pd.Series) -> pd.Series:
        if pd.api.types.is_datetime64_any_dtype(series):
            return series
        s = series.astype(str).str.strip()
        validos = s[~s.str.lower().isin(["", "nan", "nat", "none"])]
        if validos.empty:
            return pd.to_datetime(series, errors="coerce")
        if validos.str.match(r"^\d{4}-\d{1,2}-\d{1,2}").mean() > 0.6:
            return pd.to_datetime(s, errors="coerce")
        partes = validos.str.extract(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})$")
        if partes.empty or partes[0].isna().all():
            return pd.to_datetime(s, errors="coerce", dayfirst=True)
        p1 = pd.to_numeric(partes[0], errors="coerce")
        p2 = pd.to_numeric(partes[1], errors="coerce")
        if (p1 > 12).any():
            return pd.to_datetime(s, errors="coerce", dayfirst=True)
        if (p2 > 12).any():
            return pd.to_datetime(s, errors="coerce", dayfirst=False)
        return pd.to_datetime(s, errors="coerce", dayfirst=True)

    @staticmethod
    def normalizar_pontos(series: pd.Series) -> pd.Series:
        if series is None or series.empty:
            return pd.Series(dtype=float)
        if pd.api.types.is_numeric_dtype(series):
            return series.fillna(0.0).astype(float)
        s = series.astype(str).str.strip().str.replace(r"[^\d.,\-]", "", regex=True)
        has_comma = s.str.contains(",")
        has_dot = s.str.contains(r"\.")
        s = s.where(
            ~(has_comma & has_dot),
            s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
        )
        s = s.where(~has_comma | has_dot, s.str.replace(",", ".", regex=False))
        return pd.to_numeric(s, errors="coerce").fillna(0.0).astype(float)


# ====================================================
# 7. FUNÇÃO DE MERGE PRODUÇÃO (CódAuxEquip) X ATIVOS (Login)
# ====================================================
def realizar_merge_producao_ativos(
    df_prod: pd.DataFrame, df_ativos: pd.DataFrame
) -> pd.DataFrame:
    """
    Realiza LEFT JOIN da Produção com a Lista Ativos:
    Unindo CódAuxEquip (Produção) == Login (Lista Ativos).
    """
    if df_prod.empty or df_ativos.empty:
        return df_prod

    # Procura CódAuxEquip na tabela de Produção
    col_prod_key = Utilitarios.buscar_coluna(
        df_prod,
        [
            "CódAuxEquipe",
        ],
    )

    # Procura Login na tabela Lista Ativos
    col_ativos_key = Utilitarios.buscar_coluna(
        df_ativos, ["Login", "LOGIN", "CodAuxEquipe", "RE", "MATRICULA"]
    )

    if not col_prod_key or not col_ativos_key:
        return df_prod

    df_p = df_prod.copy()
    df_a = df_ativos.copy()

    # Normalização das chaves (ex: "Z638189" == "Z638189")
    df_p["__chave_merge__"] = Utilitarios.normalizar_chave_string(df_p[col_prod_key])
    df_a["__chave_merge__"] = Utilitarios.normalizar_chave_string(df_a[col_ativos_key])

    # Remove duplicados na base de ativos para evitar efeito multiplicador
    df_a = df_a.drop_duplicates(subset=["__chave_merge__"], keep="first")

    # Realiza o Merge mantendo todos os registros de produção
    df_merged = df_p.merge(
        df_a, on="__chave_merge__", how="left", suffixes=("", "_ativos")
    )
    df_merged = df_merged.drop(columns=["__chave_merge__"])

    return df_merged


class Graficos:
    @staticmethod
    def grafico_combo_raiox(
        df: pd.DataFrame,
        x_col: str,
        y_bar: str,
        y_line: str,
        meta_dia: Optional[float] = None,
    ) -> go.Figure:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=df[x_col],
                y=df[y_bar],
                name="Volume O.S.",
                marker_color="#CBD5E1",
                opacity=0.8,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df[x_col],
                y=df[y_line],
                name="Pontos",
                mode="lines+markers",
                line=dict(color="#012869", width=3),
                marker=dict(size=8, color="#F37C04"),
                yaxis="y2",
            )
        )
        if meta_dia and meta_dia > 0:
            fig.add_hline(
                y=meta_dia,
                line_dash="dash",
                line_color="#F37C04",
                annotation_text=f"Meta/dia necessária: {Utilitarios.formatar_numero(meta_dia, 1)} pts",
                annotation_position="top left",
            )
        fig.update_layout(
            margin=dict(l=0, r=50, t=30, b=0),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            hovermode="x unified",
            yaxis=dict(
                title="Quantidade O.S.", showgrid=True, gridcolor="rgba(0,0,0,0.05)"
            ),
            yaxis2=dict(
                title="Pontos",
                overlaying="y",
                side="right",
                showgrid=False,
                tickformat=".1f",
            ),
            xaxis=dict(showgrid=False),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        return fig


# ====================================================
# 8. PROCESSAMENTO (METAS E CONTEXTO)
# ====================================================
METAS_MENSAIS = (300, 350, 375, 400)
META_PRINCIPAL = 400


class ProcessamentoDados:
    @staticmethod
    def calcular_painel_metas(
        pontos_atuais: float, dias_restantes: int
    ) -> pd.DataFrame:
        seguros = max(1, dias_restantes)
        linhas: List[Dict[str, Any]] = []
        for meta in METAS_MENSAIS:
            falta = max(0.0, float(meta) - pontos_atuais)
            pct = min(100.0, (pontos_atuais / meta) * 100) if meta else 0.0
            necessario = falta / seguros
            _, txt_var = Utilitarios.calcular_variacao(pontos_atuais, float(meta))

            if pontos_atuais >= meta:
                situacao = "✅ Atingida"
            elif necessario <= 100:
                situacao = "🎯 Em busca"
            else:
                situacao = "🔴 Exige ritmo alto"

            linhas.append(
                {
                    "Meta": meta,
                    "Pontos Atuais": round(pontos_atuais, 2),
                    "Progresso": round(pct, 1),
                    "Faltam": round(falta, 1),
                    "Pontos/Dia Necessário": round(necessario, 2),
                    "Vs Meta": txt_var,
                    "Situação": situacao,
                }
            )
        return pd.DataFrame(linhas)

    @staticmethod
    def calcular_contexto_geral(
        df_global: pd.DataFrame,
        col_pontos: str,
        col_tec: Optional[str],
        identidade: Optional[str],
    ) -> tuple[float, int, Optional[int]]:
        pontos_globais = float(df_global[col_pontos].sum())
        if not col_tec or col_tec not in df_global.columns or not identidade:
            return pontos_globais, 0, None
        try:
            serie_tec = df_global[col_tec].astype(str).str.strip().str.upper()
            ranking = (
                df_global.assign(__tec=serie_tec)
                .groupby("__tec")[col_pontos]
                .sum()
                .sort_values(ascending=False)
            )
            total_tecnicos = int(len(ranking))
            ident = identidade.strip().upper()
            posicao: Optional[int] = None
            if ident in ranking.index:
                loc = ranking.index.get_loc(ident)
                if isinstance(loc, (int, np.integer)):
                    posicao = int(loc) + 1
            return pontos_globais, total_tecnicos, posicao
        except Exception:
            return pontos_globais, 0, None


_TEMAS_CARD = {
    "azul": {
        "fundo": "#F0F9FF",
        "texto": "#012869",
        "borda": "#0EA5E9",
        "titulo": "#075985",
    },
    "verde": {
        "fundo": "#F0FDF4",
        "texto": "#15803D",
        "borda": "#22C55E",
        "titulo": "#166534",
    },
    "laranja": {
        "fundo": "#FFF7ED",
        "texto": "#F37C04",
        "borda": "#F97316",
        "titulo": "#9A3412",
    },
    "cinza": {
        "fundo": "#F8FAFC",
        "texto": "#334155",
        "borda": "#94A3B8",
        "titulo": "#64748B",
    },
    "escuro": {
        "fundo": "#0F172A",
        "texto": "#F8FAFC",
        "borda": "#64748B",
        "titulo": "#94A3B8",
    },
}


def _criar_card_tooltip(
    titulo: str,
    valor: str,
    tema: str = "azul",
    subtitulo: str = "",
    icone: str = "",
    tooltip: str = "",
) -> str:
    cores = _TEMAS_CARD.get(tema, _TEMAS_CARD["azul"])
    html_tooltip = f'<div class="tooltip-premium">{tooltip}</div>' if tooltip else ""
    return f"""
    <div class="card-premium" style="background:{cores['fundo']};padding:20px;border-radius:10px; border-left:5px solid {cores['borda']}; box-shadow:0 4px 6px rgba(0,0,0,0.05); height:100%;display:flex;flex-direction:column; justify-content:center; transition:transform 0.2s, box-shadow 0.2s;" onmouseover="this.style.transform='translateY(-3px)'; this.style.boxShadow='0 8px 15px rgba(0,0,0,0.1)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px rgba(0,0,0,0.05)';">
        <p style="margin:0;font-size:14px;color:{cores['titulo']};font-weight:700;">{icone} {titulo}</p>
        <h2 style="margin:5px 0 0;color:{cores['texto']};font-weight:900;font-size:32px;">{valor}</h2>
        <p style="margin:5px 0 0;font-size:12px;color:{'#94A3B8' if tema == 'escuro' else '#64748B'};font-weight:600;">{subtitulo}</p>
        {html_tooltip}
    </div>
    """


# ====================================================
# 9. INICIALIZAÇÃO DA INTERFACE & EXECUÇÃO DO MERGE
# ====================================================
aplicar_estilo()
aplicar_tema_claro()
injetar_css_menu_sidebar()
render_sidebar_perfil()

nome_exibicao = nome_logado.title() if nome_logado else (user_logado or login_logado)

render_hero_totale_1(
    titulo="Prévia de Produtividade",
    subtitulo=f"Auditoria de O.S., Pontos e Metas para o técnico(a) {nome_exibicao.upper()}",
    icone="bar_chart",
    badge="Painel do Técnico",
    usar_material=True,
)

loader = st.empty()
loader.markdown(
    """<div class="loading-totale">
        <span style="color:#012869; font-weight:700;">⚡ Sincronizando produção e lista de ativos...</span>
        <span style="color:#F37C04; font-weight:800; font-size:13px;">Aguarde</span>
    </div>""",
    unsafe_allow_html=True,
)

df_prod_raw = carregar_base_producao()
df_ativos_raw = carregar_base_ativos()

# 🔗 EXECUTA O MERGE: Produção (CódAuxEquip) ↔ Lista Ativos (Login)
df_raw = realizar_merge_producao_ativos(df_prod_raw, df_ativos_raw)

loader.empty()

if df_raw.empty:
    render_insight(
        "Não foi possível carregar a base de produção do Google Sheets. Verifique o compartilhamento da planilha.",
        "critico",
    )
    st.stop()


# ====================================================
# 10. FILTRAGEM DO TÉCNICO LOGADO
# ====================================================
def filtrar_tecnico(df: pd.DataFrame) -> pd.DataFrame:
    mask = pd.Series(False, index=df.index)
    colunas_identidade = {
        "LOGIN",
        "MATRICULA",
        "MATRÍCULA",
        "RE",
        "NETSALES",
        "ID",
        "CODIGO",
        "CÓDIGO",
        "USER",
        "USUARIO",
        "USUÁRIO",
        "USERNAME",
        "CODAUXEQUIP",
        "CODAUXEQUIPE",
        "COD_AUX_EQUIPE",
    }
    colunas_nome = {
        "TECNICO",
        "TÉCNICO",
        "VENDEDOR",
        "NOME",
        "NOME EQUIPE",
        "NOME TÉCNICO",
        "NOME_TECNICO",
        "COLABORADOR",
    }

    for col in df.columns:
        col_name = str(col).strip().upper()
        col_series = df[col].astype(str).str.strip().str.upper()

        if col_name in colunas_identidade:
            if login_logado:
                mask |= col_series.eq(login_logado)
            if user_logado:
                mask |= col_series.eq(user_logado)

        if col_name in colunas_nome:
            if nome_logado:
                mask |= col_series.eq(nome_logado)
    return df[mask].copy()


df_prod = filtrar_tecnico(df_raw)

if df_prod.empty:
    render_insight(
        f"Nenhum registro de produção localizado para <b>{nome_exibicao}</b> "
        f"(Login: <b>{login_logado or '—'}</b> · User: <b>{user_logado or '—'}</b>).",
        "alerta",
    )
    st.stop()

col_tec_global = Utilitarios.buscar_coluna(
    df_raw, ["TECNICO", "TÉCNICO", "NOME", "COLABORADOR", "NOME EQUIPE"]
)
identidade_tec: Optional[str] = None
if col_tec_global and col_tec_global in df_prod.columns:
    try:
        moda = df_prod[col_tec_global].dropna().astype(str).str.strip().mode()
        if not moda.empty:
            identidade_tec = str(moda.iloc[0])
    except Exception:
        identidade_tec = None

col_data = Utilitarios.buscar_coluna(
    df_prod, ["DATA", "DATA AGENDAMENTO", "DATA CONCLUSÃO", "DATA_EXECUCAO", "DATE"]
)
if col_data:
    df_prod[col_data] = Utilitarios.converter_data(df_prod[col_data]).dt.date

# ====================================================
# 11. FILTROS DE PERÍODO
# ====================================================
with st.container(border=True):
    render_section_header("🎯", "Filtro de Período")
    mask_data = pd.Series(True, index=df_prod.index)

    if (
        col_data
        and col_data in df_prod.columns
        and not df_prod[col_data].dropna().empty
    ):
        min_date = df_prod[col_data].dropna().min()
        max_date = df_prod[col_data].dropna().max()

        default_ini = st.session_state.get("filtro_data_inicio", min_date)
        default_fim = st.session_state.get("filtro_data_fim", max_date)
        default_ini = max(min_date, min(default_ini, max_date))
        default_fim = max(min_date, min(default_fim, max_date))

        c1, c2, c3 = st.columns([1.2, 1.2, 1.6])
        with c1:
            data_inicio = st.date_input(
                "📅 Data inicial",
                value=default_ini,
                min_value=min_date,
                max_value=max_date,
                format="DD/MM/YYYY",
                key="data_inicio_input",
            )
        with c2:
            data_fim = st.date_input(
                "📅 Data final",
                value=default_fim,
                min_value=min_date,
                max_value=max_date,
                format="DD/MM/YYYY",
                key="data_fim_input",
            )
        with c3:
            st.write("")
            st.write("")
            b1, b2, b3 = st.columns(3)
            if b1.button("Hoje", use_container_width=True):
                st.session_state["filtro_data_inicio"] = max_date
                st.session_state["filtro_data_fim"] = max_date
                st.rerun()
            if b2.button("7 dias", use_container_width=True):
                st.session_state["filtro_data_inicio"] = max(
                    min_date, max_date - timedelta(days=6)
                )
                st.session_state["filtro_data_fim"] = max_date
                st.rerun()
            if b3.button("Mês", use_container_width=True):
                st.session_state["filtro_data_inicio"] = max(
                    min_date, max_date.replace(day=1)
                )
                st.session_state["filtro_data_fim"] = max_date
                st.rerun()

        if data_inicio > data_fim:
            render_insight(
                "A **data inicial** não pode ser maior que a **data final**.", "alerta"
            )
            st.stop()

        mask_data &= (df_prod[col_data] >= data_inicio) & (
            df_prod[col_data] <= data_fim
        )

    df_tec_prod = df_prod[mask_data].copy()

if df_tec_prod.empty:
    st.info("💡 Nenhuma produção encontrada para o período selecionado.")
    st.stop()

st.divider()

# ====================================================
# 12. PROCESSAMENTO DE PONTOS, DIAS ÚTEIS E MÉTRICAS
# ====================================================
col_pontos = Utilitarios.buscar_coluna(
    df_tec_prod, ["PONTOS", "PONTO", "PTS", "PONTUACAO", "PREVIA"]
)
col_origem = Utilitarios.buscar_coluna(
    df_tec_prod, ["ORIGEM", "TIPO", "SISTEMA", "FONTE", "TIPO_OS", "__ORIGEM__"]
)
col_prod_especifica = Utilitarios.buscar_coluna(
    df_tec_prod, ["PONTOS_PROD", "PROD_PONTOS", "PONTOS PROD"]
)
col_gpon_especifica = Utilitarios.buscar_coluna(
    df_tec_prod, ["PONTOS_GPON", "GPON_PONTOS", "PONTOS GPON"]
)

if col_pontos:
    df_tec_prod[col_pontos] = Utilitarios.normalizar_pontos(df_tec_prod[col_pontos])

pontos_prod = 0.0
pontos_gpon = 0.0

if col_prod_especifica and col_gpon_especifica:
    df_tec_prod[col_prod_especifica] = Utilitarios.normalizar_pontos(
        df_tec_prod[col_prod_especifica]
    )
    df_tec_prod[col_gpon_especifica] = Utilitarios.normalizar_pontos(
        df_tec_prod[col_gpon_especifica]
    )
    pontos_prod = float(df_tec_prod[col_prod_especifica].sum())
    pontos_gpon = float(df_tec_prod[col_gpon_especifica].sum())
elif col_origem and col_pontos:
    origem_series = df_tec_prod[col_origem].astype(str).str.upper()
    mask_prod = origem_series.str.contains("PROD", na=False)
    mask_gpon = origem_series.str.contains("GPON", na=False)
    pontos_prod = float(df_tec_prod.loc[mask_prod, col_pontos].sum())
    pontos_gpon = float(df_tec_prod.loc[mask_gpon, col_pontos].sum())
    outros = float(df_tec_prod.loc[~(mask_prod | mask_gpon), col_pontos].sum())
    pontos_gpon += outros
elif col_pontos:
    pontos_gpon = float(df_tec_prod[col_pontos].sum())

t_os = len(df_tec_prod)
t_pontos = pontos_prod + pontos_gpon

# Dias úteis sem domingos
dias_brutos, dias_seguros, data_ref, dias_passados = Utilitarios.calcular_dias_uteis(
    df_tec_prod, col_data=col_data
)

dias_com_os = 1
if (
    col_data
    and col_data in df_tec_prod.columns
    and not df_tec_prod[col_data].dropna().empty
):
    datas_validas = pd.to_datetime(df_tec_prod[col_data]).dropna()
    dias_com_os = max(datas_validas.dt.normalize().nunique(), 1)

media_diaria = t_pontos / dias_com_os
t_projecao = t_pontos + (media_diaria * dias_brutos)

sub_proj = f"Média {Utilitarios.formatar_numero(media_diaria, 2)} pts/dia × {dias_brutos} dias restantes"
tip_proj = (
    f"Projeção = {Utilitarios.formatar_numero(t_pontos, 2)} pts atuais + "
    f"({Utilitarios.formatar_numero(media_diaria, 2)} pts/dia × {dias_brutos} dias úteis restantes, sem domingos). "
    f"Referência: {pd.Timestamp(data_ref).strftime('%d/%m/%Y')}."
)

media_pontos = t_pontos / t_os if t_os > 0 else 0.0

pontos_globais = 0.0
t_os_global = 0
posicao_geral: Optional[int] = None
total_tecnicos = 0

# 🆕 Detecta a coluna de Projeto na base
col_projeto = Utilitarios.buscar_coluna(
    df_raw, ["PROJETO", "CAMPANHA", "OPERAÇÃO", "OPERACAO", "CONTRATO_PROJETO"]
)

# 🆕 Descobre o projeto do técnico logado
projeto_tecnico: Optional[str] = None
if col_projeto and col_projeto in df_tec_prod.columns:
    try:
        moda_proj = df_tec_prod[col_projeto].dropna().astype(str).str.strip().mode()
        if not moda_proj.empty:
            projeto_tecnico = str(moda_proj.iloc[0])
    except Exception:
        projeto_tecnico = None

pontos_projeto = 0.0  # 🆕 Total de pontos do projeto do técnico

if col_pontos and col_pontos in df_raw.columns:
    df_global = df_raw.copy()
    df_global[col_pontos] = Utilitarios.normalizar_pontos(df_global[col_pontos])
    pontos_globais = float(df_global[col_pontos].sum())
    t_os_global = len(df_global)
    pontos_globais, total_tecnicos, posicao_geral = (
        ProcessamentoDados.calcular_contexto_geral(
            df_global, col_pontos, col_tec_global, identidade_tec
        )
    )

    # 🆕 Filtra apenas os pontos do projeto do técnico
    if col_projeto and projeto_tecnico and col_projeto in df_global.columns:
        proj_series = df_global[col_projeto].astype(str).str.strip().str.upper()
        mask_proj = proj_series == projeto_tecnico.strip().upper()
        pontos_projeto = float(df_global.loc[mask_proj, col_pontos].sum())
    else:
        pontos_projeto = pontos_globais  # fallback: usa geral se não achar projeto

# 🔁 ALTERADO: Share agora é calculado sobre o PROJETO, não sobre o geral
classe_share, txt_share = Utilitarios.calcular_share(t_pontos, pontos_projeto)
media_os_geral = pontos_globais / t_os_global if t_os_global > 0 else 0.0
classe_var, txt_var = Utilitarios.calcular_variacao(media_pontos, media_os_geral)
icone_var = {"positiva": "⬆️", "negativa": "⬇️"}.get(classe_var, "➖")

df_metas = ProcessamentoDados.calcular_painel_metas(t_pontos, dias_brutos)
meta_dia_principal = (
    float(
        df_metas.loc[df_metas["Meta"] == META_PRINCIPAL, "Pontos/Dia Necessário"].iloc[
            0
        ]
    )
    if not df_metas.empty
    else 0.0
)

# ====================================================
# 13. DASHBOARD OPERACIONAL & CARDS
# ====================================================
render_section_header("⚙️", "Resumo de Execução Física")
kr1, kr2, kr3, kr4 = st.columns(4)

with kr1:
    st.markdown(
        _criar_card_tooltip(
            "O.S. Realizadas",
            str(t_os),
            "cinza",
            "Visitas executadas",
            "📋",
            "Total O.S. no período",
        ),
        unsafe_allow_html=True,
    )
with kr2:
    st.markdown(
        _criar_card_tooltip(
            "Prévia de Pontos",
            Utilitarios.formatar_numero(t_pontos, 2),
            "azul",
            f"Prod: {Utilitarios.formatar_numero(pontos_prod, 2)} | Gpon: {Utilitarios.formatar_numero(pontos_gpon, 2)}",
            "🎯",
            "Prévia total (Prod + Gpon)",
        ),
        unsafe_allow_html=True,
    )
with kr3:
    st.markdown(
        _criar_card_tooltip(
            "Projeção Fim do Mês",
            Utilitarios.formatar_numero(t_projecao, 2),
            "escuro",
            sub_proj,
            "📈",
            tip_proj,
        ),
        unsafe_allow_html=True,
    )
with kr4:
    st.markdown(
        _criar_card_tooltip(
            "Média por O.S.",
            Utilitarios.formatar_numero(media_pontos, 2),
            "verde",
            f"{icone_var} {txt_var} vs média da operação",
            "📊",
            f"Média da operação: {Utilitarios.formatar_numero(media_os_geral, 2)} pts/O.S.",
        ),
        unsafe_allow_html=True,
    )

st.write("")

st.write("")

# 🔁 ALTERADO: Removido card "Posição no Ranking" — agora são 3 cards
kr6, kr7, kr8 = st.columns(3)

with kr6:
    # 🔁 Subtítulo dinâmico com o nome do projeto
    sub_share = (
        f"Participação no projeto {projeto_tecnico}"
        if projeto_tecnico
        else "Participação no total"
    )
    tip_share = (
        f"Seus pontos ÷ pontos totais do projeto <b>{projeto_tecnico}</b>. "
        f"Total do projeto: {Utilitarios.formatar_numero(pontos_projeto, 2)} pts."
        if projeto_tecnico
        else "Seus pontos ÷ pontos totais da operação"
    )
    st.markdown(
        _criar_card_tooltip(
            "Share de Pontos",
            txt_share,
            "azul",
            sub_share,
            "🧩",
            tip_share,
        ),
        unsafe_allow_html=True,
    )
with kr7:
    st.markdown(
        _criar_card_tooltip(
            "Média Pontos/Dia",
            Utilitarios.formatar_numero(media_diaria, 2),
            "verde",
            f"Em {dias_com_os} dia(s) com produção",
            "⚡",
            "Pontos totais ÷ dias efetivamente com O.S.",
        ),
        unsafe_allow_html=True,
    )
with kr8:
    st.markdown(
        _criar_card_tooltip(
            "Dias Úteis Restantes",
            str(dias_brutos),
            "cinza",
            f"Mês de referência: {pd.Timestamp(data_ref).strftime('%m/%Y')}",
            "📆",
            "Segunda a sábado (sem domingos), até o fim do mês",
        ),
        unsafe_allow_html=True,
    )

st.write("---")

# ====================================================
# 14. PAINEL DE METAS
# ====================================================
render_section_header("🏆", "Painel de Metas Mensais")


def _aplicar_styler(df: pd.DataFrame, func: Any, coluna: str) -> Any:
    subset = cast(Any, [coluna])
    if hasattr(df.style, "map"):
        return df.style.map(func, subset=subset)
    estilo_antigo = getattr(df.style, "applymap", None)
    if estilo_antigo is not None:
        return estilo_antigo(func, subset=subset)
    return df.style


if not df_metas.empty and col_pontos:
    styler_metas = _aplicar_styler(
        df_metas, Utilitarios.colorir_metas, "Pontos/Dia Necessário"
    )

    st.dataframe(
        styler_metas,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Meta": st.column_config.NumberColumn("🎯 Meta Mensal", format="%.2f"),
            "Pontos Atuais": st.column_config.NumberColumn(
                "📌 Pontos Atuais", format="%.2f"
            ),
            "Progresso": st.column_config.ProgressColumn(
                "📊 Progresso", min_value=0.0, max_value=100.0, format="%.1f%%"
            ),
            "Faltam": st.column_config.NumberColumn("➖ Faltam", format="%.2f"),
            "Pontos/Dia Necessário": st.column_config.NumberColumn(
                "📅 Pontos/Dia Necessário",
                format="%.2f",
                help="Faltam ÷ dias úteis restantes (sem domingos)",
            ),
            "Vs Meta": st.column_config.TextColumn("📈 Vs Meta"),
            "Situação": st.column_config.TextColumn("Status"),
        },
    )
    st.caption(
        "🎨 **Régua de cores** (Pontos/Dia Necessário): 🟦 ≥ 400 · 🟩 ≥ 300 · 🟨 ≥ 275 · 🟥 < 275"
    )
else:
    st.info("💡 Coluna de pontos não identificada — Painel de Metas indisponível.")

st.write("---")

# ====================================================
# 15. EVOLUÇÃO TEMPORAL
# ====================================================
if col_data and col_data in df_tec_prod.columns and col_pontos:
    render_section_header("📊", "Evolução Diária vs Meta")
    df_tempo = (
        df_tec_prod.groupby(col_data)
        .agg(Pontos=(col_pontos, "sum"), Qtd_OS=(col_pontos, "count"))
        .reset_index()
        .sort_values(col_data)
    )
    st.plotly_chart(
        Graficos.grafico_combo_raiox(
            df_tempo, col_data, "Qtd_OS", "Pontos", meta_dia=meta_dia_principal
        ),
        use_container_width=True,
        config={"displayModeBar": False},
    )
    st.caption(
        f"➖ Linha tracejada = ritmo diário necessário para alcançar a meta de "
        f"**{Utilitarios.formatar_numero(META_PRINCIPAL, 2)} pontos** no mês "
        f"({Utilitarios.formatar_numero(meta_dia_principal, 2)} pts/dia)."
    )

st.write("---")
