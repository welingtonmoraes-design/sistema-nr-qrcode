import re
import unicodedata

from openpyxl import load_workbook

from models import db, CatalogoNR, ColaboradorCurso

PALAVRAS_PERIODO = {
    "TRIMESTRAL": 3, "SEMESTRAL": 6, "ANUAL": 12,
    "BIENAL": 24, "TRIENAL": 36, "QUINQUENAL": 60,
}

FRASES_SEM_VALIDADE = (
    "SEM VALIDADE", "NAO POSSUI", "NAO SE APLICA", "NAO APLICAVEL", "NAO HA",
    "NAO EXIGE", "NAO TEM", "NAO PREVISTA", "NAO PREVISTO",
    "INDETERMINAD", "PERMANENTE", "VITALICI", "UNICO", "UNICA",
)


def _norm(valor):
    """Sem acentos, maiusculo, sem espacos extras."""
    if valor is None:
        return ""
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.upper().split())


def _texto(valor):
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def interpretar_validade(valor):
    """
    Converte o texto de validade/reciclagem em meses.
    Retorna (meses, avisos). meses=None significa "sem validade".
    """
    avisos = []

    if valor is None or str(valor).strip() == "":
        return None, ["validade vazia: cadastrada como sem validade"]

    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        meses = int(round(valor))
        if meses <= 0:
            return None, ["validade 0: cadastrada como sem validade"]
        return meses, [f"numero sem unidade ({meses}): considerado em MESES, confira"]

    original = str(valor).strip()
    txt = _norm(original)

    if len(original) > 40:
        avisos.append("texto de validade longo, confira o valor")

    # 1) numero + unidade (ex: "2 anos", "12 meses", "1,5 anos")
    encontrados = []
    for num, unidade in re.findall(r"(\d+(?:[.,]\d+)?)\s*(ANOS?|MESES|MES)\b", txt):
        n = float(num.replace(",", "."))
        meses = int(round(n * 12)) if unidade.startswith("ANO") else int(round(n))
        if meses > 0:
            encontrados.append(meses)
    if encontrados:
        if len(set(encontrados)) > 1:
            avisos.append(f"mais de um prazo no texto ('{original}'): usado {encontrados[0]} meses")
        return encontrados[0], avisos

    # 2) palavras (anual, bienal...)
    for palavra, meses in PALAVRAS_PERIODO.items():
        if re.search(r"\b" + palavra + r"\b", txt):
            return meses, avisos

    # 3) sem validade
    if txt in ("-", "--", "N/A", "NA", "NAO") or any(f in txt for f in FRASES_SEM_VALIDADE):
        return None, avisos

    avisos.append(f"validade nao reconhecida ('{original}'): cadastrada como sem validade, revise")
    return None, avisos


def _achar_cabecalho(ws):
    """Procura o cabecalho nas 15 primeiras linhas. Retorna (linha, colunas)."""
    for idx, row in enumerate(ws.iter_rows(min_row=1, max_row=15, values_only=True), start=1):
        norm = [_norm(c) for c in row]
        colunas = {}
        for i, c in enumerate(norm):
            if not c:
                continue
            if "OBSERV" in c:
                colunas.setdefault("obs", i)
            elif "CARGA" in c:
                colunas.setdefault("carga", i)
            elif "VALIDADE" in c or "RECICLAGEM" in c:
                colunas.setdefault("validade", i)
            elif "NOME" in c or "CURSO" in c or "TREINAMENTO" in c:
                colunas.setdefault("curso", i)
            elif c.startswith("NORMA"):
                colunas.setdefault("norma", i)
        if "curso" in colunas and ("norma" in colunas or "validade" in colunas):
            return idx, colunas
    return None, {}


def _montar_nome(norma, curso):
    norma, curso = norma.strip(), curso.strip()
    if norma and curso:
        if _norm(curso).startswith(_norm(norma)):
            return curso
        return f"{norma} - {curso}"
    return norma or curso


