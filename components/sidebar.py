# components/sidebar.py
"""
Módulo de Sidebar corporativo TOTALE para producao-totale.

Uso:
    from components.sidebar import injetar_css_sidebar_corp, render_sidebar_corp
    injetar_css_sidebar_corp()
    render_sidebar_corp(on_logout=lambda: st.session_state.clear())
"""

import streamlit as st
from typing import Optional, Callable
from datetime import datetime
from zoneinfo import ZoneInfo

TOTALE_AZUL = "#012869"
TOTALE_LARANJA = "#F37C04"
FUSO_HORARIO = ZoneInfo("America/Sao_Paulo")


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
        
        /* Mantém os rótulos nativos da navegação para evitar páginas ocultas ou nomes incorretos. */
        [data-testid="stSidebarNav"] li:first-child {{ display: list-item !important; }}
        [data-testid="stSidebarNav"] a span {{ font-size: 14px !important; }}
        [data-testid="stSidebarNav"] a span::before {{ content: none !important; }}

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
            background: {TOTALE_LARANJA} !important;
            color: #FFFFFF !important;
            border-color: transparent !important;
        }}

        /* Ajustes finais do tema claro Totale */
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #F4F6F9 0%, #EEF2F7 100%) !important;
            border-right: 1px solid #D9E0E9 !important;
        }}
        [data-testid="stSidebar"] .sidebar-profile-card {{
            background: #FFFFFF !important;
            border-color: #D9E0E9 !important;
            border-left-color: {TOTALE_LARANJA} !important;
            box-shadow: 0 4px 12px rgba(1, 40, 105, 0.08) !important;
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


# ====================================================
# 🧩 FUNÇÕES HELPER ADICIONAIS
# ====================================================

def render_sidebar_info(
    user_name: str = "Usuário",
    email: Optional[str] = None,
    role: Optional[str] = None,
    avatar: Optional[str] = None,
) -> None:
    """
    Renderiza bloco de informações do usuário logado no topo do sidebar.

    Args:
        user_name: Nome do usuário
        email: Email do usuário (opcional)
        role: Cargo/Role do usuário (opcional)
        avatar: URL ou emoji do avatar (opcional)
    """
    avatar_text = avatar or "👤"
    role_text = f" • {role}" if role else ""

    st.markdown(
        f"""
        <div style="
            background: rgba(255, 255, 255, 0.12);
            border: 1px solid rgba(1, 40, 105, 0.25);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 12px;
            text-align: center;
        ">
            <div style="font-size: 28px; margin-bottom: 6px;">{avatar_text}</div>
            <p style="
                color: #1C1C1E;
                font-weight: 700;
                font-size: 13px;
                margin: 0 0 4px 0;
            ">{user_name}</p>
            {f'<p style="color: {TOTALE_LARANJA}; font-size: 11px; margin: 2px 0;">{role_text.strip(" • ")}</p>' if role else ''}
            {f'<p style="color: #636366; font-size: 11px; margin: 4px 0 0 0; word-break: break-word;">{email}</p>' if email else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_status(
    sistema_ok: bool = True,
    ultima_atualizacao: Optional[datetime] = None,
    mensagem: str = "Sistema operacional",
) -> None:
    """
    Renderiza indicador de status do sistema no sidebar.

    Args:
        sistema_ok: Status do sistema (True=OK, False=erro)
        ultima_atualizacao: Datetime da última atualização
        mensagem: Mensagem customizada
    """
    cor_fundo = "rgba(34, 197, 94, 0.1)" if sistema_ok else "rgba(220, 38, 38, 0.1)"
    cor_borda = "#059669" if sistema_ok else "#DC2626"
    icone = "✅" if sistema_ok else "❌"

    if ultima_atualizacao:
        tempo = ultima_atualizacao.strftime("%d/%m/%Y %H:%M")
        submsg = f"<p style='font-size: 11px; margin: 4px 0 0 0; color: #636366;'>🕒 {tempo}</p>"
    else:
        submsg = ""

    st.markdown(
        f"""
        <div style="
            background: {cor_fundo};
            border: 1px solid {cor_borda};
            border-radius: 6px;
            padding: 10px;
            margin: 12px 0;
            text-align: center;
        ">
            <p style="
                font-size: 13px;
                font-weight: 600;
                margin: 0;
                color: #1C1C1E;
            ">
                {icone} {mensagem}
            </p>
            {submsg}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_filtro(
    label: str,
    options: list,
    default: Optional[str] = None,
    key: Optional[str] = None,
    help_text: Optional[str] = None,
    multi: bool = False,
):
    """
    Renderiza filtro customizado no sidebar com styling corporativo.

    Args:
        label: Rótulo do filtro
        options: Lista de opções
        default: Valor padrão
        key: Chave de session_state
        help_text: Texto de ajuda
        multi: Permitir múltiplas seleções

    Returns:
        Valor(es) selecionado(s)
    """
    if multi:
        return st.multiselect(
            label,
            options=options,
            default=default,
            key=key,
            help=help_text,
        )
    else:
        return st.selectbox(
            label,
            options=options,
            index=options.index(default) if default and default in options else 0,
            key=key,
            help=help_text,
        )


def render_sidebar_section(title: str) -> None:
    """Renderiza um título de seção no sidebar."""
    st.markdown(f"#### {title}", unsafe_allow_html=False)


def render_sidebar_divider() -> None:
    """Renderiza divisor visual no sidebar."""
    st.divider()


def render_sidebar_footer_info(
    versao: str = "1.0.0",
    ambiente: str = "Produção",
    mostrar_timestamp: bool = True,
) -> None:
    """
    Renderiza bloco de informações footer no sidebar.

    Args:
        versao: Versão do sistema
        ambiente: Ambiente (Produção, Staging, Dev)
        mostrar_timestamp: Mostrar timestamp atual
    """
    agora = datetime.now(FUSO_HORARIO)
    hora_str = agora.strftime("%d/%m/%Y %H:%M") if mostrar_timestamp else ""

    info_items = [f"v{versao}", ambiente]
    if hora_str:
        info_items.append(hora_str)

    info_text = " • ".join(info_items)

    st.markdown(
        f"""
        <div style="
            background: rgba(0, 0, 0, 0.08);
            border-top: 1px solid rgba(1, 40, 105, 0.12);
            border-radius: 0;
            padding: 10px 12px;
            margin-top: 20px;
            text-align: center;
            font-size: 11px;
            color: #636366;
            font-weight: 500;
        ">
            {info_text}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ====================================================
# 🔧 HELPER FUNCTIONS
# ====================================================

def get_hora_atual_brt() -> str:
    """Retorna a hora atual em formato BRT (São Paulo)."""
    return datetime.now(FUSO_HORARIO).strftime("%H:%M:%S")


def get_data_atual_br() -> str:
    """Retorna a data atual em formato DD/MM/YYYY."""
    return datetime.now(FUSO_HORARIO).strftime("%d/%m/%Y")