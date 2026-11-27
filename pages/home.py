"""pages/home.py — Visão Geral unificada do Portal TOTALE.

Página de entrada após o login. Reúne, em uma única leitura, a prévia de
produção, consultivo e indicadores do técnico logado (ou da operação, para
administradores) e oferece atalhos para as páginas de detalhe.

Os valores aqui são prévias calculadas por ``utils._home_data``. O cálculo
oficial de cada frente continua nas páginas específicas.
"""

from __future__ import annotations

from datetime import date, timedelta

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
# 4. PREFERÊNCIAS DA SESSÃO E ALERTAS
# ====================================================
# Preferências valem para a sessão atual; não são armazenadas em base central.
if "portal_favoritos" not in st.session_state:
    st.session_state["portal_favoritos"] = ["Produtividade", "Indicadores"]
if is_admin:
    with st.sidebar.expander("⚙️ Configurar alertas (sessão)", expanded=False):
        st.caption("Parâmetros temporários; serão redefinidos ao encerrar a sessão.")
        st.session_state["alerta_atraso_dias"] = st.number_input(
            "Alertar fonte após (dias)", min_value=1, max_value=30,
            value=int(st.session_state.get("alerta_atraso_dias", 3)), step=1,
        )
        st.session_state["alerta_progresso_minimo"] = st.slider(
            "Progresso mínimo da meta (%)", min_value=0, max_value=100,
            value=int(st.session_state.get("alerta_progresso_minimo", 50)),
        )
else:
    with st.sidebar.expander("🔔 Minhas preferências de alertas", expanded=False):
        st.caption("Preferências pessoais válidas nesta sessão.")
        st.session_state["alerta_fonte_ativo"] = st.checkbox(
            "Avisar sobre fonte atrasada", value=st.session_state.get("alerta_fonte_ativo", True)
        )
        st.session_state["alerta_meta_ativo"] = st.checkbox(
            "Avisar quando a meta estiver em risco", value=st.session_state.get("alerta_meta_ativo", True)
        )
        st.session_state["alerta_indicadores_ativo"] = st.checkbox(
            "Avisar sobre indicadores pendentes", value=st.session_state.get("alerta_indicadores_ativo", True)
        )

avisos: list[tuple[str, str]] = []

if not producao.get("ok"):
    avisos.append(("⚠️ Produção indisponível", producao.get("motivo", "fonte sem dados")))
else:
    pontos = float(producao["pontos"])
    meta = float(producao["meta"])
    dias = int(producao["dias_restantes"])
    data_ref = producao["data_ref"]
    atraso_limite = int(st.session_state.get("alerta_atraso_dias", 3))
    progresso_minimo = int(st.session_state.get("alerta_progresso_minimo", 50))
    if (is_admin or st.session_state.get("alerta_fonte_ativo", True)) and isinstance(data_ref, date) and (date.today() - data_ref).days >= atraso_limite:
        avisos.append(
            ("🕒 Fonte de produção atrasada",
             f"Última produção em {data_ref.strftime('%d/%m/%Y')}.")
        )
    progresso_pct = float(producao.get("progresso", 0) or 0)
    if (is_admin or st.session_state.get("alerta_meta_ativo", True)) and pontos < meta and progresso_pct < progresso_minimo:
        avisos.append(("⚠️ Progresso abaixo do limite", f"Meta em {fmt_num(progresso_pct, 1)}%; limite configurado: {progresso_minimo}% ."))
    if (is_admin or st.session_state.get("alerta_meta_ativo", True)) and pontos >= meta:
        avisos.append(
            ("🏆 Meta principal atingida",
             f"{fmt_num(pontos, 2)} pts de {fmt_num(meta)} pts.")
        )
    elif dias > 0 and (is_admin or st.session_state.get("alerta_meta_ativo", True)):
        necessario = (meta - pontos) / dias
        avisos.append(
            ("🎯 Ritmo para a meta principal",
             f"Faltam {fmt_num(meta - pontos, 2)} pts em {dias} dias úteis "
             f"({fmt_num(necessario, 2)} pts/dia).")
        )

if not consultivo.get("ok"):
    avisos.append(("⚠️ Consultivo indisponível", consultivo.get("motivo", "fonte sem dados")))

if not qualidade.get("ok"):
    if is_admin or st.session_state.get("alerta_indicadores_ativo", True):
        avisos.append(
            ("ℹ️ Qualidade sem prévia",
             qualidade.get("motivo", "verifique seus registros no painel de Indicadores"))
        )
