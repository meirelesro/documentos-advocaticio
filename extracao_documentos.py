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


def extrair_campos(texto: str) -> dict[str, str]:
    """Extrai apenas padrões claros; o usuário sempre revisa o resultado."""
    texto = texto.replace("\r", "")
    resultado = {
        "nome": _primeiro([r"(?:nome(?: completo)?|titular)\s*[:\-]\s*([^\n]+)"], texto),
        "cpf": _primeiro([r"CPF\s*[:\-]?\s*([0-9.\-]{11,14})", r"\b([0-9]{3}\.?[0-9]{3}\.?[0-9]{3}\-?[0-9]{2})\b"], texto),
        "rg": _primeiro([r"(?:RG|identidade|CI)\s*[:nº°\-]*\s*([0-9.\-]{4,20})"], texto),
        "pis": _primeiro([r"(?:PIS|NIT|PASEP)\s*[:nº°\-]*\s*([0-9.\-]{8,20})"], texto),
        "endereco": _primeiro([r"(?:endereço|resid[eê]ncia)\s*[:\-]\s*([^\n]+)"], texto),
        "data_nascimento": _primeiro([r"(?:nascimento|nascido em)\s*[:\-]?\s*([0-9]{1,2}[\/-][0-9]{1,2}[\/-][0-9]{2,4})"], texto),
        "empregador": _primeiro([r"(?:empregador|empresa|razão social)\s*[:\-]\s*([^\n]+)"], texto),
        "funcao": _primeiro([r"(?:função|cargo|ocupação)\s*[:\-]\s*([^\n]+)"], texto),
        "admissao": _primeiro([r"(?:admissão|admissao|início)\s*[:\-]?\s*([0-9]{1,2}[\/-][0-9]{1,2}[\/-][0-9]{2,4})"], texto),
        "desligamento": _primeiro([r"(?:desligamento|saída|saida)\s*[:\-]?\s*([0-9]{1,2}[\/-][0-9]{1,2}[\/-][0-9]{2,4})"], texto),
        "salario": _primeiro([r"(?:salário|salario|remuneração)\s*[:\-]?\s*(R\$\s*[0-9.,]+)"], texto),
        "fgts_saldo": _primeiro([r"(?:saldo(?: disponível)?|saldo FGTS)\s*[:\-]?\s*(R\$\s*[0-9.,]+)"], texto),
    }
    return {chave: _normalizar_documento(valor) for chave, valor in resultado.items() if valor}


def campos_faltantes(dados: dict[str, str]) -> list[str]:
    obrigatorios = ["nome", "cpf", "endereco"]
    return [rotulo for chave, rotulo in CAMPOS if chave in obrigatorios and not dados.get(chave)]
