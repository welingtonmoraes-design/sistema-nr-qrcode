"""
Script para inicializar o banco de dados com dados de exemplo.
Execute localmente: python init_db.py
No Render: use o Shell do painel e rode o mesmo comando.
"""
from app import app
from models import db, Colaborador, Usuario, CatalogoNR, ColaboradorCurso
from werkzeug.security import generate_password_hash
from datetime import date, timedelta


def criar_banco():
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

        nr35 = CatalogoNR(nome_curso="NR-35", validade_meses=24,
                          descricao="Trabalho em Altura")
        nr10 = CatalogoNR(nome_curso="NR-10", validade_meses=24,
                          descricao="Seguranca em Instalacoes Eletricas")
        nr33 = CatalogoNR(nome_curso="NR-33", validade_meses=12,
                          descricao="Espacos Confinados")
        nr12 = CatalogoNR(nome_curso="NR-12", validade_meses=12,
                          descricao="Seguranca em Maquinas e Equipamentos")
        nr06 = CatalogoNR(nome_curso="NR-06", validade_meses=12,
                          descricao="Equipamento de Protecao Individual")
        db.session.add_all([nr35, nr10, nr33, nr12, nr06])
        db.session.commit()

        colaboradores = [
            Colaborador(nome="Joao Pereira", cpf="111.222.333-44",
                        matricula="0001", ativo=True),
            Colaborador(nome="Carlos Silva", cpf="222.333.444-55",
                        matricula="0002", ativo=True),
            Colaborador(nome="Ana Oliveira", cpf="333.444.555-66",
                        matricula="0003", ativo=True),
            Colaborador(nome="Pedro Santos", cpf="444.555.666-77",
                        matricula="0004", ativo=True),
        ]
        db.session.add_all(colaboradores)
        db.session.commit()

        # Datas relativas a hoje, garantindo cenario sempre realista
        hoje = date.today()

        dados_cursos = [
            (colaboradores[0], nr35, hoje -
             timedelta(days=700)),   # proximo a vencer
            (colaboradores[1], nr10, hoje - timedelta(days=800)),   # vencido
            (colaboradores[2], nr33, hoje - timedelta(days=30)),    # valido
            (colaboradores[3], nr06, hoje - timedelta(days=10)),    # valido
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

        print("Banco de dados criado com sucesso!")
        print(f"   - {len(colaboradores)} colaboradores cadastrados")
        print("   - 5 cursos NR no catalogo")
        print(f"   - {len(cursos_realizados)} registros de cursos realizados")
        print("\nStatus dos cursos cadastrados:")
        for registro in cursos_realizados:
            status, dias = registro.status()
            print(f"   - {registro.colaborador.nome} | {registro.catalogo.nome_curso} "
                  f"| Vence em: {registro.data_vencimento} | Status: {status} ({dias} dias)")

        print("\nUsuarios de acesso:")
        print("   admin001 / admin123 (perfil: admin)")
        print("   msouza / 123456 (perfil: comum)")


if __name__ == "__main__":
    criar_banco()
