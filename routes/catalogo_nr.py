from flask import Blueprint, render_template, redirect, url_for, flash
from models import db, CatalogoNR
from forms import CatalogoNRForm
from flask_login import login_required

bp_catalogo = Blueprint("catalogo_nr", __name__, url_prefix="/catalogo-nr")


@bp_catalogo.route("/")
@login_required
def listar():
    cursos = CatalogoNR.query.order_by(CatalogoNR.nome_curso).all()
    return render_template("catalogo_nr/listar.html", cursos=cursos)


@bp_catalogo.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    form = CatalogoNRForm()
    if form.validate_on_submit():
        curso = CatalogoNR(
            nome_curso=form.nome_curso.data,
            validade_meses=form.validade_meses.data,
            descricao=form.descricao.data
        )
        db.session.add(curso)
        db.session.commit()
        flash("Curso NR cadastrado no catálogo!", "success")
        return redirect(url_for("catalogo_nr.listar"))
    return render_template("catalogo_nr/form.html", form=form)


@bp_catalogo.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar(id):
    curso = CatalogoNR.query.get_or_404(id)
    form = CatalogoNRForm(obj=curso)
    if form.validate_on_submit():
        curso.nome_curso = form.nome_curso.data
        curso.validade_meses = form.validade_meses.data
        curso.descricao = form.descricao.data
        db.session.commit()
        flash("Catálogo atualizado!", "success")

        # Recalcula vencimento de todos os cursos vinculados a este catálogo
        for registro in curso.colaboradorcurso_set if hasattr(curso, "colaboradorcurso_set") else []:
            registro.calcular_vencimento(curso)
        db.session.commit()

        return redirect(url_for("catalogo_nr.listar"))
    return render_template("catalogo_nr/form.html", form=form, curso=curso)


@bp_catalogo.route("/excluir/<int:id>", methods=["POST"])
@login_required
def excluir(id):
    curso = CatalogoNR.query.get_or_404(id)
    db.session.delete(curso)
    db.session.commit()
    flash("Curso removido do catálogo.", "warning")
    return redirect(url_for("catalogo_nr.listar"))
