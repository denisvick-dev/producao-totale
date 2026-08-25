# utils/_auth.py
from typing import Tuple
import bcrypt
import streamlit as st
from ._database import get_db


class AuthManager:
    def __init__(self) -> None:
        self.db = get_db()

    @staticmethod
    def verify_password(plain_password: str, stored_password: str) -> bool:
        plain = plain_password.strip()
        stored = str(stored_password).strip()

        if stored.startswith("$2b$") or stored.startswith("$2a$"):
            try:
                return bcrypt.checkpw(plain.encode("utf-8"), stored.encode("utf-8"))
            except Exception:
                return False

        return plain == stored

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
        for key in ["authenticated", "tecnico", "login_code", "user_code"]:
            if key in st.session_state:
                del st.session_state[key]