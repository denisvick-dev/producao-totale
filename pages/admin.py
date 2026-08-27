# pages/admin.py
import io
import calendar
import datetime
import locale
import requests
from datetime import timedelta
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# ====================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ====================================================
st.set_page_config(
    page_title="Painel Admin | TOTALE",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ====================================================
# 2. PROTEÇÃO DE ACESSO (AUTENTICAÇÃO + PERFIL ADMIN)
# ====================================================
if not st.session_state.get("authenticated", False):
    st.switch_page("streamlit_app.py")

info_logado = st.session_state.get("user_info", {}) or {}
nome_logado = str(info_logado.get("tecnico", "")).strip().upper()
login_logado = str(info_logado.get("login", "")).strip().upper()
user_logado = str(info_logado.get("user", "")).strip().upper()
perfil_logado = str(info_logado.get("perfil", "")).strip().upper()

# ── Gate de Admin ──
ADMIN_IDENTIFIERS = {
    "ADMIN",
    "ADM",
    "ADMINISTRADOR",
    "GESTOR",
    "MANAGER",
    "SUPERVISOR",
    "COORDENADOR",
}
is_admin = perfil_logado in ADMIN_IDENTIFIERS or login_logado.startswith("ADM")

if not is_admin:
    st.error(
        "🔒 **Acesso Negado** — Esta área é restrita a administradores e gestores."
    )
    st.info(
        f"Seu perfil atual: **{perfil_logado or 'TÉCNICO'}**. Solicite acesso ao administrador do sistema."
    )
    if st.button("⬅️ Voltar para Produção", type="primary"):
        st.switch_page("pages/producao.py")
    st.stop()

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
# 4. CSS UNIFICADO (ADMIN)
# ====================================================
def injetar_css_admin() -> None:
    st.markdown(
        """
        <style>
        /* ── Sidebar Admin (tema escuro) ── */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0F172A 0%, #1E293B 100%) !important;
            border-right: 1px solid #334155 !important;
        }
        
        /* Oculta os itens Consultivo e Produção no menu lateral SOMENTE nesta página */
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:first-child { display: none !important; }
        [data-testid="stSidebarNav"] a[href*="consultivo"] { display: none !important; }
        [data-testid="stSidebarNav"] a[href*="producao"] { display: none !important; }

        /* Estiliza o botão Admin */
        [data-testid="stSidebarNav"] a[href*="admin"] span { font-size: 0 !important; }
        [data-testid="stSidebarNav"] a[href*="admin"] span::before { content: "🛡️ Admin" !important; font-size: 14px !important; font-weight: 700 !important; color: #F8FAFC !important; }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
            background: rgba(255,255,255,0.05) !important;
            border: 1px solid #334155 !important;
            border-radius: 8px !important;
            margin: 4px 16px !important;
            padding: 10px 14px !important;
            transition: all 0.2s ease;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"],
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-selected="true"] {
            background: linear-gradient(90deg, rgba(249,115,22,0.15) 0%, rgba(249,115,22,0.05) 100%) !important;
            border: 1px solid #F97316 !important;
            border-left: 4px solid #F97316 !important;
        }

        section[data-testid="stSidebar"] .admin-profile-card,
        section[data-testid="stSidebar"] .admin-profile-card div,
        section[data-testid="stSidebar"] .admin-profile-card p,
        section[data-testid="stSidebar"] .admin-profile-card span {
            color: #F8FAFC !important;
        }
        section[data-testid="stSidebar"] .admin-profile-card .admin-profile-label { color: #F97316 !important; }
        section[data-testid="stSidebar"] .admin-profile-card .admin-profile-login { color: #CBD5E1 !important; }
        section[data-testid="stSidebar"] .admin-profile-card .admin-profile-login-value { color: #FFFFFF !important; }
        section[data-testid="stSidebar"] .admin-profile-card .admin-profile-status { color: #FCA5A5 !important; }
        section[data-testid="stSidebar"] .admin-profile-card .badge-admin { color: #FFFFFF !important; }
        section[data-testid="stSidebar"] .admin-profile-card .admin-profile-avatar { color: #FFFFFF !important; }

        .btn-logout button {
            background: linear-gradient(180deg, #334155 0%, #1E293B 100%) !important;
            border: 1px solid #475569 !important;
            color: #F8FAFC !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            margin-top: 10px !important;
        }
        .btn-logout button:hover {
            background: #475569 !important;
            border-color: #F97316 !important;
        }

        /* ── Cards Admin ── */
        .card-admin { position: relative; cursor: default; }
        .tooltip-premium {
            visibility: hidden; background-color: #0F172A; color: #F8FAFC;
            text-align: center; border-radius: 8px; padding: 8px 12px;
            position: absolute; z-index: 999; bottom: 115%; left: 50%;
            transform: translateX(-50%); opacity: 0;
            transition: opacity 0.3s ease, bottom 0.3s ease;
            font-size: 11px; font-weight: 500; min-width: 200px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3); pointer-events: none;
        }
        .tooltip-premium::after {
            content: ""; position: absolute; top: 100%; left: 50%;
            margin-left: -6px; border-width: 6px; border-style: solid;
            border-color: #0F172A transparent transparent transparent;
        }
        .card-admin:hover .tooltip-premium { visibility: visible; opacity: 1; bottom: 105%; }

        /* ── Inputs ── */
        [data-testid="stMain"] [data-baseweb="input"],
        [data-testid="stMain"] [data-testid="stDateInput"] > div > div,
        [data-testid="stMain"] div[data-baseweb="select"] > div {
            background-color: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
        }
        [data-testid="stMain"] input {
            color: #0F172A !important;
            font-weight: 600 !important;
            font-size: 14px !important;
        }

        /* ── Badge Admin ── */
        .badge-admin {
            display: inline-flex; align-items: center; gap: 6px;
            background: linear-gradient(90deg, #F97316, #EA580C);
            color: white; font-size: 10px; font-weight: 800;
            padding: 3px 10px; border-radius: 20px;
            letter-spacing: 1px; text-transform: uppercase;
        }

        .loading-totale {
            background: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid #F37C04;
            padding: 16px 20px; border-radius: 10px; margin-bottom: 20px;
            display: flex; align-items: center; justify-content: space-between;
        }

        /* ── Tabs customizadas ── */
        .stTabs [data-baseweb="tab-list"] { gap: 4px; }
        .stTabs [data-baseweb="tab"] {
            background: #F1F5F9; border-radius: 8px 8px 0 0;
            padding: 10px 20px; font-weight: 700; color: #475569;
        }
        .stTabs [aria-selected="true"] {
            background: #012869 !important; color: #FFFFFF !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_admin() -> None:
    partes = nome_logado.split()
    if len(partes) >= 2:
        iniciais = partes[0][0] + partes[1][0]
    elif len(partes) == 1:
        iniciais = partes[0][:2]
    else:
        iniciais = "AD"

    with st.sidebar:
        st.markdown(
            f"""
            <div class="admin-profile-card" style="background: linear-gradient(145deg, #1E293B 0%, #0F172A 100%);
                        border: 1px solid #334155; border-left: 4px solid #F97316;
                        border-radius: 12px; padding: 16px; margin: 16px;">
                <div class="admin-profile-label" style="font-size: 11px; font-weight: 800; letter-spacing: 1.5px; color: #F97316; margin-bottom: 12px;">
                    ⚡ TOTALE · ADMIN
                </div>
                <div class="admin-profile-avatar" style="width: 52px; height: 52px; border-radius: 50%;
                            background: linear-gradient(135deg, #F97316 0%, #DC2626 100%);
                            color: white; display: flex; align-items: center; justify-content: center;
                            font-size: 18px; font-weight: 800; margin-bottom: 12px;
                            box-shadow: 0 4px 10px rgba(249,115,22,0.3);">
                    {iniciais}
                </div>
                <p style="color: #F8FAFC; font-weight: 800; font-size: 14px; margin: 0 0 4px 0;">
                    {nome_logado or 'ADMINISTRADOR'}
                </p>
                <div style="margin-bottom: 12px;">
                    <span class="badge-admin">🛡️ {perfil_logado or 'ADMIN'}</span>
                </div>
                <div style="display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px;">
                    <div class="admin-profile-login" style="font-size: 12px; color: #94A3B8;">
                        Login: <span class="admin-profile-login-value" style="background: #334155; color: #E2E8F0; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-weight: 600;">{login_logado or 'N/A'}</span>
                    </div>
                </div>
                <div class="admin-profile-status" style="background: rgba(239,68,68,0.15); border: 1px solid #EF4444; color: #FCA5A5;
                            padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700;
                            display: inline-flex; align-items: center; gap: 6px;">
                    <div style="width: 6px; height: 6px; background: #EF4444; border-radius: 50%;"></div>
                    Sessão Admin
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="btn-logout">', unsafe_allow_html=True)
        if st.button("🚪 Encerrar Sessão", use_container_width=True):
            st.session_state["authenticated"] = False
            st.switch_page("streamlit_app.py")
        st.markdown("</div>", unsafe_allow_html=True)


# ====================================================
# 5. CARREGAMENTO DAS BASES (PRODUÇÃO + LISTA ATIVOS)
# ====================================================
SPREADSHEET_ID_PRODUCAO = "11Dp9WdZYUrT_LBvfo07Mi8muKXZykU7v"
SPREADSHEET_ID_ATIVOS = "1LQKDcLshC6XSXLBVWaEYSpxrro6uydyU9pwDLc38pEg"


@st.cache_data(ttl=600, show_spinner=False)
def carregar_base_producao() -> pd.DataFrame:
    """Carrega a planilha de produção exportando XLSX para ler todas as abas (Prod + Gpon)."""
    urls_xlsx = [
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID_PRODUCAO}/export?format=xlsx",
    ]
    for url in urls_xlsx:
        try:
            resp = requests.get(url, timeout=35)
            if resp.status_code == 200 and len(resp.content) > 100:
                excel_file = pd.read_excel(
                    io.BytesIO(resp.content), sheet_name=None, engine="openpyxl"
                )
                dfs = []
                for sheet_name, df_sheet in excel_file.items():
                    if not df_sheet.empty and df_sheet.shape[1] > 1:
                        # Adiciona tag de origem conforme o nome da aba se a coluna não existir
                        cols_upper = [str(c).upper().strip() for c in df_sheet.columns]
                        if not any(
                            k in cols_upper
                            for k in ["ORIGEM", "TIPO", "SISTEMA", "FONTE", "TIPO_OS"]
                        ):
                            df_sheet["ORIGEM"] = sheet_name
                        dfs.append(df_sheet)
                if dfs:
                    return pd.concat(dfs, ignore_index=True)
        except Exception:
            pass

    # Fallback para CSV
    urls_csv = [
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID_PRODUCAO}/export?format=csv",
        f"https://drive.google.com/uc?export=download&id={SPREADSHEET_ID_PRODUCAO}",
    ]
    for url in urls_csv:
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 100:
                for sep_val, enc in ((None, "utf-8"), (";", "latin-1"), (",", "utf-8")):
                    try:
                        eng = "python" if sep_val is None else "c"
                        df = pd.read_csv(
                            io.BytesIO(resp.content),
                            sep=sep_val,
                            engine=eng,
                            encoding=enc,
                        )
                        if not df.empty and df.shape[1] > 1:
                            return df
                    except Exception:
                        continue
        except Exception:
            continue
    return pd.DataFrame()


@st.cache_data(ttl=600, show_spinner=False)
def carregar_lista_ativos() -> pd.DataFrame:
    """Carrega a planilha Lista_Ativos para merge."""
    urls = [
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
        for sep_val, enc in ((None, "utf-8"), (";", "latin-1"), (",", "utf-8")):
            try:
                eng = "python" if sep_val is None else "c"
                df = pd.read_csv(
                    io.BytesIO(content), sep=sep_val, engine=eng, encoding=enc
                )
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


def criar_dataframe_completo(
    df_prod: pd.DataFrame, df_ativos: pd.DataFrame
) -> pd.DataFrame:
    """Combina produção e ativos preservando todas as colunas disponíveis."""
    if df_prod.empty:
        return pd.DataFrame()
    if df_ativos.empty:
        return df_prod.copy()

    col_login_ativos = Utilitarios.buscar_coluna(
        df_ativos, ["LOGIN", "MATRICULA", "MATRÍCULA", "RE", "ID", "CODIGO", "USUARIO"]
    )
    col_login_prod = Utilitarios.buscar_coluna(
        df_prod, ["LOGIN", "MATRICULA", "MATRÍCULA", "RE", "ID", "CODIGO", "USUARIO"]
    )
    if not col_login_ativos or not col_login_prod:
        return df_prod.copy()

    producao = df_prod.copy()
    ativos = df_ativos.copy()
    producao[col_login_prod] = (
        producao[col_login_prod].astype(str).str.strip().str.upper()
    )
    ativos[col_login_ativos] = (
        ativos[col_login_ativos].astype(str).str.strip().str.upper()
    )
    return producao.merge(
        ativos,
        left_on=col_login_prod,
        right_on=col_login_ativos,
        how="left",
        suffixes=("", "_ativos"),
    )


# ====================================================
# 6. UTILITÁRIOS
# ====================================================
METAS_MENSAIS = (300, 350, 375, 400)
META_PRINCIPAL = 400


class Utilitarios:
    @staticmethod
    def buscar_coluna(df: pd.DataFrame, palavras_chave: List[str]) -> Optional[str]:
        cols_upper = {str(c).upper().strip(): str(c) for c in df.columns}
        # 1. Match exato
        for palavra in palavras_chave:
            key = palavra.upper().strip()
            if key in cols_upper:
                return cols_upper[key]
        # 2. Match parcial (substring)
        for palavra in palavras_chave:
            key = palavra.upper().strip()
            for col_up, col_real in cols_upper.items():
                if key in col_up:
                    return col_real
        return None

    @staticmethod
    def formatar_numero(v: float, casas: int = 2) -> str:
        """Formata números com 2 casas decimais (padrão para pontos)."""
        if pd.isna(v):
            return "0,00"
        return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def formatar_posicao(valor: Any) -> str:
        try:
            v = int(valor)
            return {1: "🥇 1º", 2: "🥈 2º", 3: "🥉 3º"}.get(v, f"{v}º")
        except (ValueError, TypeError):
            return str(valor)

    @staticmethod
    def normalizar_pontos(series: pd.Series) -> pd.Series:
        """Normalização robusta de números no formato PT-BR ou US."""
        if series is None or series.empty:
            return pd.Series(dtype=float)
        if pd.api.types.is_numeric_dtype(series):
            return series.fillna(0.0).astype(float)

        s = series.astype(str).str.strip().str.replace(r"[^\d.,\-]", "", regex=True)

        has_dot_and_comma = s.str.contains(r"\.") & s.str.contains(",")
        has_only_comma = s.str.contains(",") & ~s.str.contains(r"\.")

        s = s.where(
            ~has_dot_and_comma,
            s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
        )
        s = s.where(~has_only_comma, s.str.replace(",", ".", regex=False))

        return pd.to_numeric(s, errors="coerce").fillna(0.0).astype(float)

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
    def calcular_dias_uteis(
        df: pd.DataFrame, col_data: Optional[str]
    ) -> Tuple[int, int, Any, int]:
        data_max: Any = (
            pd.to_datetime(df[col_data].max()).date()
            if col_data and col_data in df.columns and pd.notna(df[col_data].max())
            else datetime.date.today()
        )
        ano, mes = data_max.year, data_max.month
        primeiro = datetime.date(ano, mes, 1)
        _, ult = calendar.monthrange(ano, mes)
        ultimo = datetime.date(ano, mes, ult)
        p_np = np.datetime64(primeiro)
        m_np = np.datetime64(data_max)
        u_np = np.datetime64(ultimo)
        wm = "1111110"
        total = int(np.busday_count(p_np, u_np + np.timedelta64(1, "D"), weekmask=wm))
        passados = int(
            np.busday_count(p_np, m_np + np.timedelta64(1, "D"), weekmask=wm)
        )
        brutos = max(0, total - passados)
        return brutos, max(1, brutos), data_max, passados

    @staticmethod
    def exportar_excel(abas: Dict[str, pd.DataFrame]) -> bytes:
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for nome, df in abas.items():
                sheet = str(nome)[:31] or "Aba"
                df.to_excel(writer, index=False, sheet_name=sheet)
                ws = writer.sheets[sheet]
                cor_cab = PatternFill("solid", fgColor="012869")
                cor_par = PatternFill("solid", fgColor="F8FAFC")
                cor_impar = PatternFill("solid", fgColor="FFFFFF")
                f_cab = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
                borda = Border(
                    left=Side(style="thin", color="D9D9D9"),
                    right=Side(style="thin", color="D9D9D9"),
                    top=Side(style="thin", color="D9D9D9"),
                    bottom=Side(style="thin", color="D9D9D9"),
                )
                centro = Alignment(horizontal="center", vertical="center")

                for row in ws.iter_rows(
                    min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column
                ):
                    for cel in row:
                        cel.border = borda
                        if cel.row == 1:
                            cel.fill = cor_cab
                            cel.font = f_cab
                            cel.alignment = centro
                            continue
                        cel.fill = cor_par if cel.row % 2 == 0 else cor_impar

                for col in ws.columns:
                    letra = get_column_letter(col[0].column)
                    max_len = max(
                        (len(str(c.value)) for c in col if c.value is not None),
                        default=0,
                    )
                    ws.column_dimensions[letra].width = max(max_len + 3, 12)
                ws.freeze_panes = "A2"
                ws.auto_filter.ref = ws.dimensions
        return output.getvalue()


# ====================================================
# 7. PROCESSAMENTO DE RANKING (CORPORATIVO)
# ====================================================
class ProcessamentoAdmin:
    @staticmethod
    def construir_ranking(
        df: pd.DataFrame,
        col_tec: str,
        col_pontos: str,
        dias_brutos: int,
        dias_seguros: int,
        dias_passados: int,
        col_equipe: Optional[str] = None,
        col_supervisor: Optional[str] = None,
        col_origem: Optional[str] = None,
    ) -> pd.DataFrame:
        group_cols = [col_tec]
        if col_equipe and col_equipe in df.columns and col_equipe not in group_cols:
            group_cols.append(col_equipe)
        if (
            col_supervisor
            and col_supervisor in df.columns
            and col_supervisor not in group_cols
        ):
            group_cols.append(col_supervisor)

        base = (
            df.groupby(group_cols)[col_pontos]
            .sum()
            .reset_index()
            .rename(columns={col_pontos: "Total Pontos"})
            .sort_values("Total Pontos", ascending=False)
            .reset_index(drop=True)
        )
        base.insert(0, "Posição", range(1, len(base) + 1))

        # Contagem de O.S. (Apenas PROD)
        if col_origem and col_origem in df.columns:
            is_prod = (
                df[col_origem].astype(str).str.upper().str.contains("PROD", na=False)
            )
            os_count = df[is_prod].groupby(col_tec).size().reset_index(name="Qtd O.S.")
        else:
            os_count = df.groupby(col_tec).size().reset_index(name="Qtd O.S.")

        base = base.merge(os_count, on=col_tec, how="left").fillna({"Qtd O.S.": 0})

        # Dias trabalhados
        if "Dias Trab Tecnico" in df.columns:
            dias_trab = (
                df.groupby(col_tec)["Dias Trab Tecnico"]
                .max()
                .fillna(dias_passados)
                .astype(int)
            )
        else:
            dias_trab = pd.Series(dias_passados, index=df[col_tec].unique())
        dias_trab = dias_trab.replace(0, 1)
        base["Dias Trab"] = (
            base[col_tec].map(dias_trab).fillna(dias_passados).astype(int)
        )

        # Métricas derivadas
        base["Média/Dia"] = base["Total Pontos"] / base["Dias Trab"]
        base["Média/O.S."] = base["Total Pontos"] / base["Qtd O.S."].replace(0, 1)
        base["Projeção"] = base["Total Pontos"] + (base["Média/Dia"] * dias_brutos)

        return base

    @staticmethod
    def resumo_equipes(
        df_ranking: pd.DataFrame, col_equipe: str
    ) -> Optional[pd.DataFrame]:
        if col_equipe not in df_ranking.columns:
            return None
        return (
            df_ranking.groupby(col_equipe)
            .agg(
                Técnicos=("Posição", "count"),
                **{
                    "Total Pontos": ("Total Pontos", "sum"),
                    "Média Pontos": ("Total Pontos", "mean"),
                    "Projeção Média": ("Projeção", "mean"),
                    "Qtd O.S. Total": ("Qtd O.S.", "sum"),
                },
            )
            .sort_values("Total Pontos", ascending=False)
            .reset_index()
        )


# ====================================================
# 8. COMPONENTES VISUAIS
# ====================================================
_TEMAS_CARD = {
    "azul": {
        "fundo": "#EFF6FF",
        "texto": "#1E3A8A",
        "borda": "#3B82F6",
        "titulo": "#1E40AF",
    },
    "verde": {
        "fundo": "#F0FDF4",
        "texto": "#15803D",
        "borda": "#22C55E",
        "titulo": "#166534",
    },
    "laranja": {
        "fundo": "#FFF7ED",
        "texto": "#EA580C",
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
        "borda": "#475569",
        "titulo": "#94A3B8",
    },
    "vermelho": {
        "fundo": "#FEF2F2",
        "texto": "#991B1B",
        "borda": "#EF4444",
        "titulo": "#7F1D1D",
    },
}


def _card(
    titulo: str,
    valor: str,
    tema: str = "azul",
    sub: str = "",
    icone: str = "",
    tooltip: str = "",
) -> str:
    c = _TEMAS_CARD.get(tema, _TEMAS_CARD["azul"])
    sub_color = "#94A3B8" if tema == "escuro" else "#64748B"
    tip = f'<div class="tooltip-premium">{tooltip}</div>' if tooltip else ""
    return f"""
    <div class="card-admin" style="background:{c['fundo']};padding:20px;border-radius:10px;
         border-left:5px solid {c['borda']};box-shadow:0 4px 6px rgba(0,0,0,0.05);
         height:100%;display:flex;flex-direction:column;justify-content:center;
         transition:transform 0.2s,box-shadow 0.2s;"
         onmouseover="this.style.transform='translateY(-3px)';this.style.boxShadow='0 8px 15px rgba(0,0,0,0.1)';"
         onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 4px 6px rgba(0,0,0,0.05)';">
        <p style="margin:0;font-size:13px;color:{c['titulo']};font-weight:700;">{icone} {titulo}</p>
        <h2 style="margin:5px 0 0;color:{c['texto']};font-weight:900;font-size:30px;">{valor}</h2>
        <p style="margin:5px 0 0;font-size:11px;color:{sub_color};font-weight:600;">{sub}</p>
        {tip}
    </div>"""


# ====================================================
# 9. INICIALIZAÇÃO
# ====================================================
aplicar_estilo()
aplicar_tema_claro()
injetar_css_admin()
render_sidebar_admin()

render_hero_totale_1(
    titulo="Painel Administrativo",
    subtitulo="Visão consolidada de produção, rankings e performance de toda a operação",
    icone="shield",
    badge="Área Restrita",
    usar_material=True,
)

# ====================================================
# 10. CARREGAMENTO DOS DADOS (PRODUÇÃO + ATIVOS)
# ====================================================
loader = st.empty()
loader.markdown(
    """<div class="loading-totale">
        <span style="color:#012869;font-weight:700;">⚡ Carregando bases (Produção + Lista Ativos)...</span>
        <span style="color:#F37C04;font-weight:800;font-size:13px;">Aguarde</span>
    </div>""",
    unsafe_allow_html=True,
)

df_prod = carregar_base_producao()
df_ativos = carregar_lista_ativos()
loader.empty()

if df_prod.empty:
    render_insight(
        "Base de produção indisponível. Verifique o compartilhamento da planilha.",
        "critico",
    )
    st.stop()

# ── DataFrame completo: produção + lista de ativos ──
df_raw = criar_dataframe_completo(df_prod, df_ativos)

# ── Detecção Inteligente de Colunas ──
col_tec = Utilitarios.buscar_coluna(
    df_raw,
    [
        "NOME EQUIPE",
        "NOME_EQUIPE",
        "NOME TÉCNICO",
        "NOME_TECNICO",
        "TECNICO",
        "TÉCNICO",
        "NOME",
        "COLABORADOR",
        "VENDEDOR",
        "LOGIN",
        "USUARIO",
        "USER",
        "MATRICULA",
    ],
)
col_pontos = Utilitarios.buscar_coluna(
    df_raw, ["PONTOS", "PONTO", "PTS", "PONTUACAO", "PREVIA"]
)
col_data = Utilitarios.buscar_coluna(
    df_raw, ["DATA", "DATA AGENDAMENTO", "DATA CONCLUSÃO", "DATA_EXECUCAO", "DATE"]
)
col_equipe = Utilitarios.buscar_coluna(
    df_raw, ["EQUIPE", "NOME EQUIPE", "NOME_EQUIPE", "EQUIPE TÉCNICA"]
)
col_supervisor = Utilitarios.buscar_coluna(
    df_raw, ["SUPERVISOR", "SUPERVISOR EQUIPE", "GESTOR"]
)
col_origem = Utilitarios.buscar_coluna(
    df_raw, ["ORIGEM", "TIPO", "SISTEMA", "FONTE", "TIPO_OS"]
)
col_projeto = Utilitarios.buscar_coluna(df_raw, ["PROJETO", "CAMPANHA", "OPERAÇÃO"])

# ── Tratamento de Erro Explícito ─
if not col_tec:
    st.error("🚨 Coluna de técnico não identificada na base de dados.")
    st.info(
        f"**Colunas detectadas na planilha:** \n\n {', '.join(df_raw.columns.tolist())}"
    )
    st.warning(
        "Verifique se a planilha possui uma coluna indicando o nome ou login do técnico."
    )
    st.stop()

if not col_pontos:
    st.error("🚨 Coluna de pontos não identificada na base de dados.")
    st.stop()

# ─ Garantia de Tipo String para Colunas Textuais (Evita AttributeError) ──
if col_tec:
    df_raw[col_tec] = df_raw[col_tec].astype(str).str.strip()
if col_equipe and col_equipe in df_raw.columns:
    df_raw[col_equipe] = df_raw[col_equipe].astype(str).str.strip()
if col_supervisor and col_supervisor in df_raw.columns:
    df_raw[col_supervisor] = df_raw[col_supervisor].astype(str).str.strip()
if col_projeto and col_projeto in df_raw.columns:
    df_raw[col_projeto] = df_raw[col_projeto].astype(str).str.strip()
if col_origem and col_origem in df_raw.columns:
    df_raw[col_origem] = df_raw[col_origem].astype(str).str.strip()

# ── Normalização Numérica e de Data ──
df_raw[col_pontos] = Utilitarios.normalizar_pontos(df_raw[col_pontos])
if col_data:
    df_raw[col_data] = Utilitarios.converter_data(df_raw[col_data]).dt.date

# ====================================================
# 11. FILTROS GLOBAIS
# ====================================================
with st.container(border=True):
    render_section_header("🎯", "Filtros Globais")

    f1, f2, f3, f4 = st.columns([1, 1, 1.2, 1])

    mask_data = pd.Series(True, index=df_raw.index)

    # ─ Filtro de Data ──
    if col_data and not df_raw[col_data].dropna().empty:
        min_d = df_raw[col_data].dropna().min()
        max_d = df_raw[col_data].dropna().max()
        with f1:
            d_ini = st.date_input(
                "📅 De",
                value=min_d,
                min_value=min_d,
                max_value=max_d,
                format="DD/MM/YYYY",
            )
        with f2:
            d_fim = st.date_input(
                "📅 Até",
                value=max_d,
                min_value=min_d,
                max_value=max_d,
                format="DD/MM/YYYY",
            )
        if d_ini <= d_fim:
            mask_data &= (df_raw[col_data] >= d_ini) & (df_raw[col_data] <= d_fim)
        else:
            render_insight("Data inicial > data final.", "alerta")
    else:
        with f1:
            st.info("Sem data")
        with f2:
            st.write("")

    # ── Filtro de Projeto ──
    with f3:
        if col_projeto and col_projeto in df_raw.columns:
            projetos = sorted(df_raw[col_projeto].dropna().unique().tolist())
            projeto_sel = st.selectbox("📁 Projetos", ["Todos", *projetos])
            if projeto_sel != "Todos":
                mask_data &= df_raw[col_projeto] == projeto_sel
        else:
            st.write("")

    # ── Filtro Rápido (Atalho) ──
    with f4:
        quick = st.selectbox(
            "⚡ Atalho", ["Todos", "Hoje", "Últimos 7 dias", "Mês Atual"]
        )
        if col_data and quick != "Todos":
            if quick == "Hoje":
                mask_data &= df_raw[col_data] == max_d
            elif quick == "Últimos 7 dias":
                mask_data &= df_raw[col_data] >= max_d - timedelta(days=6)
            elif quick == "Mês Atual":
                mask_data &= df_raw[col_data] >= max_d.replace(day=1)

df_filtered = df_raw[mask_data].copy()

if df_filtered.empty:
    st.info("💡 Nenhum dado encontrado para os filtros selecionados.")
    st.stop()

st.divider()

# ====================================================
# 12. KPIs GLOBAIS
# ====================================================
dias_brutos, dias_seguros, data_ref, dias_passados = Utilitarios.calcular_dias_uteis(
    df_filtered, col_data
)

total_pontos = float(df_filtered[col_pontos].sum())
total_tecnicos = df_filtered[col_tec].nunique()

# Prod vs Gpon & Contagem OS (apenas PROD)
pts_prod = 0.0
pts_gpon = 0.0
total_os = 0
if col_origem:
    origem = df_filtered[col_origem].astype(str).str.upper()
    is_prod = origem.str.contains("PROD", na=False)
    pts_prod = float(df_filtered.loc[is_prod, col_pontos].sum())
    pts_gpon = float(df_filtered.loc[~is_prod, col_pontos].sum())
    total_os = int(is_prod.sum())  # Conta apenas OS Prod
else:
    pts_gpon = total_pontos
    total_os = len(df_filtered)

# Técnicos Elite (≥ 400 pts)
tec_acima_400 = 0
tec_criticos = 0
if total_tecnicos > 0:
    pts_por_tec = df_filtered.groupby(col_tec)[col_pontos].sum()
    tec_acima_400 = int((pts_por_tec >= 400).sum())
    tec_criticos = int((pts_por_tec < 275).sum())

render_section_header("📊", "Visão Geral da Operação")
k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.markdown(
        _card(
            "Total de Pontos",
            Utilitarios.formatar_numero(total_pontos, 2),
            "azul",
            f"Prod: {Utilitarios.formatar_numero(pts_prod, 2)} | Gpon: {Utilitarios.formatar_numero(pts_gpon, 2)}",
            "🎯",
        ),
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        _card(
            "O.S. Realizadas (Prod)",
            str(total_os),
            "cinza",
            "Apenas atendimentos de Produção",
            "📋",
        ),
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        _card(
            "Técnicos Ativos",
            str(total_tecnicos),
            "verde",
            f"{dias_passados} dias úteis passados",
            "👷",
        ),
        unsafe_allow_html=True,
    )
with k4:
    st.markdown(
        _card(
            "Elite (≥ 400 pts)",
            f"{tec_acima_400}/{total_tecnicos}",
            "escuro",
            "Técnicos que já bateram a meta principal",
            "🏆",
        ),
        unsafe_allow_html=True,
    )
with k5:
    st.markdown(
        _card(
            "Críticos (< 275)",
            str(tec_criticos),
            "vermelho" if tec_criticos > 0 else "verde",
            f"{(tec_criticos / max(total_tecnicos, 1) * 100):.0f}% da equipe",
            "⚠️",
        ),
        unsafe_allow_html=True,
    )

st.write("---")

# ====================================================
# 13. TABS PRINCIPAIS
# ====================================================
tab_ranking, tab_equipes, tab_graficos = st.tabs(
    ["🏆 Ranking Geral", "👥 Por Equipe", "📈 Gráficos"]
)

# ── TAB 1: RANKING GERAL ──
with tab_ranking:
    render_section_header("🏆", "Ranking de Técnicos — Produção Consolidada")

    df_ranking = ProcessamentoAdmin.construir_ranking(
        df_filtered,
        col_tec,
        col_pontos,
        dias_brutos,
        dias_seguros,
        dias_passados,
        col_equipe=col_equipe,
        col_supervisor=col_supervisor,
        col_origem=col_origem,
    )

    r1, r2, r3 = st.columns(3)
    with r1:
        proj_media = df_ranking["Projeção"].mean()
        st.markdown(
            _card(
                "Projeção Média Equipe",
                Utilitarios.formatar_numero(proj_media, 2),
                "escuro",
                "Fim do mês estimado",
                "📈",
            ),
            unsafe_allow_html=True,
        )
    with r2:
        top1 = df_ranking.iloc[0][col_tec] if not df_ranking.empty else "—"
        top1_pts = df_ranking.iloc[0]["Total Pontos"] if not df_ranking.empty else 0
        st.markdown(
            _card(
                "Top 1 Técnico",
                str(top1).title(),
                "laranja",
                f"{Utilitarios.formatar_numero(top1_pts, 2)} pts",
                "🥇",
            ),
            unsafe_allow_html=True,
        )
    with r3:
        st.markdown(
            _card(
                "Dias Úteis Restantes",
                str(dias_brutos),
                "cinza",
                f"Ref: {pd.Timestamp(data_ref).strftime('%d/%m/%Y')}",
                "📆",
            ),
            unsafe_allow_html=True,
        )

    st.write("")

    # ── Tabela Formato Imagem ──
    colunas_ranking = ["Posição", col_tec]
    if col_supervisor and col_supervisor in df_ranking.columns:
        colunas_ranking.append(col_supervisor)
    colunas_ranking += [
        "Qtd O.S.",
        "Total Pontos",
        "Dias Trab",
        "Média/Dia",
        "Média/O.S.",
        "Projeção",
    ]

    df_rank_display = df_ranking[colunas_ranking].copy()
    df_rank_display["Posição"] = df_rank_display["Posição"].apply(
        Utilitarios.formatar_posicao
    )

    col_config = {
        "Posição": st.column_config.TextColumn("Posição"),
        "Dias Trab": st.column_config.NumberColumn("Dias Trab.", format="%d"),
        col_tec: st.column_config.TextColumn("Nome Equipe"),
        col_supervisor: st.column_config.TextColumn("Supervisor"),
        "Qtd O.S.": st.column_config.NumberColumn("📋 O.S.", format="%d"),
        "Total Pontos": st.column_config.NumberColumn("🎯 Pontos", format="%.2f"),
        "Média/Dia": st.column_config.NumberColumn("⚡ Méd/Dia", format="%.2f"),
        "Média/O.S.": st.column_config.NumberColumn("📊 Méd/O.S.", format="%.2f"),
        "Projeção": st.column_config.NumberColumn("📈 Projeção", format="%.2f"),
    }

    st.dataframe(
        df_rank_display,
        use_container_width=True,
        hide_index=True,
        height=500,
        column_config=col_config,
    )

# ── TAB 2: POR EQUIPE ──
with tab_equipes:
    render_section_header("👥", "Performance por Equipe")
    if col_equipe and col_equipe in df_ranking.columns:
        df_eq = ProcessamentoAdmin.resumo_equipes(df_ranking, col_equipe)
        if df_eq is not None and not df_eq.empty:
            st.dataframe(
                df_eq,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Total Pontos": st.column_config.NumberColumn(
                        "🎯 Total Pontos", format="%.2f"
                    ),
                    "Média Pontos": st.column_config.NumberColumn(
                        "📊 Média/Téc", format="%.2f"
                    ),
                    "Projeção Média": st.column_config.NumberColumn(
                        "📈 Projeção Méd", format="%.2f"
                    ),
                    "Qtd O.S. Total": st.column_config.NumberColumn(
                        "📋 O.S.", format="%d"
                    ),
                    "Técnicos": st.column_config.NumberColumn(
                        "👷 Técnicos", format="%d"
                    ),
                },
            )
            fig_eq = px.bar(
                df_eq.sort_values("Total Pontos"),
                x="Total Pontos",
                y=col_equipe,
                orientation="h",
                color="Média Pontos",
                color_continuous_scale=["#EF4444", "#F97316", "#22C55E", "#012869"],
                text_auto=True,
                title="Pontos Totais por Equipe",
            )
            fig_eq.update_traces(texttemplate="%{x:.2f}")
            fig_eq.update_layout(
                margin=dict(l=0, r=20, t=40, b=0),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(
                fig_eq, use_container_width=True, config={"displayModeBar": False}
            )
        else:
            st.info("💡 Sem dados de equipe disponíveis.")
    else:
        st.info("💡 Coluna de equipe não identificada na base de dados.")

# ── TAB 3: GRÁFICOS ──
with tab_graficos:
    render_section_header("📈", "Análises Gráficas")
    g1, g2 = st.columns(2)
    with g1:
        st.subheader("🏆 Top 15 Técnicos")
        top15 = df_ranking.head(15).copy()
        fig_top = go.Figure(
            go.Bar(
                x=top15["Total Pontos"],
                y=top15[col_tec].astype(str).str.title(),
                orientation="h",
                marker_color=np.where(
                    top15["Total Pontos"] >= 400,
                    "#012869",
                    np.where(
                        top15["Total Pontos"] >= 300,
                        "#22C55E",
                        np.where(top15["Total Pontos"] >= 275, "#F97316", "#EF4444"),
                    ),
                ),
                text=top15["Total Pontos"].apply(lambda x: f"{x:.2f}"),
                textposition="outside",
            )
        )
        fig_top.update_layout(
            margin=dict(l=0, r=60, t=10, b=0),
            yaxis=dict(autorange="reversed"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
        )
        st.plotly_chart(
            fig_top, use_container_width=True, config={"displayModeBar": False}
        )
    with g2:
        st.subheader("📊 Distribuição de Pontos")
        fig_hist = go.Figure(
            go.Histogram(
                x=df_ranking["Total Pontos"],
                nbinsx=20,
                marker_color="#012869",
                opacity=0.8,
            )
        )
        for meta, cor in [(300, "#22C55E"), (350, "#F97316"), (400, "#012869")]:
            fig_hist.add_vline(
                x=meta,
                line_dash="dash",
                line_color=cor,
                annotation_text=f"Meta {meta}",
                annotation_position="top",
            )
        fig_hist.update_layout(
            margin=dict(l=0, r=20, t=10, b=0),
            xaxis_title="Pontos",
            yaxis_title="Técnicos",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(
            fig_hist, use_container_width=True, config={"displayModeBar": False}
        )