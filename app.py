from routes.cursos import bp_cursos
from routes.catalogo_nr import bp_catalogo
from routes.usuarios import bp_usuarios
from routes.colaboradores import bp_colaboradores
from routes.auth import bp_auth
from flask import Flask, render_template, session
from flask_login import LoginManager, login_required, current_user
from models import db, Usuario, ColaboradorCurso
from services.validade_service import listar_cursos_criticos
from flask import render_template
from models import Colaborador


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///sistema_nr.db"
app.config["SECRET_KEY"] = "troque-esta-chave-em-producao"

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"


@app.route("/verificar/<cpf>")
def verificar_colaborador(cpf):
    colaborador = Colaborador.query.filter_by(cpf=cpf).first_or_404()
    cursos_info = [
        {"curso": c, "status": c.status()[0], "dias_restantes": c.status()[1]}
        for c in colaborador.cursos
    ]
    return render_template("verificacao_publica.html", colaborador=colaborador, cursos_info=cursos_info)


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


# --- Blueprints ---

app.register_blueprint(bp_auth)
app.register_blueprint(bp_colaboradores)
app.register_blueprint(bp_usuarios)
app.register_blueprint(bp_catalogo)
app.register_blueprint(bp_cursos)


@app.before_request
def alerta_vencimento():
    if current_user.is_authenticated:
        session["alertas_nr"] = listar_cursos_criticos(ColaboradorCurso)


@app.route("/")
@login_required
def home():
    alertas = session.get("alertas_nr", [])
    return render_template("home.html", alertas=alertas)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
