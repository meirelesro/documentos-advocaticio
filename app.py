from __future__ import annotations

import io
import json
import zipfile
from datetime import date
from pathlib import Path

import streamlit as st

from extracao_documentos import CAMPOS, campos_faltantes, extrair_campos, ler_documento
from gerar_pdfs import gerar_documentos_a_partir_dados


st.set_page_config(page_title="Gerador de documentos advocatícios", page_icon=None, layout="centered")
st.title("Gerador de documentos advocatícios")
st.write("Envie os documentos do cliente, confira os dados identificados e gere a procuração, o contrato e a declaração.")
st.info("Os arquivos são processados localmente nesta execução. Não envie documentos pessoais para o repositório público do GitHub.")

if "dados" not in st.session_state:
    st.session_state.dados = {"data": date.today().strftime("%d de %B de %Y")}
if "textos" not in st.session_state:
    st.session_state.textos = []

st.subheader("1. Envie os documentos")
arquivos = st.file_uploader(
    "CTPS, extrato de FGTS, RG, CPF ou comprovante de endereço",
    type=["pdf", "png", "jpg", "jpeg", "webp", "tif", "tiff"],
    accept_multiple_files=True,
)

if arquivos and st.button("Ler documentos", type="primary"):
    encontrados: dict[str, str] = {}
    textos = []
    with st.spinner("Lendo os documentos e identificando os campos..."):
        for arquivo in arquivos:
            try:
                texto = ler_documento(arquivo, arquivo.name)
                textos.append(f"--- {arquivo.name} ---\n{texto}")
                encontrados.update(extrair_campos(texto))
            except Exception as erro:
                st.error(f"Não foi possível ler {arquivo.name}: {erro}")
    st.session_state.dados.update(encontrados)
    st.session_state.textos = textos
    st.success(f"Leitura concluída. {len(encontrados)} campo(s) foram encontrados; confira tudo abaixo.")

st.subheader("2. Confira e complete os dados")
with st.form("dados_cliente"):
    dados = st.session_state.dados
    col1, col2 = st.columns(2)
    atualizados: dict[str, str] = {}
    for indice, (chave, rotulo) in enumerate(CAMPOS):
        coluna = col1 if indice % 2 == 0 else col2
        with coluna:
            atualizados[chave] = st.text_input(rotulo, value=str(dados.get(chave, "")), key=f"campo_{chave}")
    atualizados["data"] = st.text_input("Data do documento", value=str(dados.get("data", "")), key="campo_data")
    confirmar = st.form_submit_button("Salvar conferência")
    if confirmar:
        st.session_state.dados = {k: v.strip() for k, v in atualizados.items() if v.strip()}
        st.success("Dados salvos para a geração.")

faltantes = campos_faltantes(st.session_state.dados)
if faltantes:
    st.warning("Ainda faltam campos essenciais: " + ", ".join(faltantes) + ". Complete-os antes de gerar.")
else:
    st.success("Os campos essenciais estão preenchidos. Ainda assim, confira os dados antes de gerar.")

st.subheader("3. Gere os documentos")
if st.button("Gerar procuração, contrato e declaração", disabled=bool(faltantes)):
    with st.spinner("Gerando documentos..."):
        try:
            arquivos_saida = gerar_documentos_a_partir_dados(st.session_state.dados)
            pacote = io.BytesIO()
            with zipfile.ZipFile(pacote, "w", zipfile.ZIP_DEFLATED) as arquivo_zip:
                for caminho in arquivos_saida:
                    arquivo_zip.write(caminho, arcname=Path(caminho).name)
            pacote.seek(0)
            st.download_button("Baixar documentos em ZIP", pacote.getvalue(), "documentos_gerados.zip", "application/zip")
            st.success("Documentos gerados. Revise o conteúdo antes de qualquer assinatura ou uso.")
        except Exception as erro:
            st.error(f"Erro ao gerar os documentos: {erro}")

with st.expander("Texto capturado para conferência"):
    if st.session_state.textos:
        st.text_area("OCR", "\n\n".join(st.session_state.textos), height=280)
    else:
        st.caption("O texto aparecerá aqui depois da leitura.")
