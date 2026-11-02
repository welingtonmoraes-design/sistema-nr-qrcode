from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file
from flask_login import login_required

from services.pessoas_service import listar_pessoas_qr, montar_itens_qr
from services.pt_loto_service import _norm
from services.qrcode_service import (
    BASE_URL, MAX_POR_PDF, montar_folha_a4, paginas_para_pdf_bytes
)

bp_qrcodes = Blueprint("qrcodes", __name__, url_prefix="/qrcodes")


@bp_qrcodes.route("/", methods=["GET", "POST"])
@login_required
def gerar():
    if request.method == "POST":
        chaves = request.form.getlist("pessoas")
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

        pdf = paginas_para_pdf_bytes(montar_folha_a4(itens))
        return send_file(pdf, mimetype="application/pdf",
                         as_attachment=True, download_name="qrcodes_ehs.pdf")

    # --- GET: filtros aplicados no servidor ---
    busca = request.args.get("busca", "").strip()
    tipo = request.args.get("tipo", "").strip()
    marcar = request.args.get("marcar", "") == "1"

    termos = _norm(busca).split()
    pessoas = []
    for p in listar_pessoas_qr():
        nome = _norm(p["nome"])
        if termos and not all(t in nome for t in termos):
            continue
        if tipo == "nr" and not p["n_nr"]:
            continue
        if tipo == "pt" and not p["tem_pt"]:
            continue
        pessoas.append(p)

    return render_template(
        "qrcodes/gerar.html",
        pessoas=pessoas, busca=busca, tipo=tipo, marcar=marcar,
        base_url=BASE_URL,
        url_local=("127.0.0.1" in BASE_URL or "localhost" in BASE_URL),
        limite=MAX_POR_PDF,
    )
