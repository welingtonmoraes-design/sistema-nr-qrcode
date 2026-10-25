from flask import Blueprint, render_template, redirect, url_for, flash, request
from models import db, Colaborador
from forms import ColaboradorForm
from flask_login import login_required

bp_colaboradores = Blueprint(
    "colaboradores", __name__, url_prefix="/colaboradores")


@bp_colaboradores.route("/")
@login_required
def listar():
    busca = request.args.get("busca", "")
    query = Colaborador.query
    if busca:
        query = query.filter(Colaborador.nome.ilike(f"%{busca}%"))
    colaboradores = query.order_by(Colaborador.nome).all()
    return render_template("colaboradores/listar.html", colaboradores=colaboradores, busca=busca)


@bp_colaboradores.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    form = ColaboradorForm()
    if form.validate_on_submit():
        existe = Colaborador.query.filter_by(cpf=form.cpf.data).first()
        if existe:
            flash("CPF já cadastrado!", "danger")
            return render_template("colaboradores/form.html", form=form)

        colaborador = Colaborador(
            nome=form.nome.data,
            cpf=form.cpf.data,
            matricula=form.matricula.data,
            ativo=form.ativo.data
        )
        db.session.add(colaborador)
        db.session.commit()
        flash("Colaborador cadastrado com sucesso!", "success")
        return redirect(url_for("colaboradores.listar"))
    return render_template("colaboradores/form.html", form=form)


@bp_colaboradores.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar(id):
    colaborador = Colaborador.query.get_or_404(id)
    form = ColaboradorForm(obj=colaborador)
    if form.validate_on_submit():
        colaborador.nome = form.nome.data
        colaborador.cpf = form.cpf.data
        colaborador.matricula = form.matricula.data
        colaborador.ativo = form.ativo.data
        db.session.commit()
        flash("Colaborador atualizado!", "success")
        return redirect(url_for("colaboradores.listar"))
    return render_template("colaboradores/form.html", form=form, colaborador=colaborador)


@bp_colaboradores.route("/excluir/<int:id>", methods=["POST"])
@login_required
def excluir(id):
    colaborador = Colaborador.query.get_or_404(id)
    db.session.delete(colaborador)
    db.session.commit()
    flash("Colaborador excluído.", "warning")
    return redirect(url_for("colaboradores.listar"))


@bp_colaboradores.route("/<int:id>")
@login_required
def detalhes(id):
    colaborador = Colaborador.query.get_or_404(id)
    cursos_info = [
        {"curso": c, "status": c.status()[0], "dias_restantes": c.status()[1]}
        for c in colaborador.cursos
    ]
    return render_template("colaboradores/detalhes.html", colaborador=colaborador, cursos_info=cursos_info)
