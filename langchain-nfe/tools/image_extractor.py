import json
from pathlib import Path
import streamlit as st


import json
import base64
import requests
from pathlib import Path
import streamlit as st

def extrair_texto_google_vision(image_path: str) -> str:
    try:
        key = st.secrets.get("GOOGLE_API_KEY")
        if not key:
            return json.dumps({"success": False, "error": "Chave da API não encontrada"}, ensure_ascii=False)

        path = Path(image_path)
        if not path.exists():
            return json.dumps({"success": False, "error": "Arquivo não encontrado"}, ensure_ascii=False)

        with open(image_path, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")

        url = f"https://vision.googleapis.com/v1/images:annotate?key={key}"
        body = {
            "requests": [{
                "image": {"content": content},
                "features": [{"type": "TEXT_DETECTION"}]
            }]
        }

        response = requests.post(url, json=body)
        result = response.json()

        if "error" in result:
            return json.dumps({"success": False, "error": result["error"]["message"]}, ensure_ascii=False)

        text = result["responses"][0].get("fullTextAnnotation", {}).get("text", "")

        return json.dumps({
            "success": True,
            "file_path": str(image_path),
            "file_name": path.name,
            "text": text,
            "text_length": len(text),
            "has_content": len(text) > 0,
            "message": "Texto extraído com sucesso" if text else "Nenhum texto encontrado"
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# Manter compatibilidade com versão anterior
def extrair_texto_google_vision_legacy(image_path: str) -> str:
    """
    Versão legada que retorna apenas o texto (para compatibilidade).
    """
    result = extrair_texto_google_vision(image_path)
    try:
        data = json.loads(result)
        if data.get('success'):
            return data.get('text', '')
        else:
            return f"Erro: {data.get('error', 'Erro desconhecido')}"
    except:
        return result