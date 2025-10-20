import os
import zipfile
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import streamlit as st
from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain.agents.agent_types import AgentType

from tools.file_extractor import extract_text_from_file
from tools.image_extractor import extrair_texto_google_vision
from langchain.tools import Tool

# Carregar variáveis de ambiente
load_dotenv()

## Constantes globais
DATA_FOLDER = 'data'
CABECALHO_PATH = DATA_FOLDER + '/202401_NFs_Cabecalho.csv'
ITEMS_PATH = DATA_FOLDER+ '/202401_NFs_Itens.csv'
ZIP_PATH =  DATA_FOLDER + '/202401_NFs.zip'
MODEL_NAME = 'gemini-2.0-flash'

# garanta que existe o arquivo .env com a chave da API. Ou então, exporte como
## variável de ambiente
GOOGLE_API_KEY = st.secrets.get('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("A variável de ambiente GOOGLE_API_KEY não está definida.")

# Inicializar o modelo Gemini
llm = ChatGoogleGenerativeAI(model=MODEL_NAME, google_api_key=GOOGLE_API_KEY)

# Função para descompactar o arquivo ZIP e carregar os CSVs
def carregar_dados(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(DATA_FOLDER)
    cabecalho_df = pd.read_csv(CABECALHO_PATH, sep=',', encoding='utf-8')
    itens_df = pd.read_csv(ITEMS_PATH, sep=',', encoding='utf-8')
    return cabecalho_df, itens_df

# Carregar os dados
cabecalho_df, itens_df = carregar_dados(ZIP_PATH)

# Entregando ferramenta de extracao de docx, pdf e xlsx ao agente
read_files = Tool.from_function(
    name="ExtratorDeArquivo",
    description="Extrai texto de arquivos PDF, XLSX ou DOCX",
    func=extract_text_from_file
)

# Entregando ferramenta de extracao de imagem
text_from_image = Tool.from_function(
    name='OCR',
    description="Extrai texto de imagens",
    func=extrair_texto_google_vision
    )

# Criar o agente com os DataFrames
agent = create_pandas_dataframe_agent(
    llm,
    [cabecalho_df, itens_df],
    verbose=True,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    handle_parsing_errors=True,
    allow_dangerous_code=True, # otherwise it won't work locally
    extra_tools=[read_files, text_from_image ]
)

# # Definir o modelo de entrada para a API
# class QuestionRequest(BaseModel):
#     question: str


PROMPT_PREFIX = """
You are an invoice analyzer.

Analyze the user request to decide which tool use, don't start reading the dataframe altough the use request it.

The provided dataframes represents different invoice detail level, being identified unically by the 'CHAVE DE ACESSO' column. 
The first dataframe have consolidated invoice information, that is, each line represents a unique invoice. 
The second dataframe details each invoice item.
First set the pandas display options to show all columns.
Get the column names, then answer the question in brasilian portuguese.

If the user request to read XLSX, PDF or DOCX data, use the tool: ExtratorDeArquivo
If the user request to extract text from images, use the tool: OCR

### OCR Extraction:
    Information to Extract from the Invoice
    - **Issuer and recipient information**
    - **Invoice items:** description, quantity, and value
    - **Taxes:** ICMS, IPI, PIS, COFINS
    - **Fiscal codes:** CFOP, CST, and other relevant codes


**Question:**
"""

PROMPT_SUFFIX = """
- Before giving the final answer, try other methods. Reflect on the results of the two methods and then ask yourself if it answers correctly the original question.
- Do not make up an answer or use you prior knowldge, only use the results of the calculations you have done.
- The final answer should be user oriented and friendly, so, you don't have to explain you thought chain.
- Do not use special caracters in the final answer
- Always answear the questions in brasilian Portuguese.
- If you need to execute code, use only the Action: section. Do not include a Final Answer: until all actions have been completed.
- Always ensure your entire response is valid Markdown.
"""

# # Inicializar a aplicação FastAPI
# app = FastAPI()

# # Definir o endpoint para responder perguntas
# @app.post("/ask")
# def answer_question(request: QuestionRequest):
#     try:
#         resposta = agent.invoke(PROMPT_PREFIX + request.question + PROMPT_SUFFIX )
#         return {"answer": resposta['output']}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# Configuração da página
st.set_page_config(page_title="Assistente IA", layout="centered")
st.title("🤖 Assistente Inteligente")

# Diretório de upload - CORRIGIDO: usando caminho mais portável
upload_dir = Path.home() / "tmp" / "uploads"
upload_dir.mkdir(parents=True, exist_ok=True)

# Tipos permitidos
tipos_permitidos = ["pdf", "docx", "xlsx", "png", "jpg", "jpeg"]

# Histórico de conversa
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Upload de arquivos
st.subheader("📁 Envie arquivos para análise")
arquivos = st.file_uploader(
    "Tipos permitidos: PDF, DOCX, XLSX, PNG, JPG",
    type=tipos_permitidos,
    accept_multiple_files=True
)

# Salvar arquivos enviados
arquivos_salvos = []
if arquivos:
    for arquivo in arquivos:
        caminho = upload_dir / arquivo.name
        with open(caminho, "wb") as f:
            f.write(arquivo.getbuffer())
        arquivos_salvos.append(str(caminho))
        st.success(f"✅ Arquivo salvo: {arquivo.name}")

# Debug: mostrar arquivos salvos
if arquivos_salvos:
    st.info(f"📂 Diretório de upload: {upload_dir}")
    for a in arquivos_salvos:
        print(f"Arquivo salvo: {a}")

# Mostrar histórico de conversa
st.subheader("💬 Conversa com o assistente")
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Entrada do usuário
prompt = st.chat_input("Digite sua pergunta...")

if prompt:
    # Mostrar pergunta
    st.chat_message("user").markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    # Gerar resposta com contexto dos arquivos (se houver)
    contexto = ""
    if arquivos_salvos:
        # Separar arquivos por tipo
        imagens = [f for f in arquivos_salvos if Path(f).suffix.lower() in ['.png', '.jpg', '.jpeg']]
        documentos = [f for f in arquivos_salvos if Path(f).suffix.lower() in ['.pdf', '.docx', '.xlsx']]
        
        # Adicionar informações dos arquivos ao contexto
        if documentos:
            contexto += "\n\nDocumentos enviados:\n" + "\n".join(documentos)
        
        # Se houver imagens, extrair texto automaticamente
        if imagens:
            contexto += "\n\nImagens enviadas:\n" + "\n".join(imagens)
            # Informar ao agente que há imagens disponíveis para OCR
            contexto += f"\n\nPara extrair texto das imagens, use a ferramenta OCR com o diretório: {upload_dir}"

    # Invocar o agente com o contexto completo
    try:
        with st.spinner("🤔 Processando sua pergunta..."):
            response = agent.invoke(PROMPT_PREFIX + prompt + contexto + PROMPT_SUFFIX)
            resposta = response['output']
        
        # Mostrar resposta
        st.chat_message("assistant").markdown(resposta)
        st.session_state.chat_history.append({"role": "assistant", "content": resposta})
    
    except Exception as e:
        erro_msg = f"❌ Erro ao processar a pergunta: {str(e)}"
        st.error(erro_msg)
        st.session_state.chat_history.append({"role": "assistant", "content": erro_msg})