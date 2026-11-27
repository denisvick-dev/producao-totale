# Portal TOTALE

Painel interno para acompanhamento de produção técnica, consultivo, pontos,
metas e indicadores operacionais.

## Estrutura

- `streamlit_app.py`: autenticação e entrada do portal.
- `pages/home.py`: Visão Geral unificada (página inicial após o login).
- `pages/`: visões de Início, Produção, Consultivo, Indicadores e Admin.
- `components/`: design system e componentes visuais reutilizáveis.
- `utils/`: autenticação, banco, prévias da Visão Geral, configurações e leitura centralizada das bases.
- `utils/_datasources.py`: loader único das bases de produção (abas `Prod` + `Gpon`), com validação de HTML, fallbacks de XLSX/CSV/Drive e acesso autenticado por service account.
- `data/`: arquivos locais de apoio.

## Execução local

> Requer **Python 3.12 ou superior** (as versões fixadas de `numpy` e
> `contourpy` usam esse requisito).

1. Crie ou ative o ambiente virtual.

2. Instale as dependências:

   ```powershell
   pip install -r requirements.txt
   ```

3. Inicie o portal:

   ```powershell
   streamlit run streamlit_app.py
   ```

## Configuração

As credenciais do Google devem ser fornecidas pelo mecanismo de Secrets do
Streamlit, usando a chave `gcp_service_account`. Os IDs das planilhas ficam
centralizados em `utils/_config.py`. Para trocar a competência sem editar
código, use os Secrets `producao_spreadsheet_id` e
`producao_mes_anterior_spreadsheet_id`. A aba **Últimos 3 meses** da página
Produtividade usa ainda `producao_dois_meses_atras_spreadsheet_id` para a
competência de dois meses atrás (por padrão, setembro/2026). Atualize esse
Secret junto com o arquivo de mês anterior a cada nova competência; o painel
filtra os dados do técnico logado antes de agregar os resultados.

## Painel de Indicadores

`pages/indicadores.py` cruza seis abas operacionais com a Lista de Ativos e
mostra **apenas os registros do técnico logado**: visão consolidada dos seis
indicadores e um painel por indicador com o recorte de período e a evolução
diária. O login da sessão é aplicado como filtro antes do merge, então a
página não expõe dados de outros profissionais.

A planilha de indicadores precisa conter as abas `Geoloc_Os`,
`Aderencia_Ura`, `Nr35`, `Tec1` e `Baixa_Pda` (o indicador O.S. Digital é
calculado sobre a base de `Geoloc_Os`). Configure o ID dela nos Secrets do
Streamlit:

```toml
indicadores_spreadsheet_id = "SEU_ID_AQUI"
```

Alternativamente, preencha `INDICADORES_SPREADSHEET_ID` em
`utils/_config.py`. A planilha pode ser lida por exportação pública ou, se
estiver restrita, pela service account configurada em `gcp_service_account`.

## Blocos HTML

Blocos HTML multilinha enviados ao Streamlit devem ser dedentados antes da
renderização (`textwrap.dedent(...).strip()`). Sem isso, a indentação do
código-fonte é interpretada como bloco de código e a página mostra as tags
`<div>` cruas em vez do componente.

## Sidebar

Todas as páginas autenticadas usam o mesmo card de perfil/logout
(`render_sidebar_portal`) e o mesmo menu lateral (`injetar_css_menu_nomes`),
com os itens Início, Produtividade, Consultivo, Indicadores e Admin. O item
Admin só aparece para perfis administrativos.

## Visão Geral

Após o login, o portal abre `pages/home.py`. A página reúne prévia de pontos,
O.S., consultivos/vendas e indicadores na meta, além dos quatro indicadores de
produção e de atalhos para as páginas de detalhe. Os números vêm de
`utils/_home_data.py`, com cache; se alguma fonte estiver indisponível, a página
mostra um aviso em vez de falhar. A base de produção é lida pelo mesmo parser de
`pages/producao.py`, então os dois painéis não divergem por diferença de abas ou
fallback de download. O cálculo oficial continua nas páginas específicas.

## Produtividade e Painel de Metas

`pages/producao.py` organiza o conteúdo em três abas — **Resumo**, **Metas e
Cenários** e **Evolução Diária** — mantendo o filtro de período visível acima de
todas elas. O Resumo reúne os cartões operacionais, contexto/ritmo e histórico
do mês anterior. A aba de metas mostra três cenários de fechamento
(conservador, provável e otimista), os pontos/dia necessários, uma
classificação simplificada de chance (alta/média/baixa) e os dias úteis
restantes. Os botões abaixo da tabela abrem as O.S. que compõem o acumulado de
cada meta, com opção de exportar em CSV. A aba **Últimos 3 meses** compara a
produção individual das competências atual, anterior e dois meses atrás; os
IDs históricos são configuráveis por Secrets conforme as competências avançam.

## Autenticação

`AuthManager.validar_senha()` confirma login e senha **sem abrir sessão** e é
usada na troca de senha. Somente `AuthManager.login()` autentica o usuário. A
lista de colaboradores não é mais exibida nas telas públicas; a consulta de
logins fica restrita à aba `🔐 Logins` do painel Admin. Logins criados ou com
senha redefinida pelo Admin são marcados para troca obrigatória no primeiro
acesso: o usuário só entra no portal após validar a senha inicial e salvar uma
nova senha. O marcador fica junto ao hash na coluna `Pass` e é removido após a
troca bem-sucedida.
