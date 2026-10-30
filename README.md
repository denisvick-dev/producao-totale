# Portal TOTALE

Painel interno para acompanhamento de produção técnica, consultivo, pontos,
metas e indicadores operacionais.

## Estrutura

- `streamlit_app.py`: autenticação e entrada do portal.
- `pages/`: visões de Produção, Consultivo, Indicadores e Admin.
- `components/`: design system e componentes visuais reutilizáveis.
- `utils/`: autenticação, banco e configurações compartilhadas.
- `data/`: arquivos locais de apoio.

## Execução local

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
centralizados em `utils/_config.py`.

## Painel de Indicadores

`pages/indicadores.py` cruza seis abas operacionais com a Lista de Ativos e
oferece visão consolidada, drill-down por técnico e um painel por indicador.

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
