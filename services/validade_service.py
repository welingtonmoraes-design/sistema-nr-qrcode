from datetime import date


def status_curso(curso):
    """
    Recebe um objeto ColaboradorCurso e retorna (status, dias_restantes).
    Mantido aqui como camada de serviço, mas também disponível
    como método no próprio model (curso.status()).
    """
    if not curso.data_vencimento:
        return "INDEFINIDO", None

    hoje = date.today()
    dias_restantes = (curso.data_vencimento - hoje).days

    if dias_restantes < 0:
        return "VENCIDO", dias_restantes
    elif dias_restantes <= 30:
        return "A_VENCER", dias_restantes
    return "VALIDO", dias_restantes


def listar_cursos_criticos(ColaboradorCurso):
    """
    Retorna lista de dicts com cursos vencidos ou a vencer (<=30 dias).
    Recebe a classe do model para evitar import circular.
    """
    cursos = ColaboradorCurso.query.all()
    criticos = []

    for c in cursos:
        status, dias = status_curso(c)
        if status in ("VENCIDO", "A_VENCER"):
            criticos.append({
                "colaborador": c.colaborador.nome,
                "colaborador_id": c.colaborador_id,
                "curso": c.catalogo.nome_curso,
                "vencimento": c.data_vencimento,
                "status": status,
                "dias_restantes": dias
            })

    # ordena: vencidos primeiro, depois por menor dias_restantes
    criticos.sort(key=lambda x: (
        x["status"] != "VENCIDO", x["dias_restantes"] if x["dias_restantes"] is not None else 9999))
    return criticos
