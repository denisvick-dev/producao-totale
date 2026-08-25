# pages/producao.py (ou pages/1_📊_Minha_Produção.py)
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Optional, List
import datetime as _dt
from datetime import timedelta, date as _date
import time

# ⚠️ O set_page_config OBRIGATORIAMENTE deve ser o primeiro comando Streamlit do arquivo
st.set_page_config(
    page_title="Minha Produção | Totale",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils._auth import AuthManager
from utils._database import get_db
from components.sidebar import render_sidebar_corp

# ====================================================
# 🔒 SEGURANÇA E REDIRECIONAMENTO
# ====================================================
if not st.session_state.get("authenticated", False):
    st.switch_page("streamlit_app.py")

auth = AuthManager()

# 🎨 Sidebar corporativo Totale
render_sidebar_corp(on_logout=auth.logout, logout_page="streamlit_app.py")


# ====================================================
# IMPORTAÇÃO DO DESIGN SYSTEM CORPORATIVO
# ====================================================
try:
    from components.componentes import (
        aplicar_estilo,
        render_hero,
        render_insight,
        render_section_header,
    )
except ImportError:
    st.error("⚠️ Módulo 'componentes.py' não encontrado. Verifique a pasta components/")
    st.stop()


# ====================================================
# BLOCO 1: FUNÇÕES UTILITÁRIAS
# ====================================================
class Utilitarios:
    @staticmethod
    def buscar_coluna(df: pd.DataFrame, palavras_chave: List[str]) -> Optional[str]:
        cols_upper = {c.upper(): c for c in df.columns}
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
        for col in df_export.select_dtypes(
            include=["float", "float64", "float32"]
        ).columns:
            df_export[col] = df_export[col].apply(
                lambda x: Utilitarios.formatar_numero(x) if pd.notna(x) else "0,00"
            )
        return df_export.to_csv(index=False, sep=";", encoding="utf-8-sig").encode(
            "utf-8-sig"
        )


# ====================================================
# BLOCO 2: CSS EXCLUSIVO — TOOLTIP PREMIUM E CARDS
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
        .card-premium:hover .tooltip-premium {
            visibility: visible; opacity: 1; bottom: 105%;
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
    "roxo": {
        "fundo": "#FAF5FF",
        "texto": "#7E22CE",
        "borda": "#A855F7",
        "titulo": "#581C87",
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
    <div class="card-premium"
         style="background:{cores['fundo']};padding:20px;border-radius:10px;
                border-left:5px solid {cores['borda']}; box-shadow:0 4px 6px rgba(0,0,0,0.05);
                height:100%;display:flex;flex-direction:column; justify-content:center;
                transition:transform 0.2s, box-shadow 0.2s;"
         onmouseover="this.style.transform='translateY(-3px)'; this.style.boxShadow='0 8px 15px rgba(0,0,0,0.1)';"
         onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px rgba(0,0,0,0.05)';">
        <p style="margin:0;font-size:14px;color:{cores['titulo']};font-weight:700;">{icone} {titulo}</p>
        <h2 style="margin:5px 0 0;color:{cores['texto']};font-weight:900;font-size:32px;">{valor}</h2>
        <p style="margin:5px 0 0;font-size:12px;color:#64748B;font-weight:600;">{subtitulo}</p>
        {html_tooltip}
    </div>
    """


# ====================================================
# BLOCO 3: GRÁFICOS E CACHE
# ====================================================
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


def preparar_base_cache(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "Pontos" in df.columns:
        df["Pontos"] = pd.to_numeric(df["Pontos"], errors="coerce").fillna(0.0)
    return df


# ====================================================
# RENDERIZAÇÃO DA PÁGINA
# ====================================================
aplicar_estilo()
_injetar_css_tooltip()

tecnico = str(st.session_state.get("tecnico", ""))
login_code = str(st.session_state.get("login_code", ""))
user_code = str(st.session_state.get("user_code", ""))

render_hero(
    titulo="🔍 Raio-X: Desempenho Operacional",
    subtitulo=f"Auditoria de Execução Física (O.S. e Pontuação) exclusiva para {tecnico}",
    badge="Painel do Técnico",
)

# ── Carregamento de Dados com Barra de Progresso Totale ──
progress_box = st.empty()

with progress_box.container():
    st.markdown(
        """
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid #F37C04; padding: 16px 20px; border-radius: 10px; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                <span style="color: #012869; font-weight: 700; font-size: 15px;">
                    ⚡ Sincronizando seus dados com o Google Sheets...
                </span>
                <span style="color: #F37C04; font-weight: 800; font-size: 13px;">
                    Aguarde
                </span>
            </div>
        """,
        unsafe_allow_html=True,
    )

    # Barra de progresso animada por etapas
    bar = st.progress(10)
    time.sleep(0.1)

    bar.progress(35)
    db = get_db()

    bar.progress(70)
    df_prod = db.get_producao_by_tecnico(tecnico, login_code, user_code)

    bar.progress(100)
    time.sleep(0.2)

    st.markdown("</div>", unsafe_allow_html=True)

# Limpa a barra de carregamento após a conclusão
progress_box.empty()

if df_prod.empty:
    render_insight(
        f"Nenhum registro de produção encontrado para o usuário ({login_code}).",
        "alerta",
    )
    st.stop()

df_prod = preparar_base_cache(df_prod)

col_data = Utilitarios.buscar_coluna(
    df_prod, ["DATA", "DATA AGENDAMENTO", "DATA CONCLUSÃO", "DATA_EXECUCAO", "DATE"]
)
if col_data:
    df_prod[col_data] = pd.to_datetime(df_prod[col_data], errors="coerce").dt.date


# ====================================================
# FILTROS DE PERÍODO — CALENDÁRIOS (INÍCIO E FIM)
# ====================================================
with st.container(border=True):
    render_section_header("🎯", "Filtro de Período")

    mask = pd.Series(True, index=df_prod.index)

    if col_data and not df_prod[col_data].dropna().empty:
        min_date = df_prod[col_data].min()
        max_date = df_prod[col_data].max()

        if not isinstance(min_date, _date):
            min_date = pd.to_datetime(min_date).date()
        if not isinstance(max_date, _date):
            max_date = pd.to_datetime(max_date).date()

        c1, c2, c3 = st.columns([1.2, 1.2, 1.6])

        with c1:
            data_inicio = st.date_input(
                "📅 Data inicial",
                value=min_date,
                min_value=min_date,
                max_value=max_date,
                format="DD/MM/YYYY",
                key="filtro_data_inicio",
            )

        with c2:
            data_fim = st.date_input(
                "📅 Data final",
                value=max_date,
                min_value=min_date,
                max_value=max_date,
                format="DD/MM/YYYY",
                key="filtro_data_fim",
            )

        with c3:
            st.write("")
            st.write("")
            b1, b2, b3 = st.columns(3)
            hoje = max_date

            with b1:
                if st.button("Hoje", use_container_width=True, key="btn_hoje"):
                    st.session_state["filtro_data_inicio"] = hoje
                    st.session_state["filtro_data_fim"] = hoje
                    st.rerun()
            with b2:
                if st.button("7 dias", use_container_width=True, key="btn_7d"):
                    st.session_state["filtro_data_inicio"] = max(
                        min_date, hoje - timedelta(days=6)
                    )
                    st.session_state["filtro_data_fim"] = hoje
                    st.rerun()
            with b3:
                if st.button("Mês", use_container_width=True, key="btn_mes"):
                    st.session_state["filtro_data_inicio"] = max(
                        min_date, hoje.replace(day=1)
                    )
                    st.session_state["filtro_data_fim"] = hoje
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
if not df_tec_prod.empty:
    st.divider()

    if "Pontos" not in df_tec_prod.columns:
        render_insight(
            "Aviso: A coluna 'Pontos' não foi localizada na base de dados.", "alerta"
        )
        st.stop()

    # 1️⃣ Quantidade Total de O.S. (DECLARADA PRIMEIRO AQUI)
    t_os = len(df_tec_prod)

    # 2️⃣ Prévia = Soma Pontos (Prod) + Soma Pontos (Gpon)
    col_origem = "__origem__" if "__origem__" in df_tec_prod.columns else None

    if col_origem:
        pontos_prod = (
            pd.to_numeric(
                df_tec_prod.loc[
                    df_tec_prod[col_origem].astype(str).str.upper() == "PROD", "Pontos"
                ],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )
        pontos_gpon = (
            pd.to_numeric(
                df_tec_prod.loc[
                    df_tec_prod[col_origem].astype(str).str.upper() == "GPON", "Pontos"
                ],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )
    else:
        pontos_prod = 0.0
        pontos_gpon = (
            pd.to_numeric(df_tec_prod["Pontos"], errors="coerce").fillna(0).sum()
        )

    t_pontos = float(pontos_prod) + float(pontos_gpon)

    # 3️⃣ Projeção
    if col_data and not df_tec_prod[col_data].dropna().empty:
        datas_validas = pd.to_datetime(df_tec_prod[col_data], errors="coerce").dropna()
        dias_com_os = max(datas_validas.dt.normalize().nunique(), 1)

        data_ref = datas_validas.max()
        dias_no_mes = pd.Period(data_ref, freq="M").days_in_month

        media_diaria = t_pontos / dias_com_os
        t_projecao = media_diaria * dias_no_mes
        sub_proj = f"Média/dia × {dias_no_mes} dias"
        tip_proj = f"Projeção = ({Utilitarios.formatar_numero(media_diaria)} pts/dia) × {dias_no_mes} dias do mês."
    else:
        t_projecao = t_pontos
        sub_proj = "Sem coluna de data"
        tip_proj = "Sem datas válidas."

    # 4️⃣ Média por O.S.
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
                "Total de O.S. no período selecionado (Prod + Gpon)",
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
                f"Prévia = Prod ({Utilitarios.formatar_numero(pontos_prod)}) + Gpon ({Utilitarios.formatar_numero(pontos_gpon)})",
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
                "Média de pontos por cada O.S. executada (Prévia ÷ Qtd O.S.)",
            ),
            unsafe_allow_html=True,
        )

    st.write("---")

    # ── Gráfico ──
    if col_data:
        render_section_header("📊", "Evolução Diária — Volume vs Qualidade")
        df_grafico = df_tec_prod.dropna(subset=[col_data]).copy()

        if not df_grafico.empty:
            df_tempo = (
                df_grafico.groupby(col_data)
                .agg(Pontos=("Pontos", "sum"), Qtd_OS=("Pontos", "count"))
                .reset_index()
            )
            st.plotly_chart(
                Graficos.grafico_combo_raiox(df_tempo, col_data, "Qtd_OS", "Pontos"),
                use_container_width=True,
                config={"displayModeBar": False},
            )

    st.write("---")

    # ── Tabela de extrato ──
    render_section_header("🧾", "Extrato Operacional Detalhado")

    colunas_exib = [
        c
        for c in df_tec_prod.columns
        if c
        not in {
            "lat",
            "lon",
            "latitude",
            "longitude",
            "Posição",
            "Cidade",
            "Unnamed: 0",
        }
    ]
    df_exibir = df_tec_prod[colunas_exib].copy()

    if col_data:
        df_exibir = df_exibir.sort_values(by=col_data, ascending=False)

    col_configs = {}
    if "Pontos" in df_exibir.columns:
        col_configs["Pontos"] = st.column_config.NumberColumn(
            "🎯 Pontos", format="%.2f"
        )
    if col_data:
        col_configs[col_data] = st.column_config.DateColumn(
            "📅 Data", format="DD/MM/YYYY"
        )

    st.dataframe(
        df_exibir,
        use_container_width=True,
        hide_index=True,
        column_config=col_configs,
        height=400,
    )

    # ── Download + Resumo ──
    st.write("")
    col_d, col_v = st.columns([1, 4])
    with col_d:
        st.download_button(
            label="📥 Baixar Extrato (CSV)",
            data=Utilitarios.formatar_dataframe_para_download(df_exibir),
            file_name=f"extrato_totale_{login_code}.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True,
        )

    st.write("")

    if col_data and "Pontos" in df_exibir.columns:
        df_exec = df_exibir.dropna(subset=[col_data]).copy()
        if not df_exec.empty:
            df_resumo_dia = (
                df_exec.groupby(col_data)["Pontos"]
                .sum()
                .reset_index()
                .sort_values(col_data)
            )

            max_val = df_resumo_dia["Pontos"].max()
            min_val = df_resumo_dia["Pontos"].min()

            dia_max = pd.to_datetime(
                df_resumo_dia[df_resumo_dia["Pontos"] == max_val].iloc[0][col_data]
            )
            dia_min = pd.to_datetime(
                df_resumo_dia[df_resumo_dia["Pontos"] == min_val].iloc[0][col_data]
            )

            col_met1, col_met2, col_met3 = st.columns(3)
            with col_met1:
                st.metric(
                    "📅 Período Analisado",
                    f"{df_exibir[col_data].min().strftime('%d/%m')} a {df_exibir[col_data].max().strftime('%d/%m')}",
                )
            with col_met2:
                st.metric(
                    "📈 Melhor Dia",
                    dia_max.strftime("%d/%m/%Y"),
                    f"{Utilitarios.formatar_numero(max_val)} pts",
                )
            with col_met3:
                st.metric(
                    "📉 Pior Dia",
                    dia_min.strftime("%d/%m/%Y"),
                    f"{Utilitarios.formatar_numero(min_val)} pts",
                )
else:
    st.info(
        "💡 Nenhuma produção encontrada para as datas selecionadas. Ajuste o filtro acima."
    )
