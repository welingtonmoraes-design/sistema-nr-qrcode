from flask import Blueprint, render_template, redirect, url_for, flash
from models import db, CatalogoNR, ColaboradorCurso
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
        validade = None if form.sem_validade.data else form.validade_meses.data

        if not form.sem_validade.data and not form.validade_meses.data:
            flash("Informe a validade em meses, ou marque 'Sem validade'.", "danger")
            return render_template("catalogo_nr/form.html", form=form)

        curso = CatalogoNR(
            nome_curso=form.nome_curso.data,
            validade_meses=validade,
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

    # No GET (primeira exibicao), marca o checkbox se o curso atual
    # nao possui validade definida.
    if not form.is_submitted():
        form.sem_validade.data = curso.validade_meses is None

    if form.validate_on_submit():
        validade = None if form.sem_validade.data else form.validade_meses.data

        if not form.sem_validade.data and not form.validade_meses.data:
            flash("Informe a validade em meses, ou marque 'Sem validade'.", "danger")
            return render_template("catalogo_nr/form.html", form=form, curso=curso)

        curso.nome_curso = form.nome_curso.data
        curso.validade_meses = validade
        curso.descricao = form.descricao.data
        db.session.commit()

        # Recalcula vencimento de todos os cursos vinculados a este catalogo
        registros = ColaboradorCurso.query.filter_by(catalogo_nr_id=curso.id).all()
        for registro in registros:
            registro.calcular_vencimento(curso)
        db.session.commit()

        flash("Catálogo atualizado!", "success")
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
