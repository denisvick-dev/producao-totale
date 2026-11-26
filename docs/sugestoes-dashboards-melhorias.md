# Sugestões de dashboards e melhorias — Portal TOTALE

Data: 26/11/2026 · Branch: `arena/f7ad03c1-producao-totale`

## Implementação nesta branch

- ✅ **2.1 Visão Geral** — `pages/home.py` + `utils/_home_data.py`, com abertura automática após o login e atalhos para as demais páginas.
- ✅ **2.3 Central de Metas com cenários** — três cenários, pontos/dia necessários, chance simplificada, dias úteis restantes e drill-down das O.S. em `pages/producao.py`.
- ✅ **Item 3 de segurança** — `AuthManager.validar_senha()` separa validação de autenticação e a lista de usuários saiu das telas públicas.
- ⏳ Demais itens seguem como proposta para próximas iterações.

## 1. Diagnóstico rápido

O portal já tem uma base sólida:

- **Produção** (`pages/producao.py`): O.S., pontos Prod/GPON, projeção, share, metas, mês anterior, evolução diária.
- **Consultivo** (`pages/consultivo.py`): abordagens, vendas, win rate, mix Mesh/TV/Virtua, projeção, ritmo diário.
- **Indicadores** (`pages/indicadores.py`): seis indicadores com recorte por período, comparação de 7 dias, evolução diária, aba por indicador, glossário e alerta de fonte atrasada.
- **Admin** (`pages/admin.py`): ranking, visão por equipe, gráficos, plano de recuperação, ficha individual, consultivo e gestão de logins.

Pontos fortes: identidade por login aplicada antes do merge (privacidade), cache de leitura, design system compartilhado, tooltips e legendas de status.

Principais lacunas observadas:

1. Não existe uma **página inicial unificada**: o técnico cai direto em Produção e o admin em Admin; para ter a visão completa é preciso navegar entre quatro páginas.
2. Alguns comparativos **não respeitam o filtro de período** (ex.: o contexto global de pontos em `producao.py` usa `df_raw` sem filtrar; o "mês anterior" é fixo, independentemente do intervalo escolhido).
3. A planilha de produção está **fixa** em `11Dp9...` (`PRODUCAO_SPREADSHEET_ID` / `SPREADSHEET_ID_PRODUCAO`), enquanto há arquivos mensais de 2025 e 2026 no Drive.
4. Não há **exportação** das tabelas, nem um relatório simples para o supervisor.
5. Não há uma visão de **qualidade consolidada da equipe** nem de **saúde dos dados** (atualidade/cobertura/erros de esquema), fora do recorte pessoal de Indicadores.

---

## 2. Propostas de dashboards

Ordem sugerida por valor percebido × esforço.

### 2.1. 🏠 Visão Geral (home do portal) — P1 · esforço M

Substituir o redirecionamento direto para Produção/Admin por uma página única, com cartões de todas as frentes e atalhos para o detalhe.

Conteúdo mínimo (MVP):

- **Técnico:** pontos no mês vs meta, projeção, indicadores na meta (X de 6), consultivos e vendas no mês, alerta de fonte desatualizada.
- **Admin:** pontos da operação vs meta, % da equipe na meta, maiores desvios de qualidade (agregado), atraso das fontes.
- Um bloco de "Atenção" com no máximo 5 avisos acionáveis (ex.: "Geoloc_Os parada há 3 dias", "faltam 82 pts/dia para a meta").

Por quê: hoje o valor está espalhado; uma home reduz o tempo até a informação e padroniza o ponto de entrada. Não exige nova fonte de dados — reusa os componentes existentes.

### 2.2. 📅 Tendência 90 dias / comparativo mensal — P2 · esforço M-A

Série temporal unificada de pontos, O.S., consultivos e indicadores, com média móvel de 7 dias e comparação mês contra mês.

- Permite ver se a queda de um indicador é pontual ou tendência.
- Usa os arquivos mensais de produção já presentes no Drive; precisa de um índice de IDs por competência (hoje os IDs estão espalhados no código).
- Incluir banda de projeção (cenário conservador / provável / otimista) em vez de um único número.

### 2.3. 🎯 Central de Metas e Projeção com cenários — P1 · esforço M

Evoluir o `Painel de Metas Mensais` de `producao.py`:

- Três cenários: **provável** (média dos dias com O.S.), **conservador** (mediana dos últimos 14 dias) e **otimista** (melhor semana recente).
- Mostrar `pontos/dia necessários`, **probabilidade simplificada de atingir a meta** (ex.: "baixa / média / alta") e dias úteis restantes.
- Clicar em uma meta abre o detalhe das O.S. que compõem os pontos (drill-down).

### 2.4. 💼 Consultivo com funil e metas — P1 · esforço M

Complementar `pages/consultivo.py`:

- Filtro de período (hoje inexistente) com os mesmos atalhos de Produção.
- Funil **abordagem → oferta → venda** e taxa de conversão por produto (Mesh/TV/Virtua), não só o win rate agregado.
- Meta por produto e por técnico, com projeção comparada à meta.
- No Admin: ranking de vendedores já existe; acrescentar evolução por semana e comparativo com o mês anterior.

### 2.5. 🔍 Qualidade da equipe (somente Admin) — P2 · esforço M

Agregar as seis abas de indicadores por **base, monitor e equipe**:

- Heatmap dia × indicador (verde/âmbar/vermelho) para achar a data de ruptura.
- Ranking de maiores desvios e quantidade de técnicos fora da meta por indicador.
- Ficha individual com os mesmos números que o técnico vê — sem expandir o acesso de não-admins.

