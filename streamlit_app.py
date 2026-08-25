# streamlit_app.py
import streamlit as st
import pandas as pd
from utils._auth import AuthManager
from utils._database import get_db

# ====================================================
# CONFIGURAÇÃO DA PÁGINA
# ====================================================
st.set_page_config(
    page_title="Totale | Login Técnico",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",  # Sidebar visível
)

# Caminho único da página de produção (ajuste se o arquivo tiver outro nome)
PAGINA_PRODUCAO = "pages/producao.py"
# Se renomeou para: pages/1_📊_Minha_Produção.py
# PAGINA_PRODUCAO = "pages/1_📊_Minha_Produção.py"


# ====================================================
# CSS — LOGIN + SIDEBAR PRATA/CINZA METÁLICO TOTALE
# ====================================================
def injetar_css_login():
    st.markdown(
        """
        <style>
        /* ═══════════════════════════════════════════════════
           SIDEBAR — PRATA / CINZA METÁLICO CLARO + TOTALE
        ═══════════════════════════════════════════════════ */
        section[data-testid="stSidebar"] {
            background: linear-gradient(
                165deg,
                #F8F8FA  0%,
                #F0F0F5 14%,
                #E8E8ED 28%,
                #DEDEE6 44%,
                #D1D1D6 60%,
                #C7C7CC 76%,
                #B8B8C0 90%,
                #AEAEB2 100%
            ) !important;
            border-right: 3px solid #012869 !important;
            box-shadow:
                inset 1px 0 0 rgba(255,255,255,0.85),
                4px 0 24px rgba(1,40,105,0.12) !important;
            position: relative;
            overflow: hidden;
        }

        /* Brilho metálico */
        section[data-testid="stSidebar"]::before {
            content: '';
            position: absolute;
            top: 0; left: 18%;
            width: 38%; height: 100%;
            background: linear-gradient(
                90deg,
                transparent 0%,
                rgba(255,255,255,0.20) 35%,
                rgba(255,255,255,0.45) 50%,
                rgba(255,255,255,0.20) 65%,
                transparent 100%
            );
            transform: skewX(-14deg);
            pointer-events: none;
            z-index: 0;
        }

        /* Faixa azul → laranja */
        section[data-testid="stSidebar"]::after {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 4px;
            background: linear-gradient(90deg, #012869 0%, #012869 45%, #F37C04 75%, #F37C04 100%);
            z-index: 99;
        }

        section[data-testid="stSidebar"] > div:first-child {
            position: relative;
            z-index: 1;
        }

        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] .stMarkdown,
        section[data-testid="stSidebar"] span {
            color: #1C1C1E !important;
        }

        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: #012869 !important;
            font-weight: 800 !important;
        }

        section[data-testid="stSidebar"] hr {
            border: none !important;
            height: 1px !important;
            background: linear-gradient(
                90deg,
                transparent,
                rgba(1,40,105,0.18),
                rgba(243,124,4,0.55),
                rgba(1,40,105,0.18),
                transparent
            ) !important;
        }

        /* Menu nativo multipage */
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li {
            margin: 4px 10px !important;
        }

        /* Oculta o item "streamlit app" (home) no menu — opcional */
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:first-child {
            display: none !important;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
            background: linear-gradient(135deg, rgba(255,255,255,0.85), rgba(240,240,245,0.95)) !important;
            border: 1px solid rgba(1,40,105,0.12) !important;
            border-radius: 12px !important;
            padding: 11px 14px !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05), inset 0 1px 0 rgba(255,255,255,0.95) !important;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a span {
            color: #3A3A3C !important;
            font-weight: 700 !important;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {
            border-color: rgba(243,124,4,0.45) !important;
            border-left: 3px solid #F37C04 !important;
            transform: translateX(2px);
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"],
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-selected="true"] {
            background: linear-gradient(90deg, #FFF8F0 0%, #FFE9D0 55%, #FADBB9 100%) !important;
            border: 1px solid rgba(243,124,4,0.45) !important;
            border-left: 4px solid #F37C04 !important;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] span,
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-selected="true"] span {
            color: #012869 !important;
            font-weight: 800 !important;
        }
        
        /* Troca o texto 'producao' visualmente no sidebar */
        [data-testid="stSidebarNav"] a[href*="producao"] span {
            font-size: 0 !important;
        }
        [data-testid="stSidebarNav"] a[href*="producao"] span::before {
            content: "📊 Minha Produção" !important;
            font-size: 14px !important;
            font-weight: 700 !important;
            color: #012869 !important;
        }

        /* Card de marca no sidebar (login) */
        .sidebar-login-brand {
            background: linear-gradient(145deg, rgba(255,255,255,0.95), rgba(232,232,237,0.95));
            border: 1px solid rgba(1,40,105,0.12);
            border-left: 4px solid #F37C04;
            border-radius: 14px;
            padding: 18px 16px;
            margin: 8px 0 12px 0;
            box-shadow: 0 8px 20px rgba(1,40,105,0.08), inset 0 1px 0 rgba(255,255,255,0.95);
        }
        .sidebar-login-brand .brand {
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 2px;
            text-transform: uppercase;
            color: #F37C04;
            margin-bottom: 8px;
        }
        .sidebar-login-brand .title {
            color: #012869;
            font-weight: 800;
            font-size: 18px;
            margin: 0 0 6px 0;
        }
        .sidebar-login-brand .sub {
            color: #64748B;
            font-size: 12px;
            font-weight: 600;
            margin: 0;
        }
        .sidebar-login-footer {
            text-align: center;
            font-size: 10px;
            color: #636366;
            margin-top: 16px;
            letter-spacing: 1.2px;
            font-weight: 600;
        }
        .sidebar-login-footer b { color: #F37C04; }

        /* Cabeçalho centralizado */
        .login-header {
            text-align: center;
            padding: 1.5rem 0 2.2rem 0;
        }
        .login-header h1 {
            color: #012869;
            font-size: 3.5rem;
            font-weight: 900;
            letter-spacing: -1px;
            margin-bottom: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.06);
        }
        .login-header h1 span { color: #F37C04; }
        .login-header p {
            color: #64748B;
            font-size: 1.1rem;
            font-weight: 600;
            margin-top: -5px;
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        /* Card de login — cinza claro metálico */
        [data-testid="stForm"] {
            background: linear-gradient(165deg, #FFFFFF 0%, #F8FAFC 45%, #E2E8F0 100%) !important;
            border: 1px solid #CBD5E1 !important;
            border-top: 4px solid #F37C04 !important;
            border-radius: 14px !important;
            padding: 2.2rem 1.8rem !important;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.08) !important;
        }

        [data-testid="stForm"] p,
        [data-testid="stForm"] label {
            color: #1E293B !important;
            font-weight: 700 !important;
            font-size: 14px !important;
        }

        [data-testid="stForm"] [data-baseweb="input"] {
            background-color: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
            box-shadow: inset 0 1px 2px rgba(0,0,0,0.03) !important;
        }

        [data-testid="stForm"] input {
            color: #0F172A !important;
            font-weight: 600 !important;
            font-size: 15px !important;
            background-color: #FFFFFF !important;
        }

        [data-testid="stForm"] input::placeholder {
            color: #94A3B8 !important;
        }

        [data-testid="stForm"] [data-baseweb="input"]:focus-within {
            border-color: #F37C04 !important;
            box-shadow: 0 0 0 3px rgba(243,124,4,0.25) !important;
        }

        [data-testid="stForm"] [data-baseweb="input"] button {
            background: transparent !important;
            color: #64748B !important;
            border: none !important;
        }
        [data-testid="stForm"] [data-baseweb="input"] button:hover {
            color: #F37C04 !important;
        }

        [data-testid="stForm"] button[type="submit"] {
            background: linear-gradient(135deg, #012869 0%, #023a8c 100%) !important;
            color: #FFFFFF !important;
            border: 1px solid #012869 !important;
            border-radius: 8px !important;
            font-weight: 800 !important;
            letter-spacing: 1px !important;
            text-transform: uppercase !important;
            padding: 0.6rem !important;
            margin-top: 1rem !important;
            transition: all 0.3s ease !important;
        }

        [data-testid="stForm"] button[type="submit"]:hover {
            background: linear-gradient(135deg, #F37C04 0%, #ff8f1f 100%) !important;
            border-color: #F37C04 !important;
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(243,124,4,0.35) !important;
        }

        /* Pesquisa à direita */
        [data-testid="stMain"] div:not([data-testid="stForm"]) [data-baseweb="input"] {
            background-color: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
        }

        [data-testid="stMain"] div:not([data-testid="stForm"]) input {
            color: #0F172A !important;
            background-color: #FFFFFF !important;
        }

        [data-testid="stMain"] div:not([data-testid="stForm"]) [data-baseweb="input"]:focus-within {
            border-color: #012869 !important;
            box-shadow: 0 0 0 3px rgba(1,40,105,0.15) !important;
        }

        .tabela-info {
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-left: 4px solid #012869;
            padding: 1rem 1.2rem;
            border-radius: 8px;
            margin-bottom: 1.2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_login() -> None:
    """Sidebar de marca na tela de login (sem dados de usuário)."""
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-login-brand">
                <div class="brand">⚡ Totale · Portal</div>
                <p class="title">Acesso do Técnico</p>
                <p class="sub">Faça login para ver sua produção e indicadores.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()
        st.markdown("**Como entrar**")
        st.caption("Use seu **Login** (ex: Z659935) ou **User** (ex: DENIS.VICK) e a senha cadastrada.")
        st.divider()
        st.markdown(
            '<div class="sidebar-login-footer">POWERED BY <b>TOTALE</b></div>',
            unsafe_allow_html=True,
        )


# ====================================================
# AUTH + REDIRECT
# ====================================================
auth = AuthManager()

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if st.session_state["authenticated"]:
    st.switch_page(PAGINA_PRODUCAO)


# ====================================================
# TELA DE LOGIN
# ====================================================
def render_login() -> None:
    injetar_css_login()
    render_sidebar_login()

    st.markdown(
        """
        <div class="login-header">
            <h1>⚡ TOTALE<span>.</span></h1>
            <p>Portal Operacional do Técnico</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_vazia_esq, col_form, col_tabela, col_vazia_dir = st.columns(
        [0.3, 2.2, 3.4, 0.3], gap="large"
    )

    with col_form:
        with st.form("login_form"):
            st.markdown(
                "<h3 style='color:#012869;margin-bottom:1.2rem;font-size:20px;font-weight:800;'>🔑 Acesso Restrito</h3>",
                unsafe_allow_html=True,
            )

            identifier = st.text_input(
                "Login ou User",
                placeholder="Ex: Z659935 ou DENIS.VICK",
            )
            password = st.text_input("Senha", type="password", placeholder="••••••••")

            submit = st.form_submit_button("AUTENTICAR", use_container_width=True)

            if submit:
                if not identifier or not password:
                    st.error("⚠️ Preencha todos os campos!")
                else:
                    with st.spinner("Autenticando..."):
                        success, message = auth.login(identifier, password)
                    if success:
                        st.switch_page(PAGINA_PRODUCAO)
                    else:
                        st.error(f"❌ {message}")

    with col_tabela:
        st.markdown(
            """
            <div class="tabela-info">
                <h4 style="color:#012869;margin:0 0 4px 0;font-size:16px;font-weight:700;">📋 Base de Colaboradores Ativos</h4>
                <p style="color:#64748B;margin:0;font-size:13px;font-weight:500;">Consulte seu código de acesso na lista abaixo (Apenas para conferência).</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        db = get_db()
        df_users = db.get_users_dataframe()

        if not df_users.empty:
            search = st.text_input(
                "🔍 Localize seu cadastro:",
                placeholder="Digite seu nome, login Z ou user...",
            )
            df_display = df_users.copy()

            if search:
                df_display = df_display[
                    df_display["Técnico"].astype(str).str.contains(search, case=False, na=False)
                    | df_display["Login"].astype(str).str.contains(search, case=False, na=False)
                    | df_display["User"].astype(str).str.contains(search, case=False, na=False)
                ]

            # Remove coluna de senha da conferência
            if "Pass" in df_display.columns:
                df_display = df_display.drop(columns=["Pass"])

            st.dataframe(df_display, use_container_width=True, hide_index=True, height=290)
        else:
            st.warning("Falha ao carregar a base de técnicos.")


render_login()