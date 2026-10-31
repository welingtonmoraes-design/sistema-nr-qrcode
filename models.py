import calendar
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import date

db = SQLAlchemy()


def adicionar_meses(data, meses):
    """Soma meses a uma data mantendo o dia (ajusta para o ultimo dia do mes se necessario)."""
    total = data.year * 12 + (data.month - 1) + meses
    ano, mes = divmod(total, 12)
    mes += 1
    dia = min(data.day, calendar.monthrange(ano, mes)[1])
    return date(ano, mes, dia)


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
    nome_curso = db.Column(db.String(100), nullable=False)
    validade_meses = db.Column(db.Integer, nullable=True)  # None = sem validade
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
        cat = catalogo or self.catalogo
        if cat is None:
            raise ValueError(
                "Nao foi possivel determinar o catalogo NR. "
                "Informe o parametro 'catalogo'."
            )

        if cat.validade_meses is None:
            self.data_vencimento = None
            return None

        meses = cat.validade_meses
        ano = self.data_realizado.year + (self.data_realizado.month - 1 + meses) // 12
        mes = (self.data_realizado.month - 1 + meses) % 12 + 1
        dia = min(self.data_realizado.day, 28)

        self.data_vencimento = self.data_realizado.replace(year=ano, month=mes, day=dia)
        return self.data_vencimento

    def status(self):
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


class TreinamentoPTLoto(db.Model):
    """Treinamentos de PT e LOTO (validade fixa de 12 meses)."""
    __tablename__ = "treinamento_pt_loto"

    VALIDADE_MESES = 12

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    matricula = db.Column(db.String(50))   # Matricula/SSO
    empresa = db.Column(db.String(150))
    data_treinamento = db.Column(db.Date, nullable=False)
    instrutor = db.Column(db.String(150))

    @property
    def data_validade(self):
        try:
            return adicionar_meses(self.data_treinamento, self.VALIDADE_MESES)
        except (ValueError, OverflowError):
            return None

    def condicao(self):
        """
        Retorna (codigo, texto, dias_restantes).
        codigo: VALIDO (verde) | REAVALIAR (amarelo) | VENCIDO (vermelho)
        Data invalida e tratada como VENCIDO para poder ser corrigida.
        """
        validade = self.data_validade
        if validade is None:
            return "VENCIDO", "Data inválida", -99999
        dias = (validade - date.today()).days
        if dias < 0:
            return "VENCIDO", "Vencido", dias
        if dias <= 30:
            return "REAVALIAR", "Reavaliar em 30 dias", dias
        return "VALIDO", "Dentro da validade", dias

    def __repr__(self):
        return f"<TreinamentoPTLoto {self.nome}>"
