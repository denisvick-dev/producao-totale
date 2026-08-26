"""
componentes.py
==============
Módulo central de estilos, fontes e componentes reutilizáveis
para todo o projeto Streamlit.

Uso em qualquer página:
    from componentes import aplicar_estilo, render_kpi, render_insight
    aplicar_estilo()

Fontes corporativas:
    • Inter        → textos, labels, inputs, tabelas, botões
    • Manrope      → títulos, KPIs, headers, badges
    • JetBrains Mono → blocos de código
    • Material     → Ícones nativos e customizados
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
# TIPOGRAFIA CORPORATIVA (INTER + MANROPE + JETBRAINS)
# ====================================================
FONTE_TITULO = (
    "'Manrope', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
)
FONTE_TEXTO = (
    "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
)
FONTE_CODIGO = "'JetBrains Mono', 'Fira Code', Consolas, monospace"

# ── URLs do Google Fonts (Otimizadas e completas para Ícones) ──
_GOOGLE_FONTS_URLS: list[str] = [
    # Inter: pesos 300–800, latin + latin-ext
    (
        "https://fonts.googleapis.com/css2"
        "?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;"
        "14..32,600;14..32,700;14..32,800&display=swap"
    ),
    # Manrope: pesos 300–900
    (
        "https://fonts.googleapis.com/css2"
        "?family=Manrope:wght@300;400;500;600;700;800;900&display=swap"
    ),
    # JetBrains Mono: pesos 400–500 (código)
    (
        "https://fonts.googleapis.com/css2"
        "?family=JetBrains+Mono:wght@400;500&display=swap"
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
COR_PRIMARIA = "#012869"
COR_SECUNDARIA = "#F37C04"
COR_SUCESSO = "#059669"
COR_ALERTA = "#DC2626"
COR_NEUTRO = "#64748B"
COR_TEXTO = "#1F2937"
COR_TEXTO_2 = "#374151"
COR_TEXTO_3 = "#6B7280"
COR_BORDA = "#E2E8F0"
COR_FUNDO = "#F8FAFC"

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
# 1. PLOTLY — TEMA GLOBAL COM FONTES CORPORATIVAS
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
            legend=dict(
                font=dict(family="Inter, sans-serif", size=12, color=COR_TEXTO_2),
            ),
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
# 2. INJEÇÃO DE FONTES NO DOCUMENTO PAI
# ====================================================
def _injetar_fontes_no_head_pai() -> None:
    urls_js = ", ".join(f'"{u}"' for u in _GOOGLE_FONTS_URLS)
    preconnects_js = ", ".join(f'"{u}"' for u in _PRECONNECT_URLS)

    components.html(
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
                    {{ family: 'Inter', weights: ['400','500','600','700','800'] }},
                    {{ family: 'Manrope', weights: ['400','600','700','800','900'] }},
                    {{ family: 'JetBrains Mono', weights: ['400','500'] }},
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
        """,
        height=0,
    )


# ====================================================
# 3. CSS GLOBAL COM TIPOGRAFIA E ISOLAMENTO DE ÍCONES
# ====================================================
def _injetar_css_global() -> None:
    css = f"""
    <style>
    /* ═════════ IMPORTAÇÃO VIA CSS (FALLBACK) ═════════ */
    @import url('https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700;14..32,800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;500;600;700;800;900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');
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
        --radius-sm: 6px;
        --radius-md: 10px;
        --radius-lg: 14px;
        --shadow-sm: 0 1px 3px rgba(0,0,0,0.06);
        --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
        --shadow-lg: 0 10px 28px rgba(0,0,0,0.12);
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

    /* ── Títulos e Cabeçalhos (Manrope) ── */
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

    /* ── Código (JetBrains Mono) ── */
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
    [data-testid="stExpander"] summary span {{
        font-family: var(--font-titulo) !important;
        font-weight: 700 !important;
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
        background: linear-gradient(165deg, #F8FAFC 0%, #F1F5F9 50%, #E2E8F0 100%) !important;
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
        background: linear-gradient(90deg, #FFFDF9 0%, #FFF3E5 60%, #FFE8CC 100%) !important;
        border: 1.5px solid #F37C04 !important;
        border-left: 4px solid #F37C04 !important;
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
        background: linear-gradient(90deg, #012869 0%, #1e40a6 35%, #4c4c8a 55%, #b86a2e 85%, #d3751f 100%);
        border-radius: var(--radius-lg); padding: 28px 32px;
        position: relative; overflow: hidden; margin-bottom: 28px;
        box-shadow: var(--shadow-md); display: flex; align-items: center; gap: 20px; min-height: 100px;
    }}
    .hero-totale-1::after {{
        content: ''; position: absolute; top: -50%; bottom: -50%; left: 45%; width: 60px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
        transform: rotate(25deg); pointer-events: none;
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
        background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
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
    st.markdown(css, unsafe_allow_html=True)


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
        f"""
        <div class="hero-totale-1">
            <div class="hero-t1-icon-box">{icone_html}</div>
            <div class="hero-t1-content">
                <h1 class="hero-t1-title">{titulo_limpo}</h1>
                {sub_html}
                {badge_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    
def render_hero_totale_2(titulo: str, subtitulo: str = "") -> None:
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
        f"""
        <div style="padding:10px 10px 18px 10px; border-bottom:1px solid var(--cor-borda);">
            <h2 style="font-family:{FONTE_TITULO};font-size:18px;color:var(--cor-primaria);margin:0;font-weight:900;display:flex;align-items:center;gap:8px;">
                <span>{icone}</span> {titulo}
            </h2>
            {sub_html}
        </div>
        """,
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
    col: Any, label: str, valor: str, sub: str = "", tema: TemaKPI = "azul"
) -> None:
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
    container: Any, label: str, valor: str, sub: str = "", tema: TemaKPI = "azul"
) -> None:
    cor = _resolver_cor_tema(tema)
    container.markdown(
        f"""
        <div style="background:white;border-radius:var(--radius-sm);padding:12px 14px;border:1px solid var(--cor-borda);border-left:3px solid {cor};margin-bottom:8px;box-shadow:var(--shadow-sm);">
            <div style="font-family:{FONTE_TEXTO};font-size:10px;color:var(--cor-texto-3);text-transform:uppercase;letter-spacing:0.05em;font-weight:700;">{label}</div>
            <div style="font-family:{FONTE_TITULO};font-size:20px;color:{cor};font-weight:800;line-height:1.2;margin-top:4px;font-variant-numeric:tabular-nums;">{valor}</div>
            <div style="font-family:{FONTE_TEXTO};font-size:11px;color:var(--cor-texto-3);margin-top:2px;">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_insight(msg: str, tipo: TipoInsight = "info") -> None:
    if not msg:
        return
    config = _INSIGHT_CONFIG.get(tipo, _INSIGHT_CONFIG["info"])
    bg, texto, borda, icone = config
    msg_html = _markdown_inline_para_html(msg)
    st.markdown(
        f"""
        <div style="background:{bg};color:{texto};border-left:4px solid {borda};padding:12px 16px;border-radius:var(--radius-sm);margin:12px 0;font-family:{FONTE_TEXTO};font-size:14px;line-height:1.6;font-weight:500;">
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
                st.dataframe(df.style.format(fmt_valido), height=height, use_container_width=True, hide_index=True, **kwargs)  # type: ignore
                return
            except Exception:
                logger.exception("Falha ao formatar DataFrame.")
    st.dataframe(df, height=height, use_container_width=True, hide_index=True, **kwargs)
    

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