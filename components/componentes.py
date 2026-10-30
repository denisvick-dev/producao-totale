"""
componentes.py
==============
Módulo central de estilos, fontes e componentes reutilizáveis
para todo o projeto Streamlit.

Uso em qualquer página:
    from componentes import aplicar_estilo, render_kpi, render_insight
    aplicar_estilo()

Fontes corporativas:
    • IBM Plex Sans → textos, títulos, KPIs, labels, tabelas e botões
    • IBM Plex Mono → blocos de código
    • Material     → Ícones nativos e customizados
"""

from __future__ import annotations

import html
import logging
import re
import textwrap
from collections.abc import Callable
from typing import Any, Literal

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

logger = logging.getLogger(__name__)

# ====================================================
# TIPOS LITERAIS
# ====================================================
TemaKPI = Literal["azul", "verde", "vermelho", "laranja", "cinza"]
TipoInsight = Literal["ok", "info", "alerta", "critico", "acao"]

BaseFormatter = str | Callable[[object], str]
FmtDict = dict[str, BaseFormatter | None]


# ====================================================
# TIPOGRAFIA CORPORATIVA (IBM PLEX SANS + IBM PLEX MONO)
# ====================================================
FONTE_TITULO = "'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
FONTE_TEXTO = "'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
FONTE_CODIGO = "'IBM Plex Mono', Consolas, monospace"

# ── URLs do Google Fonts (Otimizadas e completas para Ícones) ──
_GOOGLE_FONTS_URLS: list[str] = [
    # Inter: pesos 300–800, latin + latin-ext
    (
        "https://fonts.googleapis.com/css2"
        "?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap"
    ),
    # IBM Plex Sans: pesos 400–700
    (
        "https://fonts.googleapis.com/css2"
        "?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap"
    ),
    # IBM Plex Mono: pesos 400–500 (código)
    (
        "https://fonts.googleapis.com/css2"
        "?family=IBM+Plex+Mono:wght@400;500&display=swap"
    ),
    # Material Icons (Clássico - Necessário para o Streamlit nativo)
    "https://fonts.googleapis.com/icon?family=Material+Icons",
    "https://fonts.googleapis.com/icon?family=Material+Icons+Outlined",
    "https://fonts.googleapis.com/icon?family=Material+Icons+Round",
    # Material Symbols (Novo - Para ícones customizados do app)
    (
        "https://fonts.googleapis.com/css2"
        "?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=block"
    ),
    (
        "https://fonts.googleapis.com/css2"
        "?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=block"
    ),
]

# Preconnects para acelerar resolução DNS/TLS
_PRECONNECT_URLS: list[str] = [
    "https://fonts.googleapis.com",
    "https://fonts.gstatic.com",
]


# ====================================================
# PALETA CORPORATIVA TOTALE
# ====================================================
COR_PRIMARIA = "#12304A"
COR_SECUNDARIA = "#C66A16"
COR_SUCESSO = "#16745B"
COR_ALERTA = "#B42318"
COR_NEUTRO = "#536779"
COR_TEXTO = "#172B3A"
COR_TEXTO_2 = "#3E5566"
COR_TEXTO_3 = "#6B7C89"
COR_BORDA = "#D9E2E8"
COR_FUNDO = "#F4F7F9"

_TEMA_CORES: dict[str, str] = {
    "azul": COR_PRIMARIA,
    "verde": COR_SUCESSO,
    "vermelho": COR_ALERTA,
    "laranja": COR_SECUNDARIA,
    "cinza": COR_NEUTRO,
}

#: Fundos suaves usados quando ``render_kpi(colorida=True)``.
_FUNDO_KPI: dict[str, str] = {
    "azul": "#F1F5F9",
    "verde": "#E8F4EF",
    "vermelho": "#FDECEA",
    "laranja": "#FFF3E4",
    "cinza": "#F3F5F7",
}

_INSIGHT_CONFIG: dict[str, tuple[str, str, str, str]] = {
    "ok": ("#E8F4EF", "#145C49", "#16745B", "✅"),
    "info": ("#E8F0F5", "#214B68", "#4D7B99", "ℹ️"),
    "alerta": ("#FFF3E4", "#8A4B16", "#C66A16", "⚠️"),
    "critico": ("#FDECEA", "#8E2119", "#B42318", "🚨"),
    "acao": ("#EAF1F3", "#245665", "#327D8C", "🎯"),
}

_PLOTLY_COLORWAY = [
    COR_PRIMARIA,
    COR_SECUNDARIA,
    COR_SUCESSO,
    COR_ALERTA,
    "#327D8C",
    "#7A8791",
    "#B9853B",
    "#6B8E8E",
    "#A65D3D",
    COR_NEUTRO,
]


