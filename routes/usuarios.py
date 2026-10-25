from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from models import db, Usuario
from forms import UsuarioForm

bp_usuarios = Blueprint("usuarios", __name__, url_prefix="/usuarios")


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.perfil != "admin":
            flash("Acesso restrito a administradores.", "danger")
            return redirect(url_for("home"))
        return func(*args, **kwargs)
    return wrapper


@bp_usuarios.route("/")
@login_required
@admin_required
def listar():
    usuarios = Usuario.query.order_by(Usuario.nome).all()
    return render_template("usuarios/listar.html", usuarios=usuarios)


@bp_usuarios.route("/novo", methods=["GET", "POST"])
@login_required
@admin_required
def novo():
    form = UsuarioForm()
    if form.validate_on_submit():
        if not form.senha.data:
            flash("Senha é obrigatória para novo usuário.", "danger")
            return render_template("usuarios/form.html", form=form)

        usuario = Usuario(
            nome=form.nome.data,
            sso=form.sso.data,
            email=form.email.data,
            senha_hash=generate_password_hash(form.senha.data),
            perfil=form.perfil.data
        )
        db.session.add(usuario)
        db.session.commit()
        flash("Usuário cadastrado!", "success")
        return redirect(url_for("usuarios.listar"))
    return render_template("usuarios/form.html", form=form)


@bp_usuarios.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
@admin_required
def editar(id):
    usuario = Usuario.query.get_or_404(id)
    form = UsuarioForm(obj=usuario)
    if form.validate_on_submit():
        usuario.nome = form.nome.data
        usuario.sso = form.sso.data
        usuario.email = form.email.data
        usuario.perfil = form.perfil.data
        if form.senha.data:
            usuario.senha_hash = generate_password_hash(form.senha.data)
        db.session.commit()
        flash("Usuário atualizado!", "success")
        return redirect(url_for("usuarios.listar"))
    return render_template("usuarios/form.html", form=form, usuario=usuario)


@bp_usuarios.route("/excluir/<int:id>", methods=["POST"])
@login_required
@admin_required
def excluir(id):
    usuario = Usuario.query.get_or_404(id)
    db.session.delete(usuario)
    db.session.commit()
    flash("Usuário excluído.", "warning")
    return redirect(url_for("usuarios.listar"))
