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

# Limites da fonte do nome (em pixels, a 200 DPI)
FONTE_MIN_PX = 10
FONTE_MAX_PX = 44

FONTES = [
    "arial.ttf",
    "DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "LiberationSans-Bold.ttf",
]

_cache_fontes = {}


def _fonte(tamanho):
    """Carrega a fonte no tamanho pedido (com cache)."""
    tamanho = int(tamanho)
    if tamanho in _cache_fontes:
        return _cache_fontes[tamanho]

    fonte = None
    for caminho in FONTES:
        try:
            fonte = ImageFont.truetype(caminho, tamanho)
            break
        except Exception:
            continue
    if fonte is None:
        try:
            fonte = ImageFont.load_default(size=tamanho)
        except TypeError:
            fonte = ImageFont.load_default()

    _cache_fontes[tamanho] = fonte
    return fonte


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

    # Fonte maxima proporcional ao QR (o ajuste automatico reduz se o nome for longo)
    fonte_max = max(12, min(FONTE_MAX_PX, int(qr_px * 0.11)))
    linha_px = int(fonte_max * 1.25)

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
        "qr_px": qr_px, "fonte_max": fonte_max,
        "gap_x": gap_x, "cel_w": cel_w, "cel_h": cel_h, "margem": margem,
        "colunas": colunas, "linhas": linhas,
    }


def capacidade_por_pagina(tamanho_cm):
    """Quantos QR Codes cabem em uma folha A4 com o tamanho informado."""
    lay = _layout(tamanho_cm)
    return lay["colunas"] * lay["linhas"]


def paginas_necessarias(qtd, tamanho_cm):
    return math.ceil(qtd / capacidade_por_pagina(tamanho_cm)) if qtd else 0


def _quebrar_texto(draw, texto, fonte, largura_max, max_linhas=2, truncar=True):
    """
    Quebra o texto em linhas que cabem na largura.
    Se nao couber em 'max_linhas' e truncar=False, retorna None.
    Se truncar=True, corta o excesso e termina com '...'.
    """
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

    cabe = (
        len(linhas) <= max_linhas
        and all(draw.textlength(l, font=fonte) <= largura_max for l in linhas)
    )
    if cabe:
        return linhas
    if not truncar:
        return None

    houve_corte = len(linhas) > max_linhas
    linhas = linhas[:max_linhas]
    for i, linha in enumerate(linhas):
        eh_ultima = (i == len(linhas) - 1)
        sufixo = "..." if (eh_ultima and houve_corte) else ""
        while linha and draw.textlength(linha + sufixo, font=fonte) > largura_max:
            linha = linha[:-1]
            sufixo = "..."
        linhas[i] = linha.rstrip() + sufixo
    return linhas


def _ajustar_nome(draw, nome, largura_max, fonte_max, max_linhas=2):
    """
    Escolhe a MAIOR fonte (entre fonte_max e FONTE_MIN_PX) em que o nome cabe
    em ate 'max_linhas' linhas dentro da largura. Retorna (fonte, linhas, tamanho).
    Se nem a fonte minima servir, corta com '...'.
    """
    for tam in range(int(fonte_max), FONTE_MIN_PX - 1, -1):
        fonte = _fonte(tam)
        linhas = _quebrar_texto(draw, nome, fonte, largura_max, max_linhas, truncar=False)
        if linhas is not None:
            return fonte, linhas, tam

    fonte = _fonte(FONTE_MIN_PX)
    linhas = _quebrar_texto(draw, nome, fonte, largura_max, max_linhas, truncar=True)
    return fonte, linhas, FONTE_MIN_PX


def montar_folha_a4(itens, tamanho_cm=TAMANHO_PADRAO_CM):
    """
    Monta paginas A4 com QR Codes do tamanho pedido (em cm).
    Cada item e um dict: {"nome": "...", "url": "https://..."}.
    O nome e centralizado abaixo do QR, com a fonte ajustada para caber.
    As paginas sao em tons de cinza para economizar memoria.
    """
    lay = _layout(tamanho_cm)
    qr_px = lay["qr_px"]
    colunas, linhas = lay["colunas"], lay["linhas"]
    por_pagina = colunas * linhas
    largura_texto = int(qr_px * 0.96)     # pequena folga nas laterais

    grade_w = colunas * qr_px + (colunas - 1) * lay["gap_x"]
    x_inicio = (A4_LARGURA - grade_w) // 2

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

        # Nome: fonte ajustada automaticamente ao espaco disponivel
        fonte, linhas_texto, tam = _ajustar_nome(
            draw, item["nome"], largura_texto, lay["fonte_max"]
        )
        altura_linha = int(tam * 1.2)
        y_texto = y0 + qr_px + 6
        for texto in linhas_texto:
            largura = draw.textlength(texto, font=fonte)
            draw.text((x0 + (qr_px - largura) / 2, y_texto), texto, fill=0, font=fonte)
            y_texto += altura_linha

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
