import io
import os

import qrcode
from PIL import Image, ImageDraw, ImageFont

QRCODE_DIR = os.path.join("static", "qrcodes")
os.makedirs(QRCODE_DIR, exist_ok=True)

# URL publica do sistema (variavel de ambiente do Render)
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000").rstrip("/")

# A4 a 200 DPI (leve para o servidor gratuito e nitido para leitura do QR)
A4_LARGURA = 1654
A4_ALTURA = 2339
MARGEM = 70
MAX_POR_PDF = 120

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


def montar_folha_a4(itens, qr_por_linha=3, qr_por_coluna=4):
    """
    Monta paginas A4 com varios QR Codes. Cada item e um dict:
        {"nome": "Fulano de Tal", "url": "https://.../verificar/..."}
    Abaixo de cada QR aparece somente o nome.
    """
    esp_x = (A4_LARGURA - 2 * MARGEM) // qr_por_linha
    esp_y = (A4_ALTURA - 2 * MARGEM) // qr_por_coluna
    tamanho_qr = min(esp_x - 40, esp_y - 100)
    fonte = _carregar_fonte(32)
    por_pagina = qr_por_linha * qr_por_coluna

    paginas = []
    folha = Image.new("RGB", (A4_LARGURA, A4_ALTURA), "white")
    draw = ImageDraw.Draw(folha)

    for i, item in enumerate(itens):
        pos = i % por_pagina
        if pos == 0 and i != 0:
            paginas.append(folha)
            folha = Image.new("RGB", (A4_LARGURA, A4_ALTURA), "white")
            draw = ImageDraw.Draw(folha)

        col = pos % qr_por_linha
        lin = pos // qr_por_linha
        x0 = MARGEM + col * esp_x + (esp_x - tamanho_qr) // 2
        y0 = MARGEM + lin * esp_y

        qr_img = gerar_qrcode_imagem(item["url"]).resize((tamanho_qr, tamanho_qr))
        folha.paste(qr_img, (x0, y0))

        linhas = _quebrar_texto(draw, item["nome"], fonte, tamanho_qr)
        y_texto = y0 + tamanho_qr + 8
        for linha in linhas:
            largura = draw.textlength(linha, font=fonte)
            draw.text((x0 + (tamanho_qr - largura) / 2, y_texto), linha, fill="black", font=fonte)
            y_texto += 40

    paginas.append(folha)
    return paginas


def paginas_para_pdf_bytes(paginas):
    """Converte as paginas em um unico PDF (em memoria)."""
    if not paginas:
        raise ValueError("Nenhuma pagina para exportar.")
    buf = io.BytesIO()
    paginas[0].save(buf, format="PDF", save_all=True,
                    append_images=paginas[1:], resolution=200)
    buf.seek(0)
    return buf
