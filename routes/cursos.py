from datetime import date

from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, send_file, make_response, abort)
from flask_login import login_required

from models import db, Colaborador, CatalogoNR, ColaboradorCurso
from forms import ColaboradorCursoForm, RevalidarCursoForm
from services.certificado_service import aplicar_certificado

bp_cursos = Blueprint("cursos", __name__, url_prefix="/cursos")


def _filtros():
    """Filtros e ordenacao do painel (mantidos ao voltar da edicao)."""
    return {
        "nome": request.args.get("nome", "").strip(),
        "curso": request.args.get("curso", "").strip(),
        "condicao": request.args.get("condicao", "").strip(),
        "ordem": request.args.get("ordem", "").strip(),
        "direcao": request.args.get("direcao", "").strip(),
    }


def _voltar_painel():
    return redirect(url_for("nrs.painel", **_filtros()))


def _preparar_form(form, colaborador_atual_id=None):
    colaboradores = Colaborador.query.filter(
        (Colaborador.ativo == True) | (Colaborador.id == colaborador_atual_id)  # noqa: E712
    ).order_by(Colaborador.nome).all()
    form.colaborador_id.choices = [(c.id, c.nome) for c in colaboradores]
    form.catalogo_nr_id.choices = [
        (c.id, c.nome_curso) for c in CatalogoNR.query.order_by(CatalogoNR.nome_curso).all()
    ]


@bp_cursos.route("/gerar-qrcodes")
@login_required
def gerar_qrcodes():
    # O gerador agora fica na pagina inicial (todos os treinamentos).
    return redirect(url_for("qrcodes.gerar"))


def novo():
    form = ColaboradorCursoForm()
    _preparar_form(form)

    if form.validate_on_submit():
        catalogo = db.session.get(CatalogoNR, form.catalogo_nr_id.data)
        registro = ColaboradorCurso(
            colaborador_id=form.colaborador_id.data,
            catalogo_nr_id=form.catalogo_nr_id.data,
            data_realizado=form.data_realizado.data,
        )
        try:
            aplicar_certificado(registro, form.certificado.data)
        except ValueError as e:
            flash(str(e), "danger")
            return render_template("cursos/form.html", form=form, filtros=_filtros())

        registro.calcular_vencimento(catalogo)
        db.session.add(registro)
        db.session.commit()
        flash("Treinamento cadastrado!", "success")
        return redirect(url_for("nrs.painel"))

    return render_template("cursos/form.html", form=form, filtros=_filtros())


@bp_cursos.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar(id):
    registro = db.get_or_404(ColaboradorCurso, id)
    form = ColaboradorCursoForm(obj=registro)
    _preparar_form(form, colaborador_atual_id=registro.colaborador_id)

    if form.validate_on_submit():
        catalogo = db.session.get(CatalogoNR, form.catalogo_nr_id.data)
        registro.colaborador_id = form.colaborador_id.data
        registro.catalogo_nr_id = form.catalogo_nr_id.data
        registro.data_realizado = form.data_realizado.data
        try:
            aplicar_certificado(registro, form.certificado.data,
                                remover=form.remover_certificado.data)
        except ValueError as e:
            db.session.rollback()
            flash(str(e), "danger")
            return render_template("cursos/form.html", form=form, registro=registro,
                                   filtros=_filtros())

        registro.calcular_vencimento(catalogo)
        db.session.commit()
        flash("Treinamento atualizado!", "success")
        return _voltar_painel()

    return render_template("cursos/form.html", form=form, registro=registro,
                           filtros=_filtros())


@bp_cursos.route("/revalidar/<int:id>", methods=["GET", "POST"])
@login_required
def revalidar(id):
    """Informa a nova data de realizacao (e, se houver, o novo certificado)."""
    registro = db.get_or_404(ColaboradorCurso, id)
    form = RevalidarCursoForm()

    if form.validate_on_submit():
        registro.data_realizado = form.data_realizado.data
        try:
            aplicar_certificado(registro, form.certificado.data)
        except ValueError as e:
            db.session.rollback()
            flash(str(e), "danger")
            return render_template("cursos/revalidar.html", form=form,
                                   registro=registro, filtros=_filtros())

        registro.calcular_vencimento(registro.catalogo)
        db.session.commit()
        venc = registro.data_vencimento
        flash(
            f"Treinamento de {registro.colaborador.nome} revalidado. "
            f"Novo vencimento: {venc.strftime('%d/%m/%Y') if venc else 'sem validade'}.",
            "success"
        )
        return _voltar_painel()

    if not form.is_submitted():
        form.data_realizado.data = date.today()

    return render_template("cursos/revalidar.html", form=form, registro=registro,
                           filtros=_filtros())


@bp_cursos.route("/excluir/<int:id>", methods=["POST"])
@login_required
def excluir(id):
    registro = db.get_or_404(ColaboradorCurso, id)
    db.session.delete(registro)
    db.session.commit()
    flash("Treinamento excluído.", "warning")
    return _voltar_painel()


@bp_cursos.route("/certificado/<int:id>")
@login_required
def certificado(id):
    """Exibe (ou baixa, com ?baixar=1) o certificado. Somente usuarios logados."""
    registro = db.get_or_404(ColaboradorCurso, id)
    if not registro.certificado_nome or not registro.certificado_dados:
        abort(404)

    resposta = make_response(bytes(registro.certificado_dados))
    resposta.headers["Content-Type"] = registro.certificado_tipo or "application/octet-stream"
    disposicao = "attachment" if request.args.get("baixar") else "inline"
    resposta.headers["Content-Disposition"] = f'{disposicao}; filename="{registro.certificado_nome}"'
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["Cache-Control"] = "private, max-age=300"
    return resposta


@bp_cursos.route("/gerar-qrcodes", methods=["GET", "POST"])
@login_required
def gerar_qrcodes():
    from services.qrcode_service import montar_folha_a4, exportar_paginas_pdf

    if request.method == "POST":
        ids = request.form.getlist("colaboradores")
        if not ids:
            flash("Selecione ao menos um colaborador.", "danger")
            return redirect(url_for("cursos.gerar_qrcodes"))

        colaboradores = Colaborador.query.filter(Colaborador.id.in_(ids)).all()
        paginas = montar_folha_a4(colaboradores)
        caminho_pdf = exportar_paginas_pdf(paginas, "static/qrcodes/lote_qrcodes.pdf")
        return send_file(caminho_pdf, as_attachment=True)

    colaboradores = Colaborador.query.filter_by(ativo=True).order_by(Colaborador.nome).all()
    return render_template("cursos/gerar_qrcodes.html", colaboradores=colaboradores)
