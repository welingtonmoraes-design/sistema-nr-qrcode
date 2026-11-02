import os
from flask import Flask, render_template, session, request
from flask_login import LoginManager, login_required, current_user
from services.validade_service import listar_cursos_criticos
from models import db, Usuario, ColaboradorCurso, Colaborador, TreinamentoPTLoto
from services.pt_loto_service import buscar_pt_colaborador, ultimo_pt_da_pessoa

from modulos import MODULOS
from routes.qrcodes import bp_qrcodes
app.register_blueprint(bp_qrcodes)
app = Flask(__name__)

# --- Configuração do Banco de Dados ---
database_url = os.environ.get("DATABASE_URL", "sqlite:///sistema_nr.db")

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

if database_url.startswith("postgresql://") and "+psycopg" not in database_url:
    database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024 # aceita fotos de celular (ate 12 MB)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))


# --- Blueprints ---
from routes.auth import bp_auth
from routes.colaboradores import bp_colaboradores
from routes.usuarios import bp_usuarios
from routes.catalogo_nr import bp_catalogo
from routes.cursos import bp_cursos
from routes.nrs import bp_nrs
from routes.pt_loto import bp_pt_loto

app.register_blueprint(bp_auth)
app.register_blueprint(bp_colaboradores)
app.register_blueprint(bp_usuarios)
app.register_blueprint(bp_catalogo)
app.register_blueprint(bp_cursos)
app.register_blueprint(bp_nrs)
app.register_blueprint(bp_pt_loto)


@app.context_processor
def injetar_modulos():
    """Disponibiliza a lista de modulos e o modulo atual em todos os templates."""
    bp = request.blueprint
    atual = next((m for m in MODULOS if bp in m["blueprints"]), None)
    return {"MODULOS": MODULOS, "modulo_atual": atual}


@app.before_request
def alerta_vencimento():
    if request.endpoint in ("static", "catalogo_nr.atualizar_estrutura"):
        return
    if current_user.is_authenticated:
        try:
            session["alertas_nr"] = listar_cursos_criticos(ColaboradorCurso)
        except Exception:
            db.session.rollback()
            session["alertas_nr"] = []


@app.route("/")
@login_required
def home():
    """Homepage do Sistema de Controle de EHS (hub de modulos)."""
    alertas = session.get("alertas_nr", [])
    return render_template("home.html", alertas=alertas)


def _pt_info(pt):
    """Dados do PT para a pagina publica (ou None se nao houver registro)."""
    if not pt:
        return None
    codigo, texto, dias = pt.condicao()
    return {"registro": pt, "codigo": codigo, "texto": texto, "dias": dias}


@app.route("/verificar/<cpf>")
def verificar_colaborador(cpf):
    """
    Rota publica (sem login) para verificacao via QR Code.
    NAO ALTERAR este caminho: QR Codes ja impressos dependem dele.
    """
    colaborador = Colaborador.query.filter_by(cpf=cpf).first_or_404()

    cursos_info = []
    for c in colaborador.cursos:
        status, dias = c.status()
        cursos_info.append({"curso": c, "status": status, "dias_restantes": dias})

    return render_template(
        "verificacao_publica.html",
        nome=colaborador.nome,
        cursos_info=cursos_info,
        pt_info=_pt_info(buscar_pt_colaborador(colaborador)),
        mostrar_nr=True,
    )


@app.route("/verificar-pt/<int:id>")
def verificar_pt(id):
    """Pagina publica para pessoas que possuem apenas treinamento de PT/LOTO."""
    base = db.get_or_404(TreinamentoPTLoto, id)
    return render_template(
        "verificacao_publica.html",
        nome=base.nome,
        cursos_info=[],
        pt_info=_pt_info(ultimo_pt_da_pessoa(base)),
        mostrar_nr=False,
    )    
@app.errorhandler(413)
def arquivo_muito_grande(e):
    return "Arquivo muito grande (máximo 12 MB). Volte e envie um arquivo menor.", 413


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
