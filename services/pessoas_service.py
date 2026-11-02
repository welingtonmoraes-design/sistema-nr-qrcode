from models import Colaborador, TreinamentoPTLoto
from services.pt_loto_service import _norm


def _indice_pt():
    """Treinamento de PT mais recente por matricula e por nome."""
    por_matricula, por_nome = {}, {}
    for r in TreinamentoPTLoto.query.all():
        m = (r.matricula or "").strip().upper()
        n = _norm(r.nome)
        if m:
            atual = por_matricula.get(m)
            if atual is None or r.data_treinamento > atual.data_treinamento:
                por_matricula[m] = r
        atual = por_nome.get(n)
        if atual is None or r.data_treinamento > atual.data_treinamento:
            por_nome[n] = r
    return por_matricula, por_nome


def listar_pessoas_qr():
    """
    Lista unica de pessoas para gerar QR Code:
    - colaboradores ativos (com NR e/ou PT);
    - pessoas que existem apenas no modulo PT/LOTO.
    """
    por_matricula, por_nome = _indice_pt()
    matriculas_usadas, nomes_usados = set(), set()
    pessoas = []

    for c in Colaborador.query.filter_by(ativo=True).order_by(Colaborador.nome).all():
        m = (c.matricula or "").strip().upper()
        n = _norm(c.nome)
        pt = por_matricula.get(m) if m else None
        if pt is None:
            pt = por_nome.get(n)
        if pt is not None:
            if m in por_matricula:
                matriculas_usadas.add(m)
            nomes_usados.add(n)
        pessoas.append({
            "chave": f"c{c.id}",
            "nome": c.nome,
            "n_nr": len(c.cursos),
            "tem_pt": pt is not None,
        })

    # Pessoas que so tem PT/LOTO (agrupadas por matricula ou nome)
    grupos = {}
    for r in TreinamentoPTLoto.query.all():
        m = (r.matricula or "").strip().upper()
        chave = ("M", m) if m else ("N", _norm(r.nome))
        atual = grupos.get(chave)
        if atual is None or r.data_treinamento > atual.data_treinamento:
            grupos[chave] = r

    for (tipo, valor), r in grupos.items():
        m = (r.matricula or "").strip().upper()
        if (m and m in matriculas_usadas) or _norm(r.nome) in nomes_usados:
            continue
        pessoas.append({
            "chave": f"p{r.id}",
            "nome": r.nome,
            "n_nr": 0,
            "tem_pt": True,
        })

    pessoas.sort(key=lambda p: _norm(p["nome"]))
    return pessoas


def montar_itens_qr(chaves, base_url):
    """Converte as chaves marcadas (c12, p5...) em itens {nome, url}."""
    ids_c, ids_p = [], []
    for ch in chaves:
        ch = (ch or "").strip()
        if len(ch) > 1 and ch[1:].isdigit():
            if ch[0] == "c":
                ids_c.append(int(ch[1:]))
            elif ch[0] == "p":
                ids_p.append(int(ch[1:]))

    itens = []
    if ids_c:
        for c in Colaborador.query.filter(Colaborador.id.in_(ids_c)).all():
            itens.append({"nome": c.nome, "url": f"{base_url}/verificar/{c.cpf}"})
    if ids_p:
        for r in TreinamentoPTLoto.query.filter(TreinamentoPTLoto.id.in_(ids_p)).all():
            itens.append({"nome": r.nome, "url": f"{base_url}/verificar-pt/{r.id}"})

    itens.sort(key=lambda i: _norm(i["nome"]))
    return itens
