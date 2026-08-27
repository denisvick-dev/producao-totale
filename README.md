# Portal TOTALE

Painel interno para acompanhamento de produção técnica, consultivo, pontos,
metas e indicadores operacionais.

## Estrutura

- `streamlit_app.py`: autenticação e entrada do portal.
- `pages/`: visões de Produção e Consultivo.
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
