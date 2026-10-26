from routes.cursos import bp_cursos
from routes.catalogo_nr import bp_catalogo
from routes.usuarios import bp_usuarios
from routes.colaboradores import bp_colaboradores
from routes.auth import bp_auth
import os
from flask import Flask, render_template, session
from flask_login import LoginManager, login_required, current_user
from models import db, Usuario, ColaboradorCurso, Colaborador
from services.validade_service import listar_cursos_criticos

app = Flask(__name__)

# --- Configuração do Banco de Dados ---
database_url = os.environ.get("DATABASE_URL", "sqlite:///sistema_nr.db")

# Corrige formato antigo do Render (postgres:// -> postgresql://)
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Garante que o driver psycopg2 seja usado explicitamente,
# evitando ambiguidade entre psycopg (v3) e psycopg2
if database_url.startswith("postgresql://") and "+psycopg" not in database_url:
    database_url = database_url.replace(
        "postgresql://", "postgresql+psycopg2://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "troque-esta-chave-em-producao")

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))


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


@app.route("/verificar/<cpf>")
def verificar_colaborador(cpf):
    """
    Rota pública (sem login) para verificação via QR Code.
    Mostra todos os cursos NR e validades do colaborador.
    """
    colaborador = Colaborador.query.filter_by(cpf=cpf).first_or_404()
    cursos_info = [
        {"curso": c, "status": c.status()[0], "dias_restantes": c.status()[1]}
        for c in colaborador.cursos
    ]
    return render_template(
        "verificacao_publica.html",
        colaborador=colaborador,
        cursos_info=cursos_info
    )


# --- Criação automática das tabelas no deploy ---
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