Atenção à privacidade: manter a regra atual de filtrar por login antes do merge; esta visão deve ser restrita a perfis administrativos e agregada por padrão.

### 2.6. 🩺 Saúde dos dados (Data Ops) — P2 · esforço M

Painel de confiança das fontes, hoje só parcial no sidebar de Indicadores:

- Última atualização por fonte (usuários, produção, ativos, indicadores, consultivo), com semáforo de atraso.
- Cobertura: quantos técnicos têm registro em cada aba, linhas novas por dia, colunas obrigatórias ausentes.
- Status do cache, hora do último refresh e botão "recarregar bases" (já existe em Indicadores; generalizar).
- Histórico de incidentes de carga (quando a fonte falhou e por quanto tempo).

---

## 3. Melhorias pontuais no que já existe

| # | Item | Onde | Impacto | Esforço |
|---|---|---|---|---|
| 1 | Aplicar o mesmo período ao comparativo global: hoje `pontos_globais`, `posicao_geral` e `pontos_projeto` usam `df_raw` sem filtro, enquanto os pontos do técnico usam `df_tec_prod` | `pages/producao.py` (~linhas 1210-1250) | Share e ranking deixam de ser enganosos | P0 · S |
| 2 | Tornar o "mês anterior" relativo ao filtro ou, no mínimo, rotular explicitamente o mês comparado | `pages/producao.py` | Evita comparar períodos diferentes sem aviso | P0 · S |
| 3 | Filtros rápidos compartilhados (Hoje / 7 dias / 30 dias / Mês / Mês anterior) via `st.session_state`, com os mesmos rótulos nas quatro páginas | `pages/*.py`, `components/` | Consistência e menos cliques | P1 · M |
| 4 | Seletor de competência da produção (ID da planilha por mês) + aviso quando a fonte estiver desatualizada | `utils/_config.py`, `pages/producao.py`, `pages/admin.py` | Remove o ID fixo de nov/25; evita análise de mês errado | P1 · M |
| 5 | Exportação CSV/XLSX das tabelas e "relatório para supervisor" em PDF/HTML imprimível | todas as páginas | Fecha o ciclo de gestão fora do portal | P1 · S |
| 6 | Drill-down dos KPIs para os registros que os compõem (O.S. ou linhas do indicador) | `producao.py`, `indicadores.py` | Transforma o alerta em ação | P1 · M |
| 7 | Centralizar os loaders duplicados em `utils/_datasources.py` evalidar esquema (colunas obrigatórias, tipos, linhas vazias) com mensagem amigável | `pages/producao.py`, `admin.py`, `indicadores.py` | Menos código duplicado, falhas mais claras | P1 · M |
| 8 | Projeção com mediana e intervalo, tratando dias sem O.S. e feriados explicitamente | `pages/producao.py`, `pages/consultivo.py` | Número mais confiável para metas | P2 · M |
| 9 | Unificar os cartões de KPI (HTML em Produção/Admin/Consultivo × `st.metric` em Indicadores) e revisar contraste/responsividade | `components/componentes.py` | Interface mais consistente e acessível | P2 · M |
| 10 | Adicionar `st.query_params` para período/filtros (link compartilhável) | todas as páginas | Facilita discussões em reunião | P2 · S |
| 11 | Testes automatizados das regras de negócio (normalização de pontos, dias úteis, comparação 7d, classificação de status) | novo `tests/` | Evita regressão ao evoluir dashboards | P1 · M |

### Segurança e higiene (P0)

- `tela_trocar_senha()` valida a senha atual chamando `auth.login()`, que **marca a sessão como autenticada**. Após o sucesso, o fluxo volta ao login e o app redireciona para a página interna. Separar "validar senha" de "abrir sessão" (`auth.validar_senha()`).
- A tela de login mostra a lista de colaboradores (nome, login, user) para "conferência". Isso facilita enumeração de usuários; substituir por ajuda discretizada ou exigir autenticação para consulta.
- `AuthManager.login()` aceita senha em texto puro como fallback. Migrar hashes antigos e remover o fallback.
- Registrar auditoria de alterações sensíveis (senha, perfil, exclusão de login, upload do consultivo) — hoje não há trilha.
- Aplicar limite de tentativas de login e mensagens genéricas de erro.

---

## 4. Roadmap sugerido

**Onda 1 — correções e ganho rápido (1-2 dias)**
Itens 1, 2 e 5 da tabela e os ajustes de segurança: deixa os números confiáveis e a operação segura antes de expandir.

**Onda 2 — experiência e flexibilidade (3-5 dias)**
Visão Geral, filtros compartilhados, seletor de competência, funil do consultivo, loaders centralizados e testes.

**Onda 3 — inteligência e governança (1-2 semanas)**
Tendência 90 dias, qualidade da equipe, saúde dos dados, projeção com cenários e relatório imprimível.

## 5. Como medir se deu certo

- Tempo médio até o técnico encontrar "faltam X pontos para a meta" (alvo: uma tela).
- % de sessões que passam pela Visão Geral e chegam ao detalhe.
- Número de dias por mês com fonte atrasada ou falha de leitura (alvo: zero sem alerta).
- Erro médio da projeção contra o fechamento real (MAPE) — comparação mês a mês.
- Tempo de carregamento da página inicial (alvo: < 3 s com cache morno).

> Próximo passo: escolher os itens a implementar. Posso começar pela Onda 1 sem alterar o layout das páginas e, em seguida, evoluir para a Visão Geral.
