import io
import os

from PIL import Image, ImageOps
from werkzeug.utils import secure_filename

LIMITE_BYTES = 5 * 1024 * 1024      # 5 MB por certificado (depois de processado)
LADO_MAXIMO = 2200                  # px: fotos maiores sao reduzidas


def processar_certificado(arquivo):
    """
    Valida e prepara o arquivo enviado. Retorna (nome, tipo, bytes).
    Aceita PDF, JPG e PNG (conferidos pelo conteudo, nao so pela extensao).
    Imagens sao reduzidas e salvas como JPEG para economizar espaco.
    Levanta ValueError com mensagem amigavel se algo estiver errado.
    """
    dados = arquivo.read()
    if not dados:
        raise ValueError("O arquivo enviado está vazio.")

    nome_original = secure_filename(arquivo.filename or "") or "certificado"
    base = os.path.splitext(nome_original)[0][:100] or "certificado"

    if dados[:5] == b"%PDF-":
        tipo, extensao = "application/pdf", ".pdf"

    elif dados[:3] == b"\xff\xd8\xff" or dados[:8] == b"\x89PNG\r\n\x1a\n":
        try:
            img = Image.open(io.BytesIO(dados))
            img = ImageOps.exif_transpose(img)          # corrige foto girada do celular
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
                fundo = Image.new("RGB", img.size, "white")
                fundo.paste(img, mask=img.split()[3])
                img = fundo
            else:
                img = img.convert("RGB")
            img.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
            saida = io.BytesIO()
            img.save(saida, "JPEG", quality=82, optimize=True)
            dados = saida.getvalue()
        except Exception:
            raise ValueError("Não foi possível ler a imagem. Tente outra foto.")
        tipo, extensao = "image/jpeg", ".jpg"

    else:
        raise ValueError(
            "Formato não aceito. Envie PDF, JPG ou PNG "
            "(fotos em HEIC do iPhone devem ser salvas como JPG)."
        )

    if len(dados) > LIMITE_BYTES:
        raise ValueError(
            f"O arquivo tem {len(dados) / 1024 / 1024:.1f} MB. O limite é 5 MB. "
            "Para PDF, reduza o tamanho do escaneamento."
        )

    return base + extensao, tipo, dados


def aplicar_certificado(registro, arquivo, remover=False):
    """
    Grava (ou remove) o certificado no registro do curso.
    Retorna True se houve alteracao. Levanta ValueError se o arquivo for invalido.
    """
    if arquivo is not None and getattr(arquivo, "filename", ""):
        nome, tipo, dados = processar_certificado(arquivo)
        registro.certificado_nome = nome
        registro.certificado_tipo = tipo
        registro.certificado_dados = dados
        return True

    if remover:
        registro.certificado_nome = None
        registro.certificado_tipo = None
        registro.certificado_dados = None
        return True

    return False
