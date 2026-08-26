# pages/producao.py
from datetime import date as _date, timedelta
import datetime as _dt
from typing import Any, List, Optional
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ⚠️ CONFIGURAÇÃO OBRIGATÓRIA NO TOPO
st.set_page_config(
    page_title="Visão Produção | TOTALE",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from components.sidebar import render_sidebar_corp
from utils._auth import AuthManager
from utils._database import get_db

# ====================================================
# 🔒 SEGURANÇA E REDIRECIONAMENTO
# ====================================================
if not st.session_state.get("authenticated", False):
    st.switch_page("streamlit_app.py")

auth = AuthManager()
render_sidebar_corp(on_logout=auth.logout, logout_page="streamlit_app.py")

# ====================================================
# IMPORTAÇÃO DO DESIGN SYSTEM
# ====================================================
try:
    from components.componentes import (
        aplicar_estilo,
        render_hero_totale_1,
        render_insight,
        render_section_header,
        injetar_css_menu_nomes,
        aplicar_tema_claro,
    )
except ImportError:
    st.error("⚠️ Módulo 'componentes.py' não encontrado.")
    st.stop()


# ====================================================
# UTILITÁRIOS E CLASSES
# ====================================================
class Utilitarios:
    @staticmethod
    def buscar_coluna(df: pd.DataFrame, palavras_chave: List[str]) -> Optional[str]:
        cols_upper = {str(c).upper(): str(c) for c in df.columns}
        for palavra in palavras_chave:
            if palavra in cols_upper:
                return cols_upper[palavra]
        return None

    @staticmethod
    def formatar_numero(valor: float, casas_decimais: int = 2) -> str:
        if pd.isna(valor):
            return "0," + "0" * casas_decimais
        return (
            f"{valor:,.{casas_decimais}f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    @staticmethod
    def formatar_dataframe_para_download(df: pd.DataFrame) -> bytes:
        df_export = df.copy()
        for col in df_export.select_dtypes(include=["float", "float64"]).columns:
            df_export[col] = df_export[col].apply(
                lambda x: (
                    Utilitarios.formatar_numero(float(x)) if pd.notna(x) else "0,00"
                )
            )
        return df_export.to_csv(index=False, sep=";", encoding="utf-8-sig").encode(
            "utf-8-sig"
        )


class Graficos:
    @staticmethod
    def grafico_combo_raiox(
        df: pd.DataFrame, x_col: str, y_bar: str, y_line: str
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
# FUNÇÕES DE CACHE E OTIMIZAÇÃO
# ====================================================
@st.cache_data(ttl=600, show_spinner=False)
def carregar_dados_tecnico_cache(
    tecnico: str, login_code: str, user_code: str
) -> pd.DataFrame:
    db = get_db()
    df = db.get_producao_by_tecnico(tecnico, login_code, user_code)

    if not df.empty:
        if "Pontos" in df.columns:
            df["Pontos"] = pd.to_numeric(df["Pontos"], errors="coerce").fillna(0.0)

        col_data = Utilitarios.buscar_coluna(
            df, ["DATA", "DATA AGENDAMENTO", "DATA CONCLUSÃO", "DATA_EXECUCAO", "DATE"]
        )
        if col_data and col_data in df.columns:
            df[col_data] = pd.to_datetime(df[col_data], errors="coerce").dt.date

    return df


# ====================================================
# CSS EXCLUSIVO
# ====================================================
def _injetar_css_tooltip() -> None:
    st.markdown(
        """
        <style>
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

        [data-testid="stMain"] [data-testid="stWidgetLabel"] p,
        [data-testid="stMain"] [data-testid="stWidgetLabel"] label {
            color: #1E293B !important;
            font-weight: 700 !important;
            font-size: 13px !important;
        }

        [data-testid="stMain"] [data-testid="stDateInput"] svg,
        [data-testid="stMain"] [data-baseweb="input"] svg {
            color: #012869 !important;
            fill: #012869 !important;
        }

        [data-testid="stMain"] [data-baseweb="input"]:focus-within {
            border-color: #012869 !important;
            box-shadow: 0 0 0 3px rgba(1, 40, 105, 0.15) !important;
        }

        [data-testid="stMain"] div[data-testid="stContainer"] .stButton > button {
            background-color: #FFFFFF !important;
            color: #012869 !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
            font-weight: 700 !important;
            transition: all 0.2s ease !important;
        }

        [data-testid="stMain"] div[data-testid="stContainer"] .stButton > button:hover {
            background-color: #F8FAFC !important;
            border-color: #F37C04 !important;
            color: #F37C04 !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 10px rgba(243, 124, 4, 0.15) !important;
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
        <p style="margin:5px 0 0;font-size:12px;color:#64748B;font-weight:600;">{subtitulo}</p>
        {html_tooltip}
    </div>
    """


# ====================================================
# RENDERIZAÇÃO DA PÁGINA
# ====================================================
aplicar_estilo()
aplicar_tema_claro()
injetar_css_menu_nomes({
    "consultivo": "🗣️ Consultivo",
    "producao": "📊 Produção",
})
_injetar_css_tooltip()

tecnico = str(st.session_state.get("tecnico", ""))
login_code = str(st.session_state.get("login_code", ""))
user_code = str(st.session_state.get("user_code", ""))

render_hero_totale_1(
    titulo="Central de Produção Técnica",
    subtitulo="Auditoria de O.S. e Pontos para o técnico(a) ADRIEL ALEXANDER DE LIMA",
    icone="bar_chart",
    badge="Painel do Técnico",
    usar_material=True,
)

# ── Carregamento ──
loader = st.empty()
loader.markdown(
    """<div class="loading-totale">
        <span style="color:#012869; font-weight:700;">⚡ Sincronizando dados corporativos...</span>
        <span style="color:#F37C04; font-weight:800; font-size:13px;">Aguarde</span>
    </div>""",
    unsafe_allow_html=True,
)

df_prod = carregar_dados_tecnico_cache(tecnico, login_code, user_code)
loader.empty()

if df_prod.empty:
    render_insight(
        f"Nenhum registro de produção encontrado para o usuário ({login_code}).",
        "alerta",
    )
    st.stop()

col_data = Utilitarios.buscar_coluna(
    df_prod, ["DATA", "DATA AGENDAMENTO", "DATA CONCLUSÃO", "DATA_EXECUCAO", "DATE"]
)


# ====================================================
# FILTROS DE PERÍODO
# ====================================================
with st.container(border=True):
    render_section_header("🎯", "Filtro de Período")
    mask = pd.Series(True, index=df_prod.index)

    if (
        col_data
        and col_data in df_prod.columns
        and not df_prod[col_data].dropna().empty
    ):
        min_date = df_prod[col_data].min()
        max_date = df_prod[col_data].max()

        c1, c2, c3 = st.columns([1.2, 1.2, 1.6])

        with c1:
            data_inicio = st.date_input(
                "📅 Data inicial",
                value=min_date,
                min_value=min_date,
                max_value=max_date,
                format="DD/MM/YYYY",
            )
        with c2:
            data_fim = st.date_input(
                "📅 Data final",
                value=max_date,
                min_value=min_date,
                max_value=max_date,
                format="DD/MM/YYYY",
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

        mask &= (df_prod[col_data] >= data_inicio) & (df_prod[col_data] <= data_fim)

    df_tec_prod = df_prod[mask].copy()


# ====================================================
# DASHBOARD OPERACIONAL
# ====================================================
if df_tec_prod.empty:
    st.info(
        "💡 Nenhuma produção encontrada para as datas selecionadas. Ajuste o filtro acima."
    )
    st.stop()

st.divider()

if "Pontos" not in df_tec_prod.columns:
    render_insight("Aviso: A coluna 'Pontos' não foi localizada.", "alerta")
    st.stop()

t_os = len(df_tec_prod)

col_origem = "__origem__" if "__origem__" in df_tec_prod.columns else None

if col_origem:
    pontos_prod = float(
        df_tec_prod.loc[
            df_tec_prod[col_origem].astype(str).str.upper() == "PROD", "Pontos"
        ].sum()
    )
    pontos_gpon = float(
        df_tec_prod.loc[
            df_tec_prod[col_origem].astype(str).str.upper() == "GPON", "Pontos"
        ].sum()
    )
else:
    pontos_prod, pontos_gpon = 0.0, float(df_tec_prod["Pontos"].sum())

t_pontos = float(pontos_prod) + float(pontos_gpon)

# ── Projeção (Sem Domingos) ──
if (
    col_data
    and col_data in df_tec_prod.columns
    and not df_tec_prod[col_data].dropna().empty
):
    datas_validas = pd.to_datetime(df_tec_prod[col_data]).dropna()
    dias_com_os = max(datas_validas.dt.normalize().nunique(), 1)

    data_ref = datas_validas.max()
    inicio_mes = pd.Timestamp(data_ref.year, data_ref.month, 1)
    fim_mes = inicio_mes + pd.offsets.MonthEnd(1)

    dias_uteis_mes = int((pd.date_range(inicio_mes, fim_mes).dayofweek != 6).sum())

    media_diaria = t_pontos / dias_com_os
    t_projecao = media_diaria * dias_uteis_mes

    sub_proj = f"Média/dia × {dias_uteis_mes} dias úteis"
    tip_proj = f"Projeção = ({Utilitarios.formatar_numero(media_diaria)} pts/dia) × {dias_uteis_mes} dias úteis (sem domingos)."
else:
    t_projecao, sub_proj, tip_proj = (
        t_pontos,
        "Sem coluna de data",
        "Sem dados para projeção.",
    )

media_pontos = t_pontos / t_os if t_os > 0 else 0.0

# ── CARDS KPI ──
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
            Utilitarios.formatar_numero(t_pontos),
            "azul",
            f"Prod: {Utilitarios.formatar_numero(pontos_prod)} | Gpon: {Utilitarios.formatar_numero(pontos_gpon)}",
            "🎯",
            "Prévia total (Prod + Gpon)",
        ),
        unsafe_allow_html=True,
    )
with kr3:
    st.markdown(
        _criar_card_tooltip(
            "Projeção",
            Utilitarios.formatar_numero(t_projecao),
            "laranja",
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
            Utilitarios.formatar_numero(media_pontos),
            "verde",
            "Pts médio por O.S.",
            "📊",
            "Média por O.S. executada",
        ),
        unsafe_allow_html=True,
    )

st.write("---")

# ── Gráfico ──
if col_data and col_data in df_tec_prod.columns:
    render_section_header("📊", "Evolução Diária")
    df_tempo = (
        df_tec_prod.groupby(col_data)
        .agg(Pontos=("Pontos", "sum"), Qtd_OS=("Pontos", "count"))
        .reset_index()
    )
    st.plotly_chart(
        Graficos.grafico_combo_raiox(df_tempo, col_data, "Qtd_OS", "Pontos"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

st.write("---")

# ── Tabela ──
render_section_header("🧾", "Extrato Operacional Detalhado")
colunas_exib = [
    c
    for c in df_tec_prod.columns
    if str(c)
    not in {
        "lat",
        "lon",
        "latitude",
        "longitude",
        "Posição",
        "Cidade",
        "Unnamed: 0",
        "__origem__",
    }
]
df_exibir = df_tec_prod[colunas_exib].copy()

if col_data and col_data in df_exibir.columns:
    df_exibir = df_exibir.sort_values(by=col_data, ascending=False)

# 🛠️ CORREÇÃO DO PYLANCE PARA COLUMN_CONFIG:
# Constrói o dicionário garantindo que todas as chaves sejam estritamente `str`
column_config_dict: dict[str, Any] = {}
if "Pontos" in df_exibir.columns:
    column_config_dict["Pontos"] = st.column_config.NumberColumn(
        "🎯 Pontos", format="%.2f"
    )
if col_data is not None and col_data in df_exibir.columns:
    column_config_dict[col_data] = st.column_config.DateColumn(
        "📅 Data", format="DD/MM/YYYY"
    )

st.dataframe(
    df_exibir,
    use_container_width=True,
    hide_index=True,
    height=400,
    column_config=column_config_dict,
)

# ── Download + Resumo ──
st.write("")
col_d, col_v = st.columns([1, 4])
with col_d:
    st.download_button(
        "📥 Baixar Extrato (CSV)",
        data=Utilitarios.formatar_dataframe_para_download(df_exibir),
        file_name=f"extrato_{login_code}.csv",
        mime="text/csv",
        type="primary",
        use_container_width=True,
    )

# 🛠️ CORREÇÃO DO PYLANCE PARA .ILOC:
if col_data and col_data in df_exibir.columns:
    df_resumo = (
        df_exibir.groupby(col_data)["Pontos"].sum().reset_index().sort_values(col_data)
    )
    if not df_resumo.empty:
        max_v = float(df_resumo["Pontos"].max())
        min_v = float(df_resumo["Pontos"].min())

        df_max_rows = df_resumo[df_resumo["Pontos"] == max_v]
        df_min_rows = df_resumo[df_resumo["Pontos"] == min_v]

        if not df_max_rows.empty and not df_min_rows.empty:
            data_max_val = df_max_rows[col_data].iloc[0]
            data_min_val = df_min_rows[col_data].iloc[0]

            d_max = pd.to_datetime(data_max_val)
            d_min = pd.to_datetime(data_min_val)

            st.write("")
            c1, c2, c3 = st.columns(3)
            min_d_str = pd.to_datetime(df_exibir[col_data].min()).strftime("%d/%m")
            max_d_str = pd.to_datetime(df_exibir[col_data].max()).strftime("%d/%m")

            c1.metric("📅 Período Analisado", f"{min_d_str} a {max_d_str}")
            c2.metric(
                "📈 Melhor Dia",
                d_max.strftime("%d/%m/%Y"),
                f"{Utilitarios.formatar_numero(max_v)} pts",
            )
            c3.metric(
                "📉 Pior Dia",
                d_min.strftime("%d/%m/%Y"),
                f"{Utilitarios.formatar_numero(min_v)} pts",
            )
