from models import Colaborador, TreinamentoPTLoto
from services.pt_loto_service import _norm


def _indices_pt():
    """
    Indices do PT/LOTO (registro mais recente de cada pessoa):
    - por nome normalizado;
    - por matricula, mas SO matriculas que pertencem a uma unica pessoa
      (matriculas repetidas, como '-' ou '0', sao ignoradas).
    """
    por_nome, por_matricula, nomes_por_matricula = {}, {}, {}

    for r in TreinamentoPTLoto.query.all():
        n = _norm(r.nome)
        m = (r.matricula or "").strip().upper()

        atual = por_nome.get(n)
        if atual is None or r.data_treinamento > atual.data_treinamento:
            por_nome[n] = r

        if m:
            nomes_por_matricula.setdefault(m, set()).add(n)
            atual = por_matricula.get(m)
            if atual is None or r.data_treinamento > atual.data_treinamento:
                por_matricula[m] = r

    por_matricula = {
        m: r for m, r in por_matricula.items()
        if len(nomes_por_matricula[m]) == 1
    }
    return por_matricula, por_nome


def listar_pessoas_qr():
    """
    Lista unica de pessoas para gerar QR Code:
    - TODOS os colaboradores (ativos e inativos), com NR e/ou PT;
    - pessoas que existem apenas no modulo PT/LOTO (uma por nome).
    """
    por_matricula, por_nome = _indices_pt()
    nomes_pt_usados = set()
    pessoas = []

    for c in Colaborador.query.order_by(Colaborador.nome).all():
        m = (c.matricula or "").strip().upper()
        pt = por_matricula.get(m) if m else None
        if pt is None:
            pt = por_nome.get(_norm(c.nome))
        if pt is not None:
            nomes_pt_usados.add(_norm(pt.nome))

        pessoas.append({
            "chave": f"c{c.id}",
            "nome": c.nome,
            "n_nr": len(c.cursos),
            "tem_pt": pt is not None,
            "inativo": not c.ativo,
        })

    # Pessoas que so tem PT/LOTO
    for nome_norm, r in por_nome.items():
        if nome_norm in nomes_pt_usados:
            continue
        pessoas.append({
            "chave": f"p{r.id}",
            "nome": r.nome,
            "n_nr": 0,
            "tem_pt": True,
            "inativo": False,
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
