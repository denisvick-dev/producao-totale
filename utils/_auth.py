"""
utils/_auth.py
==============
Módulo de Gerenciamento de Autenticação do Portal TOTALE.
Processa validação de login, hash Bcrypt e alteração de senhas.
"""

from __future__ import annotations

import logging
import bcrypt
import pandas as pd
import streamlit as st
from utils._database import get_db

logger = logging.getLogger(__name__)


class AuthManager:
    """Gerenciador central de autenticação e sessão dos colaboradores."""

    def login(self, identifier: str, password: str) -> tuple[bool, str]:
        """
        Autentica o colaborador comparando a senha informada com o Hash Bcrypt.

        Parâmetros:
            identifier: Login (ex: Z569935) ou User (ex: DENIS.ADMIN)
            password: Senha em texto plano informada no formulário

        Retorna:
            tuple[bool, str]: (Sucesso booleano, Mensagem para interface)
        """
        if not identifier or not password:
            return False, "Preencha o usuário e a senha para acessar."

        try:
            db = get_db()
            df_users = db.get_users_dataframe()

            if df_users is None or df_users.empty:
                return False, "Não foi possível carregar a base de colaboradores."

            # Normalização de busca (insensível a maiúsculas/minúsculas e espaços)
            identifier_clean = str(identifier).strip().upper()

            user_mask = (
                df_users["Login"].astype(str).str.strip().str.upper() == identifier_clean
            ) | (
                df_users["User"].astype(str).str.strip().str.upper() == identifier_clean
            )

            matched_user = df_users[user_mask]

            if matched_user.empty:
                return False, "Usuário ou senha incorretos."

            # Extrai dados do usuário encontrado
            row = matched_user.iloc[0]
            hash_salvo = str(row.get("Pass", "")).strip()

            if not hash_salvo or hash_salvo.lower() in ("nan", "none", "null", ""):
                return False, "Usuário sem senha cadastrada no sistema."

            # Preparação dos bytes para validação Bcrypt
            password_bytes = password.strip().encode("utf-8")
            hash_bytes = hash_salvo.encode("utf-8")

            is_valid = False

            # Validação Bcrypt padrão ($2b$, $2a$, $2y$)
            if hash_salvo.startswith(("$2a$", "$2b$", "$2y$")):
                try:
                    is_valid = bcrypt.checkpw(password_bytes, hash_bytes)
                except Exception as exc:
                    logger.error("Falha ao checar Bcrypt: %s", exc)
                    return False, "Formato de senha inválido na base."
            else:
                # Fallback de segurança para senhas antigas sem hash (texto puro)
                is_valid = (password.strip() == hash_salvo)

            if is_valid:
                # Captura nome do técnico independente da variação do nome da coluna
                nome_tecnico = str(
                    row.get("Técnico", row.get("TECNICO", row.get("Nome", "")))
                ).strip()
                login_codigo = str(row.get("Login", "")).strip()
                user_nome = str(row.get("User", "")).strip()

                # Regra de perfil Admin
                is_admin = (
                    user_nome.upper().endswith(".ADMIN")
                    or "ADMIN" in user_nome.upper()
                )

                # Salva sessão do Streamlit
                st.session_state["authenticated"] = True
                st.session_state["is_admin"] = is_admin
                st.session_state["user_info"] = {
                    "tecnico": nome_tecnico,
                    "login": login_codigo,
                    "user": user_nome,
                }

                logger.info("Usuário %s (%s) logado com sucesso.", user_nome, login_codigo)
                return True, "Login efetuado com sucesso!"

            return False, "Usuário ou senha incorretos."

        except Exception as err:
            logger.exception("Erro crítico no método login.")
            return False, f"Erro interno de autenticação: {str(err)}"

    def update_password(self, identifier: str, nova_senha: str) -> tuple[bool, str]:
        """
        Gera o Hash Bcrypt da nova senha e atualiza o cadastro no banco/planilha.

        Parâmetros:
            identifier: Login (ex: Z569935) ou User (ex: DENIS.ADMIN)
            nova_senha: Nova senha em texto plano (mínimo 6 caracteres)

        Retorna:
            tuple[bool, str]: (Sucesso booleano, Mensagem para interface)
        """
        if not identifier or not nova_senha:
            return False, "Preencha todos os campos obrigatórios."

        if len(nova_senha.strip()) < 6:
            return False, "A nova senha deve possuir no mínimo 6 caracteres."

        try:
            db = get_db()
            df_users = db.get_users_dataframe()

            if df_users is None or df_users.empty:
                return False, "Base de colaboradores indisponível."

            identifier_clean = str(identifier).strip().upper()

            user_mask = (
                df_users["Login"].astype(str).str.strip().str.upper() == identifier_clean
            ) | (
                df_users["User"].astype(str).str.strip().str.upper() == identifier_clean
            )

            matched_user = df_users[user_mask]

            if matched_user.empty:
                return False, "Usuário não encontrado na base de dados."

            # 1. Gera novo Hash Bcrypt com rounds=12
            bytes_senha = nova_senha.strip().encode("utf-8")
            salt = bcrypt.gensalt(rounds=12)
            hash_bcrypt = bcrypt.hashpw(bytes_senha, salt).decode("utf-8")

            # 2. Obtém a chave 'Login' exata da linha encontrada
            login_real = str(matched_user.iloc[0]["Login"]).strip()

            # 3. Atualiza no banco de dados / planilha
            sucesso = db.update_user_password(login_real, hash_bcrypt)

            if sucesso:
                logger.info("Senha do usuário %s atualizada com sucesso.", login_real)
                return True, "Senha alterada com sucesso! Você já pode realizar o login."

            return False, "Falha ao gravar a nova senha na base de dados."

        except Exception as err:
            logger.exception("Erro crítico no método update_password.")
            return False, f"Erro interno ao atualizar senha: {str(err)}"

    def logout(self) -> None:
        """Encerra a sessão ativa do usuário no Streamlit."""
        st.session_state["authenticated"] = False
        st.session_state["user_info"] = {}
        st.session_state["is_admin"] = False
        st.session_state["auth_view"] = "login"