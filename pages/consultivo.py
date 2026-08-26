# pages/consultivo.py
import io
import locale
import requests
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, List
import streamlit as st

# ====================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ====================================================
st.set_page_config(
    page_title="Visão Consultivo | TOTALE", page_icon="🗣️", layout="wide"
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
# 3. DESIGN SYSTEM CORPORATIVO
# ====================================================
try:
    from components.componentes import (
        aplicar_estilo,
        aplicar_tema_claro,
        render_hero_totale_1,
        render_sidebar_portal,
        injetar_css_menu_nomes,
        render_kpi,
        render_insight,
    )
except ImportError:
    st.error("⚠️ Módulo 'componentes.py' não encontrado.")
    st.stop()


def configurar_locale():
    try:
        locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")
    except Exception:
        try:
            locale.setlocale(locale.LC_TIME, "Portuguese_Brazil.1252")
        except Exception:
            pass


configurar_locale()


# ====================================================
# 4. CSS DO MENU E SIDEBAR (IDÊNTICO À IMAGEM)
# ====================================================
def injetar_css_menu_sidebar():
    st.markdown(
        """
        <style>
        /* Fundo Geral do Sidebar */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #F4F5F7 0%, #FFFFFF 100%) !important;
            border-right: 1px solid #E2E8F0 !important;
        }
        
        /* Oculta item Home padrão */
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:first-child { display: none !important; }
        
        /* Renomeia Itens do Menu */
        [data-testid="stSidebarNav"] a[href*="consultivo"] span { font-size: 0 !important; }
        [data-testid="stSidebarNav"] a[href*="consultivo"] span::before { content: "🗣️ Consultivo" !important; font-size: 14px !important; font-weight: 700 !important; color: #1E293B !important; }
        
        [data-testid="stSidebarNav"] a[href*="producao"] span { font-size: 0 !important; }
        [data-testid="stSidebarNav"] a[href*="producao"] span::before { content: "📊 Produção" !important; font-size: 14px !important; font-weight: 700 !important; color: #1E293B !important; }

        /* Estilo dos Botões do Menu */
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
            background: #F8FAFC !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 8px !important;
            margin: 4px 16px !important;
            padding: 10px 14px !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
            transition: all 0.2s ease;
        }
        
        /* Item do Menu Selecionado (Laranja) */
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"],
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-selected="true"] {
            background: linear-gradient(90deg, #FFF7ED 0%, #FFEDD5 100%) !important;
            border: 1px solid #F97316 !important;
            border-left: 4px solid #F97316 !important;
            box-shadow: 0 4px 10px rgba(249, 115, 22, 0.1) !important;
        }
        
        /* Botão Sair / Encerrar Sessão */
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
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_perfil():
    # Calcula Iniciais para o Avatar (ex: FRANCISCO IGOR -> FI)
    partes_nome = nome_logado.split()
    iniciais = ""
    if len(partes_nome) >= 2:
        iniciais = partes_nome[0][0] + partes_nome[1][0]
    elif len(partes_nome) == 1:
        iniciais = partes_nome[0][:2]
    else:
        iniciais = "US"

    with st.sidebar:
        st.markdown(
            f"""
            <div style="background: linear-gradient(145deg, #F8FAFC 0%, #E2E8F0 100%); 
                        border: 1px solid #CBD5E1; border-left: 4px solid #F97316; 
                        border-radius: 12px; padding: 16px; margin: 16px; 
                        box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
                
                <div style="font-size: 11px; font-weight: 800; letter-spacing: 1.5px; color: #F97316; margin-bottom: 12px; display: flex; align-items: center; gap: 4px;">
                    ⚡ TOTALE · PORTAL
                </div>
                
                <div style="width: 52px; height: 52px; border-radius: 50%; 
                            background: linear-gradient(135deg, #012869 0%, #F97316 100%); 
                            color: white; display: flex; align-items: center; justify-content: center; 
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
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="btn-logout">', unsafe_allow_html=True)
        if st.button("🚪 Encerrar Sessão", use_container_width=True):
            st.session_state["authenticated"] = False
            st.switch_page("streamlit_app.py")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="text-align: center; font-size: 10px; color: #64748B; margin-top: 16px; font-weight: 600; letter-spacing: 1px;">
                POWERED BY <span style="color: #F97316;">TOTALE</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ====================================================
# 5. CLASSES DO MOTOR DE PROCESSAMENTO DE DADOS
# ====================================================
class ProcessadorDeDados:
    VAZIOS = ["-", "N/A", "nan", "None", "NaN", "null"]

    @staticmethod
    def _normalizar_serie(serie: pd.Series) -> pd.Series:
        return (
            serie.astype(str)
            .str.strip()
            .replace(ProcessadorDeDados.VAZIOS, "")
            .fillna("")
        )

    @staticmethod
    def tratar_planos_vetorizado(df: pd.DataFrame) -> pd.DataFrame:
        for col in ["PLANO TV", "PLANO INTERNET", "OBSERVACAO"]:
            if col not in df.columns:
                df[col] = ""

        tv_bruta = (
            df["PLANO TV"]
            .astype(str)
            .str.strip()
            .replace("SERVIÇOS AVANÇADOS", "CLARO TV+ BOX")
        )
        internet_bruta = df["PLANO INTERNET"].astype(str).str.strip()
        partes = internet_bruta.str.split(".", n=1, expand=True)

        internet_limpa = ProcessadorDeDados._normalizar_serie(partes[0])
        tv_do_internet = (
            ProcessadorDeDados._normalizar_serie(partes[1])
            if partes.shape[1] > 1
            else pd.Series("", index=df.index, dtype=str)
        )

        tv_normalizada = ProcessadorDeDados._normalizar_serie(tv_bruta)
        tv_limpa = pd.Series(
            np.where(tv_normalizada != "", tv_normalizada, tv_do_internet),
            index=df.index,
            dtype=str,
        )

        tem_tv = tv_limpa != ""
        tem_internet = internet_limpa != ""
        df["QTDE_CONSULTIVO"] = tem_tv.astype(int) + tem_internet.astype(int)

        condicoes = [
            tem_tv & tem_internet,
            tem_tv & ~tem_internet,
            ~tem_tv & tem_internet,
        ]
        opcoes = [tv_limpa + " & " + internet_limpa, tv_limpa, internet_limpa]
        df["TIPO SERVIÇO"] = np.select(condicoes, opcoes, default="Sem Tipo")
        df["PLANO TV"] = tv_limpa
        df["PLANO INTERNET"] = internet_limpa

        df["LISTA_PRODUTOS"] = (
            df["OBSERVACAO"].fillna("").astype(str).str.findall(r"\b\d{9,12}\b")
        )
        df["QTDE_PRODUTOS"] = df["LISTA_PRODUTOS"].apply(len)

        qtde_prod = df["QTDE_PRODUTOS"].fillna(0).astype(int)
        is_combinado = df["TIPO SERVIÇO"].str.contains("&", case=False, regex=False)
        flag_tv = df["TIPO SERVIÇO"].str.contains("TV", case=False, regex=False)
        flag_virtua = df["TIPO SERVIÇO"].str.contains(
            r"MEGA|GIGA", case=False, regex=True
        )

        df["QTDE_TV"] = np.where(
            is_combinado, flag_tv.astype(int), flag_tv.astype(int) * qtde_prod
        )
        df["QTDE_VIRTUA"] = np.where(
            is_combinado, flag_virtua.astype(int), flag_virtua.astype(int) * qtde_prod
        )
        df["QTDE_MESH"] = (qtde_prod - df["QTDE_TV"] - df["QTDE_VIRTUA"]).clip(lower=0)

        return df


class Calculos:
    @staticmethod
    def fator_projecao(df: pd.DataFrame) -> tuple[float, int]:
        col_data = Utilitarios.buscar_coluna(df, ["DATA", "DATA AGENDAMENTO", "DATE"])
        if df.empty or not col_data or df[col_data].isna().all():
            return 1.0, 0
        datas = pd.to_datetime(df[col_data], errors="coerce")
        hoje = pd.Timestamp.today().normalize()
        if datas.max().month != hoje.month or datas.max().year != hoje.year:
            return 1.0, 0

        inicio_mes = hoje.replace(day=1)
        prox_mes = inicio_mes.replace(day=28) + pd.Timedelta(days=4)
        fim_mes = prox_mes - pd.Timedelta(days=prox_mes.day)

        dias_uteis_total = len(
            [d for d in pd.date_range(inicio_mes, fim_mes) if d.dayofweek < 6]
        )
        dias_decorridos = len(
            [d for d in pd.date_range(inicio_mes, hoje) if d.dayofweek < 6]
        )
        faltantes = dias_uteis_total - dias_decorridos

        fator = (
            (dias_uteis_total / dias_decorridos)
            if dias_decorridos > 0 and faltantes > 0
            else 1.0
        )
        return fator, faltantes


class Utilitarios:
    @staticmethod
    def buscar_coluna(df: pd.DataFrame, palavras: List[str]) -> Optional[str]:
        cols = {c.upper(): c for c in df.columns}
        for p in palavras:
            if p in cols:
                return cols[p]
        return None

    @staticmethod
    def finalizar_colunas(df: pd.DataFrame, fator_proj: float = 1.0) -> pd.DataFrame:
        if df.empty:
            return df
        df.columns = df.columns.str.upper().str.strip()
        mapa = {
            "CONSULTIVOS": ["QTDE_CONSULTIVO", "QTDE. CONS.", "QTDE_CONS"],
            "VENDAS": ["QTDE_PRODUTOS", "QTDE. PROD.", "PRODUTOS"],
            "MESH": ["QTDE_MESH", "QTDE. MESH"],
            "TV": ["QTDE_TV", "QTDE. TV", "TV BOX"],
            "VIRTUA": ["QTDE_VIRTUA", "QTDE. VIRTUA"],
        }
        for col_dst, origens in mapa.items():
            encontrada = next((o for o in origens if o in df.columns), None)
            if encontrada:
                df[col_dst] = (
                    pd.to_numeric(df[encontrada], errors="coerce").fillna(0).astype(int)
                )
            elif col_dst not in df.columns:
                df[col_dst] = 0

        col_data = Utilitarios.buscar_coluna(df, ["DATA", "DATA AGENDAMENTO", "DATE"])
        if col_data:
            df["DATA"] = pd.to_datetime(df[col_data], errors="coerce", dayfirst=True)

        df["PROJ_CONSULTIVOS"] = (df["CONSULTIVOS"] * fator_proj).round().astype(int)
        df["PROJ_VENDAS"] = (df["VENDAS"] * fator_proj).round().astype(int)
        df["TAXA_CONVERSAO"] = np.where(
            df["CONSULTIVOS"] > 0, (df["VENDAS"] / df["CONSULTIVOS"]).round(4), 0.0
        )
        return df


class Graficos:
    @staticmethod
    def grafico_linhas_vendas(df, x_col, y_cons, y_prod) -> go.Figure:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df[x_col],
                y=df[y_cons],
                name="Consultivos",
                mode="lines+markers",
                line=dict(color="#94A3B8", width=2),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df[x_col],
                y=df[y_prod],
                name="Produtos",
                mode="lines+markers",
                line=dict(color="#F37C04", width=3),
                marker=dict(size=8),
            )
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=30, b=0),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            hovermode="x unified",
        )
        return fig

    @staticmethod
    def grafico_rosca_mix(df_mix) -> go.Figure:
        fig = px.pie(
            df_mix,
            names="Produto",
            values="Quantidade",
            hole=0.6,
            color_discrete_sequence=["#012869", "#F37C04", "#059669"],
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(margin=dict(t=10, b=10, l=0, r=0), showlegend=False)
        return fig


# ====================================================
# 6. DOWNLOAD E ENGINE DE DADOS (GOOGLE DRIVE)
# ====================================================
FILE_ID_CONSULTIVO = "1YOWJ0HuGcEP2vJaZwl2kcgrtNgsoMBDs"


@st.cache_data(ttl=600, show_spinner=False)
def carregar_e_processar_base() -> pd.DataFrame:
    urls = [
        f"https://drive.google.com/uc?export=download&id={FILE_ID_CONSULTIVO}",
        f"https://docs.google.com/spreadsheets/d/{FILE_ID_CONSULTIVO}/export?format=csv",
    ]
    df_bruto = pd.DataFrame()
    for url in urls:
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 100:
                bio = io.BytesIO(resp.content)
                for reader in (
                    lambda: pd.read_csv(
                        bio, sep=None, engine="python", encoding="utf-8"
                    ),
                    lambda: (
                        bio.seek(0),
                        pd.read_csv(bio, sep=";", encoding="latin-1"),
                    )[1],
                    lambda: (bio.seek(0), pd.read_excel(bio, engine="openpyxl"))[1],
                ):
                    try:
                        df = reader()
                        if not df.empty and df.shape[1] > 1:
                            df_bruto = df
                            break
                    except Exception:
                        continue
                if not df_bruto.empty:
                    break
        except Exception:
            continue

    if df_bruto.empty:
        return df_bruto

    df_proc = ProcessadorDeDados.tratar_planos_vetorizado(df_bruto)
    fator_proj, _ = Calculos.fator_projecao(df_proc)
    df_final = Utilitarios.finalizar_colunas(df_proc, fator_proj)

    return df_final


# ====================================================
# 7. INICIALIZAÇÃO DA INTERFACE
# ====================================================
aplicar_estilo()
aplicar_tema_claro()
render_sidebar_portal(
    nome=nome_logado.title(),
    login=login_logado,
    user=user_logado,
)

injetar_css_menu_nomes({
    "consultivo": "🗣️ Consultivo",
    "producao": "📊 Produção",
})

render_hero_totale_1(
    titulo="Raio-X: Consultivo",
    subtitulo="Contagens realizadas, mix de produtos e projeção fim do mês",
    badge="Vendas & Oportunidades",
)

if not nome_logado and not login_logado:
    render_insight(
        "Sessão expirada ou usuário não identificado. Faça login novamente.", "alerta"
    )
    st.stop()


# ====================================================
# 8. FILTRAGEM DO TÉCNICO LOGADO
# ====================================================
with st.spinner("Sincronizando base de dados e processando indicadores..."):
    df_cons = carregar_e_processar_base()

if df_cons.empty:
    render_insight("Não foi possível carregar a base do Google Drive.", "critico")
    st.stop()

col_tec = Utilitarios.buscar_coluna(
    df_cons, ["VENDEDOR", "TÉCNICO", "TECNICO", "NOME EQUIPE", "NOME"]
)
col_login = Utilitarios.buscar_coluna(df_cons, ["LOGIN", "MATRICULA", "RE"])
col_sup = Utilitarios.buscar_coluna(
    df_cons, ["SUPERVISOR", "MONITOR", "GESTOR", "COORDENADOR"]
)
col_base = Utilitarios.buscar_coluna(df_cons, ["BASE", "PROJETO", "CIDADE", "FILIAL"])

df_cons[col_tec] = df_cons[col_tec].astype(str).str.strip().str.upper()

mask_logado = pd.Series(False, index=df_cons.index)
if nome_logado:
    mask_logado |= df_cons[col_tec].str.contains(nome_logado, regex=False, na=False)
if login_logado and col_login:
    mask_logado |= (
        df_cons[col_login].astype(str).str.strip().str.upper() == login_logado
    )

df_tec = df_cons[mask_logado].copy()

if df_tec.empty:
    render_insight(
        f"Nenhum registro de produção consultiva para **{nome_logado or login_logado}**.",
        "info",
    )
    st.stop()


# ====================================================
# 9. CARDS E PAINEL DO TÉCNICO
# ====================================================
sup_tec = (
    df_tec[col_sup].mode()[0]
    if col_sup and not df_tec[col_sup].dropna().empty
    else "Não Atribuído"
)
base_tec = (
    df_tec[col_base].mode()[0]
    if col_base and not df_tec[col_base].dropna().empty
    else "Não Atribuída"
)
render_insight(
    f"👤 <b>Gestor:</b> {sup_tec} &nbsp;|&nbsp; 📍 <b>Base:</b> {base_tec}", "info"
)

t_cons = int(df_tec["CONSULTIVOS"].sum())
t_prod = int(df_tec["VENDAS"].sum())
t_mesh = int(df_tec["MESH"].sum())
t_tv = int(df_tec["TV"].sum())
t_vir = int(df_tec["VIRTUA"].sum())

proj_cons = int(df_tec["PROJ_CONSULTIVOS"].sum())
proj_prod = int(df_tec["PROJ_VENDAS"].sum())
taxa_conversao = (t_prod / t_cons) if t_cons > 0 else 0.0
fator_proj, falt_dias = Calculos.fator_projecao(df_tec)

# ── Linha 1: Realizado ──
st.markdown("### 🎯 Resultado Realizado (Até o momento)")
k1, k2, k3 = st.columns(3)
render_kpi(
    k1,
    "Total Consultivos",
    f"{t_cons:,}".replace(",", "."),
    "🗣️ Abordagens realizadas",
    "azul",
)
render_kpi(
    k2,
    "Total Produtos",
    f"{t_prod:,}".replace(",", "."),
    "🚀 Conversões fechadas",
    "laranja",
)
cor_win = "verde" if taxa_conversao >= 0.1 else "laranja"
render_kpi(k3, "Win Rate", f"{taxa_conversao:.1%}", "📈 Taxa de Conversão", cor_win)

# ── Linha 2: Mix de Produtos ──
st.markdown("#### 📦 Mix de Produtos Vendidos")
m1, m2, m3 = st.columns(3)
render_kpi(m1, "Mesh", f"{t_mesh:,}".replace(",", "."), "📶 Internet Mesh", "azul")
render_kpi(m2, "TV Box", f"{t_tv:,}".replace(",", "."), "📺 TV por assinatura", "cinza")
render_kpi(m3, "Virtua", f"{t_vir:,}".replace(",", "."), "🌐 Banda larga", "verde")

# ── Linha 3: Projeção Fim do Mês ──
st.divider()
if falt_dias > 0:
    st.markdown(
        f"### 🔮 Projeção Fim do Mês <span style='font-size:14px; color:#64748B;'>(faltam {falt_dias} dias úteis)</span>",
        unsafe_allow_html=True,
    )
    p1, p2, _ = st.columns([1, 1, 2])
    render_kpi(
        p1,
        "Proj. Consultivos",
        f"{proj_cons:,}".replace(",", "."),
        f"➕ +{proj_cons - t_cons} estimados",
        "laranja",
    )
    render_kpi(
        p2,
        "Proj. Produtos",
        f"{proj_prod:,}".replace(",", "."),
        f"➕ +{proj_prod - t_prod} estimados",
        "laranja",
    )

# ====================================================
# 10. GRÁFICOS
# ====================================================
st.divider()
g_linha, g_pizza = st.columns([2, 1])

with g_linha:
    st.markdown("#### 📉 Ritmo de Ofertas Diárias")
    if "DATA" in df_tec.columns and df_tec["DATA"].notna().any():
        df_graf = df_tec.dropna(subset=["DATA"]).copy()
        df_graf["DIA"] = df_graf["DATA"].dt.date
        if not df_graf.empty:
            df_tempo = (
                df_graf.groupby("DIA")[["CONSULTIVOS", "VENDAS"]].sum().reset_index()
            )
            st.plotly_chart(
                Graficos.grafico_linhas_vendas(
                    df_tempo, "DIA", "CONSULTIVOS", "VENDAS"
                ),
                use_container_width=True,
            )
    else:
        render_insight("Coluna de data não encontrada na base.", "alerta")

with g_pizza:
    st.markdown("#### 🥧 Proporção do Mix")
    df_mix = pd.DataFrame(
        {"Produto": ["Mesh", "TV Box", "Virtua"], "Quantidade": [t_mesh, t_tv, t_vir]}
    )
    df_mix = df_mix[df_mix["Quantidade"] > 0]
    if not df_mix.empty:
        st.plotly_chart(Graficos.grafico_rosca_mix(df_mix), use_container_width=True)
    else:
        render_insight("Nenhum produto (Mesh/TV/Virtua) vendido no período.", "ok")