def ler_planilha_catalogo(stream):
    """
    Le a planilha de NRs. Retorna (linhas, erros, avisos).
    """
    wb = load_workbook(stream, data_only=True)

    ws, linha_cab, colunas = None, None, {}
    for planilha in wb.worksheets:
        linha_cab, colunas = _achar_cabecalho(planilha)
        if linha_cab:
            ws = planilha
            break

    if ws is None:
        raise ValueError(
            "Cabecalho nao encontrado. A planilha precisa ter as colunas "
            "'Normas NR' e 'Nome do curso/treinamento'."
        )

    def pegar(row, chave):
        i = colunas.get(chave)
        if i is None or i >= len(row):
            return None
        return row[i]

    linhas, erros, avisos = [], [], []
    ultima_norma = ""

    for num, row in enumerate(
        ws.iter_rows(min_row=linha_cab + 1, values_only=True), start=linha_cab + 1
    ):
        if all(c is None or str(c).strip() == "" for c in row):
            continue

        norma = _texto(pegar(row, "norma"))
        if norma:
            ultima_norma = norma          # celulas mescladas: repete a norma
        else:
            norma = ultima_norma

        curso = _texto(pegar(row, "curso"))
        carga = _texto(pegar(row, "carga"))
        bruto_validade = pegar(row, "validade")
        obs = _texto(pegar(row, "obs"))

        # linha so com a norma (titulo de grupo): nao cria curso
        if not curso and not carga and not obs and \
                (bruto_validade is None or str(bruto_validade).strip() == ""):
            continue

        nome = _montar_nome(norma, curso)
        if not nome:
            erros.append(f"Linha {num}: sem norma e sem nome do curso.")
            continue

        if len(nome) > 100:
            avisos.append(f"Linha {num}: nome com mais de 100 caracteres, foi cortado.")
            nome = nome[:100]

        if carga and isinstance(pegar(row, "carga"), (int, float)):
            carga = f"{carga}h"
        if len(carga) > 50:
            avisos.append(f"Linha {num} ({nome}): carga horaria cortada em 50 caracteres.")
            carga = carga[:50]

        meses, avisos_val = interpretar_validade(bruto_validade)
        for a in avisos_val:
            avisos.append(f"Linha {num} ({nome}): {a}.")

        linhas.append({
            "linha": num,
            "nome_curso": nome,
            "carga_horaria": carga or None,
            "validade_meses": meses,
            "descricao": obs or None,
        })

    return linhas, erros, avisos


def gravar_catalogo(linhas, atualizar=False):
    """
    Grava no catalogo. Duplicado = mesmo nome de curso (sem acento/maiuscula).
    Retorna dict com inseridos, atualizados, recalculados e ignorados (lista de textos).
    """
    existentes = {_norm(c.nome_curso): c for c in CatalogoNR.query.all()}
    novos = set()
    inseridos = atualizados = 0
    ignorados = []
    para_recalcular = []

    for l in linhas:
        chave = _norm(l["nome_curso"])

        if chave in novos:
            ignorados.append(f"Linha {l['linha']} ({l['nome_curso']}): repetida na planilha.")
            continue

        if chave in existentes:
            if not atualizar:
                ignorados.append(f"Linha {l['linha']} ({l['nome_curso']}): ja existe no catalogo.")
                continue
            c = existentes[chave]
            if c.validade_meses != l["validade_meses"]:
                para_recalcular.append(c)
            c.carga_horaria = l["carga_horaria"]
            c.validade_meses = l["validade_meses"]
            c.descricao = l["descricao"]
            atualizados += 1
            continue

        c = CatalogoNR(
            nome_curso=l["nome_curso"],
            carga_horaria=l["carga_horaria"],
            validade_meses=l["validade_meses"],
            descricao=l["descricao"],
        )
        db.session.add(c)
        existentes[chave] = c
        novos.add(chave)
        inseridos += 1

    db.session.commit()

    # validade mudou: recalcula o vencimento dos cursos ja lancados
    recalculados = 0
    for c in para_recalcular:
        for reg in ColaboradorCurso.query.filter_by(catalogo_nr_id=c.id).all():
            reg.calcular_vencimento(c)
            recalculados += 1
    if recalculados:
        db.session.commit()

    return {
        "inseridos": inseridos,
        "atualizados": atualizados,
        "recalculados": recalculados,
        "ignorados": ignorados,
    }
