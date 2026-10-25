from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash
from models import Usuario
from forms import LoginForm

bp_auth = Blueprint("auth", __name__)


@bp_auth.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(sso=form.sso.data).first()
        if usuario and check_password_hash(usuario.senha_hash, form.senha.data):
            login_user(usuario)
            flash(f"Bem-vindo, {usuario.nome}!", "success")
            return redirect(url_for("home"))
        flash("SSO ou senha inválidos.", "danger")
    return render_template("login.html", form=form)


@bp_auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("auth.login"))
