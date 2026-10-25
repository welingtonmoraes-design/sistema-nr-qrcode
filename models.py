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
    validade_meses = db.Column(db.Integer, nullable=False)
    descricao = db.Column(db.String(255))

    def __repr__(self):
        return f"<CatalogoNR {self.nome_curso}>"


class ColaboradorCurso(db.Model):
    __tablename__ = "colaborador_curso"

    id = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey(
        "colaboradores.id"), nullable=False)
    catalogo_nr_id = db.Column(db.Integer, db.ForeignKey(
        "catalogo_nr.id"), nullable=False)
    data_realizado = db.Column(db.Date, nullable=False)
    data_vencimento = db.Column(db.Date)

    catalogo = db.relationship("CatalogoNR", lazy="joined")

    def calcular_vencimento(self, catalogo=None):
        """
        Calcula a data de vencimento somando os meses de validade
        à data de realização do curso.

        Pode receber o objeto `catalogo` diretamente (útil quando o
        registro ainda não está persistido na sessão do SQLAlchemy,
        como em scripts de seed/importação em massa).
        """
        cat = catalogo or self.catalogo
        if cat is None:
            raise ValueError(
                "Não foi possível determinar o catálogo NR. "
                "Informe o parâmetro 'catalogo' ou garanta que o "
                "registro esteja associado a uma sessão válida."
            )

        meses = cat.validade_meses

        ano = self.data_realizado.year + \
            (self.data_realizado.month - 1 + meses) // 12
        mes = (self.data_realizado.month - 1 + meses) % 12 + 1
        # evita erro em meses com menos dias
        dia = min(self.data_realizado.day, 28)

        self.data_vencimento = self.data_realizado.replace(
            year=ano, month=mes, day=dia)
        return self.data_vencimento

    def status(self):
        """Retorna (status, dias_restantes) com base na data de hoje."""
        if not self.data_vencimento:
            return "INDEFINIDO", None

        hoje = date.today()
        dias_restantes = (self.data_vencimento - hoje).days

        if dias_restantes < 0:
            return "VENCIDO", dias_restantes
        elif dias_restantes <= 30:
            return "A_VENCER", dias_restantes
        return "VALIDO", dias_restantes

    def __repr__(self):
        return f"<ColaboradorCurso colaborador_id={self.colaborador_id} catalogo_nr_id={self.catalogo_nr_id}>"
