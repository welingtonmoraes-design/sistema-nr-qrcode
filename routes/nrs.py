import unicodedata

from flask import Blueprint, render_template, request
from flask_login import login_required
from sqlalchemy.orm import joinedload

from models import ColaboradorCurso, CatalogoNR

bp_nrs = Blueprint("nrs", __name__, url_prefix="/nrs")

COLUNAS_ORDEM = {"colaborador", "curso", "realizado", "vencimento", "condicao"}

# status do modelo -> (codigo do painel, texto)
CODIGOS = {
    "VALIDO": ("VALIDO", "Dentro da validade"),
    "SEM_VENCIMENTO": ("VALIDO", "Sem validade"),
    "A_VENCER": ("AVENCER", "Vence em até 30 dias"),
    "VENCIDO": ("VENCIDO", "Vencido"),
}


def _norm(texto):
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.casefold().split())


def _valor_ordenacao(item, chave):
    r = item["r"]
    if chave == "colaborador":
        return _norm(r.colaborador.nome)
    if chave == "curso":
        return _norm(r.catalogo.nome_curso)
    if chave == "realizado":
        return r.data_realizado
    if chave == "vencimento":
        return r.data_vencimento
    if chave == "condicao":
        return item["dias"]
    return _norm(r.colaborador.nome)


def _ordenar(itens, chave, direcao):
    """Registros sem valor (ex.: sem validade) ficam sempre no final."""
    com_valor, vazios = [], []
    for item in itens:
        v = _valor_ordenacao(item, chave)
        if v is None or v == "":
            vazios.append(item)
        else:
            com_valor.append((v, item))
    com_valor.sort(key=lambda x: x[0], reverse=(direcao == "desc"))
    return [i for _, i in com_valor] + vazios


@bp_nrs.route("/")
@login_required
def painel():
    nome = request.args.get("nome", "").strip()
    curso = request.args.get("curso", "").strip()
    filtro = request.args.get("condicao", "").strip()   # "" (em vigor) | VALIDO | AVENCER | VENCIDO | TODOS
    ordem = request.args.get("ordem", "")
    direcao = request.args.get("direcao", "")
    if ordem not in COLUNAS_ORDEM:
        ordem = "colaborador"
    if direcao not in ("asc", "desc"):
        direcao = "asc"

    registros = (
        ColaboradorCurso.query
        .options(joinedload(ColaboradorCurso.colaborador))
        .all()
    )
    lista_cursos = CatalogoNR.query.order_by(CatalogoNR.nome_curso).all()

    termos = _norm(nome).split()
    contagem = {"VALIDO": 0, "AVENCER": 0, "VENCIDO": 0}
    itens = []
    total = 0

    for r in registros:
        if termos:
            nome_norm = _norm(r.colaborador.nome)
            if not all(t in nome_norm for t in termos):
                continue
        if curso and str(r.catalogo_nr_id) != curso:
            continue

        total += 1
        status, dias = r.status()
        codigo, texto = CODIGOS[status]
        contagem[codigo] += 1

        if filtro == "":
            visivel = codigo != "VENCIDO"
        elif filtro == "TODOS":
            visivel = True
        else:
            visivel = (codigo == filtro)

        if visivel:
            itens.append({"r": r, "codigo": codigo, "texto": texto,
                          "status": status, "dias": dias})

    itens = _ordenar(itens, ordem, direcao)

    return render_template(
        "nrs/painel.html",
        itens=itens, contagem=contagem, total=total,
        em_vigor=contagem["VALIDO"] + contagem["AVENCER"],
        nome=nome, curso=curso, filtro=filtro,
        ordem=ordem, direcao=direcao,
        lista_cursos=lista_cursos,
        filtros_ativos=bool(nome or curso or filtro),
    )
