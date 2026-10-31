from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import or_

from models import db, TreinamentoPTLoto
from forms import TreinamentoPTLotoForm, ImportarExcelForm
from services.pt_loto_service import ler_planilha, gravar_linhas

bp_pt_loto = Blueprint("pt_loto", __name__, url_prefix="/pt-loto")


@bp_pt_loto.route("/")
@login_required
def index():
    busca = request.args.get("busca", "").strip()
    filtro = request.args.get("condicao", "")

    query = TreinamentoPTLoto.query
    if busca:
        like = f"%{busca}%"
        query = query.filter(or_(
            TreinamentoPTLoto.nome.ilike(like),
            TreinamentoPTLoto.matricula.ilike(like),
            TreinamentoPTLoto.empresa.ilike(like),
            TreinamentoPTLoto.instrutor.ilike(like),
        ))

    registros = query.order_by(TreinamentoPTLoto.nome).all()

    contagem = {"VALIDO": 0, "REAVALIAR": 0, "VENCIDO": 0}
    itens = []
    for r in registros:
        codigo, texto, dias = r.condicao()
        contagem[codigo] += 1
        if not filtro or filtro == codigo:
            itens.append({"r": r, "codigo": codigo, "texto": texto, "dias": dias})

    return render_template(
        "pt_loto/index.html",
        itens=itens, contagem=contagem, total=len(registros),
        busca=busca, filtro=filtro
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
    return render_template("pt_loto/form.html", form=form)


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
        return redirect(url_for("pt_loto.index"))
    return render_template("pt_loto/form.html", form=form, registro=registro)


@bp_pt_loto.route("/excluir/<int:id>", methods=["POST"])
@login_required
def excluir(id):
    registro = db.get_or_404(TreinamentoPTLoto, id)
    db.session.delete(registro)
    db.session.commit()
    flash("Registro excluído.", "warning")
    return redirect(url_for("pt_loto.index"))


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
    """
    Cria apenas as tabelas que ainda nao existem (NAO apaga dados).
    Restrito a administradores. Necessario uma vez, por causa da nova tabela.
    """
    if current_user.perfil != "admin":
        flash("Acesso restrito a administradores.", "danger")
        return redirect(url_for("pt_loto.index"))
    db.create_all()
    flash("Tabelas verificadas/criadas com sucesso.", "success")
    return redirect(url_for("pt_loto.index"))
