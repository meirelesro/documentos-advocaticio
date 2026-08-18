#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def carregar_dados(arquivo_json="dados.json"):
    """Carrega os dados do arquivo JSON"""
    try:
        with open(arquivo_json, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Erro: Arquivo '{arquivo_json}' não encontrado!")
        exit(1)
    except json.JSONDecodeError:
        print(f"Erro: Arquivo '{arquivo_json}' não é um JSON válido!")
        exit(1)

def processar_campos(texto, dados_cliente):
    """Substitui os campos dinâmicos no texto"""
    # Mapeia os placeholders para os dados
    substituicoes = {
        '«RECLAMANTE»': dados_cliente.get('nome', '___________________________________'),
        '«CPF»': dados_cliente.get('cpf', '___________________________________'),
        '«RG»': dados_cliente.get('rg', '___________________________________'),
        '«PIS»': dados_cliente.get('pis', '___________________________________'),
        '«ENDEREÇO»': dados_cliente.get('endereco', '___________________________________'),
        '«DATA_ATUAL»': dados_cliente.get('data', datetime.now().strftime('%d de %B de %Y'))
    }
    
    # Se não houver RG, remove a referência a ele
    if not dados_cliente.get('rg'):
        texto = texto.replace('portador(a) do CI/RG nº «RG», ', '')
        texto = texto.replace(', portador(a) do CI/RG nº «RG»', '')
    
    # Se não houver PIS, remove a referência a ele
    if not dados_cliente.get('pis'):
        texto = texto.replace('portador(a) do PIS nº «PIS», ', '')
        texto = texto.replace(', portador(a) do PIS nº «PIS»', '')
    
    # Realiza as substituições
    for placeholder, valor in substituicoes.items():
        texto = texto.replace(placeholder, valor)
    
    return texto

def carregar_template(arquivo_template):
    """Carrega o conteúdo do template"""
    try:
        with open(arquivo_template, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Erro: Template '{arquivo_template}' não encontrado!")
        exit(1)

def adicionar_paragrafo_com_negrito(doc, texto, dados_cliente):
    """Adiciona um parágrafo, colocando o nome do cliente em negrito"""
    nome_cliente = dados_cliente.get('nome', '')
    
    # Processa os campos primeiro
    texto_processado = processar_campos(texto, dados_cliente)
    
    # Se o texto contém o nome do cliente, faz em negrito
    if nome_cliente and nome_cliente in texto_processado:
        paragrafo = doc.add_paragraph()
        
        # Divide o texto pelo nome
        partes = texto_processado.split(nome_cliente)
        
        if len(partes) > 1:
            # Adiciona a parte antes do nome
            if partes[0]:
                paragrafo.add_run(partes[0])
            
            # Adiciona o nome em negrito
            run_nome = paragrafo.add_run(nome_cliente)
            run_nome.bold = True
            
            # Adiciona o resto do texto
            for parte in partes[1:]:
                paragrafo.add_run(parte)
        else:
            # Se não encontrou o nome exato, adiciona normal
            paragrafo.add_run(texto_processado)
        
        return paragrafo
    else:
        # Adiciona normal
        return doc.add_paragraph(texto_processado)

def criar_documento(template_word, conteudo_texto, nome_arquivo, dados_cliente):
    """Cria um documento Word com base no template"""
    # Carrega o documento template
    try:
        doc = Document(template_word)
        print(f"   Usando template: {template_word}")
    except FileNotFoundError:
        print(f"⚠️  Template Word '{template_word}' não encontrado!")
        print("   Criando documento sem template visual...")
        doc = Document()
    
    # Cria pasta de saída se não existir
    pasta_saida = Path("saida")
    pasta_saida.mkdir(exist_ok=True)
    
    # Processa o conteúdo
    linhas = conteudo_texto.split('\n')
    
    for linha in linhas:
        linha = linha.strip()
        
        if not linha:
            # Linha vazia
            doc.add_paragraph()
        elif linha.isupper() and len(linha) > 3:
            # Título (texto em maiúsculas)
            titulo = doc.add_paragraph()
            titulo.style = 'Heading 1'
            titulo_run = titulo.add_run(linha)
            titulo_run.bold = True
            titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        else:
            # Conteúdo normal (pode ter nome em negrito)
            adicionar_paragrafo_com_negrito(doc, linha, dados_cliente)
    
    # Salva o documento
    caminho_docx = pasta_saida / nome_arquivo
    
    try:
        doc.save(str(caminho_docx))
        print(f"✓ Documento criado: {caminho_docx}")
        return True
    except Exception as e:
        print(f"✗ Erro ao criar documento {nome_arquivo}: {e}")
        return False

def converter_para_pdf(arquivo_docx):
    """Converte o documento Word para PDF"""
    try:
        from docx2pdf import convert
        arquivo_pdf = str(arquivo_docx).replace('.docx', '.pdf')
        convert(str(arquivo_docx), arquivo_pdf)
        print(f"✓ PDF criado: {arquivo_pdf}")
        return True
    except ImportError:
        print("⚠️  Para gerar PDFs, instale: pip install python-docx python-docx2pdf")
        return False
    except Exception as e:
        print(f"⚠️  Erro ao converter para PDF: {e}")
        return False

def gerar_documentos():
    """Função principal que gera todos os documentos"""
    print("\n" + "="*60)
    print("GERADOR DE DOCUMENTOS ADVOCATÍCIOS - MEIRELES E SOUZA")
    print("="*60 + "\n")
    
    # Carrega os dados
    dados = carregar_dados()
    cliente = dados.get('cliente', {})
    nome_cliente = cliente.get('nome', 'cliente').lower().replace(' ', '_')
    
    print(f"👤 Cliente: {cliente.get('nome')}")
    print(f"📋 CPF: {cliente.get('cpf')}")
    print(f"📋 RG: {cliente.get('rg', 'Não informado')}")
    print(f"📋 PIS: {cliente.get('pis', 'Não informado')}")
    print(f"📍 Endereço: {cliente.get('endereco')}")
    print("\n" + "-"*60 + "\n")
    
    # Usa o template Word disponível
    template_word = "Modelo Pagina 2.docx"
    
    # Templates
    templates = [
        ("templates/contrato.txt", "Contrato de Serviços Advocatícios", f"01_contrato_{nome_cliente}.docx"),
        ("templates/hipossuficiencia.txt", "Declaração de Hipossuficiência", f"02_hipossuficiencia_{nome_cliente}.docx"),
        ("templates/procuracao.txt", "Procuração Ad-Judicia", f"03_procuracao_{nome_cliente}.docx"),
    ]
    
    documentos_gerados = 0
    
    # Gera cada documento
    for arquivo_template, nome_doc, nome_saida in templates:
        print(f"📝 Processando: {nome_doc}...")
        
        # Carrega o template de texto
        template = carregar_template(arquivo_template)
        
        # Cria o documento
        if criar_documento(template_word, template, nome_saida, cliente):
            documentos_gerados += 1
            
            # Tenta converter para PDF
            arquivo_docx = Path("saida") / nome_saida
            converter_para_pdf(arquivo_docx)
    
    print("\n" + "-"*60)
    print(f"\n✅ Processo concluído!")
    print(f"✅ {documentos_gerados} documento(s) gerado(s) na pasta 'saida/'")
    print(f"📁 Local: {Path('saida').absolute()}")
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    gerar_documentos()
