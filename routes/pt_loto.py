from flask import Blueprint, render_template
from flask_login import login_required

bp_pt_loto = Blueprint("pt_loto", __name__, url_prefix="/pt-loto")


@bp_pt_loto.route("/")
@login_required
def index():
    return render_template("pt_loto/index.html")
