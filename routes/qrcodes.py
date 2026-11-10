from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file
from flask_login import login_required

from services.pessoas_service import listar_pessoas_qr, montar_itens_qr
from services.pt_loto_service import _norm
from services.qrcode_service import (
    BASE_URL, MAX_POR_PDF, MAX_PAGINAS, TAMANHOS_CM, TAMANHO_PADRAO_CM,
    capacidade_por_pagina, paginas_necessarias,
    montar_folha_a4, paginas_para_pdf_bytes,
)

bp_qrcodes = Blueprint("qrcodes", __name__, url_prefix="/qrcodes")


def _ler_tamanho(valor):
    """Converte o valor do formulario em cm, aceitando so os tamanhos permitidos."""
    try:
        cm = float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return TAMANHO_PADRAO_CM
    return cm if cm in TAMANHOS_CM else TAMANHO_PADRAO_CM


@bp_qrcodes.route("/", methods=["GET", "POST"])
@login_required
def gerar():
    if request.method == "POST":
        chaves = request.form.getlist("pessoas")
        tamanho_cm = _ler_tamanho(request.form.get("tamanho"))

        if not chaves:
            flash("Selecione ao menos uma pessoa.", "danger")
            return redirect(url_for("qrcodes.gerar"))

        itens = montar_itens_qr(chaves, BASE_URL)
        if not itens:
            flash("Nenhuma pessoa válida foi selecionada.", "danger")
            return redirect(url_for("qrcodes.gerar"))

        if len(itens) > MAX_POR_PDF:
            flash(f"Selecione no máximo {MAX_POR_PDF} pessoas por PDF "
                  f"(você marcou {len(itens)}). Gere em lotes.", "danger")
            return redirect(url_for("qrcodes.gerar"))

        paginas = paginas_necessarias(len(itens), tamanho_cm)
        if paginas > MAX_PAGINAS:
            flash(f"Com QR Codes de {tamanho_cm:g} cm, {len(itens)} pessoas geram "
                  f"{paginas} páginas (máximo {MAX_PAGINAS}). Escolha um tamanho menor "
                  f"ou gere em lotes.", "danger")
            return redirect(url_for("qrcodes.gerar"))

        pdf = paginas_para_pdf_bytes(montar_folha_a4(itens, tamanho_cm))
        return send_file(pdf, mimetype="application/pdf",
                         as_attachment=True,
                         download_name=f"qrcodes_ehs_{tamanho_cm:g}cm.pdf")

    # --- GET: filtros aplicados no servidor ---
    busca = request.args.get("busca", "").strip()
    tipo = request.args.get("tipo", "").strip()
    marcar = request.args.get("marcar", "") == "1"

    todas = listar_pessoas_qr()
    termos = _norm(busca).split()

    pessoas = []
    for p in todas:
        if termos and not all(t in _norm(p["nome"]) for t in termos):
            continue
        if tipo == "nr" and not p["n_nr"]:
            continue
        if tipo == "pt" and not p["tem_pt"]:
            continue
        pessoas.append(p)

    tamanhos = [
        {"cm": cm, "label": f"{cm:g}", "por_pagina": capacidade_por_pagina(cm)}
        for cm in TAMANHOS_CM
    ]

    return render_template(
        "qrcodes/gerar.html",
        pessoas=pessoas, busca=busca, tipo=tipo, marcar=marcar,
        total_geral=len(todas),
        total_nr=sum(1 for p in todas if p["n_nr"]),
        total_pt=sum(1 for p in todas if p["tem_pt"]),
        total_inativos=sum(1 for p in todas if p["inativo"]),
        tamanhos=tamanhos, tamanho_padrao=TAMANHO_PADRAO_CM,
        base_url=BASE_URL,
        url_local=("127.0.0.1" in BASE_URL or "localhost" in BASE_URL),
        limite=MAX_POR_PDF,
    )
