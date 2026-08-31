# streamlit_app.py
import time
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
    initial_sidebar_state="expanded",
)

PAGINA_PRODUCAO = "pages/producao.py"
PAGINA_CONSULTIVO = "pages/consultivo.py"
PAGINA_ADMIN = "pages/admin.py"

# ====================================================
# ESTADO DA SESSÃO (ROTEAMENTO)
# ====================================================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if "auth_view" not in st.session_state:
    st.session_state["auth_view"] = "login"  # 'login' ou 'trocar_senha'

if st.session_state["authenticated"]:
    pagina_inicial = (
        PAGINA_ADMIN if st.session_state.get("is_admin", False) else PAGINA_PRODUCAO
    )
    st.switch_page(pagina_inicial)

auth = AuthManager()


# ====================================================
# CSS — LOGIN + SIDEBAR PRATA/CINZA METÁLICO TOTALE
# ====================================================
def injetar_css_login():
    st.markdown(
        """
        <style>
        /* Sidebar PRATA / CINZA METÁLICO CLARO */
        section[data-testid="stSidebar"] {
            background: linear-gradient(165deg, #F8F8FA 0%, #F0F0F5 14%, #E8E8ED 28%, #DEDEE6 44%, #D1D1D6 60%, #C7C7CC 76%, #B8B8C0 90%, #AEAEB2 100%) !important;
            border-right: 3px solid #012869 !important;
            box-shadow: inset 1px 0 0 rgba(255,255,255,0.85), 4px 0 24px rgba(1,40,105,0.12) !important;
            position: relative; overflow: hidden;
        }
        section[data-testid="stSidebar"]::before {
            content: ''; position: absolute; top: 0; left: 18%; width: 38%; height: 100%;
            background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.20) 35%, rgba(255,255,255,0.45) 50%, rgba(255,255,255,0.20) 65%, transparent 100%);
            transform: skewX(-14deg); pointer-events: none; z-index: 0;
        }
        section[data-testid="stSidebar"]::after {
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px;
            background: linear-gradient(90deg, #012869 0%, #012869 45%, #F37C04 75%, #F37C04 100%); z-index: 99;
        }
        section[data-testid="stSidebar"] > div:first-child { position: relative; z-index: 1; }
        section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] span { color: #1C1C1E !important; }
        section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 { color: #012869 !important; font-weight: 800 !important; }
        section[data-testid="stSidebar"] hr { border: none !important; height: 1px !important; background: linear-gradient(90deg, transparent, rgba(1,40,105,0.18), rgba(243,124,4,0.55), rgba(1,40,105,0.18), transparent) !important; }
        
        /* Oculta navegação e injeta visual no menu lateral */
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li { margin: 4px 10px !important; }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:first-child { display: none !important; }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a { background: linear-gradient(135deg, rgba(255,255,255,0.85), rgba(240,240,245,0.95)) !important; border: 1px solid rgba(1,40,105,0.12) !important; border-radius: 12px !important; padding: 11px 14px !important; box-shadow: 0 2px 8px rgba(0,0,0,0.05), inset 0 1px 0 rgba(255,255,255,0.95) !important; }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a span { color: #3A3A3C !important; font-weight: 700 !important; }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover { border-color: rgba(243,124,4,0.45) !important; border-left: 3px solid #F37C04 !important; transform: translateX(2px); }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"], section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-selected="true"] { background: linear-gradient(90deg, #FFF8F0 0%, #FFE9D0 55%, #FADBB9 100%) !important; border: 1px solid rgba(243,124,4,0.45) !important; border-left: 4px solid #F37C04 !important; }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] span, section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-selected="true"] span { color: #012869 !important; font-weight: 800 !important; }
        
        [data-testid="stSidebarNav"] a[href*="producao"] span { font-size: 0 !important; }
        [data-testid="stSidebarNav"] a[href*="producao"] span::before { content: "📊 Produção" !important; font-size: 14px !important; font-weight: 700 !important; color: #012869 !important; }
        [data-testid="stSidebarNav"] a[href*="consultivo"] span { font-size: 0 !important; }
        [data-testid="stSidebarNav"] a[href*="consultivo"] span::before { content: "🗣️ Consultivo" !important; font-size: 14px !important; font-weight: 700 !important; color: #012869 !important; }
        [data-testid="stSidebarNav"] a[href*="admin"] { display: none !important; }
        
        .sidebar-login-brand { background: linear-gradient(145deg, rgba(255,255,255,0.95), rgba(232,232,237,0.95)); border: 1px solid rgba(1,40,105,0.12); border-left: 4px solid #F37C04; border-radius: 14px; padding: 18px 16px; margin: 8px 0 12px 0; box-shadow: 0 8px 20px rgba(1,40,105,0.08), inset 0 1px 0 rgba(255,255,255,0.95); }
        .sidebar-login-brand .brand { font-size: 11px; font-weight: 800; letter-spacing: 2px; text-transform: uppercase; color: #F37C04; margin-bottom: 8px; }
        .sidebar-login-brand .title { color: #012869; font-weight: 800; font-size: 18px; margin: 0 0 6px 0; }
        .sidebar-login-brand .sub { color: #64748B; font-size: 12px; font-weight: 600; margin: 0; }
        .sidebar-login-footer { text-align: center; font-size: 10px; color: #636366; margin-top: 16px; letter-spacing: 1.2px; font-weight: 600; }
        .sidebar-login-footer b { color: #F37C04; }
        
        .login-header { text-align: center; padding: 1.5rem 0 2.2rem 0; }
        .login-header h1 { color: #012869; font-size: 2.5rem; font-weight: 900; letter-spacing: -1px; margin-bottom: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.06); }
        .login-header h1 span { color: #F37C04; }
        .login-header p { color: #64748B; font-size: 1.1rem; font-weight: 600; margin-top: -5px; letter-spacing: 1px; text-transform: uppercase; }
        
        /* Estilo Formulários */
        [data-testid="stForm"] { background: linear-gradient(165deg, #FFFFFF 0%, #F8FAFC 45%, #E2E8F0 100%) !important; border: 1px solid #CBD5E1 !important; border-top: 4px solid #F37C04 !important; border-radius: 14px !important; padding: 2.2rem 1.8rem !important; box-shadow: 0 12px 30px rgba(0, 0, 0, 0.08) !important; }
        [data-testid="stForm"] p, [data-testid="stForm"] label { color: #1E293B !important; font-weight: 700 !important; font-size: 14px !important; }
        [data-testid="stForm"] [data-baseweb="input"] { background-color: #FFFFFF !important; border: 1px solid #CBD5E1 !important; border-radius: 8px !important; box-shadow: inset 0 1px 2px rgba(0,0,0,0.03) !important; }
        [data-testid="stForm"] input { color: #0F172A !important; font-weight: 600 !important; font-size: 15px !important; background-color: #FFFFFF !important; }
        [data-testid="stForm"] input::placeholder { color: #94A3B8 !important; }
        [data-testid="stForm"] [data-baseweb="input"]:focus-within { border-color: #F37C04 !important; box-shadow: 0 0 0 3px rgba(243,124,4,0.25) !important; }
        [data-testid="stForm"] button[type="submit"] { background: linear-gradient(135deg, #012869 0%, #023a8c 100%) !important; color: #FFFFFF !important; border: 1px solid #012869 !important; border-radius: 8px !important; font-weight: 800 !important; letter-spacing: 1px !important; text-transform: uppercase !important; padding: 0.6rem !important; margin-top: 1rem !important; transition: all 0.3s ease !important; }
        [data-testid="stForm"] button[type="submit"]:hover { background: linear-gradient(135deg, #F37C04 0%, #ff8f1f 100%) !important; border-color: #F37C04 !important; transform: translateY(-2px); box-shadow: 0 8px 20px rgba(243,124,4,0.35) !important; }
        
        /* Tabela e Inputs Secundários */
        [data-testid="stMain"] div:not([data-testid="stForm"]) [data-baseweb="input"] { background-color: #FFFFFF !important; border: 1px solid #CBD5E1 !important; border-radius: 8px !important; }
        [data-testid="stMain"] div:not([data-testid="stForm"]) input { color: #0F172A !important; background-color: #FFFFFF !important; }
        [data-testid="stMain"] div:not([data-testid="stForm"]) [data-baseweb="input"]:focus-within { border-color: #012869 !important; box-shadow: 0 0 0 3px rgba(1,40,105,0.15) !important; }
        .tabela-info { background: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid #012869; padding: 1rem 1.2rem; border-radius: 8px; margin-bottom: 1.2rem; }
        
        /* Botão Secundário (Fora do Form) */
        button[kind="secondary"] {
            color: #64748B !important; font-weight: 600 !important; background: transparent !important;
            border: 1px solid #CBD5E1 !important; border-radius: 8px !important; padding: 0.5rem !important;
            transition: all 0.2s ease;
        }
        button[kind="secondary"]:hover { color: #F37C04 !important; border-color: #F37C04 !important; background: #FFF8F0 !important;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_login() -> None:
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
        st.caption(
            "Use seu **Login** (ex: Z659935) ou **User** (ex: DENIS.ADMIN) e a senha cadastrada."
        )
        st.divider()
        st.markdown(
            '<div class="sidebar-login-footer">POWERED BY <b>TOTALE</b></div>',
            unsafe_allow_html=True,
        )


# ====================================================
# COMPONENTE: TABELA DE PESQUISA (REUTILIZÁVEL)
# ====================================================
def render_tabela_consulta():
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
            placeholder="Digite seu nome ou login Z...",
            key="search_table",
        )
        df_display = df_users.copy()

        if search:
            df_display = df_display[
                df_display["Técnico"]
                .astype(str)
                .str.contains(search, case=False, na=False)
                | df_display["Login"]
                .astype(str)
                .str.contains(search, case=False, na=False)
            ]

        # Oculta Pass e User (User geralmente é perfil de adm/gestão, não precisa ficar exposto)
        colunas_para_remover = [
            col for col in ["Pass", "User"] if col in df_display.columns
        ]
        if colunas_para_remover:
            df_display = df_display.drop(columns=colunas_para_remover)

        st.dataframe(df_display, use_container_width=True, hide_index=True, height=290)
    else:
        st.warning("Falha ao carregar a base de técnicos.")


# ====================================================
# TELA 1: LOGIN
# ====================================================
def tela_login() -> None:
    # Ajuste nas proporções para melhorar em telas menores
    col_vazia_esq, col_form, col_tabela, col_vazia_dir = st.columns(
        [0.1, 2.5, 3.5, 0.1], gap="large"
    )

    with col_form:
        with st.form("login_form"):
            st.markdown(
                "<h3 style='color:#012869;margin-bottom:1.2rem;font-size:20px;font-weight:800;'>🔑 Acesso Restrito</h3>",
                unsafe_allow_html=True,
            )
            identifier = st.text_input(
                "Login ou User", placeholder="Ex: Z659935 ou DENIS.ADMIN"
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
                        pagina_inicial = (
                            PAGINA_ADMIN
                            if st.session_state.get("is_admin", False)
                            else PAGINA_PRODUCAO
                        )
                        st.switch_page(pagina_inicial)
                    else:
                        st.error(f"❌ {message}")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Deseja alterar sua senha?", use_container_width=True):
            st.session_state["auth_view"] = "trocar_senha"
            st.rerun()

    with col_tabela:
        render_tabela_consulta()


# ====================================================
# TELA 2: TROCAR SENHA
# ====================================================
def tela_trocar_senha() -> None:
    col_vazia_esq, col_form, col_tabela, col_vazia_dir = st.columns(
        [0.1, 2.5, 3.5, 0.1], gap="large"
    )

    with col_form:
        with st.form("reset_form"):
            st.markdown(
                "<h3 style='color:#012869;margin-bottom:0.5rem;font-size:20px;font-weight:800;'>🔄 Alterar Senha</h3>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<p style='color:#64748B;font-size:13px;margin-bottom:1.2rem;'>É necessário informar a senha atual para criar uma nova.</p>",
                unsafe_allow_html=True,
            )

            identifier = st.text_input("Seu Login ou User", placeholder="Ex: Z659935")
            old_pass = st.text_input(
                "Senha Atual", type="password", placeholder="Digite sua senha atual"
            )
            new_pass = st.text_input(
                "Nova Senha", type="password", placeholder="Mínimo 6 caracteres"
            )
            confirm_pass = st.text_input(
                "Confirme a Nova Senha",
                type="password",
                placeholder="Repita a nova senha",
            )
            submit = st.form_submit_button(
                "SALVAR NOVA SENHA", use_container_width=True
            )

            if submit:
                if not identifier or not old_pass or not new_pass or not confirm_pass:
                    st.error("⚠️ Preencha todos os campos!")
                elif new_pass != confirm_pass:
                    st.error("⚠️ As novas senhas não coincidem!")
                elif len(new_pass) < 6:
                    st.error("⚠️ A nova senha deve ter pelo menos 6 caracteres!")
                else:
                    # Passo 1: Autenticar a senha antiga primeiro (GARANTIA DE SEGURANÇA)
                    with st.spinner("Validando dados..."):
                        is_valid_user, auth_message = auth.login(identifier, old_pass)

                    if not is_valid_user:
                        st.error("❌ A senha atual informada está incorreta.")
                    else:
                        # Passo 2: Se passou na validação, atualiza a senha
                        success, message = auth.update_password(identifier, new_pass)

                        if success:
                            st.success(
                                "✅ Senha alterada com sucesso! Redirecionando..."
                            )
                            time.sleep(
                                1.5
                            )  # Aguarda 1.5s para o usuário ler a mensagem
                            st.session_state["auth_view"] = "login"
                            st.rerun()
                        else:
                            st.error(f"❌ Erro ao alterar senha: {message}")

        st.markdown(
            "<p style='text-align:center;font-size:12px;color:#94A3B8;margin-top:10px;'>Esqueceu sua senha? Solicite o reset ao seu supervisor.</p>",
            unsafe_allow_html=True,
        )
        if st.button("← Voltar para o Login", use_container_width=True):
            st.session_state["auth_view"] = "login"
            st.rerun()

    with col_tabela:
        render_tabela_consulta()


# ====================================================
# RENDERIZAÇÃO PRINCIPAL
# ====================================================
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

if st.session_state["auth_view"] == "login":
    tela_login()
else:
    tela_trocar_senha()