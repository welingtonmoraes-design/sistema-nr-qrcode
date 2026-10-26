from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SelectField,
    DateField, IntegerField, BooleanField
)
from wtforms.validators import DataRequired, Email, Length, Optional


class LoginForm(FlaskForm):
    sso = StringField("SSO", validators=[DataRequired()])
    senha = PasswordField("Senha", validators=[DataRequired()])


class ColaboradorForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired(), Length(max=150)])
    cpf = StringField("CPF", validators=[DataRequired(), Length(min=11, max=14)])
    matricula = StringField("Matrícula", validators=[Optional()])
    ativo = BooleanField("Ativo", default=True)


class UsuarioForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired()])
    sso = StringField("SSO", validators=[DataRequired()])
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    senha = PasswordField("Senha", validators=[Optional()])
    perfil = SelectField(
        "Perfil",
        choices=[("comum", "Comum"), ("admin", "Administrador")]
    )


class CatalogoNRForm(FlaskForm):
    nome_curso = StringField("Nome do Curso (ex: NR-35)", validators=[DataRequired()])
    sem_validade = BooleanField("Sem validade (curso não vence)")
    validade_meses = IntegerField("Validade (meses)", validators=[Optional()])
    descricao = StringField("Descrição", validators=[Optional()])


class ColaboradorCursoForm(FlaskForm):
    colaborador_id = SelectField("Colaborador", coerce=int, validators=[DataRequired()])
    catalogo_nr_id = SelectField("Curso NR", coerce=int, validators=[DataRequired()])
    data_realizado = DateField(
        "Data Realizado", format="%Y-%m-%d", validators=[DataRequired()]
    )
