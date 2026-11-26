"""pages/home.py — Visão Geral unificada do Portal TOTALE.

Página de entrada após o login. Reúne, em uma única leitura, a prévia de
produção, consultivo e indicadores do técnico logado (ou da operação, para
administradores) e oferece atalhos para as páginas de detalhe.

Os valores aqui são prévias calculadas por ``utils._home_data``. O cálculo
oficial de cada frente continua nas páginas específicas.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from utils._home_data import (
    resumo_consultivo,
    resumo_indicadores,
    resumo_producao,
)

st.set_page_config(
    page_title="Início | TOTALE",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ====================================================
# 1. PROTEÇÃO DE ACESSO
# ====================================================
if not st.session_state.get("authenticated", False):
    st.switch_page("streamlit_app.py")

info_logado = st.session_state.get("user_info", {}) or {}
nome_logado = str(info_logado.get("tecnico", "")).strip()
login_logado = str(info_logado.get("login", "")).strip()
user_logado = str(info_logado.get("user", "")).strip()
perfil_logado = str(info_logado.get("perfil", "")).strip()
is_admin = bool(st.session_state.get("is_admin", False)) or perfil_logado.upper() in {
    "ADMIN", "ADM", "ADMINISTRADOR", "GESTOR", "MANAGER", "SUPERVISOR", "COORDENADOR"
}

try:
    from components.componentes import (
        aplicar_estilo,
        aplicar_tema_claro,
        injetar_css_menu_nomes,
        render_hero_totale_1,
        render_insight,
        render_kpi,
        render_section_header,
        render_sidebar_portal,
    )
except ImportError:
    st.error("⚠️ Módulo 'componentes.py' não encontrado.")
    st.stop()

aplicar_estilo()
aplicar_tema_claro()
injetar_css_menu_nomes()
render_sidebar_portal(
    nome=nome_logado,
    login=login_logado,
    user=user_logado,
    perfil=perfil_logado,
    pagina_logout="streamlit_app.py",
)


# ====================================================
# 2. FORMATAÇÃO
# ====================================================
def fmt_num(valor: float | int | None, casas: int = 0) -> str:
    if valor is None or pd.isna(valor):
        return "—"
    return (
        f"{float(valor):,.{casas}f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


primeiro_nome = nome_logado.split()[0].title() if nome_logado else (user_logado or "técnico")

render_hero_totale_1(
    titulo="Visão Geral",
    subtitulo=(
        f"Olá, {primeiro_nome}. Seu resumo de produção, consultivo e qualidade "
        "em um só lugar."
    ),
    icone="dashboard",
    badge="🏠 Início · Portal TOTALE",
    usar_material=True,
)


# ====================================================
# 3. CARREGAMENTO DAS PRÉVIAS
# ====================================================
with st.spinner("Reunindo seu resumo..."):
    producao = resumo_producao(nome_logado, login_logado, user_logado, is_admin)
    consultivo = resumo_consultivo(nome_logado, login_logado, user_logado, is_admin)
    qualidade = resumo_indicadores(login_logado, user_logado)


# ====================================================
# 4. AVISOS ACIONÁVEIS
# ====================================================
avisos: list[tuple[str, str]] = []

if not producao.get("ok"):
    avisos.append(("⚠️ Produção indisponível", producao.get("motivo", "fonte sem dados")))
else:
    pontos = float(producao["pontos"])
    meta = float(producao["meta"])
    dias = int(producao["dias_restantes"])
    data_ref = producao["data_ref"]
    if isinstance(data_ref, date) and (date.today() - data_ref).days >= 3:
        avisos.append(
            ("🕒 Fonte de produção atrasada",
             f"Última produção em {data_ref.strftime('%d/%m/%Y')}.")
        )
    if pontos >= meta:
        avisos.append(
            ("🏆 Meta principal atingida",
             f"{fmt_num(pontos, 2)} pts de {fmt_num(meta)} pts.")
        )
    elif dias > 0:
        necessario = (meta - pontos) / dias
        avisos.append(
            ("🎯 Ritmo para a meta principal",
             f"Faltam {fmt_num(meta - pontos, 2)} pts em {dias} dias úteis "
             f"({fmt_num(necessario, 2)} pts/dia).")
        )

if not consultivo.get("ok"):
    avisos.append(("⚠️ Consultivo indisponível", consultivo.get("motivo", "fonte sem dados")))

if not qualidade.get("ok"):
    avisos.append(
        ("ℹ️ Qualidade sem prévia",
         qualidade.get("motivo", "verifique seus registros no painel de Indicadores"))
    )

for titulo, detalhe in avisos[:5]:
    render_insight(f"**{titulo}** — {detalhe}", tipo="alerta" if "⚠️" in titulo or "🕒" in titulo else "info")


# ====================================================
# 5. CARDS PRINCIPAIS
# ====================================================
render_section_header("📌", "Seu resumo de hoje")
k1, k2, k3, k4 = st.columns(4)

with k1:
    if producao.get("ok"):
        render_kpi(
            k1,
            "Pontos no mês" if not is_admin else "Pontos da operação",
            fmt_num(producao["pontos"], 2),
            sub=(
                f"Meta {fmt_num(producao['meta'])} · "
                f"{fmt_num(producao['progresso'], 1)}%"
            ),
            tema="azul" if producao["pontos"] < producao["meta"] else "verde",
            colorida=True,
        )
    else:
        render_kpi(k1, "Pontos no mês", "—", sub="fonte indisponível", tema="cinza")

with k2:
    if producao.get("ok"):
        render_kpi(
            k2,
            "O.S. no período" if not is_admin else "Técnicos ativos",
            fmt_num(producao["os"] if not is_admin else producao["tecnicos"]),
            sub=f"{producao['dias_restantes']} dias úteis restantes",
            tema="laranja",
            colorida=True,
        )
    else:
        render_kpi(k2, "O.S. no período", "—", sub="fonte indisponível", tema="cinza")

with k3:
    if consultivo.get("ok"):
        render_kpi(
            k3,
            "Consultivos / Vendas",
            f"{fmt_num(consultivo['consultivos'])} / {fmt_num(consultivo['produtos'])}",
            sub=f"Conversão de {fmt_num(consultivo['taxa'] * 100, 1)}%",
            tema="verde",
            colorida=True,
        )
    else:
        render_kpi(k3, "Consultivos / Vendas", "—", sub="fonte indisponível", tema="cinza")

with k4:
    if qualidade.get("ok"):
        render_kpi(
            k4,
            "Indicadores na meta",
            f"{qualidade['na_meta']} de {qualidade['total']}",
            sub="prévia · veja o painel completo em Indicadores",
            tema="verde" if qualidade["na_meta"] == qualidade["total"] else "laranja",
            colorida=True,
        )
    else:
        render_kpi(
            k4,
            "Indicadores na meta",
            "—",
            sub="abra Indicadores para detalhar",
            tema="cinza",
        )

st.caption(
    "Os números desta página são prévias com cache. Para auditoria completa, "
    "use as páginas específicas do menu."
)


# ====================================================
# 6. ATALHOS
# ====================================================
st.divider()
render_section_header("🚀", "Acesso rápido")
a1, a2, a3, a4 = st.columns(4)

with a1:
    if st.button(
        "📊 Produtividade\n pontos, metas e O.S.",
        key="atalho_producao",
        width="stretch",
    ):
        st.switch_page("pages/producao.py")
with a2:
    if st.button(
        "🗣️ Consultivo\n funil, mix e vendas",
        key="atalho_consultivo",
        width="stretch",
    ):
        st.switch_page("pages/consultivo.py")
with a3:
    if st.button(
        "⚡ Indicadores\n seus seis KPIs",
        key="atalho_indicadores",
        width="stretch",
    ):
        st.switch_page("pages/indicadores.py")
with a4:
    if is_admin:
        if st.button(
            "🛡️ Admin\n equipe, ranking e logins",
            key="atalho_admin",
            width="stretch",
        ):
            st.switch_page("pages/admin.py")
    else:
        st.info("🔒 Área Admin disponível apenas para gestores.")


# ====================================================
# 7. DETALHE DOS INDICADORES (QUANDO DISPONÍVEL)
# ====================================================
if qualidade.get("ok"):
    with st.expander("Ver prévia indicador por indicador"):
        linhas = [
            {
                "Indicador": item["nome"],
                "Aderência": (
                    "—" if item["pct"] is None else f"{fmt_num(item['pct'], 1)}%"
                ),
                "Meta": f"{fmt_num(item['meta'])}%",
                "Status": (
                    "—" if item["pct"] is None
                    else ("✅ Na meta" if item["pct"] >= item["meta"] else "🔴 Abaixo")
                ),
            }
            for item in qualidade["itens"]
        ]
        st.dataframe(pd.DataFrame(linhas), width="stretch", hide_index=True)

st.markdown("---")
st.caption(
    "Portal TOTALE · Visão Geral · "
    f"{nome_logado.title() if nome_logado else user_logado}"
)
