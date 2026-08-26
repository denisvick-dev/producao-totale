# utils/_auth.py
from typing import Tuple
import bcrypt
import streamlit as st
from ._database import get_db


class AuthManager:
    def __init__(self) -> None:
        self.db = get_db()

    @staticmethod
    def hash_password(plain_password: str) -> str:
        return bcrypt.hashpw(str(plain_password).strip().encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, stored_password: str) -> bool:
        plain = str(plain_password).strip()
        stored = str(stored_password).strip()

        if not plain or not stored:
            return False

        if stored.startswith("$2b$") or stored.startswith("$2a$"):
            try:
                return bcrypt.checkpw(plain.encode("utf-8"), stored.encode("utf-8"))
            except Exception:
                return False

        return plain == stored
    
    def update_password(self, identifier: str, nova_senha: str) -> tuple[bool, str]:
        """
        Gera o Hash Bcrypt ($2b$12$...) e envia a requisição para o banco de dados.
        Retorna (Sucesso booleano, Mensagem string).
        """
        try:
            db = get_db()
            df_users = db.get_users_dataframe()
            
            if df_users.empty:
                return False, "Erro ao carregar a base de dados."

            # 1. Verifica se o usuário existe (pelo Login 'Z...' ou User 'NOME.ADMIN')
            usuario_mask = (
                (df_users["Login"].astype(str).str.upper() == identifier.upper()) | 
                (df_users["User"].astype(str).str.upper() == identifier.upper())
            )
            
            if not df_users[usuario_mask].any().any():
                return False, "Usuário não encontrado na base."
            
            # 2. Criptografa a nova senha usando Bcrypt (custo 12 igual à sua imagem)
            bytes_senha = nova_senha.encode("utf-8")
            salt = bcrypt.gensalt(rounds=12)
            hash_bcrypt = bcrypt.hashpw(bytes_senha, salt).decode("utf-8")
            
            # 3. Descobre o 'Login' (ID Real) para enviar ao banco
            login_real = str(df_users.loc[usuario_mask, "Login"].values[0])

            # 4. Envia para a função do banco de dados fazer a atualização
            sucesso = db.update_user_password(login_real, hash_bcrypt)
            
            if sucesso:
                return True, "Senha atualizada com sucesso!"
            else:
                return False, "Erro ao salvar a nova senha no banco de dados."
                
        except Exception as e:
            return False, f"Erro interno ao atualizar: {str(e)}"  
        
    def login(self, identifier: str, password: str) -> Tuple[bool, str]:
        user = self.db.find_user_by_login_or_user(identifier)

        if not user:
            return False, "Login ou User não encontrado!"

        stored_pass = str(user.get("Pass", ""))
        if not self.verify_password(password, stored_pass):
            return False, "Senha incorreta!"

        st.session_state["authenticated"] = True
        st.session_state["tecnico"] = user.get("Técnico", "")
        st.session_state["login_code"] = user.get("Login", "")
        st.session_state["user_code"] = user.get("User", "")

        return True, f"Bem-vindo(a), {user.get('Técnico')}!"

    @staticmethod
    def logout() -> None:
        for key in ["authenticated", "tecnico", "login_code", "user_code", "auth_view", "auth_message"]:
            if key in st.session_state:
                del st.session_state[key]

        st.session_state["auth_view"] = "login"