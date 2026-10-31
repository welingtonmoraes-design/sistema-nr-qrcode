import unicodedata
from datetime import date

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from models import db, TreinamentoPTLoto
from forms import TreinamentoPTLotoForm, ImportarExcelForm, RevalidarForm
from services.pt_loto_service import ler_planilha, gravar_linhas

bp_pt_loto = Blueprint("pt_loto", __name__, url_prefix="/pt-loto")

SEM_EMPRESA = "__SEM_EMPRESA__"


def _norm(texto):
    """Minusculo, sem acentos e sem espacos duplicados (para comparar textos)."""
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.casefold().split())


def _filtros():
    """Filtros atuais vindos da URL (mantidos ao editar, revalidar e excluir)."""
    return {
        "nome": request.args.get("nome", "").strip(),
        "empresa": request.args.get("empresa", "").strip(),
        "condicao": request.args.get("condicao", "").strip(),
    }


def _voltar_lista():
    return redirect(url_for("pt_loto.index", **_filtros()))


@bp_pt_loto.route("/")
@login_required
def index():
    filtros = _filtros()
    nome = filtros["nome"]
    empresa = filtros["empresa"]
    filtro = filtros["condicao"]   # "" (em vigor) | VALIDO | REAVALIAR | VENCIDO | TODOS

    todos = TreinamentoPTLoto.query.order_by(TreinamentoPTLoto.nome).all()

    # Lista de empresas para o filtro (sem duplicar por maiuscula/acento)
    mapa_empresas = {}
    for r in todos:
        emp = (r.empresa or "").strip()
        if emp:
            mapa_empresas.setdefault(_norm(emp), emp)
    lista_empresas = sorted(mapa_empresas.values(), key=_norm)
    tem_sem_empresa = any(not (r.empresa or "").strip() for r in todos)

    termos = _norm(nome).split()
    empresa_norm = _norm(empresa)

    contagem = {"VALIDO": 0, "REAVALIAR": 0, "VENCIDO": 0}
    itens = []
    total = 0

    for r in todos:
        # --- filtro por nome (parcial ou completo, todas as palavras) ---
        if termos:
            nome_norm = _norm(r.nome)
            if not all(t in nome_norm for t in termos):
                continue

        # --- filtro por empresa ---
        if empresa:
            if empresa == SEM_EMPRESA:
                if (r.empresa or "").strip():
                    continue
            elif _norm(r.empresa) != empresa_norm:
                continue

        total += 1
        codigo, texto, dias = r.condicao()
        contagem[codigo] += 1

        if filtro == "":
            visivel = codigo != "VENCIDO"      # padrao: oculta vencidos
        elif filtro == "TODOS":
            visivel = True
        else:
            visivel = (codigo == filtro)

        if visivel:
            itens.append({"r": r, "codigo": codigo, "texto": texto, "dias": dias})

    return render_template(
        "pt_loto/index.html",
        itens=itens, contagem=contagem, total=total,
        em_vigor=contagem["VALIDO"] + contagem["REAVALIAR"],
        nome=nome, empresa=empresa, filtro=filtro,
        lista_empresas=lista_empresas, tem_sem_empresa=tem_sem_empresa,
        SEM_EMPRESA=SEM_EMPRESA,
        filtros_ativos=bool(nome or empresa or filtro),
    )


@bp_pt_loto.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    form = TreinamentoPTLotoForm()
    if form.validate_on_submit():
        registro = TreinamentoPTLoto(
            numero=form.numero.data,
            nome=form.nome.data,
            matricula=form.matricula.data,
            empresa=form.empresa.data,
            data_treinamento=form.data_treinamento.data,
            instrutor=form.instrutor.data,
        )
        db.session.add(registro)
        db.session.commit()
        flash("Registro cadastrado!", "success")
        return redirect(url_for("pt_loto.index"))
    return render_template("pt_loto/form.html", form=form, filtros=_filtros())


@bp_pt_loto.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar(id):
    registro = db.get_or_404(TreinamentoPTLoto, id)
    form = TreinamentoPTLotoForm(obj=registro)
    if form.validate_on_submit():
        registro.numero = form.numero.data
        registro.nome = form.nome.data
        registro.matricula = form.matricula.data
        registro.empresa = form.empresa.data
        registro.data_treinamento = form.data_treinamento.data
        registro.instrutor = form.instrutor.data
        db.session.commit()
        flash("Registro atualizado!", "success")
        return _voltar_lista()
    return render_template("pt_loto/form.html", form=form, registro=registro, filtros=_filtros())


@bp_pt_loto.route("/revalidar/<int:id>", methods=["GET", "POST"])
@login_required
def revalidar(id):
    """Atualiza a data do treinamento (e opcionalmente o instrutor) para revalidar."""
    registro = db.get_or_404(TreinamentoPTLoto, id)

    form = RevalidarForm()
    if form.validate_on_submit():
        registro.data_treinamento = form.data_treinamento.data
        if form.instrutor.data:
            registro.instrutor = form.instrutor.data
        db.session.commit()
        flash(
            f"Treinamento de {registro.nome} revalidado. "
            f"Nova validade: {registro.data_validade.strftime('%d/%m/%Y')}.",
            "success"
        )
        return _voltar_lista()

    if not form.is_submitted():
        form.data_treinamento.data = date.today()
        form.instrutor.data = registro.instrutor

    return render_template(
        "pt_loto/revalidar.html",
        form=form, registro=registro, filtros=_filtros()
    )


@bp_pt_loto.route("/excluir/<int:id>", methods=["POST"])
@login_required
def excluir(id):
    registro = db.get_or_404(TreinamentoPTLoto, id)
    db.session.delete(registro)
    db.session.commit()
    flash("Registro excluído.", "warning")
    return _voltar_lista()


@bp_pt_loto.route("/importar", methods=["GET", "POST"])
@login_required
def importar():
    form = ImportarExcelForm()
    erros = []
    if form.validate_on_submit():
        try:
            linhas, erros = ler_planilha(form.arquivo.data.stream)
            inseridos, duplicados = gravar_linhas(linhas, substituir=form.substituir.data)
            flash(
                f"Importação concluída: {inseridos} registro(s) inserido(s), "
                f"{duplicados} duplicado(s) ignorado(s), {len(erros)} linha(s) com erro.",
                "success" if inseridos else "warning"
            )
            if not erros:
                return redirect(url_for("pt_loto.index"))
        except Exception as e:
            db.session.rollback()
            flash(f"Não foi possível importar: {e}", "danger")
    return render_template("pt_loto/importar.html", form=form, erros=erros)


@bp_pt_loto.route("/criar-tabelas")
@login_required
def criar_tabelas():
    """Cria apenas as tabelas que ainda nao existem (NAO apaga dados). Somente admin."""
    if current_user.perfil != "admin":
        flash("Acesso restrito a administradores.", "danger")
        return redirect(url_for("pt_loto.index"))
    db.create_all()
    flash("Tabelas verificadas/criadas com sucesso.", "success")
    return redirect(url_for("pt_loto.index"))
