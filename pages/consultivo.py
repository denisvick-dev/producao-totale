# pages/consultivo.py
import io
import locale
from typing import ClassVar

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
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
        injetar_css_menu_nomes,
        render_hero_totale_1,
        render_insight,
        render_kpi,
        render_sidebar_portal,
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
# 4. SIDEBAR PADRONIZADA
# ====================================================
def render_sidebar_perfil() -> None:
    render_sidebar_portal(
        nome=nome_logado,
        login=login_logado,
        user=user_logado,
        pagina_logout="streamlit_app.py",
        perfil=str(info_logado.get("perfil", "")),
    )


# ====================================================
# 5. CLASSES DO MOTOR DE PROCESSAMENTO DE DADOS
# ====================================================
class ProcessadorDeDados:
    VAZIOS: ClassVar[list[str]] = ["-", "N/A", "nan", "None", "NaN", "null"]

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
            [d for d in pd.date_range(inicio_mes, fim_mes) if d.day_of_week < 6]
        )
        dias_decorridos = len(
            [d for d in pd.date_range(inicio_mes, hoje) if d.day_of_week < 6]
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
    def buscar_coluna(df: pd.DataFrame, palavras: list[str]) -> str | None:
        cols = {str(c).strip().upper(): c for c in df.columns}
        for p in palavras:
            chave = str(p).strip().upper()
            if chave in cols:
                return cols[chave]
        return None

    @staticmethod
    def converter_data(series: pd.Series) -> pd.Series:
        """
        Converte datas detectando o formato automaticamente:
        - ISO (2026-12-08)          → direto
        - Brasileiro (08/12/2026)   → dayfirst=True
        - Americano (12/08/2026)    → dayfirst=False (só se confirmado)
        Ambíguo → assume padrão brasileiro (DD/MM/YYYY).
        """
        if pd.api.types.is_datetime64_any_dtype(series):
            return series

        s = series.astype(str).str.strip()
        validos = s[~s.str.lower().isin(["", "nan", "nat", "none"])]

        if validos.empty:
            return pd.to_datetime(series, errors="coerce")

        # 1. ISO → pandas resolve sozinho
        if validos.str.match(r"^\d{4}-\d{1,2}-\d{1,2}").mean() > 0.6:
            return pd.to_datetime(s, errors="coerce")

        # 2. Extrai partes numéricas (d1/d2/ano)
        partes = validos.str.extract(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})$")
        if partes.empty or partes[0].isna().all():
            return pd.to_datetime(s, errors="coerce", dayfirst=True)

        p1 = pd.to_numeric(partes[0], errors="coerce")
        p2 = pd.to_numeric(partes[1], errors="coerce")

        # 3. Posição 1 tem valor > 12 → só pode ser DIA (formato BR confirmado)
        if (p1 > 12).any():
            return pd.to_datetime(s, errors="coerce", dayfirst=True)

        # 4. Posição 2 tem valor > 12 → posição 2 é o DIA (formato US confirmado)
        if (p2 > 12).any():
            return pd.to_datetime(s, errors="coerce", dayfirst=False)

        # 5. Ambíguo → padrão Brasil
        return pd.to_datetime(s, errors="coerce", dayfirst=True)

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
            df["DATA"] = Utilitarios.converter_data(df[col_data])

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


def _ler_planilha(conteudo: bytes) -> pd.DataFrame:
    """Interpreta o binário baixado como CSV (3 dialetos) ou XLSX.

    Cada tentativa usa um ``BytesIO`` novo: reaproveitar o mesmo buffer fazia
    o ``read_csv``/``read_excel`` continuar da posição deixada pela tentativa
    anterior, o que podia devolver uma base truncada.
    """
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

    try:
        df = pd.read_excel(io.BytesIO(conteudo), engine="openpyxl")
    except Exception:
        return pd.DataFrame()
    return df if not df.empty else pd.DataFrame()


@st.cache_data(ttl=600, show_spinner=False)
def carregar_e_processar_base() -> pd.DataFrame:
    urls = [
        f"https://drive.google.com/uc?export=download&id={FILE_ID_CONSULTIVO}",
        f"https://docs.google.com/spreadsheets/d/{FILE_ID_CONSULTIVO}/export?format=csv",
    ]
    df_bruto = pd.DataFrame()
    for url in urls:
        try:
            resp = requests.get(url, timeout=(5, 20))
        except requests.RequestException:
            continue
        if resp.status_code != 200 or len(resp.content) <= 100:
            continue
        df_bruto = _ler_planilha(resp.content)
        if not df_bruto.empty:
            break

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
injetar_css_menu_nomes()
render_sidebar_perfil()

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

df_cons[col_tec] = df_cons[col_tec].astype(str).str.strip().str.upper()

mask_logado = pd.Series(False, index=df_cons.index)
if nome_logado:
    mask_logado |= df_cons[col_tec].eq(nome_logado)
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
t_cons = int(df_tec["CONSULTIVOS"].sum())
t_prod = int(df_tec["VENDAS"].sum())
t_mesh = int(df_tec["MESH"].sum())
t_tv = int(df_tec["TV"].sum())
t_vir = int(df_tec["VIRTUA"].sum())

taxa_conversao = (t_prod / t_cons) if t_cons > 0 else 0.0
fator_proj, falt_dias = Calculos.fator_projecao(df_tec)
proj_cons = round(t_cons * fator_proj)
proj_prod = round(t_prod * fator_proj)

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
                width="stretch",
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
        st.plotly_chart(Graficos.grafico_rosca_mix(df_mix), width="stretch")
    else:
        render_insight("Nenhum produto (Mesh/TV/Virtua) vendido no período.", "ok")
