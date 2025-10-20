import base64
import requests
from pathlib import Path
import streamlit as st
import re

def extrair_texto_google_vision(diretorio: str) -> str:
    """
    Extrai texto da imagem mais recente no diretório especificado usando a API Google Vision.
    
    Args:
        diretorio: Caminho do diretório contendo as imagens (pode ser relativo ou absoluto)
    
    Returns:
        Texto extraído da imagem ou mensagem de erro
    """
    try:
        # Obter a chave da API
        key = st.secrets.get("GOOGLE_API_KEY")
        if not key:
            return "Chave da API Google Vision não encontrada em st.secrets."

        url = f"https://vision.googleapis.com/v1/images:annotate?key={key}"
        
        # Converter o diretório para Path
        pasta = Path(diretorio)
        
        # Se o caminho não for absoluto, tenta resolver relativamente
        if not pasta.is_absolute():
            # Tenta primeiro como caminho relativo ao diretório de trabalho atual
            if not pasta.exists():
                # Se não existir, tenta relativo ao arquivo atual (se __file__ estiver disponível)
                try:
                    pasta = Path(__file__).parent.parent / diretorio
                except NameError:
                    # Se __file__ não estiver disponível, usa o diretório atual
                    pasta = Path.cwd() / diretorio
        
        print(f"Procurando imagens em: {pasta.resolve()}")
        
        # Verificar se o diretório existe
        if not pasta.exists():
            return f"Diretório não encontrado: {pasta.resolve()}"
        
        if not pasta.is_dir():
            return f"O caminho não é um diretório: {pasta.resolve()}"

        # Buscar imagens válidas no diretório
        extensoes_validas = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
        imagens = sorted(
            [f for f in pasta.iterdir() if f.is_file() and f.suffix.lower() in extensoes_validas],
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )

        if not imagens:
            return f"Nenhuma imagem válida encontrada em: {pasta.resolve()}"

        imagem_path = imagens[0]
        print(f"Processando imagem: {imagem_path}")

        # Ler e codificar a imagem em base64
        with open(imagem_path, "rb") as img_file:
            imagem_base64 = base64.b64encode(img_file.read()).decode("utf-8")

        # Preparar o payload para a API
        payload = {
            "requests": [
                {
                    "image": {"content": imagem_base64},
                    "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                    "imageContext": {"languageHints": ["pt"]}
                }
            ]
        }

        # Fazer a requisição para a API
        response = requests.post(url, json=payload)
        response.raise_for_status()

        # Processar a resposta
        resultado = response.json()
        
        texto = resultado["responses"][0].get("fullTextAnnotation", {}).get("text", "")
        if not texto:
            return {"erro": "Nenhum texto detectado na imagem."}

        # === 3️⃣ Pré-processar texto ===
        texto_limpo = texto.replace("\n", " ").strip()

        # === 4️⃣ Extrair padrões ===
        emitente = re.search(r"Emitente[:\s]*(.*?)(?=Destinatário|CNPJ|CPF|$)", texto_limpo, re.IGNORECASE)
        destinatario = re.search(r"Destinatário[:\s]*(.*?)(?=Emitente|CNPJ|CPF|$)", texto_limpo, re.IGNORECASE)
        cnpj_emitente = re.search(r"CNPJ[:\s]*([\d./-]+)", texto_limpo)
        cnpj_destinatario = re.findall(r"CNPJ[:\s]*([\d./-]+)", texto_limpo)
        cnpj_destinatario = cnpj_destinatario[1] if len(cnpj_destinatario) > 1 else None

        # Itens (tentativa simples de capturar linhas com descrição + qtd + valor)
        itens = re.findall(r"([\w\s\-.,]+)\s+(\d+(?:,\d+)?)\s+([\d.,]+)", texto_limpo)

        # Impostos
        icms = re.search(r"ICMS[:\s]*([\d.,]+)%?", texto_limpo)
        ipi = re.search(r"IPI[:\s]*([\d.,]+)%?", texto_limpo)
        pis = re.search(r"PIS[:\s]*([\d.,]+)%?", texto_limpo)
        cofins = re.search(r"COFINS[:\s]*([\d.,]+)%?", texto_limpo)

        # Códigos fiscais
        cfop = re.search(r"CFOP[:\s]*(\d+)", texto_limpo)
        cst = re.search(r"CST[:\s]*(\d+)", texto_limpo)

        # === 5️⃣ Montar resultado estruturado ===
        dados_extraidos = {
            "emitente": {
                "nome": emitente.group(1).strip() if emitente else None,
                "cnpj": cnpj_emitente.group(1) if cnpj_emitente else None,
            },
            "destinatario": {
                "nome": destinatario.group(1).strip() if destinatario else None,
                "cnpj": cnpj_destinatario,
            },
            "itens": [
                {"descricao": i[0].strip(), "quantidade": i[1], "valor": i[2]}
                for i in itens
            ] if itens else [],
            "impostos": {
                "ICMS": icms.group(1) if icms else None,
                "IPI": ipi.group(1) if ipi else None,
                "PIS": pis.group(1) if pis else None,
                "COFINS": cofins.group(1) if cofins else None,
            },
            "codigos_fiscais": {
                "CFOP": cfop.group(1) if cfop else None,
                "CST": cst.group(1) if cst else None,
            },
            "texto_completo": texto.strip(),
        }
        
        return dados_extraidos

    except requests.exceptions.HTTPError as e:
        return {"erro": f"Erro HTTP: {str(e)} — {response.text}"}
    except Exception as e:
        return {"erro": f"Erro ao processar a nota: {str(e)}"}