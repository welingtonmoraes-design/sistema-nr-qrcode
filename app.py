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

@app.route("/init-db-secreto-xyz123")
def inicializar_banco_remoto():
    """
    Rota temporária para popular o banco de dados em produção,
    já que o plano Free do Render não oferece Shell interativo.

    ⚠️ IMPORTANTE: remova ou proteja essa rota após o uso único,
    pois ela recria todas as tabelas (apaga dados existentes).
    """
    from werkzeug.security import generate_password_hash
    from datetime import date, timedelta
    from models import CatalogoNR, Colaborador, ColaboradorCurso

    with app.app_context():
        db.drop_all()
        db.create_all()

        admin = Usuario(
            nome="Administrador Sistema",
            sso="admin001",
            email="admin@empresa.com",
            senha_hash=generate_password_hash("admin123"),
            perfil="admin"
        )
        usuario_comum = Usuario(
            nome="Maria Souza",
            sso="msouza",
            email="maria.souza@empresa.com",
            senha_hash=generate_password_hash("123456"),
            perfil="comum"
        )
        db.session.add_all([admin, usuario_comum])
        db.session.commit()

        nr35 = CatalogoNR(nome_curso="NR-35", validade_meses=24, descricao="Trabalho em Altura")
        nr10 = CatalogoNR(nome_curso="NR-10", validade_meses=24, descricao="Seguranca em Instalacoes Eletricas")
        nr33 = CatalogoNR(nome_curso="NR-33", validade_meses=12, descricao="Espacos Confinados")
        nr12 = CatalogoNR(nome_curso="NR-12", validade_meses=12, descricao="Seguranca em Maquinas e Equipamentos")
        nr06 = CatalogoNR(nome_curso="NR-06", validade_meses=12, descricao="Equipamento de Protecao Individual")
        db.session.add_all([nr35, nr10, nr33, nr12, nr06])
        db.session.commit()

        colaboradores = [
            Colaborador(nome="Joao Pereira", cpf="111.222.333-44", matricula="0001", ativo=True),
            Colaborador(nome="Carlos Silva", cpf="222.333.444-55", matricula="0002", ativo=True),
            Colaborador(nome="Ana Oliveira", cpf="333.444.555-66", matricula="0003", ativo=True),
            Colaborador(nome="Pedro Santos", cpf="444.555.666-77", matricula="0004", ativo=True),
        ]
        db.session.add_all(colaboradores)
        db.session.commit()

        hoje = date.today()
        dados_cursos = [
            (colaboradores[0], nr35, hoje - timedelta(days=700)),
            (colaboradores[1], nr10, hoje - timedelta(days=800)),
            (colaboradores[2], nr33, hoje - timedelta(days=30)),
            (colaboradores[3], nr06, hoje - timedelta(days=10)),
        ]

        cursos_realizados = []
        for colaborador, catalogo, data_realizado in dados_cursos:
            registro = ColaboradorCurso(
                colaborador_id=colaborador.id,
                catalogo_nr_id=catalogo.id,
                data_realizado=data_realizado
            )
            registro.calcular_vencimento(catalogo)
            cursos_realizados.append(registro)

        db.session.add_all(cursos_realizados)
        db.session.commit()

    return (
        "<h2>Banco de dados inicializado com sucesso!</h2>"
        "<p>Usuarios criados: admin001/admin123 e msouza/123456</p>"
        "<p>4 colaboradores e 5 cursos NR cadastrados.</p>"
        "<p><b>IMPORTANTE:</b> remova esta rota do codigo apos o uso.</p>"
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
