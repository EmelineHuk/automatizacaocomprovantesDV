import os
import re
import fitz  # PyMuPDF
from pypdf import PdfReader, PdfWriter
import easyocr

# Inicializa o leitor de OCR em português
reader_ocr = easyocr.Reader(['pt'], gpu=False)

def extrair_dados_ocr(pagina_fitz, nome_pdf=""):
    # Renderiza a página PDF como imagem
    pix = pagina_fitz.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("png")

    # Lê o texto visual da imagem
    resultados = reader_ocr.readtext(img_bytes, detail=0)
    texto_completo = " ".join(resultados)

    # 1. DATA (DD/MM/AAAA)
    data_match = re.search(r"(\d{2}/\d{2}/\d{4})", texto_completo)
    if data_match:
        data_raw = data_match.group(1)
    else:
        data_ref = re.search(r"(\d{2}\s+\d{2}\s+\d{4})", nome_pdf)
        data_raw = data_ref.group(1).replace(" ", "/") if data_ref else "00/00/0000"

    data_fmt = data_raw.replace("/", " ")
    partes = data_fmt.split()
    data_pasta = f"{partes[0]} {partes[1]} {partes[2]}" if len(partes) == 3 else "SEM_DATA"

    # 2. BENEFICIÁRIO
    beneficiario = "BENEFICIARIO DESCONHECIDO"
    for idx, item in enumerate(resultados):
        if any(term in item.lower() for term in ["beneficiário", "beneficiario", "razão social"]):
            if idx + 1 < len(resultados):
                beneficiario = resultados[idx + 1]
                break

    beneficiario_limpo = re.sub(r'[\\/*?:"<>|]', '', beneficiario).strip()

    # 3. VALOR NOMINAL
    valor = "0,00"
    valores_encontrados = re.findall(r"(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2})", texto_completo)
    if valores_encontrados:
        valor = valores_encontrados[0]

    return data_pasta, data_fmt, beneficiario_limpo, valor

def processar_comprovantes(pasta_origem="comprovantes"):
    if not os.path.exists(pasta_origem):
        pasta_origem = pasta_origem.upper()
        if not os.path.exists(pasta_origem):
            print(f"A pasta '{pasta_origem}' não foi encontrada.")
            return

    arquivos = [f for f in os.listdir(pasta_origem) if f.lower().endswith(".pdf") and os.path.isfile(os.path.join(pasta_origem, f))]

    if not arquivos:
        print(f"Nenhum arquivo PDF encontrado na pasta '{pasta_origem}'.")
        return

    for arquivo in arquivos:
        caminho_pdf = os.path.join(pasta_origem, arquivo)
        print(f"Processando com OCR: {arquivo}")

        doc_fitz = fitz.open(caminho_pdf)
        reader_pypdf = PdfReader(caminho_pdf)

        for idx, pagina_fitz in enumerate(doc_fitz):
            data_pasta, data_fmt, beneficiario, valor = extrair_dados_ocr(pagina_fitz, arquivo)

            pasta_destino = os.path.join(pasta_origem, data_pasta)
            os.makedirs(pasta_destino, exist_ok=True)

            nome_arquivo = f"{data_fmt} {beneficiario} {valor}.pdf"
            caminho_saida = os.path.join(pasta_destino, nome_arquivo)

            contador = 1
            caminho_saida_final = caminho_saida
            while os.path.exists(caminho_saida_final):
                nome_duplicado = f"{data_fmt} {beneficiario} {valor}_({contador}).pdf"
                caminho_saida_final = os.path.join(pasta_destino, nome_duplicado)
                contador += 1

            writer = PdfWriter()
            writer.add_page(reader_pypdf.pages[idx])

            with open(caminho_saida_final, "wb") as output_file:
                writer.write(output_file)

            print(f"  [OK] Página {idx + 1} -> {caminho_saida_final}")

if __name__ == "__main__":
    processar_comprovantes()