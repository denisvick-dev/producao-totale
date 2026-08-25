# app.py
import streamlit as st
import pandas as pd

# Importações vindas do diretório 'utils'
from utils._auth import AuthManager
from utils._database import get_db

st.set_page_config(
    page_title="Sistema de Autenticação - Técnicos",
    page_icon="🛠️",
    layout="wide"
)

auth = AuthManager()

# Inicializa sessão
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# ====================================================
# TELA DE LOGIN (COM DATAFRAME VISÍVEL ANTES DE LOGAR)
# ====================================================
def render_login():
    st.title("🛠️ Portal do Técnico")
    
    col1, col2 = st.columns([1, 2], gap="large")

    # Coluna 1: Formulário de Login
    with col1:
        st.subheader("🔑 Login de Acesso")
        with st.form("login_form"):
            identifier = st.text_input(
                "Login ou User",
                placeholder="Ex: Z613057 ou ADRIEL.ALEXANDER",
                help="Você pode usar o código Z ou o formato NOME.SOBRENOME"
            )
            password = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            
            submit = st.form_submit_button("Entrar", use_container_width=True, type="primary")

            if submit:
                if not identifier or not password:
                    st.error("Preencha todos os campos!")
                else:
                    with st.spinner("Verificando..."):
                        success, message = auth.login(identifier, password)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

    # Coluna 2: DataFrame Visível ANTES de logar (Para Conferência)
    with col2:
        st.subheader("📋 Dados da Planilha (Conferência Pré-Login)")
        
        db = get_db()
        df = db.get_dataframe()

        if not df.empty:
            # Filtro para busca na tabela pré-login
            search = st.text_input("🔍 Buscar Técnico / Login / User:", placeholder="Digite para filtrar...")
            
            df_display = df.copy()
            
            if search:
                df_display = df_display[
                    df_display["Técnico"].astype(str).str.contains(search, case=False, na=False) |
                    df_display["Login"].astype(str).str.contains(search, case=False, na=False) |
                    df_display["User"].astype(str).str.contains(search, case=False, na=False)
                ]

            # Mascara a coluna Pass por segurança na visualização
            if "Pass" in df_display.columns:
                df_display["Pass"] = "••••••••"

            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                height=400
            )
        else:
            st.warning("Não foi possível carregar os dados da planilha.")

# ====================================================
# TELA PRINCIPAL (APÓS LOGIN)
# ====================================================
def render_dashboard():
    with st.sidebar:
        st.title("👤 Usuário Logado")
        st.markdown(f"**Técnico:**\n{st.session_state.get('tecnico')}")
        st.markdown(f"**Login:** `{st.session_state.get('login_code')}`")
        st.markdown(f"**User:** `{st.session_state.get('user_code')}`")
        st.divider()

        if st.button("🚪 Sair", use_container_width=True, type="secondary"):
            auth.logout()
            st.rerun()

    st.title("🚀 Painel Interno")
    st.success(f"Conectado com sucesso como **{st.session_state.get('tecnico')}**!")
    
    st.subheader("📊 Métricas Rápidas")
    db = get_db()
    df = db.get_dataframe()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total de Técnicos", len(df))
    with col2:
        st.metric("Seu Usuário Ativo", st.session_state.get("user_code"))

    st.divider()
    st.subheader("📋 Tabela Completa")
    
    df_show = df.copy()
    if "Pass" in df_show.columns:
        df_show["Pass"] = "••••••••"
        
    st.dataframe(df_show, use_container_width=True, hide_index=True)

# ====================================================
# ROTEAMENTO
# ====================================================
if st.session_state["authenticated"]:
    render_dashboard()
else:
    render_login()