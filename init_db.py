"""
Script para inicializar o banco de dados com dados de exemplo.
Execute: python init_db.py
"""
from app import app
from models import db, Colaborador, Usuario, CatalogoNR, ColaboradorCurso
from werkzeug.security import generate_password_hash
from datetime import date


def criar_banco():
    with app.app_context():
        db.drop_all()
        db.create_all()

        # --- Usuários do sistema ---
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

        # --- Catálogo de NRs (validade padrão) ---
        nr35 = CatalogoNR(nome_curso="NR-35", validade_meses=24,
                          descricao="Trabalho em Altura")
        nr10 = CatalogoNR(nome_curso="NR-10", validade_meses=24,
                          descricao="Segurança em Instalações Elétricas")
        nr33 = CatalogoNR(nome_curso="NR-33", validade_meses=12,
                          descricao="Espaços Confinados")
        nr12 = CatalogoNR(nome_curso="NR-12", validade_meses=12,
                          descricao="Segurança em Máquinas e Equipamentos")
        nr06 = CatalogoNR(nome_curso="NR-06", validade_meses=12,
                          descricao="Equipamento de Proteção Individual")
        db.session.add_all([nr35, nr10, nr33, nr12, nr06])
        db.session.commit()  # ✅ commit aqui garante IDs gerados antes de usar

        # --- Colaboradores ---
        colaboradores = [
            Colaborador(nome="João Pereira", cpf="111.222.333-44",
                        matricula="0001", ativo=True),
            Colaborador(nome="Carlos Silva", cpf="222.333.444-55",
                        matricula="0002", ativo=True),
            Colaborador(nome="Ana Oliveira", cpf="333.444.555-66",
                        matricula="0003", ativo=True),
            Colaborador(nome="Pedro Santos", cpf="444.555.666-77",
                        matricula="0004", ativo=True),
        ]
        db.session.add_all(colaboradores)
        db.session.commit()  # ✅ commit aqui garante IDs gerados antes de usar

        # --- Cursos realizados (vencidos / a vencer / válidos) ---
        # Cada tupla: (colaborador, catalogo, data_realizado)
        dados_cursos = [
            # João - NR-35 próximo a vencer
            (colaboradores[0], nr35, date(2023, 10, 15)),
            # Carlos - NR-10 vencido
            (colaboradores[1], nr10, date(2022, 1, 10)),
            (colaboradores[2], nr33, date(2024, 12, 1)),   # Ana - NR-33 válido
            # Pedro - NR-06 válido
            (colaboradores[3], nr06, date(2025, 3, 1)),
        ]

        cursos_realizados = []
        for colaborador, catalogo, data_realizado in dados_cursos:
            registro = ColaboradorCurso(
                colaborador_id=colaborador.id,
                catalogo_nr_id=catalogo.id,
                data_realizado=data_realizado
            )
            # ✅ Correção: passamos o objeto `catalogo` já carregado em memória,
            # evitando o AttributeError causado pelo lazy-load do relationship
            # em objetos que ainda não foram persistidos na sessão.
            registro.calcular_vencimento(catalogo)
            cursos_realizados.append(registro)

        db.session.add_all(cursos_realizados)
        db.session.commit()

        print("✅ Banco de dados criado com sucesso!")
        print(f"   - {len(colaboradores)} colaboradores cadastrados")
        print(f"   - 5 cursos NR no catálogo")
        print(f"   - {len(cursos_realizados)} registros de cursos realizados")
        print("\nStatus dos cursos cadastrados:")
        for registro in cursos_realizados:
            status, dias = registro.status()
            print(f"   - {registro.colaborador.nome} | {registro.catalogo.nome_curso} "
                  f"| Vence em: {registro.data_vencimento} | Status: {status} ({dias} dias)")

        print("\nUsuários de acesso:")
        print("   admin / admin123 (perfil: admin)")
        print("   msouza / 123456 (perfil: comum)")


if __name__ == "__main__":
    criar_banco()