elif is_admin or st.session_state.get("alerta_indicadores_ativo", True):
    pendentes = [item for item in qualidade.get("itens", []) if item.get("pct") is not None and item["pct"] < item.get("meta", 0)]
    if pendentes:
        nomes_pendentes = ", ".join(item["nome"] for item in pendentes[:3])
        avisos.append(("📋 Indicadores pendentes", f"Abaixo da meta: {nomes_pendentes}. Consulte Indicadores para ver os detalhes."))

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

# Resumo em painel, atualizado automaticamente sempre que a página é aberta.
st.divider()
render_section_header("🗓️", "Resumo semanal · visão operacional")
rw1, rw2, rw3, rw4 = st.columns(4)
inicio_semana = date.today() - timedelta(days=date.today().weekday())
rw1.metric("Semana iniciada em", inicio_semana.strftime("%d/%m/%Y"))
rw2.metric("Produção registrada", f"{fmt_num(producao.get('pontos'), 2)} pts" if producao.get("ok") else "—")
rw3.metric("Consultivos", fmt_num(consultivo.get("consultivos")) if consultivo.get("ok") else "—")
rw4.metric("Indicadores na meta", f"{qualidade['na_meta']} / {qualidade['total']}" if qualidade.get("ok") else "—")
st.caption(
    "Resumo atualizado ao carregar esta página. As fontes atuais fornecem prévias do período/mês; "
    "não há ainda histórico semanal consolidado para calcular variação semana contra semana."
)


# ====================================================
# 5B. PRÉVIA DE PRODUTIVIDADE (MESMA BASE DA PÁGINA DE DETALHE)
# ====================================================
if producao.get("ok"):
    st.divider()
    render_section_header("📊", "Produção em foco", badge="Prod + Gpon")
    p1, p2, p3, p4 = st.columns(4)

    with p1:
        render_kpi(
            p1,
            "O.S. Realizadas",
            fmt_num(producao["os"]),
            sub="Visitas executadas no mês",
            tema="cinza",
        )
    with p2:
        render_kpi(
            p2,
            "Prévia de Pontos",
            fmt_num(producao["pontos"], 2),
            sub=(
                f"Prod: {fmt_num(producao['pontos_prod'], 2)} · "
                f"Gpon: {fmt_num(producao['pontos_gpon'], 2)}"
            ),
            tema="azul",
            colorida=True,
        )
    with p3:
        render_kpi(
            p3,
            "Projeção Fim do Mês",
            fmt_num(producao["projecao"], 2),
            sub=(
                f"Média {fmt_num(producao['media_diaria'], 2)} pts/dia × "
                f"{producao['dias_restantes']} dias restantes"
            ),
            tema="laranja",
            colorida=True,
        )
    with p4:
        variacao = float(producao["variacao_media"])
        render_kpi(
            p4,
            "Média por O.S.",
            fmt_num(producao["media_os"], 2),
            sub=f"Média da operação: {fmt_num(producao['media_operacao'], 2)}",
            tema="verde",
            delta=f"{fmt_num(variacao, 1)}% vs média da operação",
            delta_tipo=(
                "up" if variacao > 0 else "down" if variacao < 0 else "neutral"
            ),
            colorida=True,
        )

    st.caption(
        f"Prévia da base de produção até {producao['data_ref'].strftime('%d/%m/%Y')}. "
        "A projeção e os detalhes completos ficam em Produtividade."
    )


# ====================================================
# 6. ATALHOS
# ====================================================
st.divider()
render_section_header("🚀", "Favoritos e acesso rápido")
opcoes_atalho = ["Produtividade", "Consultivo", "Indicadores"] + (["Admin"] if is_admin else [])
st.session_state["portal_favoritos"] = [
    item for item in st.session_state["portal_favoritos"] if item in opcoes_atalho
]
st.multiselect(
    "Escolha os atalhos desta sessão",
    options=opcoes_atalho,
    key="portal_favoritos",
    help="A seleção fica disponível durante esta sessão e não é persistida entre logins.",
)
atalhos = {
    "Produtividade": ("📊 Produtividade · pontos, metas e O.S.", "pages/producao.py"),
    "Consultivo": ("🗣️ Consultivo · funil, mix e vendas", "pages/consultivo.py"),
    "Indicadores": ("⚡ Indicadores · seus seis KPIs", "pages/indicadores.py"),
    "Admin": ("🛡️ Admin · equipe, ranking e gestão", "pages/admin.py"),
}
favoritos = st.session_state.get("portal_favoritos", [])
if favoritos:
    cols = st.columns(min(len(favoritos), 4))
    for i, favorito in enumerate(favoritos):
        with cols[i % len(cols)]:
            label, destino = atalhos[favorito]
            if st.button(label, key=f"atalho_{favorito.lower()}", width="stretch"):
                st.switch_page(destino)
else:
    st.info("Selecione ao menos um favorito para montar seus atalhos.")


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
