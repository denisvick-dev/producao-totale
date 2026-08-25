"""
componentes.py
==============
Módulo central de estilos, fontes e componentes reutilizáveis
para todo o projeto Streamlit.

Uso em qualquer página:
    from componentes import aplicar_estilo, render_kpi, render_insight
    aplicar_estilo()

Características unificadas:
- Fonte corporativa global super Premium (Inter para texto + Manrope para títulos/KPIs)
- Tema Plotly global corporativo integrado com a tipografia do sistema
- Sidebar TOTALE: Laranja metálico limpo (sem reflexo) + borda no sombreamento
- Selecionador creme/pêssego com borda laranja (estilo pill)
- Heros TOTALE (Gradiente Imagem + Azul com faixa laranja)
- Componentes: KPIs, Insights, Dataframes, Nav Headers
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Literal, Union

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
import streamlit.components.v1 as components

logger = logging.getLogger(__name__)

# ====================================================
# TIPOS LITERAIS
# ====================================================
TemaKPI = Literal["azul", "verde", "vermelho", "laranja", "cinza"]
TipoInsight = Literal["ok", "info", "alerta", "critico", "acao"]

BaseFormatter = Union[str, Callable[[object], str]]
FmtDict = dict[str, BaseFormatter | None]


# ====================================================
# TIPOGRAFIA CORPORATIVA (INTER + MANROPE)
# ====================================================
FONTE_TITULO = "'Manrope', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
FONTE_TEXTO = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
FONTE_CODIGO = "'JetBrains Mono', 'Fira Code', Consolas, monospace"

_GOOGLE_FONTS_URLS = (
    "https://fonts.googleapis.com/icon?family=Material+Icons",
    "https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded"
    ":opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=block",
    "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined"
    ":opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=block",
    "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800"
    "&family=Manrope:wght@300;400;500;600;700;800;900"
    "&family=JetBrains+Mono:wght@400;500&display=swap",
)

# ====================================================
# PALETA CORPORATIVA TOTALE
# ====================================================
COR_PRIMARIA = "#012869"      # Azul institucional Totale
COR_SECUNDARIA = "#F37C04"    # Laranja corporativo Totale
COR_SUCESSO = "#059669"
COR_ALERTA = "#DC2626"
COR_NEUTRO = "#64748B"
COR_TEXTO = "#1F2937"
COR_TEXTO_2 = "#374151"
COR_TEXTO_3 = "#6B7280"
COR_BORDA = "#E2E8F0"
COR_FUNDO = "#F8FAFC"

# Laranja metálico
COR_LARANJA_METAL_1 = "#7A2E00"
COR_LARANJA_METAL_2 = "#C24A00"
COR_LARANJA_METAL_3 = "#E85D04"
COR_LARANJA_METAL_4 = "#F37C04"
COR_LARANJA_METAL_5 = "#FF9838"
COR_LARANJA_METAL_6 = "#FFB86B"

_TEMA_CORES: dict[str, str] = {
    "azul": COR_PRIMARIA,
    "verde": COR_SUCESSO,
    "vermelho": COR_ALERTA,
    "laranja": COR_SECUNDARIA,
    "cinza": COR_NEUTRO,
}

_INSIGHT_CONFIG: dict[str, tuple[str, str, str, str]] = {
    "ok": ("#D1FAE5", "#065F46", "#059669", "✅"),
    "info": ("#DBEAFE", "#1E40AF", "#3B82F6", "ℹ️"),
    "alerta": ("#FEF3C7", "#92400E", "#F59E0B", "⚠️"),
    "critico": ("#FEE2E2", "#991B1B", "#DC2626", "🚨"),
    "acao": ("#EDE9FE", "#5B21B6", "#8B5CF6", "🎯"),
}

_PLOTLY_COLORWAY = [
    COR_PRIMARIA,
    COR_SECUNDARIA,
    COR_SUCESSO,
    COR_ALERTA,
    "#8B5CF6",
    "#EC4899",
    "#14B8A6",
    "#F59E0B",
    "#6366F1",
    COR_NEUTRO,
]


# ====================================================
# PLOTLY (INTEGRAÇÃO DE FONTES CORPORATIVAS)
# ====================================================
def _configurar_plotly_global() -> None:
    template = go.layout.Template(
        layout=go.Layout(
            font=dict(family="Inter, sans-serif", size=13, color=COR_TEXTO),
            title=dict(
                font=dict(family="Manrope, sans-serif", size=20, color=COR_TEXTO),
                x=0.02,
                xanchor="left",
            ),
            legend=dict(font=dict(family="Inter, sans-serif", size=12, color=COR_TEXTO_2)),
            xaxis=dict(
                tickfont=dict(family="Inter, sans-serif", size=12, color=COR_TEXTO_2),
                title_font=dict(family="Inter, sans-serif", size=13, color=COR_TEXTO_2),
                gridcolor="#F1F5F9",
                zerolinecolor="#CBD5E1",
            ),
            yaxis=dict(
                tickfont=dict(family="Inter, sans-serif", size=12, color=COR_TEXTO_2),
                title_font=dict(family="Inter, sans-serif", size=13, color=COR_TEXTO_2),
                gridcolor="#F1F5F9",
                zerolinecolor="#CBD5E1",
            ),
            hoverlabel=dict(
                font=dict(family="Inter, sans-serif", size=13),
                bgcolor="white",
                bordercolor=COR_BORDA,
            ),
            paper_bgcolor="white",
            plot_bgcolor="white",
            colorway=_PLOTLY_COLORWAY,
        )
    )
    pio.templates["corporativo"] = template
    pio.templates.default = "plotly_white+corporativo"


# ====================================================
# SUPORTE PARA FONTES NOS PAINÉIS
# ====================================================
def _injetar_fontes_no_head_pai() -> None:
    urls_js = ", ".join(f'"{u}"' for u in _GOOGLE_FONTS_URLS)
    components.html(
        f"""
        <script>
        (function () {{
            const urls = [{urls_js}];
            const preconnects = [
                'https://fonts.googleapis.com',
                'https://fonts.gstatic.com'
            ];
            let parentDoc;
            try {{ parentDoc = window.parent.document; }}
            catch (e) {{ return; }}
            const head = parentDoc.head;
            preconnects.forEach(function (href) {{
                if (head.querySelector('link[href="' + href + '"]')) return;
                const link = parentDoc.createElement('link');
                link.rel = 'preconnect';
                link.href = href;
                if (href.includes('gstatic')) link.crossOrigin = 'anonymous';
                head.appendChild(link);
            }});
            const existentes = Array.from(
                head.querySelectorAll('link[rel="stylesheet"]')
            ).map(function (l) {{ return l.href; }});
            urls.forEach(function (href) {{
                if (existentes.includes(href)) return;
                const link = parentDoc.createElement('link');
                link.rel  = 'stylesheet';
                link.href = href;
                head.appendChild(link);
            }});
        }})();
        </script>
        """,
        height=0,
    )


def _build_links_html() -> str:
    tags = "\n".join(
        f'<link rel="stylesheet" href="{url}">' for url in _GOOGLE_FONTS_URLS
    )
    return (
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        + tags
    )


# ====================================================
# CSS GLOBAL E TIPOGRAFIA DE ALTA FIDELIDADE
# ====================================================
def _injetar_css_global() -> None:
    links_html = _build_links_html()

    css = f"""{links_html}
        <style>
        /* ═════════ IMPORTAÇÃO DIRETA DE FONTE (FALLBACK SEGURO) ═════════ */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Manrope:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');

        /* ═════════ VARIÁVEIS GLOBAIS ═════════ */
        :root {{
            --font-titulo:    {FONTE_TITULO};
            --font-texto:     {FONTE_TEXTO};
            --font-codigo:    {FONTE_CODIGO};
            --cor-primaria:   {COR_PRIMARIA};
            --cor-secundaria: {COR_SECUNDARIA};
            --cor-sucesso:    {COR_SUCESSO};
            --cor-alerta:     {COR_ALERTA};
            --cor-neutro:     {COR_NEUTRO};
            --cor-texto:      {COR_TEXTO};
            --cor-texto-2:    {COR_TEXTO_2};
            --cor-texto-3:    {COR_TEXTO_3};
            --cor-borda:      {COR_BORDA};
            --cor-fundo:      {COR_FUNDO};
            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 14px;
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.06);
            --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
            --shadow-lg: 0 10px 28px rgba(0,0,0,0.12);
        }}

        /* ═════════ OVERRIDES DE FONTES (FORÇADO PARA STREAMLIT) ═════════ */
        /* Estilização Geral do App */
        html, body, .stApp, 
        [data-testid="stAppViewContainer"], 
        [data-testid="stMain"], 
        [data-testid="stHeader"],
        [data-testid="stSidebar"], 
        [data-testid="stToolbar"],
        [data-testid="stAppViewBlockContainer"] {{
            font-family: var(--font-texto) !important;
            color: var(--cor-texto);
        }}

        /* Textos, Inputs, Labels e Parágrafos (Inter) */
        p, label, div, li, a, button, input, select, textarea, span,
        [data-testid="stWidgetLabel"],
        [data-testid="stMarkdownContainer"],
        [data-baseweb="select"] *,
        [data-baseweb="input"] *,
        [data-baseweb="tab"] *,
        .stSelectbox, .stMultiSelect, .stSlider {{
            font-family: var(--font-texto) !important;
        }}

        /* Títulos e Cabeçalhos Dinâmicos (Manrope) */
        h1, h2, h3, h4, h5, h6,
        [data-testid="stHeader"] *,
        .hero-title, .section-title, .kpi-value,
        [data-testid="stMetricValue"],
        .st-emotion-cache-10trblm {{
            font-family: var(--font-titulo) !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
        }}
        
        h1, .hero-title, .hero-t1-title, .hero-t2-title {{
            font-weight: 800 !important;
            letter-spacing: -0.04em !important;
        }}

        /* Streamlit Metrics (Manrope para Valores, Inter para Labels) */
        [data-testid="stMetricLabel"] {{
            font-family: var(--font-texto) !important;
            font-weight: 500 !important;
            color: var(--cor-texto-3) !important;
        }}
        [data-testid="stMetricValue"] {{
            font-family: var(--font-titulo) !important;
            font-weight: 800 !important;
            font-variant-numeric: tabular-nums;
        }}

        /* Botões Globais (Inter de Alta Densidade) */
        .stButton button, .stDownloadButton button,
        .stFormSubmitButton button, button[kind] {{
            font-family: var(--font-texto) !important;
            font-weight: 600 !important;
            letter-spacing: 0.01em !important;
            border-radius: var(--radius-sm) !important;
        }}

        /* Dataframes e Tabelas (Inter + Tabular Numbers para Dados) */
        .stDataFrame, .stTable, table, thead, tbody, tr, th, td,
        [data-testid="stTable"] *,
        div[class*="AgGrid"], div[class*="ag-theme"] {{
            font-family: var(--font-texto) !important;
        }}
        th {{ 
            font-weight: 700 !important; 
            font-family: var(--font-titulo) !important;
        }}
        td {{ 
            font-variant-numeric: tabular-nums; 
        }}

        /* Elementos de Código */
        code, pre, kbd, samp, code span {{
            font-family: var(--font-codigo) !important;
        }}

        /* Ajustes finos de Layout do Main Container */
        .main .block-container {{
            padding-top: 1.5rem;
            max-width: 1400px;
        }}

        /* Custom Scrollbar */
        ::-webkit-scrollbar       {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: #F1F5F9; }}
        ::-webkit-scrollbar-thumb {{ background: #CBD5E1; border-radius: 4px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: #94A3B8; }}

        /* ═══════════════════════════════════════════════════
        SIDEBAR — ESTILO PREMIUM TOTALE
        Fundo Clean com detalhe e seleção creme/pêssego
        ═══════════════════════════════════════════════════ */
        section[data-testid="stSidebar"] {{
            background: linear-gradient(
                165deg,
                #F8FAFC 0%,
                #F1F5F9 50%,
                #E2E8F0 100%
            ) !important;
            border-right: 1px solid var(--cor-borda) !important;
            box-shadow: 4px 0 24px rgba(1, 40, 105, 0.06) !important;
        }}

        /* Linha laranja metálica de topo do Sidebar */
        section[data-testid="stSidebar"]::after {{
            content: '' !important;
            display: block !important;
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 4px;
            background: linear-gradient(
                90deg,
                var(--cor-primaria) 0%,
                var(--cor-secundaria) 100%
            );
            z-index: 99;
        }}

        /* Header de Menus no Sidebar */
        .sidebar-menu-header {{
            font-family: var(--font-titulo) !important;
            font-size: 11px !important;
            font-weight: 800 !important;
            color: var(--cor-primaria) !important;
            letter-spacing: 0.12em !important;
            text-transform: uppercase;
            margin: 20px 10px 8px 10px;
            opacity: 0.8;
        }}

        /* Seções de Filtros no Sidebar */
        .sidebar-section-label {{
            font-family: var(--font-texto) !important;
            font-size: 12px !important;
            font-weight: 700 !important;
            color: var(--cor-texto-2) !important;
            margin-top: 15px;
            margin-bottom: 5px;
        }}

        /* ── Item Ativo de Navegação: Estilo Pill Creme/Pêssego + Borda Laranja ── */
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"],
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-selected="true"],
        section[data-testid="stSidebar"] li a[aria-current="page"],
        section[data-testid="stSidebar"] li a[aria-selected="true"] {{
            background: linear-gradient(
                90deg,
                #FFFDF9 0%,
                #FFF3E5 60%,
                #FFE8CC 100%
            ) !important;
            border: 1.5px solid #F37C04 !important;
            border-left: 4px solid #F37C04 !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 12px rgba(243, 124, 4, 0.1) !important;
        }}

        /* Reset de efeitos de hover e ajustes para links inativos */
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a,
        section[data-testid="stSidebar"] li a {{
            border-radius: 10px;
            transition: all 0.2s ease;
        }}
        
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover,
        section[data-testid="stSidebar"] li a:hover {{
            background-color: rgba(243, 124, 4, 0.05) !important;
            color: var(--cor-primaria) !important;
        }}

        /* ═════════════════════════════════════════════════
        🎨 HERO 1 — Estilo Imagem TOTALE (Azul → Laranja)
        ═════════════════════════════════════════════════ */
        .hero-totale-1 {{
            background: linear-gradient(90deg,
                #012869 0%,
                #1e40a6 35%,
                #4c4c8a 55%,
                #b86a2e 85%,
                #d3751f 100%
            );
            border-radius: var(--radius-lg);
            padding: 28px 32px;
            position: relative;
            overflow: hidden;
            margin-bottom: 28px;
            box-shadow: var(--shadow-md);
            display: flex;
            align-items: center;
            gap: 20px;
            min-height: 100px;
        }}
        .hero-totale-1::after {{
            content: '';
            position: absolute;
            top: -50%; bottom: -50%;
            left: 45%; width: 60px;
            background: linear-gradient(
                90deg,
                transparent,
                rgba(255, 255, 255, 0.15),
                transparent
            );
            transform: rotate(25deg);
            pointer-events: none;
        }}
        .hero-t1-icon-box {{
            background: white;
            padding: 10px 12px;
            border-radius: var(--radius-md);
            display: inline-flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            font-size: 32px;
            line-height: 1;
            z-index: 2;
        }}
        .hero-t1-content {{
            position: relative;
            z-index: 2;
            color: white;
        }}
        .hero-t1-title {{
            font-family: var(--font-titulo) !important;
            font-size: 30px;
            font-weight: 800;
            margin: 0;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            line-height: 1.15;
            color: #FFFFFF;
        }}
        .hero-t1-sub {{
            font-family: var(--font-texto) !important;
            font-size: 14px;
            margin: 6px 0 0 0;
            opacity: 0.92;
            font-weight: 400;
            color: #F1F5F9;
        }}

        /* ═════════════════════════════════════════════════
        🎨 HERO 2 — Azul Totale + Faixa Laranja
        ═════════════════════════════════════════════════ */
        .hero-totale-2 {{
            background: var(--cor-primaria);
            border-radius: var(--radius-lg);
            padding: 30px 36px;
            margin-bottom: 28px;
            position: relative;
            box-shadow: var(--shadow-md);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: center;
            min-height: 100px;
        }}
        .hero-totale-2::after {{
            content: '';
            position: absolute;
            bottom: 0; left: 0; right: 0;
            height: 5px;
            background: var(--cor-secundaria);
        }}
        .hero-t2-title {{
            font-family: var(--font-titulo) !important;
            color: #FFFFFF;
            font-size: 28px;
            font-weight: 800;
            margin: 0 0 6px 0;
            letter-spacing: -0.02em;
            position: relative;
            z-index: 2;
        }}
        .hero-t2-sub {{
            font-family: var(--font-texto) !important;
            color: #E2E8F0;
            font-size: 15px;
            margin: 0;
            position: relative;
            z-index: 2;
            font-weight: 400;
        }}

        /* ═════════ KPI CARDS (MANROPE) ═════════ */
        .kpi-card {{
            background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
            border-radius: var(--radius-md);
            padding: 20px 24px;
            box-shadow: var(--shadow-sm);
            border: 1px solid var(--cor-borda);
            border-left: 4px solid var(--cor-primaria);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        .kpi-card:hover {{
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
            border-color: #CBD5E1;
        }}
        .kpi-label {{
            font-family: var(--font-texto) !important;
            font-size: 11px;
            font-weight: 600;
            color: var(--cor-texto-3);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 6px;
        }}
        .kpi-value {{
            font-family: var(--font-titulo) !important;
            font-size: 28px;
            font-weight: 800;
            color: var(--cor-texto);
            line-height: 1;
            font-variant-numeric: tabular-nums;
        }}
        .kpi-sub {{
            font-family: var(--font-texto) !important;
            font-size: 12px;
            color: var(--cor-texto-3);
            margin-top: 6px;
            font-weight: 400;
        }}

        /* ═════════ SEÇÕES E DIVISORES ═════════ */
        .section-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 32px 0 16px 0;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--cor-borda);
        }}
        .section-title {{
            font-family: var(--font-titulo) !important;
            font-size: 20px;
            font-weight: 800;
            color: var(--cor-primaria);
            margin: 0;
        }}
        .section-badge {{
            background: linear-gradient(135deg, #F1F5F9 0%, #E2E8F0 100%);
            color: var(--cor-texto-2);
            padding: 4px 10px;
            border-radius: var(--radius-sm);
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border: 1px solid #CBD5E1;
        }}

        /* ═════════ ICONES MATERIAL SYSTEM ═════════ */
        .material-icons, .material-icons-outlined, .material-icons-round,
        .material-symbols-outlined, .material-symbols-rounded {{
            font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important;
            font-weight: normal !important;
            font-style: normal !important;
            line-height: 1 !important;
            letter-spacing: normal !important;
            text-transform: none !important;
            white-space: nowrap !important;
            direction: ltr !important;
            -webkit-font-smoothing: antialiased !important;
        }}
        </style>
        """

    st.markdown(css, unsafe_allow_html=True)


# ====================================================
# API PÚBLICA DE CONFIGURAÇÃO DE TELA
# ====================================================
def aplicar_estilo() -> None:
    """Aplica a tipografia corporativa Premium, tema Plotly e estilo CSS global."""
    _configurar_plotly_global()
    _injetar_fontes_no_head_pai()
    _injetar_css_global()


# ====================================================
# HELPERS DE RENDERIZAÇÃO
# ====================================================
def _resolver_cor_tema(tema: str) -> str:
    cor = _TEMA_CORES.get(tema)
    if cor is None:
        logger.warning("Tema desconhecido: '%s'. Usando 'azul'.", tema)
        return COR_PRIMARIA
    return cor


def _markdown_inline_para_html(texto: str) -> str:
    texto = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", texto)
    texto = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", texto)
    texto = re.sub(r"`([^`]+)`", r"<code>\1</code>", texto)
    return texto


# ====================================================
# HEROS DE ENTRADA E CONTEXTO
# ====================================================
def render_hero_totale_1(
    titulo: str = "Portal TOTALE",
    subtitulo: str = "Painéis de Produção, Indicadores e Gestão Estratégica",
    icone: str = "📊",
) -> None:
    """Hero Premium com gradiente luminoso azul-laranja e ícone."""
    if not titulo:
        raise ValueError("render_hero_totale_1: 'titulo' não pode ser vazio.")
    st.markdown(
        f"""
        <div class="hero-totale-1">
            <div class="hero-t1-icon-box">{icone}</div>
            <div class="hero-t1-content">
                <h1 class="hero-t1-title">{titulo}</h1>
                <p class="hero-t1-sub">{subtitulo}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero_totale_2(titulo: str, subtitulo: str = "") -> None:
    """Hero Azul Totale corporativo estruturado com friso laranja na base."""
    if not titulo:
        raise ValueError("render_hero_totale_2: 'titulo' não pode ser vazio.")
    sub_html = f'<p class="hero-t2-sub">{subtitulo}</p>' if subtitulo else ""
    st.markdown(
        f"""
        <div class="hero-totale-2">
            <h1 class="hero-t2-title">{titulo}</h1>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero(titulo: str, subtitulo: str = "", badge: str = "") -> None:
    """Fallback legado para render_hero_totale_1."""
    extra = f" · {badge}" if badge else ""
    render_hero_totale_1(titulo=titulo, subtitulo=f"{subtitulo}{extra}".strip(" ·"))


# ====================================================
# COMPONENTES DO MENU SIDEBAR
# ====================================================
def render_sidebar_nav_header(titulo: str) -> None:
    """Sub-divisor de navegação para menus estruturados."""
    if not titulo:
        return
    st.sidebar.markdown(
        f'<div class="sidebar-menu-header">{titulo}</div>',
        unsafe_allow_html=True,
    )


def render_sidebar_brand(
    titulo: str,
    subtitulo: str = "",
    icone: str = "🏢",
) -> None:
    """Identidade corporativa principal do cliente no topo do Sidebar."""
    if not titulo:
        raise ValueError("render_sidebar_brand: 'titulo' não pode ser vazio.")
    sub_html = (
        f'<p style="font-family:{FONTE_TEXTO};font-size:11px;color:var(--cor-texto-3);'
        f'margin:4px 0 0 0;font-weight:500;">{subtitulo}</p>' if subtitulo else ""
    )
    st.sidebar.markdown(
        f"""
        <div style="padding: 10px 10px 18px 10px; border-bottom: 1px solid var(--cor-borda);">
            <h2 style="font-family:{FONTE_TITULO};font-size:18px;color:var(--cor-primaria);'
            f'margin:0;font-weight:900;display:flex;align-items:center;gap:8px;">
                <span>{icone}</span> {titulo}
            </h2>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_section(label: str) -> None:
    """Label estático para organização de filtros de controle."""
    if not label:
        return
    st.sidebar.markdown(
        f'<div class="sidebar-section-label">{label}</div>',
        unsafe_allow_html=True,
    )


# ====================================================
# COMPONENTES DE CONTEÚDO E MÉTRICAS
# ====================================================
def render_section(titulo: str, divider: str = "gray") -> None:
    """Divisor padrão de seção de dashboard."""
    st.subheader(titulo, divider=divider)  # type: ignore[arg-type]


def render_section_header(icon: str, title: str, badge: str = "") -> None:
    """Título de seção corporativo com suporte para badges e ícones."""
    if not title:
        raise ValueError("render_section_header: 'title' vazio.")
    badge_html = f'<span class="section-badge">{badge}</span>' if badge else ""
    st.markdown(
        f"""
        <div class="section-header">
            <span style="font-size:22px;line-height:1;">{icon}</span>
            <h2 class="section-title">{title}</h2>
            {badge_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi(
    col: Any,
    label: str,
    valor: str,
    sub: str = "",
    tema: TemaKPI = "azul",
) -> None:
    """Renderiza um card de KPI corporativo sofisticado baseado em Manrope e Inter."""
    cor = _resolver_cor_tema(tema)
    col.markdown(
        f"""
        <div class="kpi-card" style="border-left-color:{cor};">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value" style="color:{cor};">{valor}</div>
            <div class="kpi-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_sm(
    container: Any,
    label: str,
    valor: str,
    sub: str = "",
    tema: TemaKPI = "azul",
) -> None:
    """Versão reduzida do card de KPI (compacto para sidebars e tabelas auxiliares)."""
    cor = _resolver_cor_tema(tema)
    container.markdown(
        f"""
        <div style="background:white;border-radius:var(--radius-sm);padding:12px 14px;
             border-left:3px solid {cor};margin-bottom:8px;
             border: 1px solid var(--cor-borda); border-left-color:{cor};
             box-shadow:var(--shadow-sm);">
            <div style="font-family:{FONTE_TEXTO};font-size:10px;
                 color:var(--cor-texto-3);text-transform:uppercase;
                 letter-spacing:0.05em;font-weight:700;">{label}</div>
            <div style="font-family:{FONTE_TITULO};font-size:20px;
                 color:{cor};font-weight:800;line-height:1.2;
                 margin-top:4px;font-variant-numeric:tabular-nums;">{valor}</div>
            <div style="font-family:{FONTE_TEXTO};font-size:11px;
                 color:var(--cor-texto-3);margin-top:2px;font-weight:400;">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_insight(msg: str, tipo: TipoInsight = "info") -> None:
    """Caixa de chamados e insights executivos (Inter)."""
    if not msg:
        return
    config = _INSIGHT_CONFIG.get(tipo)
    if config is None:
        logger.warning("Tipo desconhecido: '%s'. Usando 'info'.", tipo)
        config = _INSIGHT_CONFIG["info"]
    bg, texto, borda, icone = config
    msg_html = _markdown_inline_para_html(msg)
    st.markdown(
        f"""
        <div style="background:{bg};color:{texto};
             border-left:4px solid {borda};
             padding:12px 16px;border-radius:var(--radius-sm);margin:12px 0;
             font-family:{FONTE_TEXTO};font-size:14px;line-height:1.6;font-weight:500;">
            <span style="margin-right:8px;font-size:15px;">{icone}</span>{msg_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dataframe(
    df: pd.DataFrame,
    titulo: str = "",
    icone: str = "📊",
    height: int = 400,
    fmt: FmtDict | None = None,
    **kwargs: Any,
) -> None:
    """Renderização de dataframes interativos com formatação e tipografia corporativa."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"Esperado pd.DataFrame, recebido {type(df).__name__}.")
    if df.empty:
        st.info("Nenhum dado disponível para exibição.")
        return
    if titulo:
        st.markdown(
            f'<div style="font-family:{FONTE_TITULO};font-size:15px;font-weight:700;'
            f'margin-bottom:8px;color:var(--cor-texto);">{icone} {titulo}</div>',
            unsafe_allow_html=True,
        )
    if fmt:
        fmt_valido: FmtDict = {c: f for c, f in fmt.items() if c in df.columns}
        if fmt_valido:
            try:
                st.dataframe(
                    df.style.format(fmt_valido),  # type: ignore[arg-type]
                    height=height,
                    use_container_width=True,
                    hide_index=True,
                    **kwargs,
                )
                return
            except Exception:
                logger.exception("Falha ao formatar DataFrame. Exibindo sem formatação.")
    st.dataframe(df, height=height, use_container_width=True, hide_index=True, **kwargs)