# ====================================================
# 1. PLOTLY — TEMA GLOBAL COM FONTES CORPORATIVAS
# ====================================================
def _configurar_plotly_global() -> None:
    template = go.layout.Template(
        layout=go.Layout(
            font=dict(family="IBM Plex Sans, sans-serif", size=13, color=COR_TEXTO),
            title=dict(
                font=dict(family="IBM Plex Sans, sans-serif", size=20, color=COR_TEXTO),
                x=0.02,
                xanchor="left",
            ),
            legend=dict(
                font=dict(family="IBM Plex Sans, sans-serif", size=12, color=COR_TEXTO_2),
            ),
            xaxis=dict(
                tickfont=dict(family="IBM Plex Sans, sans-serif", size=12, color=COR_TEXTO_2),
                title_font=dict(family="IBM Plex Sans, sans-serif", size=13, color=COR_TEXTO_2),
                gridcolor="#F1F5F9",
                zerolinecolor="#CBD5E1",
            ),
            yaxis=dict(
                tickfont=dict(family="IBM Plex Sans, sans-serif", size=12, color=COR_TEXTO_2),
                title_font=dict(family="IBM Plex Sans, sans-serif", size=13, color=COR_TEXTO_2),
                gridcolor="#F1F5F9",
                zerolinecolor="#CBD5E1",
            ),
            hoverlabel=dict(
                font=dict(family="IBM Plex Sans, sans-serif", size=13),
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
# 2. INJEÇÃO DE FONTES NO DOCUMENTO PAI
# ====================================================
def _injetar_fontes_no_head_pai() -> None:
    urls_js = ", ".join(f'"{u}"' for u in _GOOGLE_FONTS_URLS)
    preconnects_js = ", ".join(f'"{u}"' for u in _PRECONNECT_URLS)

    st.iframe(
        textwrap.dedent(
            f"""
        <script>
        (function injectCorporateFonts() {{
            let doc;
            try {{ doc = window.parent.document; }} 
            catch (e) {{ doc = document; }}
            const head = doc.head;

            const preconnects = [{preconnects_js}];
            preconnects.forEach(function(href) {{
                if (head.querySelector('link[rel="preconnect"][href="' + href + '"]')) return;
                const link = doc.createElement('link');
                link.rel = 'preconnect'; link.href = href;
                if (href.includes('gstatic')) link.crossOrigin = 'anonymous';
                head.appendChild(link);
            }});

            const fontURLs = [{urls_js}];
            const existingHrefs = new Set(
                Array.from(head.querySelectorAll('link[rel="stylesheet"]'))
                     .map(function(l) {{ return l.href; }})
            );

            fontURLs.forEach(function(href) {{
                if (existingHrefs.has(href)) return;
                const family = href.match(/family=([^&]+)/);
                if (family) {{
                    const famDecoded = decodeURIComponent(family[1]).split(':')[0];
                    const alreadyLoaded = Array.from(existingHrefs).some(function(h) {{
                        return h.includes(famDecoded);
                    }});
                    if (alreadyLoaded) return;
                }}
                const link = doc.createElement('link');
                link.rel = 'stylesheet'; link.href = href;
                link.setAttribute('data-corporate-font', 'true');
                head.appendChild(link);
            }});

            if ('fonts' in doc) {{
                const fontFamilies = [
                    {{ family: 'IBM Plex Sans', weights: ['400','500','600','700'] }},
                    {{ family: 'IBM Plex Mono', weights: ['400','500'] }},
                ];
                fontFamilies.forEach(function(ff) {{
                    ff.weights.forEach(function(w) {{
                        try {{ doc.fonts.load(w + ' 1em "' + ff.family + '"'); }} 
                        catch(e) {{}}
                    }});
                }});
            }}

            if ('fonts' in doc && doc.fonts.ready) {{
                doc.fonts.ready.then(function() {{
                    doc.body.style.opacity = '0.99';
                    requestAnimationFrame(function() {{ doc.body.style.opacity = '1'; }});
                }});
            }}
        }})();
        </script>
        """
        ).strip(),
        width=1,
        height=1,
    )


# ====================================================
# 3. CSS GLOBAL COM TIPOGRAFIA E ISOLAMENTO DE ÍCONES
# ====================================================
def _injetar_css_global() -> None:
    css = f"""
    <style>
    /* ═════════ IMPORTAÇÃO VIA CSS (FALLBACK) ═════════ */
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&display=swap');
    @import url('https://fonts.googleapis.com/icon?family=Material+Icons');
    @import url('https://fonts.googleapis.com/icon?family=Material+Icons+Outlined');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=block');

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
        --radius-sm: 4px;
        --radius-md: 8px;
        --radius-lg: 10px;
        --shadow-sm: 0 1px 2px rgba(18,48,74,0.06);
        --shadow-md: 0 5px 14px rgba(18,48,74,0.10);
        --shadow-lg: 0 12px 28px rgba(18,48,74,0.14);
    }}

    /* ═══════════════════════════════════════════════════════════
       PROTEÇÃO RIGOROSA PARA ÍCONES MATERIAL DO STREAMLIT
       ═══════════════════════════════════════════════════════════ */
    .material-icons,
    .material-icons-outlined,
    .material-icons-round,
    .material-symbols-outlined,
    .material-symbols-rounded,
    [data-testid="stIconMaterial"],
    [data-testid="stBaseButton-headerNoPadding"] span,
    [data-testid="stSidebarCollapseButton"] span,
    [data-testid="stExpanderToggleIcon"],
    [data-testid="stExpanderToggleIcon"] *,
    [data-testid="stExpanderStepChevron"],
    [data-testid="stExpanderStepChevron"] *,
    [data-testid="stHeaderActionElements"] span,
    [data-testid="StyledFullScreenButton"] span,
    [data-testid="StyledToolbarButton"] span,
    [data-testid="stToolbarActionButton"] span,
    span[class*="material-icons"],
    span[class*="material-symbols"],
    i.material-icons,
    i.material-symbols-outlined,
    i.material-symbols-rounded {{
        font-family: "Material Symbols Rounded", 
                     "Material Symbols Outlined", 
                     "Material Icons", 
                     "Material Icons Outlined" !important;
        font-weight: normal !important;
        font-style: normal !important;
        font-size: inherit;
        line-height: 1 !important;
        letter-spacing: normal !important;
        text-transform: none !important;
        display: inline-block !important;
        white-space: nowrap !important;
        word-wrap: normal !important;
        direction: ltr !important;
        -webkit-font-feature-settings: "liga" !important;
        font-feature-settings: "liga" !important;
        -webkit-font-smoothing: antialiased !important;
        text-rendering: optimizeLegibility !important;
        font-variation-settings: "FILL" 0, "wght" 400, "GRAD" 0, "opsz" 24 !important;
    }}

    /* ═══════════════════════════════════════════════════════════
       OVERRIDES DE FONTES — TEXTOS E COMPONENTES
       ═══════════════════════════════════════════════════════════ */
    
    /* Base estrutural (sem usar curingas '*' que matam ícones) */
    html, body, .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    [data-testid="stHeader"],
    [data-testid="stSidebar"],
    [data-testid="stToolbar"],
    [data-testid="stAppViewBlockContainer"],
    [data-testid="stBottomBlockContainer"] {{
        font-family: var(--font-texto);
        color: var(--cor-texto);
    }}

    /* ── Textos e Componentes (Inter) excluindo Ícones ── */
    p, label, li, a, input, select, textarea,
    [data-testid="stWidgetLabel"],
    [data-testid="stWidgetLabel"] *:not([class*="material"]):not([data-testid*="Icon"]),
    [data-testid="stMarkdownContainer"],
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-baseweb="select"] *:not([class*="material"]),
    [data-baseweb="input"] *,
    [data-baseweb="tab"] *:not([class*="material"]),
    [data-baseweb="tag"] *,
    [data-baseweb="popover"] *,
    .stSelectbox, .stMultiSelect, .stSlider,
    .stRadio, .stCheckbox, .stDateInput,
    .stNumberInput, .stTextInput, .stTextArea,
    .stTimeInput, .stColorPicker {{
        font-family: var(--font-texto) !important;
    }}

    /* ── Sidebar Seguro (Inter) ── */
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] {{
        font-family: var(--font-texto) !important;
    }}

    /* ── Títulos e Cabeçalhos (IBM Plex Sans) ── */
    h1, h2, h3, h4, h5, h6,
    [data-testid="stHeader"] h1,
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3,
    [data-testid="stMarkdownContainer"] h4,
    .hero-title, .section-title, .kpi-value,
    [data-testid="stMetricValue"] {{
        font-family: var(--font-titulo) !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }}

    h1, .hero-title, .hero-t1-title, .hero-t2-title {{
        font-weight: 800 !important;
        letter-spacing: -0.04em !important;
    }}

    /* ── Streamlit Metrics ── */
    [data-testid="stMetricLabel"] {{
        font-family: var(--font-texto) !important;
        font-weight: 500 !important;
        color: var(--cor-texto-3) !important;
        font-size: 13px !important;
    }}
    [data-testid="stMetricValue"] {{
        font-family: var(--font-titulo) !important;
        font-weight: 800 !important;
        font-variant-numeric: tabular-nums;
        font-size: 28px !important;
    }}
    [data-testid="stMetricDelta"] {{
        font-family: var(--font-texto) !important;
        font-weight: 600 !important;
        font-size: 13px !important;
    }}

    /* ── Botões (Inter) ── */
    .stButton button, .stDownloadButton button,
    .stFormSubmitButton button, button[kind],
    [data-testid="stBaseButton-primary"],
    [data-testid="stBaseButton-secondary"] {{
        font-family: var(--font-texto) !important;
        font-weight: 600 !important;
        letter-spacing: 0.01em !important;
        border-radius: var(--radius-sm) !important;
    }}

    /* ── Dataframes e Tabelas ── */
    .stDataFrame, .stTable, table, thead, tbody, tr, th, td,
    [data-testid="stTable"] *,
    div[class*="AgGrid"], div[class*="ag-theme"],
    [data-testid="stDataFrameResizable"] *:not([class*="material"]) {{
        font-family: var(--font-texto) !important;
    }}
    th {{
        font-weight: 700 !important;
        font-family: var(--font-titulo) !important;
    }}
    td {{
        font-variant-numeric: tabular-nums;
    }}

    /* ── Código (IBM Plex Mono) ── */
    code, pre, kbd, samp, code span,
    [data-testid="stCodeBlock"] *,
    .stCodeBlock * {{
        font-family: var(--font-codigo) !important;
    }}

    /* ── Expanders e Tabs ── */
    [data-baseweb="tab"] button,
    [data-baseweb="tab-highlight"] {{
        font-family: var(--font-texto) !important;
        font-weight: 600 !important;
    }}
    [data-testid="stExpander"] summary {{
        font-family: var(--font-titulo) !important;
        font-weight: 700 !important;
    }}
    [data-testid="stExpander"] summary [data-testid="stExpanderStepChevron"],
    [data-testid="stExpander"] summary [data-testid="stExpanderStepChevron"] *,
    [data-testid="stExpander"] summary [data-testid="stExpanderToggleIcon"],
    [data-testid="stExpander"] summary [data-testid="stExpanderToggleIcon"] * {{
        font-family: "Material Symbols Rounded",
                     "Material Symbols Outlined",
                     "Material Icons",
                     "Material Icons Outlined" !important;
        font-weight: normal !important;
        font-size: 18px !important;
    }}

    /* ═══════════════════════════════════════════════════════════
       LAYOUT, SIDEBAR E SCROLLBAR
       ═══════════════════════════════════════════════════════════ */
    .main .block-container {{
        padding-top: 1.5rem;
        max-width: 1400px;
    }}

    ::-webkit-scrollbar       {{ width: 8px; height: 8px; }}
    ::-webkit-scrollbar-track {{ background: #F1F5F9; }}
    ::-webkit-scrollbar-thumb {{ background: #CBD5E1; border-radius: 4px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: #94A3B8; }}

    section[data-testid="stSidebar"] {{
        background: linear-gradient(165deg, #FFFFFF 0%, #F4F7F9 55%, #E8EEF2 100%) !important;
        border-right: 1px solid var(--cor-borda) !important;
        box-shadow: 4px 0 24px rgba(1, 40, 105, 0.06) !important;
    }}

    section[data-testid="stSidebar"]::after {{
        content: '' !important; display: block !important;
        position: absolute; top: 0; left: 0; right: 0; height: 4px;
        background: linear-gradient(90deg, var(--cor-primaria) 0%, var(--cor-secundaria) 100%);
        z-index: 99;
    }}

    .sidebar-menu-header {{
        font-family: var(--font-titulo) !important;
        font-size: 11px !important; font-weight: 800 !important;
        color: var(--cor-primaria) !important;
        letter-spacing: 0.12em !important; text-transform: uppercase;
        margin: 20px 10px 8px 10px; opacity: 0.8;
    }}

    .sidebar-section-label {{
        font-family: var(--font-texto) !important;
        font-size: 12px !important; font-weight: 700 !important;
        color: var(--cor-texto-2) !important;
        margin-top: 15px; margin-bottom: 5px;
    }}

    /* Nav Item Ativo: Pill Creme/Pêssego + Borda Laranja */
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"],
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-selected="true"],
    section[data-testid="stSidebar"] li a[aria-current="page"],
    section[data-testid="stSidebar"] li a[aria-selected="true"] {{
        background: #EAF1F3 !important;
        border: 1.5px solid #C66A16 !important;
        border-left: 4px solid #C66A16 !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(243, 124, 4, 0.1) !important;
        font-family: var(--font-texto) !important;
        font-weight: 600 !important;
    }}

    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a,
    section[data-testid="stSidebar"] li a {{
        border-radius: 10px; transition: all 0.2s ease;
        font-family: var(--font-texto) !important;
    }}

    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover,
    section[data-testid="stSidebar"] li a:hover {{
        background-color: rgba(243, 124, 4, 0.05) !important;
        color: var(--cor-primaria) !important;
    }}

    /* ═══════════════════════════════════════════════════════════
       HEROS E COMPONENTES
       ═══════════════════════════════════════════════════════════ */
    .hero-totale-1 {{
        background: linear-gradient(
            112deg,
            #0C263D 0%,
            #123B59 24%,
            #2A6680 43%,
            #1C4A66 58%,
            #B85E1D 82%,
            #D47A2A 100%
        );
        border-radius: var(--radius-md); padding: 28px 32px;
        position: relative; overflow: hidden; margin-bottom: 28px;
        box-shadow: 0 8px 24px rgba(18, 48, 74, 0.16); display: flex; align-items: center; gap: 20px; min-height: 100px;
    }}
    .hero-totale-1::after {{
        content: ''; position: absolute; top: -50%; bottom: -50%; left: 45%; width: 60px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.22), transparent);
        transform: rotate(25deg); pointer-events: none; opacity: 0.85;
    }}
    .hero-t1-icon-box {{
        background: white; padding: 10px 12px; border-radius: var(--radius-md);
        display: inline-flex; align-items: center; justify-content: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-size: 32px; line-height: 1; z-index: 2;
    }}
    .hero-t1-content {{ position: relative; z-index: 2; color: white; }}
    .hero-t1-title {{
        font-family: var(--font-titulo) !important; font-size: 30px; font-weight: 800;
        margin: 0; text-shadow: 0 2px 4px rgba(0,0,0,0.2); line-height: 1.15; color: #FFFFFF;
    }}
    .hero-t1-sub {{
        font-family: var(--font-texto) !important; font-size: 14px; margin: 6px 0 0 0;
        opacity: 0.92; font-weight: 400; color: #F1F5F9;
    }}
    
    .hero-t1-badge {{
        display: inline-block;
        margin-top: 10px;
        padding: 4px 12px;
        border-radius: 999px;
        font-family: var(--font-texto) !important;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #FFFFFF;
        background: rgba(255, 255, 255, 0.16);
        border: 1px solid rgba(255, 255, 255, 0.35);
        backdrop-filter: blur(6px);
        line-height: 1.2;
    }}

    .hero-totale-2 {{
        background: var(--cor-primaria); border-radius: var(--radius-lg);
        padding: 30px 36px; margin-bottom: 28px; position: relative;
        box-shadow: var(--shadow-md); overflow: hidden; display: flex;
        flex-direction: column; justify-content: center; min-height: 100px;
    }}
    .hero-totale-2::after {{
        content: ''; position: absolute; bottom: 0; left: 0; right: 0;
        height: 5px; background: var(--cor-secundaria);
    }}
    .hero-t2-title {{
        font-family: var(--font-titulo) !important; color: #FFFFFF; font-size: 28px;
        font-weight: 800; margin: 0 0 6px 0; letter-spacing: -0.02em; position: relative; z-index: 2;
    }}
    .hero-t2-sub {{
        font-family: var(--font-texto) !important; color: #E2E8F0; font-size: 15px;
        margin: 0; position: relative; z-index: 2; font-weight: 400;
    }}

    .kpi-card {{
        background: #FFFFFF;
        border-radius: var(--radius-md); padding: 20px 24px; box-shadow: var(--shadow-sm);
        border: 1px solid var(--cor-borda); border-left: 4px solid var(--cor-primaria);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .kpi-card:hover {{ transform: translateY(-2px); box-shadow: var(--shadow-md); border-color: #CBD5E1; }}
    .kpi-label {{
        font-family: var(--font-texto) !important; font-size: 11px; font-weight: 600;
        color: var(--cor-texto-3); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px;
    }}
    .kpi-value {{
        font-family: var(--font-titulo) !important; font-size: 28px; font-weight: 800;
        color: var(--cor-texto); line-height: 1; font-variant-numeric: tabular-nums;
    }}
    .kpi-sub {{
        font-family: var(--font-texto) !important; font-size: 12px;
        color: var(--cor-texto-3); margin-top: 6px; font-weight: 400;
    }}

    .section-header {{
        display: flex; align-items: center; gap: 12px; margin: 32px 0 16px 0;
        padding-bottom: 12px; border-bottom: 1px solid var(--cor-borda);
    }}
    .section-title {{
        font-family: var(--font-titulo) !important; font-size: 20px; font-weight: 800;
        color: var(--cor-primaria); margin: 0;
    }}
    .section-badge {{
        background: linear-gradient(135deg, #F1F5F9 0%, #E2E8F0 100%);
        color: var(--cor-texto-2); padding: 4px 10px; border-radius: var(--radius-sm);
        font-size: 11px; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.05em; border: 1px solid #CBD5E1;
    }}
    </style>
    """
    st.markdown(textwrap.dedent(css).strip(), unsafe_allow_html=True)


# ====================================================
# API PÚBLICA DE CONFIGURAÇÃO DE TELA
# ====================================================
def aplicar_estilo() -> None:
    _configurar_plotly_global()
    _injetar_fontes_no_head_pai()
    _injetar_css_global()


# ====================================================
# HELPERS DE RENDERIZAÇÃO
# ====================================================
def _resolver_cor_tema(tema: str) -> str:
    cor = _TEMA_CORES.get(tema)
    if cor is None:
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
    icone: str = "bar_chart",
    *,
    badge: str = "",
    usar_material: bool = True,
) -> None:
    """Hero Premium azul→laranja com badge opcional abaixo do subtítulo."""
    if not titulo:
        raise ValueError("render_hero_totale_1: 'titulo' não pode ser vazio.")

    titulo_limpo = re.sub(
        r"^[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F900-\U0001F9FF\s]+",
        "",
        titulo,
    ).strip()

    if usar_material:
        icone_html = (
            f'<span class="material-symbols-rounded" '
            f'style="font-size:32px;color:{COR_PRIMARIA};'
            f'font-variation-settings:\'FILL\' 0,\'wght\' 400,\'GRAD\' 0,\'opsz\' 32;">'
            f'{icone}</span>'
        )
    else:
        icone_html = icone

    sub_html = f'<p class="hero-t1-sub">{subtitulo}</p>' if subtitulo else ""
    badge_html = (
        f'<span class="hero-t1-badge">{badge}</span>' if badge else ""
    )

    st.markdown(
        textwrap.dedent(
            f"""
        <div class="hero-totale-1">
            <div class="hero-t1-icon-box">{icone_html}</div>
            <div class="hero-t1-content">
                <h1 class="hero-t1-title">{titulo_limpo}</h1>
                {sub_html}
                {badge_html}
            </div>
        </div>
        """
        ).strip(),
        unsafe_allow_html=True,
    )
    
    
def render_hero_totale_2(titulo: str, subtitulo: str = "") -> None:
    if not titulo:
        raise ValueError("render_hero_totale_2: 'titulo' não pode ser vazio.")
    sub_html = f'<p class="hero-t2-sub">{subtitulo}</p>' if subtitulo else ""
    st.markdown(
        textwrap.dedent(
            f"""
        <div class="hero-totale-2">
            <h1 class="hero-t2-title">{titulo}</h1>
            {sub_html}
        </div>
        """
        ).strip(),
        unsafe_allow_html=True,
    )


def render_hero(titulo: str, subtitulo: str = "", badge: str = "") -> None:
    extra = f" · {badge}" if badge else ""
    render_hero_totale_1(titulo=titulo, subtitulo=f"{subtitulo}{extra}".strip(" ·"))


# ====================================================
# COMPONENTES DO MENU SIDEBAR
# ====================================================
def render_sidebar_nav_header(titulo: str) -> None:
    if not titulo:
        return
    st.sidebar.markdown(
        f'<div class="sidebar-menu-header">{titulo}</div>', unsafe_allow_html=True
    )


def render_sidebar_brand(titulo: str, subtitulo: str = "", icone: str = "🏢") -> None:
    if not titulo:
        raise ValueError("render_sidebar_brand: 'titulo' não pode ser vazio.")
    sub_html = (
        f'<p style="font-family:{FONTE_TEXTO};font-size:11px;color:var(--cor-texto-3);margin:4px 0 0 0;font-weight:500;">{subtitulo}</p>'
        if subtitulo
        else ""
    )
    st.sidebar.markdown(
        textwrap.dedent(
            f"""
        <div style="padding:10px 10px 18px 10px; border-bottom:1px solid var(--cor-borda);">
            <h2 style="font-family:{FONTE_TITULO};font-size:18px;color:var(--cor-primaria);margin:0;font-weight:900;display:flex;align-items:center;gap:8px;">
                <span>{icone}</span> {titulo}
            </h2>
            {sub_html}
        </div>
        """
        ).strip(),
        unsafe_allow_html=True,
    )


def render_sidebar_section(label: str) -> None:
    if not label:
        return
    st.sidebar.markdown(
        f'<div class="sidebar-section-label">{label}</div>', unsafe_allow_html=True
    )


# ====================================================
# COMPONENTES DE CONTEÚDO E MÉTRICAS
# ====================================================
def render_section(titulo: str, divider: str = "gray") -> None:
    st.subheader(titulo, divider=divider)  # type: ignore[arg-type]


def render_section_header(icon: str, title: str, badge: str = "") -> None:
    if not title:
        raise ValueError("render_section_header: 'title' vazio.")
    badge_html = f'<span class="section-badge">{badge}</span>' if badge else ""
    st.markdown(
        textwrap.dedent(
            f"""
        <div class="section-header">
            <span style="font-size:22px;line-height:1;">{icon}</span>
            <h2 class="section-title">{title}</h2>
            {badge_html}
        </div>
        """
        ).strip(),
        unsafe_allow_html=True,
    )


def render_kpi(
    col: Any,
    label: str,
    valor: str,
    sub: str = "",
    tema: TemaKPI = "azul",
    *,
    delta: str = "",
    delta_tipo: Literal["up", "down", "neutral", "none"] = "none",
    colorida: bool = False,
) -> None:
    """Card de KPI do design system.

    ``delta`` e ``delta_tipo`` são opcionais: quando informados, o desvio é
    exibido logo abaixo do valor principal com a cor semântica correspondente.
    ``colorida`` aplica um leve tingimento de fundo na cor do tema.
    """
    cor = _resolver_cor_tema(tema)
    fundo = _FUNDO_KPI.get(tema, "#FFFFFF") if colorida else "#FFFFFF"

    delta_html = ""
    if delta:
        cores_delta = {
            "up": COR_SUCESSO,
            "down": COR_ALERTA,
            "neutral": COR_NEUTRO,
            "none": COR_TEXTO_3,
        }
        setas = {"up": "▲", "down": "▼", "neutral": "■", "none": ""}
        cor_delta = cores_delta.get(delta_tipo, COR_TEXTO_3)
        seta = setas.get(delta_tipo, "")
        delta_html = (
            f'<div class="kpi-delta" style="font-family:{FONTE_TEXTO};font-size:12px;'
            f'color:{cor_delta};font-weight:700;margin-top:8px;'
            f'font-variant-numeric:tabular-nums;">{seta} {delta}</div>'
        )

    col.markdown(
        textwrap.dedent(
            f"""
        <div class="kpi-card" style="border-left-color:{cor};background:{fundo};">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value" style="color:{cor};">{valor}</div>
            {delta_html}
            <div class="kpi-sub">{sub}</div>
        </div>
        """
        ).strip(),
        unsafe_allow_html=True,
    )


def render_kpi_sm(
    container: Any, label: str, valor: str, sub: str = "", tema: TemaKPI = "azul"
) -> None:
    cor = _resolver_cor_tema(tema)
    container.markdown(
        textwrap.dedent(
            f"""
        <div style="background:white;border-radius:var(--radius-sm);padding:12px 14px;border:1px solid var(--cor-borda);border-left:3px solid {cor};margin-bottom:8px;box-shadow:var(--shadow-sm);">
            <div style="font-family:{FONTE_TEXTO};font-size:10px;color:var(--cor-texto-3);text-transform:uppercase;letter-spacing:0.05em;font-weight:700;">{label}</div>
            <div style="font-family:{FONTE_TITULO};font-size:20px;color:{cor};font-weight:800;line-height:1.2;margin-top:4px;font-variant-numeric:tabular-nums;">{valor}</div>
            <div style="font-family:{FONTE_TEXTO};font-size:11px;color:var(--cor-texto-3);margin-top:2px;">{sub}</div>
        </div>
        """
        ).strip(),
        unsafe_allow_html=True,
    )


def render_insight(msg: str, tipo: TipoInsight = "info") -> None:
    if not msg:
        return
    config = _INSIGHT_CONFIG.get(tipo, _INSIGHT_CONFIG["info"])
    bg, texto, borda, icone = config
    msg_html = _markdown_inline_para_html(msg)
    st.markdown(
        textwrap.dedent(
            f"""
        <div style="background:{bg};color:{texto};border-left:4px solid {borda};padding:12px 16px;border-radius:var(--radius-sm);margin:12px 0;font-family:{FONTE_TEXTO};font-size:14px;line-height:1.6;font-weight:500;">
            <span style="margin-right:8px;font-size:15px;">{icone}</span>{msg_html}
        </div>
        """
        ).strip(),
        unsafe_allow_html=True,
    )


def render_progress_bar(
    valor: float,
    maximo: float = 100.0,
    label: str = "",
    mostrar_valor: bool = True,
    tema: TemaKPI = "azul",
    altura: Literal["pequeno", "medio", "grande"] = "medio",
) -> None:
    """Barra de progresso horizontal do design system TOTALE."""
    cor = _resolver_cor_tema(tema)
    try:
        limite = float(maximo)
        pct = float(valor) / limite * 100.0 if limite > 0 else 0.0
    except (TypeError, ValueError):
        pct = 0.0
    pct = max(0.0, min(100.0, pct))

    if label:
        st.caption(str(label))

    altura_px = {"pequeno": 6, "medio": 10, "grande": 14}.get(altura, 10)
    barra = (
        f'<div role="progressbar" aria-valuenow="{pct:.1f}" aria-valuemin="0" '
        f'aria-valuemax="100" style="width:100%;height:{altura_px}px;'
        'background:#E2E8F0;border-radius:999px;overflow:hidden;">'
        f'<div style="width:{pct:.1f}%;height:100%;background:{cor};'
        'border-radius:999px;transition:width 0.3s ease;"></div></div>'
    )

    if mostrar_valor:
        col_barra, col_valor = st.columns([5, 1])
        with col_barra:
            st.markdown(barra, unsafe_allow_html=True)
        with col_valor:
            st.caption(f"{pct:.1f}%")
        return

    st.markdown(barra, unsafe_allow_html=True)


_EMPTY_STATE_CONFIG: dict[str, tuple[str, str, str, str]] = {
    "dados": ("📭", "#F1F5F9", "#3E5566", "#CBD5E1"),
    "info": ("ℹ️", "#E8F0F5", "#214B68", "#4D7B99"),
    "erro": ("🚨", "#FDECEA", "#8E2119", "#B42318"),
    "alerta": ("⚠️", "#FFF3E4", "#8A4B16", "#C66A16"),
    "sucesso": ("✅", "#E8F4EF", "#145C49", "#16745B"),
}


def render_empty_state(
    tipo: Literal["dados", "info", "erro", "alerta", "sucesso"] = "dados",
    titulo: str = "",
    descricao: str = "",
    icone: str = "",
) -> None:
    """Estado vazio/erro padronizado, usado quando um recorte não tem linhas."""
    icone_padrao, fundo, texto, borda = _EMPTY_STATE_CONFIG.get(
        tipo, _EMPTY_STATE_CONFIG["dados"]
    )
    titulo_final = titulo or {
        "dados": "Sem dados para exibir",
        "info": "Informação",
        "erro": "Não foi possível concluir",
        "alerta": "Atenção",
        "sucesso": "Tudo certo",
    }.get(tipo, "")
    descricao_html = (
        f'<p style="margin:6px 0 0 0;font-family:{FONTE_TEXTO};font-size:13px;'
        f'color:{COR_TEXTO_2};line-height:1.55;">{_markdown_inline_para_html(descricao)}</p>'
        if descricao
        else ""
    )
    st.markdown(
        textwrap.dedent(
            f"""
        <div style="background:{fundo};border:1px solid {borda};border-left:4px solid {borda};
                    border-radius:var(--radius-md);padding:20px 22px;margin:14px 0;">
            <div style="display:flex;align-items:flex-start;gap:12px;">
                <span style="font-size:24px;line-height:1;">{icone or icone_padrao}</span>
                <div>
                    <div style="font-family:{FONTE_TITULO};font-size:15px;font-weight:800;
                                color:{texto};">{html.escape(str(titulo_final))}</div>
                    {descricao_html}
                </div>
            </div>
        </div>
        """
        ).strip(),
        unsafe_allow_html=True,
    )


_STATUS_BADGE: dict[str, tuple[str, str, str]] = {
    "CONCLUIDO": ("Concluído", "#E8F4EF", "#145C49"),
    "PENDENTE": ("Pendente", "#FFF3E4", "#8A4B16"),
    "CANCELADO": ("Cancelado", "#FDECEA", "#8E2119"),
}

_CORES_REGRA_TABELA: dict[str, str] = {
    "sucesso": COR_SUCESSO,
    "alerta": COR_ALERTA,
    "neutro": COR_NEUTRO,
}


def _formatar_valor_tabela(valor: Any, spec: str | None) -> str:
    try:
        if valor is None or (not isinstance(valor, (list, dict)) and pd.isna(valor)):
            return "—"
    except (TypeError, ValueError):
        pass
    if not spec:
        if isinstance(valor, float):
            return f"{valor:,.1f}"
        return str(valor)
    try:
        texto = spec.format(valor)
    except (ValueError, IndexError, KeyError, TypeError):
        try:
            texto = format(valor, spec)
        except (ValueError, TypeError):
            return str(valor)
    # Separador de milhar pt-BR para specs puramente inteiros (ex.: "{:,}").
    if "," in spec and "." not in spec:
        texto = texto.replace(",", ".")
    return texto


def render_table_html(
    df: pd.DataFrame,
    colunas: list[str] | None = None,
    alinhamentos: dict[str, str] | None = None,
    fmt: dict[str, str] | None = None,
    color_rules: dict[str, dict[str, str]] | None = None,
    titulo: str = "",
    height: int | None = None,
    mostrar_data: bool = True,  # compatibilidade de API; a tabela é sempre HTML
    **_: Any,
) -> None:
    """Tabela HTML estilizada com alinhamento, formatação e cores semânticas.

    ``color_rules`` mapeia coluna → {valor: "sucesso"|"alerta"|"neutro"}.
    A chave pode ser o valor bruto (``"95.0"``) ou já formatado (``"95.0%"``),
    o que mantém compatibilidade com as regras geradas antes da formatação.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        st.info("Nenhuma linha para exibir neste recorte.")
        return

    colunas_validas = [
        c for c in (colunas or list(df.columns)) if c in df.columns
    ] or list(df.columns)
    alinhamentos = alinhamentos or {}
    fmt = {c: s for c, s in (fmt or {}).items() if c in df.columns}
    color_rules = color_rules or {}

    if titulo:
        st.markdown(
            f'<div style="font-family:{FONTE_TITULO};font-size:15px;font-weight:800;'
            f'color:{COR_TEXTO};margin:22px 0 10px 0;">{html.escape(str(titulo))}</div>',
            unsafe_allow_html=True,
        )

    estilo_th = (
        f"font-family:{FONTE_TEXTO};font-size:10px;font-weight:800;"
        f"color:{COR_TEXTO_3};text-transform:uppercase;letter-spacing:0.05em;"
        "padding:10px 12px;background:#F8FAFC;border-bottom:2px solid #D9E2E8;"
        "white-space:nowrap;position:sticky;top:0;z-index:1;"
    )

    cabecalho = "".join(
        f'<th style="{estilo_th}text-align:{alinhamentos.get(c, "left")};">'
        f"{html.escape(str(c))}</th>"
        for c in colunas_validas
    )

    linhas: list[str] = []
    # ``itertuples`` evita criar uma Series por linha (``iterrows``), o que
    # pesa em tabelas grandes do painel administrativo.
    for valores_linha in df[colunas_validas].itertuples(index=False, name=None):
        celulas: list[str] = []
        for col, valor in zip(colunas_validas, valores_linha):
            espec = fmt.get(col)
            texto = _formatar_valor_tabela(valor, espec)

            if col == "Status" and str(valor) in _STATUS_BADGE:
                rotulo, fundo, cor = _STATUS_BADGE[str(valor)]
                conteudo = (
                    f'<span style="background:{fundo};color:{cor};border:1px solid {cor};'
                    f'padding:2px 8px;border-radius:999px;font-size:10px;'
                    f'font-weight:800;text-transform:uppercase;letter-spacing:0.04em;'
                    f'white-space:nowrap;">{html.escape(rotulo)}</span>'
                )
            else:
                regras = color_rules.get(col) or {}
                regra = regras.get(str(valor)) or regras.get(texto)
                cor = _CORES_REGRA_TABELA.get(str(regra)) if regra else None
                texto_seguro = html.escape(texto)
                conteudo = (
                    f'<span style="color:{cor};font-weight:700;">{texto_seguro}</span>'
                    if cor
                    else texto_seguro
                )

            celulas.append(
                f'<td style="font-family:{FONTE_TEXTO};font-size:13px;color:{COR_TEXTO};'
                f'padding:9px 12px;border-bottom:1px solid #E2E8F0;'
                f'text-align:{alinhamentos.get(col, "left")};'
                f'font-variant-numeric:tabular-nums;white-space:nowrap;">{conteudo}</td>'
            )
        linhas.append("<tr>" + "".join(celulas) + "</tr>")

    altura_css = f"max-height:{int(height)}px;" if height else ""
    st.markdown(
        textwrap.dedent(
            f"""
        <div style="background:#FFFFFF;border:1px solid #D9E2E8;border-radius:8px;
                    overflow:auto;{altura_css}margin-bottom:14px;
                    box-shadow:0 1px 2px rgba(18,48,74,0.06);">
            <table style="width:100%;border-collapse:collapse;background:#FFFFFF;">
                <thead><tr>{cabecalho}</tr></thead>
                <tbody>{''.join(linhas)}</tbody>
            </table>
        </div>
        """
        ).strip(),
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
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"Esperado pd.DataFrame, recebido {type(df).__name__}.")
    if df.empty:
        st.info("Nenhum dado disponível para exibição.")
        return
    if titulo:
        st.markdown(
            f'<div style="font-family:{FONTE_TITULO};font-size:15px;font-weight:700;margin-bottom:8px;color:var(--cor-texto);">{icone} {titulo}</div>',
            unsafe_allow_html=True,
        )
    if fmt:
        fmt_valido: FmtDict = {c: f for c, f in fmt.items() if c in df.columns}
        if fmt_valido:
            try:
                st.dataframe(df.style.format(fmt_valido), height=height, width="stretch", hide_index=True, **kwargs)  # type: ignore
                return
            except Exception:
                logger.exception("Falha ao formatar DataFrame.")
    st.dataframe(df, height=height, width="stretch", hide_index=True, **kwargs)
    

def render_icon(
    nome: str,
    *,
    size: int = 24,
    color: str = "inherit",
    fill: bool = False,
) -> str:
    """
    Retorna HTML de um Material Symbol.
    'nome' usa snake_case da fonte, ex: 'search', 'bar_chart', 'monitoring'.
    """
    fill_val = 1 if fill else 0
    return (
        f'<span class="material-symbols-rounded" '
        f'style="font-size:{size}px;color:{color};'
        f'font-variation-settings:\'FILL\' {fill_val}, \'wght\' 400, \'GRAD\' 0, \'opsz\' {min(size, 48)};'
        f'vertical-align:middle;line-height:1;">{nome}</span>'
    )
    
# ====================================================
# TEMA CLARO FORÇADO (CORRIGE SIDEBAR ESCURO)
# ====================================================
def aplicar_tema_claro() -> None:
    """
    Força Light Mode global no app inteiro.
    Corrige o bug do sidebar escuro quando o tema nativo é dark.
    Chamar SEMPRE logo após aplicar_estilo().
    """
    st.markdown(
        textwrap.dedent(
            """
        <style>
        /* ── FORÇA LIGHT MODE NO APP INTEIRO ── */
        html, body, .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        [data-testid="stAppViewBlockContainer"] {
            background: #F4F7F9 !important;
            color: #172B3A !important;
        }

        /* ── SIDEBAR CLARO ── */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #FFFFFF 0%, #E8EEF2 100%) !important;
            border-right: 1px solid #E2E8F0 !important;
        }
        /* A cor é herdada pelo container; não usamos !important nos
           descendentes para preservar as cores inline dos chips, do status e
           dos ícones renderizados por render_sidebar_portal(). */
        section[data-testid="stSidebar"] {
            color: #1E293B;
        }

        /* ── MENU DE NAVEGAÇÃO ── */
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:first-child {
            display: none !important;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
            background: #F8FAFC !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 10px !important;
            margin: 4px 14px !important;
            padding: 10px 14px !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
            text-decoration: none !important;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a span {
            color: #1E293B !important;
            font-weight: 700 !important;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {
            border-color: #F37C04 !important;
            background: #FFF8F0 !important;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"],
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-selected="true"] {
            background: linear-gradient(90deg, #FFFDF9 0%, #FFF3E5 60%, #FFE8CC 100%) !important;
            border: 1.5px solid #C66A16 !important;
            border-left: 4px solid #C66A16 !important;
            box-shadow: 0 4px 12px rgba(243,124,4,0.10) !important;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] span,
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-selected="true"] span {
            color: #012869 !important;
        }

        /* ── WIDGETS DO MAIN EM MODO CLARO ── */
        [data-baseweb="select"] > div,
        [data-baseweb="input"],
        [data-baseweb="textarea"] {
            background-color: #FFFFFF !important;
            color: #1F2937 !important;
            border-color: #CBD5E1 !important;
        }
        [data-baseweb="popover"] * {
            color: #1F2937 !important;
            background-color: #FFFFFF !important;
        }

        /* ── BOTÃO LOGOUT (Estilo Prata) ── */
        .btn-logout-portal button,
        .st-key-btn_logout_portal button {
            background: linear-gradient(180deg, #E2E8F0 0%, #CBD5E1 100%) !important;
            border: 1px solid #94A3B8 !important;
            color: #1E293B !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.5), 0 2px 4px rgba(0,0,0,0.05) !important;
        }
        .btn-logout-portal button:hover,
        .st-key-btn_logout_portal button:hover {
            background: #F1F5F9 !important;
            border-color: #64748B !important;
            color: #0F172A !important;
        }
        </style>
        """
        ).strip(),
        unsafe_allow_html=True,
    )


# ====================================================
# SIDEBAR DO PORTAL (CARD DE PERFIL)
# ====================================================
def render_sidebar_portal(
    nome: str = "",
    login: str = "",
    user: str = "",
    pagina_logout: str = "streamlit_app.py",
    perfil: str = "",
    tema: Literal["claro", "escuro"] = "claro",
) -> None:
    """Card de perfil, logout e rodapé padronizados para todas as páginas.

    ``tema="escuro"`` preserva a identidade visual do painel administrativo.
    """
    partes = [p for p in (nome or "").split() if p]
    if len(partes) >= 2:
        iniciais = (partes[0][0] + partes[1][0]).upper()
    elif partes:
        iniciais = partes[0][:2].upper()
    else:
        iniciais = "US"

    escuro = tema == "escuro"
    fundo = (
        "linear-gradient(145deg, #1E293B 0%, #0F172A 100%)"
        if escuro
        else "linear-gradient(145deg, #FFFFFF 0%, #EDF0F4 100%)"
    )
    borda = "#334155" if escuro else "#CBD5E1"
    cor_nome = "#F8FAFC" if escuro else "#012869"
    cor_texto = "#CBD5E1" if escuro else "#475569"
    cor_chip = "#F1F5F9" if escuro else "#0F172A"
    fundo_chip = "#334155" if escuro else "#E2E8F0"
    borda_chip = "#475569" if escuro else "#CBD5E1"
    rotulo = "⚡ TOTALE · ADMIN" if escuro else "⚡ TOTALE · PORTAL"
    status_fundo = "rgba(239,68,68,0.15)" if escuro else "#D1FAE5"
    status_borda = "#EF4444" if escuro else "#6EE7B7"
    status_texto = "#FCA5A5" if escuro else "#065F46"
    status_dot = "#EF4444" if escuro else "#10B981"
    status_label = "Sessão Admin" if escuro else "Online"

    perfil_txt = (perfil or "").strip().upper()
    mostrar_perfil = escuro or perfil_txt in {
        "ADMIN",
        "ADM",
        "ADMINISTRADOR",
        "GESTOR",
        "MANAGER",
        "SUPERVISOR",
        "COORDENADOR",
    }
    perfil_html = (
        f'<div style="display:inline-block;background:{fundo_chip};border:1px solid {borda_chip};'
        f'color:{cor_chip};padding:3px 10px;border-radius:20px;font-size:10px;'
        f'font-weight:800;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:12px;">'
        f"🛡️ {html.escape(perfil_txt or 'ADMIN')}</div>"
        if mostrar_perfil
        else ""
    )

    with st.sidebar:
        st.markdown(
            textwrap.dedent(
                f"""
                <div style="background:{fundo};
                     border:1px solid {borda};border-left:4px solid #F97316;
                     border-radius:12px;padding:18px 16px;margin:14px 14px 8px 14px;
                     box-shadow:0 4px 14px rgba(0,0,0,0.06);color:{cor_nome};
                     font-family:'IBM Plex Sans',sans-serif;">
                    <div style="font-size:11px;font-weight:800;letter-spacing:1.5px;
                         color:#F97316;margin-bottom:14px;">{rotulo}</div>
                    <div style="width:54px;height:54px;border-radius:50%;
                         background:linear-gradient(135deg,#012869 0%,#F97316 100%);
                         color:#FFFFFF;display:flex;align-items:center;justify-content:center;
                         font-size:18px;font-weight:800;margin-bottom:12px;
                         box-shadow:0 4px 10px rgba(0,0,0,0.25);">{iniciais}</div>
                    <p style="color:{cor_nome};font-weight:800;font-size:14px;
                       margin:0 0 10px 0;line-height:1.3;">
                        {html.escape(nome or 'TÉCNICO')}
                    </p>
                    {perfil_html}
                    <div style="font-size:12px;color:{cor_texto};margin-bottom:6px;">
                        Login: <span style="background:{fundo_chip};border:1px solid {borda_chip};
                        color:{cor_chip};padding:2px 8px;border-radius:4px;
                        font-family:'IBM Plex Mono',monospace;font-weight:600;">
                            {html.escape(login or '—')}</span>
                    </div>
                    <div style="font-size:12px;color:{cor_texto};margin-bottom:14px;">
                        User: <span style="background:{fundo_chip};border:1px solid {borda_chip};
                        color:{cor_chip};padding:2px 8px;border-radius:4px;
                        font-family:'IBM Plex Mono',monospace;font-weight:600;">
                            {html.escape(user or '—')}</span>
                    </div>
                    <div style="background:{status_fundo};border:1px solid {status_borda};
                         color:{status_texto};padding:4px 12px;border-radius:20px;
                         font-size:11px;font-weight:700;display:inline-flex;
                         align-items:center;gap:6px;">
                        <span style="width:6px;height:6px;background:{status_dot};
                        border-radius:50%;display:inline-block;"></span> {status_label}
                    </div>
                </div>
                """
            ).strip(),
            unsafe_allow_html=True,
        )

        if st.button("🚪 Encerrar Sessão", width="stretch", key="btn_logout_portal"):
            st.session_state["authenticated"] = False
            st.session_state["user_info"] = {}
            st.session_state["is_admin"] = False
            st.switch_page(pagina_logout)
        st.markdown(
            textwrap.dedent(
                """
                <div style="text-align:center;font-size:10px;color:#64748B;
                     margin-top:18px;font-weight:600;letter-spacing:1px;">
                    POWERED BY <span style="color:#F97316;">TOTALE</span>
                </div>
                """
            ).strip(),
            unsafe_allow_html=True,
        )


# ====================================================
# RENOMEAR ITENS DO MENU (helper reutilizável)
# ====================================================
PAGINAS_MENU: dict[str, str] = {
    "producao": "📊 Produtividade",
    "consultivo": "🗣️ Consultivo",
    "indicadores": "⚡ Indicadores",
    "admin": "🛡️ Admin",
}

_PERFIS_ADMIN = {
    "ADMIN",
    "ADM",
    "ADMINISTRADOR",
    "GESTOR",
    "MANAGER",
    "SUPERVISOR",
    "COORDENADOR",
}


def _sessao_e_admin() -> bool:
    if st.session_state.get("is_admin"):
        return True
    info = st.session_state.get("user_info", {}) or {}
    perfil = str(info.get("perfil", "")).strip().upper()
    login = str(info.get("login", "")).strip().upper()
    return perfil in _PERFIS_ADMIN or login.startswith("ADM")


def injetar_css_menu_nomes(
    nomes: dict[str, str] | None = None, *, is_admin: bool | None = None
) -> None:
    """Renomeia, ordena e padroniza o menu lateral em todas as páginas.

    O título é injetado apenas no último ``span`` do link (o rótulo), então o
    ícone Material continua visível e não há texto duplicado. O item Admin é
    exibido somente para administradores.
    """
    mapa = {**PAGINAS_MENU, **(nomes or {})}
    admin = _sessao_e_admin() if is_admin is None else is_admin

    regras: list[str] = []
    for ordem, (slug, titulo) in enumerate(mapa.items(), start=1):
        regras.append(
            f"""
        [data-testid="stSidebarNav"] li:has(a[href*="{slug}"]) {{
            order: {ordem} !important;
        }}
        [data-testid="stSidebarNav"] a[href*="{slug}"] > span:last-child {{
            font-size: 0 !important;
        }}
        [data-testid="stSidebarNav"] a[href*="{slug}"] > span:last-child::before {{
            content: "{titulo}" !important;
            font-size: 14px !important;
            font-weight: 700 !important;
            color: inherit !important;
            font-family: var(--font-texto) !important;
            white-space: nowrap !important;
        }}"""
        )

    if not admin:
        regras.append(
            '[data-testid="stSidebarNav"] a[href*="admin"] { display: none !important; }'
        )

    regras.append(
        """
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] ul {
            display: flex !important;
            flex-direction: column !important;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:first-child {
            display: none !important;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
            background: #F8FAFC !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 8px !important;
            margin: 4px 16px !important;
            padding: 10px 14px !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
            transition: all 0.2s ease;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {
            background: #F1F5F9 !important;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"],
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-selected="true"] {
            background: linear-gradient(90deg, #FFF7ED 0%, #FFEDD5 100%) !important;
            border: 1px solid #C66A16 !important;
            border-left: 4px solid #C66A16 !important;
            box-shadow: 0 4px 10px rgba(198,106,22,0.10) !important;
        }
        """
    )

    st.markdown(f"<style>{''.join(regras)}</style>", unsafe_allow_html=True)
