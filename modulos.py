"""
Lista central de modulos do Sistema de Controle de EHS.
Para adicionar um novo modulo: inclua um dicionario aqui, crie o blueprint
em routes/ e registre-o no app.py.
"""

MODULOS = [
    {
        "id": "nrs",
        "nome": "Controle NRs",
        "descricao": "Colaboradores, cursos de NRs, validades, alertas e QR Codes.",
        "icone": "🎓",
        "endpoint": "nrs.painel",
        "blueprints": ["nrs", "colaboradores", "catalogo_nr", "cursos"],
        "ativo": True,
        "submenu": [
            {"nome": "Painel", "endpoint": "nrs.painel"},
            {"nome": "Colaboradores", "endpoint": "colaboradores.listar"},
            {"nome": "Catálogo NR", "endpoint": "catalogo_nr.listar"},
            {"nome": "Cursos Realizados", "endpoint": "cursos.listar"},
            {"nome": "Gerar QR Codes", "endpoint": "cursos.gerar_qrcodes"},
        ],
    },
    {
        "id": "pt_loto",
        "nome": "Validade PT e LOTO",
        "descricao": "Controle de validade de Permissões de Trabalho e bloqueios LOTO.",
        "icone": "🔒",
        "endpoint": "pt_loto.index",
        "blueprints": ["pt_loto"],
        "ativo": True,
        "submenu": [
            {"nome": "Painel", "endpoint": "pt_loto.index"},
        ],
    },
    # --- Exemplos de modulos futuros (nomes ilustrativos, ajuste como quiser) ---
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
