from flask import Blueprint, render_template, redirect, url_for, flash
from models import db, ColaboradorCurso, Colaborador, CatalogoNR
from forms import ColaboradorCursoForm
from flask_login import login_required

bp_cursos = Blueprint("cursos", __name__, url_prefix="/cursos")


@bp_cursos.route("/")
@login_required
def listar():
    registros = ColaboradorCurso.query.all()
    dados = []
    for r in registros:
        status, dias = r.status()
        dados.append({"registro": r, "status": status, "dias_restantes": dias})
    return render_template("cursos/listar.html", dados=dados)


@bp_cursos.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    form = ColaboradorCursoForm()
    form.colaborador_id.choices = [(c.id, c.nome)
                                   for c in Colaborador.query.filter_by(ativo=True)]
    form.catalogo_nr_id.choices = [(c.id, c.nome_curso)
                                   for c in CatalogoNR.query]

    if form.validate_on_submit():
        # Busca o catálogo ANTES de criar o registro, para evitar
        # o bug de relationship None em objetos ainda não persistidos.
        catalogo = CatalogoNR.query.get(form.catalogo_nr_id.data)

        registro = ColaboradorCurso(
            colaborador_id=form.colaborador_id.data,
            catalogo_nr_id=form.catalogo_nr_id.data,
            data_realizado=form.data_realizado.data
        )
        registro.calcular_vencimento(catalogo)  # ✅ passa o objeto já carregado

        db.session.add(registro)
        db.session.commit()
        flash("Curso registrado para o colaborador!", "success")
        return redirect(url_for("cursos.listar"))
    return render_template("cursos/form.html", form=form)


@bp_cursos.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar(id):
    registro = ColaboradorCurso.query.get_or_404(id)
    form = ColaboradorCursoForm(obj=registro)
    form.colaborador_id.choices = [(c.id, c.nome)
                                   for c in Colaborador.query.filter_by(ativo=True)]
    form.catalogo_nr_id.choices = [(c.id, c.nome_curso)
                                   for c in CatalogoNR.query]

    if form.validate_on_submit():
        catalogo = CatalogoNR.query.get(form.catalogo_nr_id.data)

        registro.colaborador_id = form.colaborador_id.data
        registro.catalogo_nr_id = form.catalogo_nr_id.data
        registro.data_realizado = form.data_realizado.data
        registro.calcular_vencimento(catalogo)  # ✅ idem aqui

        db.session.commit()
        flash("Registro atualizado!", "success")
        return redirect(url_for("cursos.listar"))
    return render_template("cursos/form.html", form=form, registro=registro)


@bp_cursos.route("/excluir/<int:id>", methods=["POST"])
@login_required
def excluir(id):
    registro = ColaboradorCurso.query.get_or_404(id)
    db.session.delete(registro)
    db.session.commit()
    flash("Registro removido.", "warning")
    return redirect(url_for("cursos.listar"))


@bp_cursos.route("/gerar-qrcodes", methods=["GET", "POST"])
@login_required
def gerar_qrcodes():
    from flask import request, send_file
    from services.qrcode_service import montar_folha_a4, exportar_paginas_pdf

    if request_method_is_post := (request.method == "POST"):
        ids = request.form.getlist("colaboradores")
        if not ids:
            flash("Selecione ao menos um colaborador.", "danger")
            return redirect(url_for("cursos.gerar_qrcodes"))

        colaboradores = Colaborador.query.filter(Colaborador.id.in_(ids)).all()
        paginas = montar_folha_a4(colaboradores)
        caminho_pdf = exportar_paginas_pdf(
            paginas, "static/qrcodes/lote_qrcodes.pdf")
        return send_file(caminho_pdf, as_attachment=True)

    colaboradores = Colaborador.query.filter_by(
        ativo=True).order_by(Colaborador.nome).all()
    return render_template("cursos/gerar_qrcodes.html", colaboradores=colaboradores)
