from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import inspect, text

from models import db, CatalogoNR, ColaboradorCurso
from forms import CatalogoNRForm, ImportarCatalogoForm
from services.catalogo_service import ler_planilha_catalogo, gravar_catalogo

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
        if not form.sem_validade.data and not form.validade_meses.data:
            flash("Informe a validade em meses, ou marque 'Sem validade'.", "danger")
            return render_template("catalogo_nr/form.html", form=form)

        validade = None if form.sem_validade.data else form.validade_meses.data
        curso = CatalogoNR(
            nome_curso=form.nome_curso.data,
            carga_horaria=form.carga_horaria.data or None,
            validade_meses=validade,
            descricao=form.descricao.data or None,
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

    if not form.is_submitted():
        form.sem_validade.data = curso.validade_meses is None

    if form.validate_on_submit():
        if not form.sem_validade.data and not form.validade_meses.data:
            flash("Informe a validade em meses, ou marque 'Sem validade'.", "danger")
            return render_template("catalogo_nr/form.html", form=form, curso=curso)

        curso.nome_curso = form.nome_curso.data
        curso.carga_horaria = form.carga_horaria.data or None
        curso.validade_meses = None if form.sem_validade.data else form.validade_meses.data
        curso.descricao = form.descricao.data or None
        db.session.commit()

        for registro in ColaboradorCurso.query.filter_by(catalogo_nr_id=curso.id).all():
            registro.calcular_vencimento(curso)
        db.session.commit()

        flash("Catálogo atualizado!", "success")
        return redirect(url_for("catalogo_nr.listar"))
    return render_template("catalogo_nr/form.html", form=form, curso=curso)


@bp_catalogo.route("/excluir/<int:id>", methods=["POST"])
@login_required
def excluir(id):
    curso = CatalogoNR.query.get_or_404(id)

    em_uso = ColaboradorCurso.query.filter_by(catalogo_nr_id=curso.id).count()
    if em_uso:
        flash(
            f"Não é possível excluir '{curso.nome_curso}': há {em_uso} lançamento(s) "
            f"de colaboradores ligado(s) a este curso. Remova ou transfira esses "
            f"lançamentos antes.",
            "danger"
        )
        return redirect(url_for("catalogo_nr.listar"))

    try:
        db.session.delete(curso)
        db.session.commit()
        flash("Curso removido do catálogo.", "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"Não foi possível excluir: {e}", "danger")
    return redirect(url_for("catalogo_nr.listar"))


@bp_catalogo.route("/importar", methods=["GET", "POST"])
@login_required
def importar():
    form = ImportarCatalogoForm()
    resultado, erros, avisos = None, [], []

    if form.validate_on_submit():
        try:
            linhas, erros, avisos = ler_planilha_catalogo(form.arquivo.data.stream)
            resultado = gravar_catalogo(linhas, atualizar=form.atualizar.data)
            flash(
                f"{len(linhas) + len(erros)} linha(s) com dados: "
                f"{resultado['inseridos']} inserida(s), {resultado['atualizados']} atualizada(s), "
                f"{len(resultado['ignorados'])} ignorada(s), {len(erros)} com erro.",
                "success" if (resultado["inseridos"] or resultado["atualizados"]) else "warning"
            )
        except Exception as e:
            db.session.rollback()
            msg = str(e)
            if "carga_horaria" in msg or "UndefinedColumn" in msg:
                msg += " | Execute antes /catalogo-nr/atualizar-estrutura (admin)."
            flash(f"Não foi possível importar: {msg}", "danger")

    return render_template(
        "catalogo_nr/importar.html",
        form=form, resultado=resultado, erros=erros, avisos=avisos
    )


@bp_catalogo.route("/atualizar-estrutura")
@login_required
def atualizar_estrutura():
    """
    Ajusta o banco SEM apagar dados:
    - catalogo_nr: carga_horaria e descricao como TEXT
    - colaborador_curso: colunas do certificado
    - colaboradores: coluna empresa
    Somente admin. Pode ser executada mais de uma vez.
    """
    if current_user.perfil != "admin":
        flash("Acesso restrito a administradores.", "danger")
        return redirect(url_for("catalogo_nr.listar"))

    try:
        insp = inspect(db.engine)
        col_cat = {c["name"] for c in insp.get_columns("catalogo_nr")}
        col_cc = {c["name"] for c in insp.get_columns("colaborador_curso")}
        col_colab = {c["name"] for c in insp.get_columns("colaboradores")}
        postgres = db.engine.dialect.name == "postgresql"
        tipo_blob = "BYTEA" if postgres else "BLOB"

        with db.engine.begin() as conn:
            if "carga_horaria" not in col_cat:
                conn.execute(text("ALTER TABLE catalogo_nr ADD COLUMN carga_horaria VARCHAR(50)"))
            if postgres:
                conn.execute(text("ALTER TABLE catalogo_nr ALTER COLUMN descricao TYPE TEXT"))

            if "certificado_nome" not in col_cc:
                conn.execute(text("ALTER TABLE colaborador_curso ADD COLUMN certificado_nome VARCHAR(255)"))
            if "certificado_tipo" not in col_cc:
                conn.execute(text("ALTER TABLE colaborador_curso ADD COLUMN certificado_tipo VARCHAR(100)"))
            if "certificado_dados" not in col_cc:
                conn.execute(text(f"ALTER TABLE colaborador_curso ADD COLUMN certificado_dados {tipo_blob}"))

            if "empresa" not in col_colab:
                conn.execute(text("ALTER TABLE colaboradores ADD COLUMN empresa VARCHAR(150)"))

        flash("Estrutura do banco atualizada com sucesso.", "success")
    except Exception as e:
        flash(f"Erro ao atualizar a estrutura: {e}", "danger")

    return redirect(url_for("catalogo_nr.listar"))
