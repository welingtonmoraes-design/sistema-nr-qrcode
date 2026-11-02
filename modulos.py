"""
Lista central de modulos do Sistema de Controle de EHS.
Para adicionar um novo modulo: inclua um dicionario aqui, crie o blueprint
em routes/ e registre-o no app.py.
"""

MODULOS = [
    {
        "id": "nrs",
        "nome": "Controle NRs",
        "descricao": "Colaboradores, cursos de NRs, validades, alertas e certificados.",
        "icone": "🎓",
        "endpoint": "nrs.painel",
        "blueprints": ["nrs", "colaboradores", "catalogo_nr", "cursos"],
        "ativo": True,
        "submenu": [
            {"nome": "Treinamentos", "endpoint": "nrs.painel"},
            {"nome": "Novo lançamento", "endpoint": "cursos.novo"},
            {"nome": "Colaboradores", "endpoint": "colaboradores.listar"},
            {"nome": "Catálogo NR", "endpoint": "catalogo_nr.listar"},
        ],
    },
    {
        "id": "pt_loto",
        "nome": "Validade PT e LOTO",
        "descricao": "Controle de validade dos treinamentos de PT e LOTO (12 meses).",
        "icone": "🔒",
        "endpoint": "pt_loto.index",
        "blueprints": ["pt_loto"],
        "ativo": True,
        "submenu": [
            {"nome": "Treinamentos", "endpoint": "pt_loto.index"},
            {"nome": "Novo registro", "endpoint": "pt_loto.novo"},
            {"nome": "Importar Excel", "endpoint": "pt_loto.importar"},
        ],
    },
    {
        "id": "inspecoes",
        "nome": "Inspeções e Auditorias",
        "descricao": "Em breve.",
        "icone": "🔍",
        "endpoint": None,
        "blueprints": [],
        "ativo": False,
        "submenu": [],
    },
    {
        "id": "incidentes",
        "nome": "Incidentes e Acidentes",
        "descricao": "Em breve.",
        "icone": "🚨",
        "endpoint": None,
        "blueprints": [],
        "ativo": False,
        "submenu": [],
    },
]
