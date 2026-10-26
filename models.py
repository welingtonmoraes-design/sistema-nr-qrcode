from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import date

db = SQLAlchemy()


class Colaborador(db.Model):
    __tablename__ = "colaboradores"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    matricula = db.Column(db.String(20))
    ativo = db.Column(db.Boolean, default=True)

    cursos = db.relationship(
        "ColaboradorCurso",
        backref="colaborador",
        cascade="all, delete-orphan",
        lazy=True
    )

    def __repr__(self):
        return f"<Colaborador {self.nome}>"


class Usuario(db.Model, UserMixin):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    sso = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(20), default="comum")  # admin / comum

    def __repr__(self):
        return f"<Usuario {self.nome}>"


class CatalogoNR(db.Model):
    __tablename__ = "catalogo_nr"

    id = db.Column(db.Integer, primary_key=True)
    nome_curso = db.Column(db.String(100), nullable=False)   # ex: NR-35
    validade_meses = db.Column(db.Integer, nullable=True)    # None = sem validade
    descricao = db.Column(db.String(255))

    def __repr__(self):
        return f"<CatalogoNR {self.nome_curso}>"

    @property
    def tem_validade(self):
        return self.validade_meses is not None


class ColaboradorCurso(db.Model):
    __tablename__ = "colaborador_curso"

    id = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey("colaboradores.id"), nullable=False)
    catalogo_nr_id = db.Column(db.Integer, db.ForeignKey("catalogo_nr.id"), nullable=False)
    data_realizado = db.Column(db.Date, nullable=False)
    data_vencimento = db.Column(db.Date, nullable=True)  # None = sem vencimento

    catalogo = db.relationship("CatalogoNR", lazy="joined")

    def calcular_vencimento(self, catalogo=None):
        """
        Calcula a data de vencimento somando os meses de validade
        a data de realizacao do curso.

        Se o catalogo nao tiver validade definida (validade_meses = None),
        o curso e considerado "sem vencimento" (data_vencimento = None).

        Pode receber o objeto `catalogo` diretamente (util quando o
        registro ainda nao esta persistido na sessao do SQLAlchemy,
        como em scripts de seed/importacao em massa).
        """
        cat = catalogo or self.catalogo
        if cat is None:
            raise ValueError(
                "Nao foi possivel determinar o catalogo NR. "
                "Informe o parametro 'catalogo' ou garanta que o "
                "registro esteja associado a uma sessao valida."
            )

        if cat.validade_meses is None:
            self.data_vencimento = None
            return None

        meses = cat.validade_meses

        ano = self.data_realizado.year + (self.data_realizado.month - 1 + meses) // 12
        mes = (self.data_realizado.month - 1 + meses) % 12 + 1
        dia = min(self.data_realizado.day, 28)  # evita erro em meses com menos dias

        self.data_vencimento = self.data_realizado.replace(year=ano, month=mes, day=dia)
        return self.data_vencimento

    def status(self):
        """
        Retorna (status, dias_restantes) com base na data de hoje.

        Status possiveis:
            SEM_VENCIMENTO -> curso nao possui validade (nunca vence)
            VALIDO         -> dentro do prazo (mais de 30 dias para vencer)
            A_VENCER       -> faltam 30 dias ou menos para vencer
            VENCIDO        -> prazo ja expirou
        """
        if self.data_vencimento is None:
            return "SEM_VENCIMENTO", None

        hoje = date.today()
        dias_restantes = (self.data_vencimento - hoje).days

        if dias_restantes < 0:
            return "VENCIDO", dias_restantes
        elif dias_restantes <= 30:
            return "A_VENCER", dias_restantes
        return "VALIDO", dias_restantes

    def __repr__(self):
        return f"<ColaboradorCurso colaborador_id={self.colaborador_id} catalogo_nr_id={self.catalogo_nr_id}>"
