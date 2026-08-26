# components/sidebar.py
import streamlit as st
from typing import Optional, Callable

TOTALE_AZUL = "#012869"
TOTALE_LARANJA = "#F37C04"


def injetar_css_sidebar_corp() -> None:
    st.markdown(
        f"""
        <style>
        /* ═══════════════════════════════════════════════════
           SIDEBAR — GRADIENTE PRATA / CINZA METÁLICO CLARO
        ═══════════════════════════════════════════════════ */
        [data-testid="stSidebar"] {{
            background: linear-gradient(
                165deg,
                #F8F8FA  0%,
                #F0F0F5 12%,
                #E8E8ED 24%,
                #DEDEE6 38%,
                #D1D1D6 52%,
                #C7C7CC 66%,
                #B8B8C0 80%,
                #AEAEB2 90%,
                #A0A0A8 100%
            ) !important;
            border-right: 3px solid {TOTALE_AZUL} !important;
            box-shadow:
                4px 0 28px rgba(1, 40, 105, 0.12),
                inset -1px 0 0 rgba(255, 255, 255, 0.7),
                inset 0 1px 0 rgba(255, 255, 255, 0.9) !important;
            position: relative;
            overflow: hidden;
        }}

        /* Brilho metálico diagonal (prata) */
        [data-testid="stSidebar"]::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 15%;
            width: 40%;
            height: 100%;
            background: linear-gradient(
                90deg,
                transparent 0%,
                rgba(255, 255, 255, 0.15) 30%,
                rgba(255, 255, 255, 0.45) 50%,
                rgba(255, 255, 255, 0.15) 70%,
                transparent 100%
            );
            transform: skewX(-14deg);
            pointer-events: none;
            z-index: 0;
        }}

        /* Faixa azul → laranja no topo */
        [data-testid="stSidebar"]::after {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 4px;
            background: linear-gradient(
                90deg,
                {TOTALE_AZUL} 0%,
                {TOTALE_AZUL} 45%,
                {TOTALE_LARANJA} 75%,
                {TOTALE_LARANJA} 100%
            );
            z-index: 99;
        }}

        [data-testid="stSidebar"] > div:first-child {{
            position: relative;
            z-index: 1;
        }}

        /* Textos do sidebar (fundo claro) */
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] small {{
            color: #1C1C1E !important;
        }}

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {{
            color: {TOTALE_AZUL} !important;
            font-weight: 800 !important;
        }}

        [data-testid="stSidebar"] code {{
            background: rgba(1, 40, 105, 0.08) !important;
            color: {TOTALE_AZUL} !important;
            border: 1px solid rgba(243, 124, 4, 0.45) !important;
            border-radius: 6px !important;
            padding: 2px 8px !important;
            font-weight: 700 !important;
        }}

        [data-testid="stSidebar"] hr {{
            border: none !important;
            height: 1px !important;
            background: linear-gradient(
                90deg,
                transparent,
                rgba(1, 40, 105, 0.2),
                rgba(243, 124, 4, 0.55),
                rgba(1, 40, 105, 0.2),
                transparent
            ) !important;
            margin: 0.85rem 0 !important;
        }}

        /* ═══════════════════════════════════════════════════
           MENU NATIVO MULTIPAGE
        ═══════════════════════════════════════════════════ */
        [data-testid="stSidebarNav"] {{
            padding: 10px 8px 6px 8px !important;
            background: transparent !important;
        }}

        /* Oculta "streamlit app" (primeiro item = home) */
        [data-testid="stSidebarNav"] li:first-child {{
            display: none !important;
        }}

        /* Links do menu */
        [data-testid="stSidebarNav"] a {{
            border-radius: 12px !important;
            margin: 6px 4px !important;
            padding: 12px 16px !important;
            border: 1px solid rgba(1, 40, 105, 0.12) !important;
            background: linear-gradient(
                135deg,
                rgba(255, 255, 255, 0.75) 0%,
                rgba(240, 240, 245, 0.9) 100%
            ) !important;
            box-shadow:
                0 2px 8px rgba(0, 0, 0, 0.06),
                inset 0 1px 0 rgba(255, 255, 255, 0.9) !important;
            transition: all 0.22s ease !important;
        }}

        [data-testid="stSidebarNav"] a span {{
            color: #3A3A3C !important;
            font-weight: 700 !important;
            font-size: 14px !important;
            letter-spacing: 0.2px !important;
        }}

        /* Hover */
        [data-testid="stSidebarNav"] a:hover {{
            background: linear-gradient(
                135deg,
                rgba(1, 40, 105, 0.08) 0%,
                rgba(243, 124, 4, 0.10) 100%
            ) !important;
            border-color: rgba(243, 124, 4, 0.45) !important;
            transform: translateX(3px);
            box-shadow: 0 4px 12px rgba(1, 40, 105, 0.12) !important;
        }}

        [data-testid="stSidebarNav"] a:hover span {{
            color: {TOTALE_AZUL} !important;
        }}

        /* Página ATIVA — azul Totale + detalhe laranja */
        [data-testid="stSidebarNav"] a[aria-selected="true"],
        [data-testid="stSidebarNav"] a[aria-current="page"] {{
            background: linear-gradient(
                135deg,
                {TOTALE_AZUL} 0%,
                #023a8c 55%,
                #0a4aad 100%
            ) !important;
            border: 1px solid rgba(243, 124, 4, 0.75) !important;
            box-shadow:
                0 6px 18px rgba(1, 40, 105, 0.35),
                inset 0 1px 0 rgba(255, 255, 255, 0.2),
                0 0 0 1px rgba(243, 124, 4, 0.25) !important;
        }}

        [data-testid="stSidebarNav"] a[aria-selected="true"] span,
        [data-testid="stSidebarNav"] a[aria-current="page"] span {{
            color: #FFFFFF !important;
            font-weight: 800 !important;
        }}

        /* Ícone do menu */
        [data-testid="stSidebarNav"] img {{
            opacity: 0.95;
        }}

        [data-testid="stSidebarNav"] a[aria-selected="true"] img,
        [data-testid="stSidebarNav"] a[aria-current="page"] img {{
            filter: brightness(0) invert(1);
        }}
        
        /* Troca a escrita do item ativo e inativo no menu lateral */
        [data-testid="stSidebarNav"] a[href*="producao"] span,
        [data-testid="stSidebarNav"] a[aria-current="page"] span {{
            font-size: 0 !important;
        }}

        [data-testid="stSidebarNav"] a[href*="producao"] span::before,
        [data-testid="stSidebarNav"] a[aria-current="page"] span::before {{
            content: "📊 Produção" !important;
            font-size: 14px !important;
            font-weight: 800 !important;
            color: #012869 !important; /* Azul Totale */
        }}

        /* ═══════════════════════════════════════════════════
           BOTÕES
        ═══════════════════════════════════════════════════ */
        [data-testid="stSidebar"] .stButton > button {{
            background: linear-gradient(135deg, {TOTALE_AZUL} 0%, #023a8c 100%) !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(243, 124, 4, 0.55) !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 12px rgba(1, 40, 105, 0.25) !important;
            transition: all 0.22s ease !important;
        }}

        [data-testid="stSidebar"] .stButton > button:hover {{
            background: linear-gradient(135deg, {TOTALE_LARANJA} 0%, #ff8f1f 100%) !important;
            border-color: rgba(1, 40, 105, 0.25) !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 16px rgba(243, 124, 4, 0.35) !important;
            color: #FFFFFF !important;
        }}

        [data-testid="stSidebar"] .stButton > button[kind="secondary"] {{
            background: linear-gradient(135deg, #E8E8ED 0%, #C7C7CC 100%) !important;
            color: #1C1C1E !important;
            border: 1px solid rgba(1, 40, 105, 0.18) !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.8) !important;
        }}

        [data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {{
            background: linear-gradient(135deg, #C0392B 0%, #E74C3C 100%) !important;
            color: #FFFFFF !important;
            border-color: transparent !important;
        }}

        /* ═══════════════════════════════════════════════════
           CARD DE PERFIL
        ═══════════════════════════════════════════════════ */
        .sidebar-profile-card {{
            background: linear-gradient(
                145deg,
                rgba(255, 255, 255, 0.92) 0%,
                rgba(232, 232, 237, 0.95) 50%,
                rgba(199, 199, 204, 0.85) 100%
            );
            border: 1px solid rgba(1, 40, 105, 0.12);
            border-left: 4px solid {TOTALE_LARANJA};
            border-radius: 14px;
            padding: 16px;
            margin: 6px 0 10px 0;
            box-shadow:
                0 8px 22px rgba(1, 40, 105, 0.10),
                inset 0 1px 0 rgba(255, 255, 255, 0.95);
            position: relative;
            overflow: hidden;
        }}

        .sidebar-profile-card::after {{
            content: '';
            position: absolute;
            top: -30%;
            right: -20%;
            width: 100px;
            height: 100px;
            background: radial-gradient(circle, rgba(243, 124, 4, 0.14) 0%, transparent 70%);
            pointer-events: none;
        }}

        .sidebar-brand {{
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 2px;
            text-transform: uppercase;
            color: {TOTALE_LARANJA};
            margin-bottom: 10px;
        }}

        .sidebar-avatar {{
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: linear-gradient(135deg, {TOTALE_AZUL} 0%, #023a8c 45%, {TOTALE_LARANJA} 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 800;
            font-size: 17px;
            margin-bottom: 10px;
            box-shadow:
                0 4px 12px rgba(1, 40, 105, 0.3),
                0 0 0 2px rgba(243, 124, 4, 0.35);
        }}

        .sidebar-name {{
            color: {TOTALE_AZUL};
            font-weight: 800;
            font-size: 14px;
            margin-bottom: 8px;
            line-height: 1.3;
        }}

        .sidebar-meta {{
            font-size: 12px;
            color: #3A3A3C;
            margin: 4px 0;
            font-weight: 500;
        }}

        .sidebar-status {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            margin-top: 10px;
            padding: 4px 10px;
            border-radius: 20px;
            background: rgba(34, 197, 94, 0.12);
            border: 1px solid rgba(34, 197, 94, 0.4);
            color: #15803D;
            font-size: 11px;
            font-weight: 700;
        }}

        .sidebar-status-dot {{
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #22C55E;
            box-shadow: 0 0 8px #22C55E;
            animation: pulse-online 1.8s infinite;
        }}

        @keyframes pulse-online {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.55; transform: scale(0.85); }}
        }}

        .sidebar-footer {{
            text-align: center;
            font-size: 10px;
            color: #636366;
            margin-top: 14px;
            letter-spacing: 1.2px;
            font-weight: 600;
        }}

        .sidebar-footer b {{
            color: {TOTALE_LARANJA};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _iniciais(nome: str) -> str:
    partes = [p for p in str(nome).strip().split() if p]
    if not partes:
        return "?"
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[-1][0]).upper()


def render_sidebar_corp(
    on_logout: Optional[Callable[[], None]] = None,
    logout_page: str = "streamlit_app.py",
    show_nav_hint: bool = False,  # aceito por compatibilidade; não exibe nada
) -> None:
    """Sidebar prateado metálico + menu nativo estilizado Totale."""
    injetar_css_sidebar_corp()

    tecnico = str(st.session_state.get("tecnico", "Técnico"))
    login_code = str(st.session_state.get("login_code", "—"))
    user_code = str(st.session_state.get("user_code", "—"))

    with st.sidebar:
        st.markdown(
            f"""
            <div class="sidebar-profile-card">
                <div class="sidebar-brand">⚡ Totale · Portal</div>
                <div class="sidebar-avatar">{_iniciais(tecnico)}</div>
                <div class="sidebar-name">{tecnico}</div>
                <div class="sidebar-meta">Login: <code>{login_code}</code></div>
                <div class="sidebar-meta">User: <code>{user_code}</code></div>
                <div class="sidebar-status">
                    <span class="sidebar-status-dot"></span> Online
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        if st.button("🚪 Encerrar Sessão", use_container_width=True, type="secondary"):
            if on_logout:
                on_logout()
            else:
                for k in ["authenticated", "tecnico", "login_code", "user_code"]:
                    st.session_state.pop(k, None)
            st.switch_page(logout_page)

        st.markdown(
            '<div class="sidebar-footer">POWERED BY <b>TOTALE</b></div>',
            unsafe_allow_html=True,
        )