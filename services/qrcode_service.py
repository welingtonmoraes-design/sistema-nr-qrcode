import os
import qrcode
from PIL import Image, ImageDraw, ImageFont

QRCODE_DIR = os.path.join("static", "qrcodes")
os.makedirs(QRCODE_DIR, exist_ok=True)

# A URL base vem de variável de ambiente (definida no Render).
# Localmente, cai no fallback para teste na rede local.
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")


def gerar_qrcode_colaborador(colaborador):
    """
    Gera um QR Code contendo a URL de verificacao do colaborador.
    Ao escanear, abre no navegador a pagina /verificar/{cpf}
    com todos os cursos e validades atualizados.
    """
    conteudo = BASE_URL + "/verificar/" + colaborador.cpf

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
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


def montar_folha_a4(lista_colaboradores, qr_por_linha=3, qr_por_coluna=4):
    """
    Monta paginas A4 (300 DPI) com multiplos QR Codes + nome/CPF do colaborador.
    """
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
        tamanho_qr = espacamento_x - 60
        qr_img = Image.open(qr_path).resize((tamanho_qr, tamanho_qr))
        folha.paste(qr_img, (x + 20, y))

        texto = colaborador.nome + "\nCPF: " + colaborador.cpf
        draw.text((x + 20, y + tamanho_qr + 10), texto, fill="black", font=fonte)

    paginas.append(folha)
    return paginas


def exportar_paginas_pdf(paginas, nome_arquivo="qrcodes_colaboradores.pdf"):
    """Salva a lista de imagens (paginas) como um unico PDF multi-pagina."""
    if not paginas:
        raise ValueError("Nenhuma pagina para exportar.")

    paginas[0].save(
        nome_arquivo,
        save_all=True,
        append_images=paginas[1:]
    )
    return nome_arquivo
