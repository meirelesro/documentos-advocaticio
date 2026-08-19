"""Leitura local de documentos e extração inicial de dados.

O módulo usa texto embutido no PDF quando disponível e OCR como alternativa.
Nenhum arquivo é enviado para serviços externos.
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import BinaryIO

from PIL import Image

try:
    import pytesseract
except ImportError:  # pragma: no cover - mensagem amigável na interface
    pytesseract = None

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None

try:
    from pdf2image import convert_from_bytes
except ImportError:  # pragma: no cover
    convert_from_bytes = None


CAMPOS = [
    ("nome", "Nome completo"),
    ("cpf", "CPF"),
    ("rg", "RG"),
    ("pis", "PIS/NIT"),
    ("endereco", "Endereço"),
    ("data_nascimento", "Data de nascimento"),
    ("empregador", "Empregador"),
    ("funcao", "Função"),
    ("admissao", "Data de admissão"),
    ("desligamento", "Data de desligamento"),
    ("salario", "Salário"),
    ("fgts_saldo", "Saldo de FGTS"),
]


def _texto_pdf(conteudo: bytes) -> str:
    if PdfReader is None:
        return ""
    try:
        reader = PdfReader(__import__("io").BytesIO(conteudo))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return ""


def _ocr_imagem(imagem: Image.Image) -> str:
    if pytesseract is None:
        raise RuntimeError("Instale pytesseract e o Tesseract OCR para ler imagens.")
    try:
        return pytesseract.image_to_string(imagem, lang="por+eng")
    except Exception:
        return pytesseract.image_to_string(imagem)


def ler_documento(arquivo: BinaryIO, nome_arquivo: str) -> str:
    """Retorna o texto do arquivo; aplica OCR quando necessário."""
    conteudo = arquivo.read()
    extensao = Path(nome_arquivo).suffix.lower()
    if extensao == ".pdf":
        texto = _texto_pdf(conteudo)
        if texto.strip():
            return texto
        if convert_from_bytes is None:
            raise RuntimeError("Instale pdf2image e o Poppler para aplicar OCR em PDFs escaneados.")
        paginas = convert_from_bytes(conteudo, dpi=220, first_page=1, last_page=8)
        return "\n".join(_ocr_imagem(pagina) for pagina in paginas)
    if extensao in {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}:
        with tempfile.NamedTemporaryFile(suffix=extensao) as temporario:
            temporario.write(conteudo)
            temporario.flush()
            return _ocr_imagem(Image.open(temporario.name))
    raise ValueError("Formato não suportado. Envie PDF, PNG, JPG, JPEG, WEBP, TIF ou TIFF.")


def _primeiro(padroes: list[str], texto: str) -> str:
    for padrao in padroes:
        encontrado = re.search(padrao, texto, flags=re.IGNORECASE | re.MULTILINE)
        if encontrado:
            return " ".join(encontrado.group(1).strip().split())
    return ""


def _normalizar_documento(valor: str) -> str:
    return valor.strip(" .:;-\n\t")


def _campo_por_rotulo(texto: str, rotulos: list[str]) -> str:
    """Busca o valor na mesma linha ou na próxima linha não vazia."""
    linhas = [linha.strip() for linha in texto.splitlines()]
    padrao_rotulo = re.compile(r"^(?:" + "|".join(rotulos) + r")\s*(?:[:\-–]|n[º°o]?|$)", re.IGNORECASE)
    for indice, linha in enumerate(linhas):
        if not linha:
            continue
        mesma_linha = re.match(r"^(?:" + "|".join(rotulos) + r")\s*(?:[:\-–]|n[º°o]?\s*[:\-–]?)\s*(.+)$", linha, re.IGNORECASE)
        if mesma_linha and mesma_linha.group(1).strip():
            return _normalizar_documento(mesma_linha.group(1))
        if padrao_rotulo.match(linha):
            for proxima in linhas[indice + 1: indice + 4]:
                if proxima and not re.match(r"^(CPF|PIS|NIT|RG|DATA|ENDEREÇO)\b", proxima, re.IGNORECASE):
                    return _normalizar_documento(proxima)
    return ""


def _nome_por_heuristica(texto: str) -> str:
    """Fallback para OCR sem rótulo: seleciona uma linha provável de nome completo."""
    ignorar = {"NOME", "CPF", "PIS", "NIT", "FGTS", "TRABALHADOR", "SEGURADO", "CARTEIRA", "PROFISSIONAL"}
    for linha in texto.splitlines():
        candidato = " ".join(linha.strip().split())
        palavras = re.findall(r"[A-Za-zÀ-ÿ]+", candidato)
        if 2 <= len(palavras) <= 8 and 8 <= len(candidato) <= 80:
            maiusculas = candidato.upper() == candidato
            if maiusculas and not any(palavra in ignorar for palavra in palavras):
                return candidato
    return ""


def extrair_campos(texto: str) -> dict[str, str]:
    """Extrai padrões de documentos brasileiros; o usuário sempre revisa o resultado."""
    texto = texto.replace("\r", "")
    nome = _primeiro([
        r"(?:nome(?: completo)?|nome do trabalhador|nome do segurado|titular|trabalhador)\s*[:\-]\s*([^\n]+)",
        r"(?:nome(?: completo)?|nome do trabalhador|nome do segurado|titular)\s*\n\s*([^\n]+)",
    ], texto)
    nome = nome or _campo_por_rotulo(texto, ["nome", "nome completo", "nome do trabalhador", "nome do segurado", "titular", "segurado"])
    nome = nome or _nome_por_heuristica(texto)
    cpf = _primeiro([r"CPF\s*[:\-]?\s*([0-9.\-]{11,14})", r"\b([0-9]{3}\.?[0-9]{3}\.?[0-9]{3}\-?[0-9]{2})\b"], texto)
    pis = _primeiro([r"(?:PIS|NIT|PASEP|PIS/PASEP)\s*[:nº°\-]*\s*([0-9.\-]{8,20})"], texto)
    pis = pis or _campo_por_rotulo(texto, ["PIS", "NIT", "PASEP", "PIS/PASEP"])
    empregador = _primeiro([r"(?:empregador|empresa|razão social)\s*[:\-]\s*([^\n]+)"], texto)
    empregador = empregador or _campo_por_rotulo(texto, ["empregador", "empresa", "razão social"])
    funcao = _primeiro([r"(?:função|cargo|ocupação)\s*[:\-]\s*([^\n]+)"], texto)
    funcao = funcao or _campo_por_rotulo(texto, ["função", "cargo", "ocupação"])
    endereco = _primeiro([r"(?:endereço|resid[eê]ncia)\s*[:\-]\s*([^\n]+)"], texto)
    # CTPS informa o endereço do estabelecimento, não o endereço residencial do cliente.
    endereco = endereco or _campo_por_rotulo(texto, ["endereço", "residência"])
    data_nascimento = _primeiro([r"(?:nascimento|nascido em)\s*[:\-]?\s*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})"], texto)
    data_nascimento = data_nascimento or _campo_por_rotulo(texto, ["data de nascimento", "nascimento"])
    admissao = _primeiro([r"(?:admissão|admissao|início|data de admissão)\s*[:\-]?\s*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})"], texto)
    desligamento = _primeiro([r"(?:desligamento|saída|saida|data e código de afastamento)\s*[:\-]?\s*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})"], texto)
    intervalos = re.findall(r"\b([0-9]{2}[\/\-][0-9]{2}[\/\-][0-9]{4})\s*[-–]\s*([0-9]{2}[\/\-][0-9]{2}[\/\-][0-9]{4})\b", texto)
    if intervalos:
        # A CTPS Digital lista o vínculo mais recente primeiro.
        admissao = intervalos[0][0]
        desligamento = intervalos[0][1]
    admissao = admissao or _campo_por_rotulo(texto, ["data de admissão", "admissão", "admissao", "início"])
    desligamento = desligamento or _campo_por_rotulo(texto, ["data e código de afastamento", "desligamento", "saída", "saida"])
    salario = _primeiro([r"(?:salário|salario|remuneração)\s*[:\-]?\s*(R\$\s*[0-9.,]+)"], texto)
    salario = salario or _campo_por_rotulo(texto, ["salário contratual", "salário", "remuneração"])
    fgts_saldo = _primeiro([r"(?:saldo(?: disponível)?|saldo FGTS|valor para fins rescisórios)\s*[:\-]?\s*(R\$\s*[0-9.,]+)"], texto)
    fgts_saldo = fgts_saldo or _campo_por_rotulo(texto, ["saldo", "saldo disponível", "saldo FGTS", "valor para fins rescisórios"])
    resultado = {
        "nome": nome,
        "cpf": cpf,
        "rg": _primeiro([r"(?:RG|identidade|CI)\s*[:nº°\-]*\s*([0-9.\-]{4,20})"], texto),
        "pis": pis,
        "endereco": endereco,
        "data_nascimento": data_nascimento,
        "empregador": empregador,
        "funcao": funcao,
        "admissao": admissao,
        "desligamento": desligamento,
        "salario": salario,
        "fgts_saldo": fgts_saldo,
    }
    return {chave: _normalizar_documento(valor) for chave, valor in resultado.items() if valor}


def campos_faltantes(dados: dict[str, str]) -> list[str]:
    obrigatorios = ["nome", "cpf", "endereco"]
    return [rotulo for chave, rotulo in CAMPOS if chave in obrigatorios and not dados.get(chave)]
