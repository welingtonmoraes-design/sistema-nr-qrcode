import io
import math
import os

import qrcode
from PIL import Image, ImageDraw, ImageFont

QRCODE_DIR = os.path.join("static", "qrcodes")
os.makedirs(QRCODE_DIR, exist_ok=True)

# URL publica do sistema (variavel de ambiente do Render)
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000").rstrip("/")

# Pagina A4 a 200 DPI (210 x 297 mm). O PDF e gravado com a mesma resolucao,
# entao impresso a 100% o QR sai com o tamanho em cm escolhido.
DPI = 200
A4_LARGURA = 1654
A4_ALTURA = 2339
MM = DPI / 25.4
MARGEM_MM = 10

MAX_POR_PDF = 120
MAX_PAGINAS = 20

TAMANHOS_CM = [2, 2.5, 3, 3.5, 4, 5, 6, 7, 8, 10]
TAMANHO_PADRAO_CM = 4

FONTES = [
    "arial.ttf",
    "DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "LiberationSans-Bold.ttf",
]


def _carregar_fonte(tamanho=32):
    for caminho in FONTES:
        try:
            return ImageFont.truetype(caminho, tamanho)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=tamanho)
    except TypeError:
        return ImageFont.load_default()


def gerar_qrcode_imagem(conteudo):
    """Cria a imagem (PIL) de um QR Code com o texto/URL informado."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(conteudo)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").get_image().convert("RGB")


def gerar_qrcode_colaborador(colaborador):
    """Compatibilidade: grava o PNG do QR de um colaborador em static/qrcodes."""
    img = gerar_qrcode_imagem(BASE_URL + "/verificar/" + colaborador.cpf)
    caminho = os.path.join(QRCODE_DIR, str(colaborador.id) + ".png")
    img.save(caminho)
    return caminho


def _layout(tamanho_cm):
    """Calcula tamanhos em pixels e quantas colunas/linhas cabem na folha A4."""
    qr_px = int(round(tamanho_cm * 10 * MM))
    fonte_px = max(20, min(44, int(qr_px * 0.11)))
    linha_px = int(fonte_px * 1.25)
    gap_x = int(5 * MM)
    gap_y = int(4 * MM)
    texto_h = 2 * linha_px + int(2 * MM)

    cel_w = qr_px + gap_x
    cel_h = qr_px + texto_h + gap_y
    margem = int(MARGEM_MM * MM)
    util_w = A4_LARGURA - 2 * margem
    util_h = A4_ALTURA - 2 * margem

    colunas = max(1, (util_w + gap_x) // cel_w)
    linhas = max(1, (util_h + gap_y) // cel_h)
    return {
        "qr_px": qr_px, "fonte_px": fonte_px, "linha_px": linha_px,
        "gap_x": gap_x, "cel_w": cel_w, "cel_h": cel_h, "margem": margem,
        "colunas": colunas, "linhas": linhas,
    }


def capacidade_por_pagina(tamanho_cm):
    """Quantos QR Codes cabem em uma folha A4 com o tamanho informado."""
    lay = _layout(tamanho_cm)
    return lay["colunas"] * lay["linhas"]


def paginas_necessarias(qtd, tamanho_cm):
    return math.ceil(qtd / capacidade_por_pagina(tamanho_cm)) if qtd else 0


def _quebrar_texto(draw, texto, fonte, largura_max, max_linhas=2):
    palavras = texto.split()
    linhas, atual = [], ""
    for p in palavras:
        teste = (atual + " " + p).strip()
        if not atual or draw.textlength(teste, font=fonte) <= largura_max:
            atual = teste
        else:
            linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)

    if len(linhas) > max_linhas:
        linhas = linhas[:max_linhas]
        ultima = linhas[-1]
        while ultima and draw.textlength(ultima + "...", font=fonte) > largura_max:
            ultima = ultima[:-1]
        linhas[-1] = ultima + "..."
    return linhas


def montar_folha_a4(itens, tamanho_cm=TAMANHO_PADRAO_CM):
    """
    Monta paginas A4 com QR Codes do tamanho pedido (em cm).
    Cada item e um dict: {"nome": "...", "url": "https://..."}.
    As paginas sao em tons de cinza para economizar memoria.
    """
    lay = _layout(tamanho_cm)
    qr_px = lay["qr_px"]
    colunas, linhas = lay["colunas"], lay["linhas"]
    por_pagina = colunas * linhas

    grade_w = colunas * qr_px + (colunas - 1) * lay["gap_x"]
    x_inicio = (A4_LARGURA - grade_w) // 2
    fonte = _carregar_fonte(lay["fonte_px"])

    paginas = []
    folha = Image.new("L", (A4_LARGURA, A4_ALTURA), 255)
    draw = ImageDraw.Draw(folha)

    for i, item in enumerate(itens):
        pos = i % por_pagina
        if pos == 0 and i != 0:
            paginas.append(folha)
            folha = Image.new("L", (A4_LARGURA, A4_ALTURA), 255)
            draw = ImageDraw.Draw(folha)

        col = pos % colunas
        lin = pos // colunas
        x0 = x_inicio + col * lay["cel_w"]
        y0 = lay["margem"] + lin * lay["cel_h"]

        qr_img = gerar_qrcode_imagem(item["url"]).convert("L")
        metodo = Image.NEAREST if qr_px >= qr_img.width else Image.LANCZOS
        folha.paste(qr_img.resize((qr_px, qr_px), metodo), (x0, y0))

        y_texto = y0 + qr_px + 6
        for texto in _quebrar_texto(draw, item["nome"], fonte, qr_px):
            largura = draw.textlength(texto, font=fonte)
            draw.text((x0 + (qr_px - largura) / 2, y_texto), texto, fill=0, font=fonte)
            y_texto += lay["linha_px"]

    paginas.append(folha)
    return paginas


def paginas_para_pdf_bytes(paginas):
    """Converte as paginas em um unico PDF (em memoria), em A4 real."""
    if not paginas:
        raise ValueError("Nenhuma pagina para exportar.")
    buf = io.BytesIO()
    paginas[0].save(buf, format="PDF", save_all=True,
                    append_images=paginas[1:], resolution=DPI)
    buf.seek(0)
    return buf
