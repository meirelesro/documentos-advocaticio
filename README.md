# Gerador de documentos advocatícios

Este projeto gera cópias preenchidas dos modelos reais de contrato, procuração e declaração de hipossuficiência. Também oferece uma interface local para enviar documentos do cliente, extrair dados por leitura de texto/OCR, conferir os campos e baixar os documentos gerados.

## Segurança

O repositório é público. **Não envie CTPS, extrato de FGTS, RG, CPF ou outros documentos pessoais para o GitHub.** Os documentos enviados pela interface são processados localmente na máquina que executa o aplicativo e não devem ser incluídos em commits.

## Como executar a interface

No computador onde o projeto foi baixado, instale as dependências:

```bash
python -m pip install -r requirements.txt
```

Para PDFs escaneados ou imagens, instale também o Tesseract OCR e o Poppler. Em Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-por poppler-utils libreoffice
```

Depois inicie a interface:

```bash
streamlit run app.py
```

A página abrirá no navegador. Envie os documentos, clique em **Ler documentos**, revise os campos, complete o que estiver faltando e clique em **Gerar procuração, contrato e declaração**.

## Execução sem interface

Para gerar os documentos com os dados já preenchidos em `dados.json`, execute:

```bash
python gerar_pdfs.py
```

Os arquivos serão criados na pasta `saida/`. O workflow do GitHub Actions continua disponível para validação e geração a partir de alterações no `dados.json`, mas documentos pessoais não devem ser armazenados neste repositório público.

## Revisão obrigatória

Os documentos são gerados a partir dos modelos fornecidos e devem ser conferidos por profissional habilitado antes de assinatura, protocolo ou qualquer uso jurídico. A extração automática pode falhar em imagens ilegíveis, documentos incompletos ou formatos não previstos.
