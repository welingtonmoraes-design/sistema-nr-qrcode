import os
import base64
import qrcode
from PIL import Image, ImageDraw, ImageFont

QRCODE_DIR = os.path.join("static", "qrcodes")
os.makedirs(QRCODE_DIR, exist_ok=True)


def montar_html_colaborador(colaborador):
    linhas_cursos = ""
    if not colaborador.cursos:
        linhas_cursos = "<tr><td colspan='4' style='text-align:center;'>Nenhum curso cadastrado</td></tr>"
    else:
        for curso in colaborador.cursos:
            status, dias = curso.status()
            cor_fundo = {
                "VENCIDO": "#ffdddd",
                "A_VENCER": "#fff3cd",
                "VALIDO": "#d4edda"
            }.get(status, "#ffffff")

            data_venc = curso.data_vencimento.strftime(
                "%d/%m/%Y") if curso.data_vencimento else "N/A"

            linhas_cursos += (
                "<tr style='background:" + cor_fundo + ";'>"
                "<td>" + curso.catalogo.nome_curso + "</td>"
                "<td>" + curso.data_realizado.strftime("%d/%m/%Y") + "</td>"
                "<td>" + data_venc + "</td>"
                "<td>" + status + "</td>"
                "</tr>"
            )

    matricula_html = ""
    if colaborador.matricula:
        matricula_html = "<p><b>Matricula:</b> " + colaborador.matricula + "</p>"

    html = (
        "<!DOCTYPE html>"
        "<html lang='pt-br'>"
        "<head>"
        "<meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>"
        "<title>" + colaborador.nome + "</title>"
        "<style>"
        "body { font-family: Arial, sans-serif; margin: 15px; background: #f4f4f4; }"
        ".card { background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }"
        "h2 { color: #222; margin-top: 0; }"
        "table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }"
        "th, td { padding: 8px; border: 1px solid #ccc; text-align: left; }"
        "th { background: #333; color: white; }"
        "</style>"
        "</head>"
        "<body>"
        "<div class='card'>"
        "<h2>" + colaborador.nome + "</h2>"
        "<p><b>CPF:</b> " + colaborador.cpf + "</p>"
        + matricula_html +
        "<table>"
        "<tr><th>Curso</th><th>Realizado</th><th>Vencimento</th><th>Status</th></tr>"
        + linhas_cursos +
        "</table>"
        "<p style='margin-top:15px; font-size:11px; color:#888;'>Gerado pelo Sistema de Gestao de NRs</p>"
        "</div>"
        "</body>"
        "</html>"
    )
    return html


def gerar_qrcode_colaborador(colaborador):
    html = montar_html_colaborador(colaborador)
    html_b64 = base64.b64encode(html.encode("utf-8")).decode("utf-8")
    conteudo = "data:text/html;base64," + html_b64

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(conteudo)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    caminho = os.path.join(QRCODE_DIR, str(colaborador.id) + ".png")
    img.save(caminho)
    return caminho


def _carregar_fonte(tamanho=28):
    try:
        return ImageFont.truetype("arial.ttf", tamanho)
    except Exception:
        return ImageFont.load_default()


def montar_folha_a4(lista_colaboradores, qr_por_linha=2, qr_por_coluna=3):
    A4_LARGURA = 2480
    A4_ALTURA = 3508
    margem = 100
    espacamento_x = (A4_LARGURA - 2 * margem) // qr_por_linha
    espacamento_y = (A4_ALTURA - 2 * margem) // qr_por_coluna

    fonte = _carregar_fonte()
    por_pagina = qr_por_linha * qr_por_coluna

    paginas = []
    folha = Image.new("RGB", (A4_LARGURA, A4_ALTURA), "white")
    draw = ImageDraw.Draw(folha)

    for i, colaborador in enumerate(lista_colaboradores):
        pos_na_pagina = i % por_pagina

        if pos_na_pagina == 0 and i != 0:
            paginas.append(folha)
            folha = Image.new("RGB", (A4_LARGURA, A4_ALTURA), "white")
            draw = ImageDraw.Draw(folha)

        col = pos_na_pagina % qr_por_linha
        lin = pos_na_pagina // qr_por_linha

        x = margem + col * espacamento_x
        y = margem + lin * espacamento_y

        qr_path = gerar_qrcode_colaborador(colaborador)
        tamanho_qr = min(espacamento_x - 60, espacamento_y - 150)
        qr_img = Image.open(qr_path).resize((tamanho_qr, tamanho_qr))
        folha.paste(qr_img, (x + 20, y))

        texto = colaborador.nome + "\nCPF: " + colaborador.cpf
        draw.text((x + 20, y + tamanho_qr + 10),
                  texto, fill="black", font=fonte)

    paginas.append(folha)
    return paginas


def exportar_paginas_pdf(paginas, nome_arquivo="qrcodes_colaboradores.pdf"):
    if not paginas:
        raise ValueError("Nenhuma pagina para exportar.")

    paginas[0].save(
        nome_arquivo,
        save_all=True,
        append_images=paginas[1:]
    )
    return nome_arquivo
