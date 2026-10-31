from flask import Blueprint, render_template, session
from flask_login import login_required

bp_nrs = Blueprint("nrs", __name__, url_prefix="/nrs")


@bp_nrs.route("/")
@login_required
def painel():
    """Painel de alertas de vencimento do modulo Controle NRs."""
    alertas = session.get("alertas_nr", [])
    return render_template("nrs/painel.html", alertas=alertas)
