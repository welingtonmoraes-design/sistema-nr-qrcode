import unicodedata
from datetime import datetime, date

from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel

from models import db, TreinamentoPTLoto


def _norm(valor):
    """Normaliza cabecalho: sem acentos, maiusculo, sem espacos extras."""
    if valor is None:
        return ""
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.upper().split())


def _texto(valor):
    """Converte celula em texto limpo (1.0 vira '1')."""
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def _data(valor):
    """Converte celula em date. Retorna None se invalida."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, (int, float)):
        try:
            return from_excel(valor).date()
        except Exception:
            return None
    texto = str(valor).strip()
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def ler_planilha(stream):
    """
    Le a planilha e devolve (linhas, erros).
    Localiza sozinho a linha de cabecalho nas 15 primeiras linhas.
    """
    wb = load_workbook(stream, data_only=True)
    ws = wb.active

    linha_cab = None
    colunas = {}

    for idx, row in enumerate(ws.iter_rows(min_row=1, max_row=15, values_only=True), start=1):
        normalizados = [_norm(c) for c in row]
        if any(c.startswith("NOME") for c in normalizados) and \
           any(c.startswith("DATA") for c in normalizados):
            linha_cab = idx
            for i, c in enumerate(normalizados):
                if c.startswith("NUM") and "numero" not in colunas:
                    colunas["numero"] = i
                elif c.startswith("NOME") and "nome" not in colunas:
                    colunas["nome"] = i
                elif c.startswith("MATRICULA") and "matricula" not in colunas:
                    colunas["matricula"] = i
                elif c.startswith("EMPRESA") and "empresa" not in colunas:
                    colunas["empresa"] = i
                elif c.startswith("DATA") and "data" not in colunas:
                    colunas["data"] = i
                elif c.startswith("INSTRUTOR") and "instrutor" not in colunas:
                    colunas["instrutor"] = i
            break

    if linha_cab is None or "nome" not in colunas or "data" not in colunas:
        raise ValueError(
            "Cabecalho nao encontrado. A planilha precisa ter as colunas "
            "NOME e DATA DO TREINAMENTO."
        )

    def pegar(row, chave):
        i = colunas.get(chave)
        if i is None or i >= len(row):
            return None
        return row[i]

    linhas = []
    erros = []

    for num_linha, row in enumerate(
        ws.iter_rows(min_row=linha_cab + 1, values_only=True), start=linha_cab + 1
    ):
        if all(c is None or str(c).strip() == "" for c in row):
            continue  # linha vazia

        nome = _texto(pegar(row, "nome"))
        if not nome:
            erros.append(f"Linha {num_linha}: nome vazio.")
            continue

        data_trein = _data(pegar(row, "data"))
        if data_trein is None:
            erros.append(f"Linha {num_linha} ({nome}): data do treinamento invalida.")
            continue

        linhas.append({
            "numero": _texto(pegar(row, "numero")),
            "nome": nome,
            "matricula": _texto(pegar(row, "matricula")),
            "empresa": _texto(pegar(row, "empresa")),
            "data_treinamento": data_trein,
            "instrutor": _texto(pegar(row, "instrutor")),
        })

    return linhas, erros


def gravar_linhas(linhas, substituir=False):
    """
    Grava as linhas no banco. Retorna (inseridos, ignorados_duplicados).
    Duplicado = mesma matricula/SSO + mesma data de treinamento.
    """
    if substituir:
        TreinamentoPTLoto.query.delete()
        existentes = set()
    else:
        existentes = {
            ((r.matricula or "").upper(), r.data_treinamento)
            for r in TreinamentoPTLoto.query.all()
        }

    inseridos = 0
    duplicados = 0

    for l in linhas:
        chave = (l["matricula"].upper(), l["data_treinamento"])
        if l["matricula"] and chave in existentes:
            duplicados += 1
            continue
        existentes.add(chave)
        db.session.add(TreinamentoPTLoto(**l))
        inseridos += 1

    db.session.commit()
    return inseridos, duplicados
