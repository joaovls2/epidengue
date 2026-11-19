# Guia rápido de deploy

## Publicar no GitHub

1. Entre em https://github.com/ e crie um repositório chamado `dengue-ia-pernambuco`.
2. Para facilitar a demonstração, escolha `Public` (o código e os dados agregados do diretório `dashboard_data/` ficarão visíveis). Não há microdados individuais no pacote.
3. Extraia o ZIP do projeto.
4. Abra a pasta extraída e envie o conteúdo dela para a página do repositório usando **Add file > Upload files**. Envie também o diretório oculto `.streamlit` com o `config.toml`.
5. Faça o commit na branch `main`.

## Criar o app no Streamlit

1. Abra https://share.streamlit.io/ e entre com GitHub.
2. Clique em **Create app**.
3. Em **Repository**, selecione `dengue-ia-pernambuco`.
4. Em **Branch**, selecione `main`.
5. Em **Main file path**, informe `app.py`.
6. Clique em **Deploy**.
7. Aguarde a instalação do `requirements.txt`. Quando terminar, copie a URL `https://...streamlit.app`.

O app abre automaticamente com a série semanal agregada incluída no repositório; o professor não precisa ter a base original para visualizar o painel.

## Importante sobre os arquivos SINAN

Não envie `SINAN_-_Dengue.csv` nem outra extração individual ao GitHub público. A versão do painel publicada contém somente agregações semanais, anuais e mensais. O arquivo individual completo é opcional e deve permanecer fora do repositório. O `.gitignore` ignora CSVs e CSV.GZ na pasta `data/`.
