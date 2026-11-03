from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import (
    StringField, PasswordField, SelectField,
    DateField, IntegerField, BooleanField, TextAreaField
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
    nome_curso = StringField("Nome do Curso (ex: NR-35 - Trabalho em Altura)",
                             validators=[DataRequired(), Length(max=100)])
    carga_horaria = StringField("Carga horária mínima (ex: 8h)",
                                validators=[Optional(), Length(max=50)])
    sem_validade = BooleanField("Sem validade (curso não vence)")
    validade_meses = IntegerField("Validade / reciclagem (meses)", validators=[Optional()])
    descricao = TextAreaField("Observações técnicas", validators=[Optional()])


class ImportarCatalogoForm(FlaskForm):
    arquivo = FileField(
        "Planilha Excel (.xlsx)",
        validators=[FileRequired(), FileAllowed(["xlsx", "xlsm"], "Envie um arquivo .xlsx")]
    )
    atualizar = BooleanField("Atualizar cursos que já existem no catálogo")

class ColaboradorCursoForm(FlaskForm):
    colaborador_id = SelectField("Colaborador", coerce=int, validators=[DataRequired()])
    catalogo_nr_id = SelectField("Curso NR", coerce=int, validators=[DataRequired()])
    data_realizado = DateField(
        "Data Realizado", format="%Y-%m-%d", validators=[DataRequired()]
    )
    certificado = FileField(
        "Certificado (foto ou PDF)",
        validators=[Optional(), FileAllowed(["pdf", "jpg", "jpeg", "png"],
                                            "Envie um arquivo PDF, JPG ou PNG.")]
    )
    remover_certificado = BooleanField("Remover o certificado atual")


class RevalidarCursoForm(FlaskForm):
    data_realizado = DateField(
        "Nova data de realização", format="%Y-%m-%d", validators=[DataRequired()]
    )
    certificado = FileField(
        "Novo certificado (foto ou PDF) — opcional",
        validators=[Optional(), FileAllowed(["pdf", "jpg", "jpeg", "png"],
                                            "Envie um arquivo PDF, JPG ou PNG.")]
    )


class TreinamentoPTLotoForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired(), Length(max=150)])
    matricula = StringField("Matrícula/SSO", validators=[Optional(), Length(max=50)])
    empresa = StringField("Empresa", validators=[Optional(), Length(max=150)])
    data_treinamento = DateField(
        "Data do Treinamento", format="%Y-%m-%d", validators=[DataRequired()]
    )
    instrutor = StringField("Instrutor", validators=[Optional(), Length(max=150)])


class ImportarExcelForm(FlaskForm):
    arquivo = FileField(
        "Planilha Excel (.xlsx)",
        validators=[FileRequired(), FileAllowed(["xlsx", "xlsm"], "Envie um arquivo .xlsx")]
    )
    substituir = BooleanField("Substituir todos os registros existentes")

class RevalidarForm(FlaskForm):
    data_treinamento = DateField(
        "Nova data do treinamento", format="%Y-%m-%d", validators=[DataRequired()]
    )
    instrutor = StringField("Instrutor", validators=[Optional(), Length(max=150)])

class ColaboradorForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired(), Length(max=150)])
    cpf = StringField("CPF", validators=[DataRequired(), Length(min=11, max=14)])
    matricula = StringField("Matrícula", validators=[Optional()])
    empresa = StringField("Empresa", validators=[Optional(), Length(max=150)])
    ativo = BooleanField("Ativo", default=True)
