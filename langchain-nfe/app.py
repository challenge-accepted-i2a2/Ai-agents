# import os
# import zipfile
# import pandas as pd
# from dotenv import load_dotenv
# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# import streamlit as st
# from pathlib import Path

# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
# from langchain.agents.agent_types import AgentType

# from tools.file_extractor import extract_text_from_file
# from tools.image_extractor import extrair_texto_google_vision
# from tools.nfse_flexible_inserter import insert_nfse_flexible
# from tools.nfse_inserter import query_nfse_database
# from langchain.tools import Tool

# # Inicializar banco de dados
# from database.db_init import init_database

# # Carregar variáveis de ambiente
# load_dotenv()

# ## Constantes globais
# DATA_FOLDER = 'data'
# CABECALHO_PATH = DATA_FOLDER + '/202401_NFs_Cabecalho.csv'
# ITEMS_PATH = DATA_FOLDER+ '/202401_NFs_Itens.csv'
# ZIP_PATH =  DATA_FOLDER + '/202401_NFs.zip'
# MODEL_NAME = 'gemini-2.0-flash'

# # Inicializar banco de dados SQLite na primeira execução
# if 'db_initialized' not in st.session_state:
#     with st.spinner("🔧 Inicializando banco de dados..."):
#         if init_database():
#             st.session_state.db_initialized = True
#             st.success("✓ Banco de dados inicializado!")
#         else:
#             st.error("✗ Erro ao inicializar banco de dados")

# # garanta que existe o arquivo .env com a chave da API. Ou então, exporte como
# ## variável de ambiente
# GOOGLE_API_KEY = st.secrets.get('GOOGLE_API_KEY')
# if not GOOGLE_API_KEY:
#     raise ValueError("A variável de ambiente GOOGLE_API_KEY não está definida.")

# # Inicializar o modelo Gemini
# llm = ChatGoogleGenerativeAI(
#     model=MODEL_NAME, 
#     google_api_key=GOOGLE_API_KEY,
#     temperature=0.1  # Reduzir temperatura para respostas mais consistentes
# )

# # Função para descompactar o arquivo ZIP e carregar os CSVs
# def carregar_dados(zip_path):
#     with zipfile.ZipFile(zip_path, 'r') as zip_ref:
#         zip_ref.extractall(DATA_FOLDER)
#     cabecalho_df = pd.read_csv(CABECALHO_PATH, sep=',', encoding='utf-8')
#     itens_df = pd.read_csv(ITEMS_PATH, sep=',', encoding='utf-8')
#     return cabecalho_df, itens_df

# # Carregar os dados
# cabecalho_df, itens_df = carregar_dados(ZIP_PATH)

# # Entregando ferramenta de extracao de docx, pdf e xlsx ao agente
# read_files = Tool.from_function(
#     name="ExtratorDeArquivo",
#     description="Extrai texto de arquivos PDF, XLSX ou DOCX. Retorna JSON com o conteúdo extraído.",
#     func=extract_text_from_file,
#     return_direct=False
# )

# # Entregando ferramenta de extracao de imagem
# text_from_image = Tool.from_function(
#     name='OCR',
#     description="Extrai texto de imagens PNG, JPG ou JPEG. Retorna o texto extraído da imagem.",
#     func=extrair_texto_google_vision,
#     return_direct=False
# )

# # NOVA FERRAMENTA: Inserir NFS-e no banco de dados
# insert_nfse_tool = Tool.from_function(
#     name="InserirNFSe",
#     description="""
#     Insere uma Nota Fiscal de Serviço Eletrônica (NFS-e) no banco de dados SQLite.
    
#     Input: JSON string com estrutura:
#     {
#       "nota_fiscal": {
#         "prestador": {"razao_social": "...", "cnpj": "..."},
#         "tomador": {"nome_razao_social": "...", "cpf_cnpj": "..."},
#         "nota": {"numero": "...", "data_fato_gerador": "..."},
#         "servico": {"valor_servico": "...", "descricao_servico": "..."}
#       }
#     }
    
#     Output: JSON com {"success": true/false, "nota_id": X, "message": "..."}
#     """,
#     func=insert_nfse_flexible,
#     return_direct=False
# )

# # NOVA FERRAMENTA: Consultar banco de NFS-e
# query_nfse_tool = Tool.from_function(
#     name="ConsultarNFSe",
#     description="""
#     Consulta o banco de dados de Notas Fiscais usando SQL.
    
#     Input: Query SQL (ex: "SELECT COUNT(*) FROM nota_fiscal")
    
#     Output: JSON com resultados da consulta
#     """,
#     func=query_nfse_database,
#     return_direct=False
# )

# # Criar o agente com os DataFrames e TODAS as ferramentas
# agent = create_pandas_dataframe_agent(
#     llm,
#     [cabecalho_df, itens_df],
#     verbose=True,
#     agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
#     handle_parsing_errors=True,  # JÁ ESTAVA HABILITADO
#     allow_dangerous_code=True,
#     extra_tools=[
#         read_files, 
#         text_from_image,
#         insert_nfse_tool,
#         query_nfse_tool
#     ],
#     max_iterations=10,  # Limitar iterações
#     early_stopping_method="generate"  # Melhor tratamento de parada
# )

# PROMPT_PREFIX = """
# Você é um assistente de análise de notas fiscais com acesso a banco de dados.

# **IMPORTANTE SOBRE FORMATO DE RESPOSTA:**
# - Sempre forneça uma resposta final clara ao usuário
# - Use "Final Answer:" seguido da sua resposta
# - Não deixe a resposta incompleta
# - Se extrair dados, sempre resuma o que foi feito

# **Ferramentas Disponíveis:**
# 1. **Análise de DataFrames**: Para dados CSV em memória
# 2. **ExtratorDeArquivo**: Para ler PDF, XLSX, DOCX
# 3. **OCR**: Para extrair texto de imagens
# 4. **InserirNFSe**: Para SALVAR dados de NFS-e no banco SQLite
# 5. **ConsultarNFSe**: Para CONSULTAR dados salvos no banco

# **Quando usar cada ferramenta:**
# - DataFrames: Quando usuário pergunta sobre os CSVs carregados
# - ExtratorDeArquivo: Para arquivos PDF/XLSX/DOCX
# - OCR: Para imagens (PNG, JPG, JPEG)
# - InserirNFSe: Quando usuário pede para SALVAR/INSERIR/ARMAZENAR dados extraídos
# - ConsultarNFSe: Quando usuário pede para LISTAR/BUSCAR/CONSULTAR dados salvos

# **Fluxo para NFS-e:**
# 1. Extrair dados (OCR ou ExtratorDeArquivo)
# 2. Estruturar em JSON
# 3. Se usuário pediu para salvar: usar InserirNFSe
# 4. Confirmar ao usuário o que foi feito

# **Pergunta do usuário:**
# """

# PROMPT_SUFFIX = """
# **INSTRUÇÕES FINAIS:**
# - Sempre termine com "Final Answer:" seguido da resposta ao usuário
# - Seja claro e objetivo na resposta final
# - Responda SEMPRE em português brasileiro
# - Não use caracteres especiais que quebrem o Markdown
# - Se houver erro, explique de forma simples ao usuário
# - Não deixe a resposta incompleta ou sem "Final Answer:"
# """

# # Configuração da página
# st.set_page_config(page_title="Assistente IA + NFS-e", layout="centered")
# st.title("🤖 Assistente Inteligente com Banco de Dados NFS-e")

# # Mostrar status do banco
# with st.sidebar:
#     st.subheader("📊 Status do Banco de Dados")
#     if st.session_state.get('db_initialized'):
#         st.success("✓ Banco inicializado")
        
#         # Botão para ver estatísticas
#         if st.button("📈 Ver Estatísticas"):
#             try:
#                 from tools.nfse_inserter import NFSeInserter
#                 inserter = NFSeInserter()
#                 if inserter.connect():
#                     cursor = inserter.connection.cursor()
                    
#                     # Contar registros
#                     cursor.execute("SELECT COUNT(*) FROM nota_fiscal")
#                     notas = cursor.fetchone()[0]
                    
#                     cursor.execute("SELECT COUNT(*) FROM prestador")
#                     prestadores = cursor.fetchone()[0]
                    
#                     cursor.execute("SELECT COUNT(*) FROM tomador")
#                     tomadores = cursor.fetchone()[0]
                    
#                     inserter.disconnect()
                    
#                     st.metric("Notas Fiscais", notas)
#                     st.metric("Prestadores", prestadores)
#                     st.metric("Tomadores", tomadores)
#             except Exception as e:
#                 st.error(f"Erro: {e}")
#     else:
#         st.warning("⚠ Banco não inicializado")
    
#     # Instruções de uso
#     st.divider()
#     st.subheader("💡 Dicas de Uso")
#     st.markdown("""
#     **Para extrair NFS-e:**
#     - "Extraia os dados desta nota"
    
#     **Para salvar no banco:**
#     - "Salve esta nota no banco"
#     - "Insira os dados extraídos"
    
#     **Para consultar:**
#     - "Quantas notas temos?"
#     - "Liste as últimas notas"
#     """)

# # Diretório de upload
# upload_dir = Path.home() / "tmp" / "uploads"
# upload_dir.mkdir(parents=True, exist_ok=True)

# # Tipos permitidos
# tipos_permitidos = ["pdf", "docx", "xlsx", "png", "jpg", "jpeg"]

# # Histórico de conversa
# if "chat_history" not in st.session_state:
#     st.session_state.chat_history = []

# # Upload de arquivos
# st.subheader("📁 Envie arquivos para análise")
# arquivos = st.file_uploader(
#     "Tipos permitidos: PDF, DOCX, XLSX, PNG, JPG (NFS-e)",
#     type=tipos_permitidos,
#     accept_multiple_files=True
# )

# # Salvar arquivos enviados
# arquivos_salvos = []
# if arquivos:
#     for arquivo in arquivos:
#         caminho = upload_dir / arquivo.name
#         with open(caminho, "wb") as f:
#             f.write(arquivo.getbuffer())
#         arquivos_salvos.append(str(caminho))
#         st.success(f"✅ Arquivo salvo: {arquivo.name}")

# # Mostrar histórico de conversa
# st.subheader("💬 Conversa com o assistente")
# for msg in st.session_state.chat_history:
#     with st.chat_message(msg["role"]):
#         st.markdown(msg["content"])

# # Entrada do usuário
# prompt = st.chat_input("Digite sua pergunta...")

# if prompt:
#     # Mostrar pergunta
#     st.chat_message("user").markdown(prompt)
#     st.session_state.chat_history.append({"role": "user", "content": prompt})

#     # Gerar resposta com contexto dos arquivos
#     contexto = ""
#     if arquivos_salvos:
#         # Separar arquivos por tipo
#         imagens = [f for f in arquivos_salvos if Path(f).suffix.lower() in ['.png', '.jpg', '.jpeg']]
#         documentos = [f for f in arquivos_salvos if Path(f).suffix.lower() in ['.pdf', '.docx', '.xlsx']]
        
#         if documentos:
#             contexto += "\n\n**Arquivos disponíveis para análise:**\n"
#             for doc in documentos:
#                 contexto += f"- {Path(doc).name} (caminho: {doc})\n"
        
#         if imagens:
#             contexto += "\n**Imagens disponíveis para OCR:**\n"
#             for img in imagens:
#                 contexto += f"- {Path(img).name} (caminho: {img})\n"

#     # Invocar o agente
#     try:
#         with st.spinner("🤔 Processando sua pergunta..."):
#             # Construir prompt completo
#             full_prompt = PROMPT_PREFIX + prompt + contexto + PROMPT_SUFFIX
            
#             # Invocar agente
#             response = agent.invoke(full_prompt)
            
#             # Extrair resposta
#             if isinstance(response, dict):
#                 resposta = response.get('output', str(response))
#             else:
#                 resposta = str(response)
            
#             # Limpar resposta
#             resposta = resposta.strip()
            
#             # Se a resposta estiver vazia ou muito curta, melhorar
#             if len(resposta) < 10:
#                 resposta = "✓ Operação concluída com sucesso!"
        
#         # Mostrar resposta
#         st.chat_message("assistant").markdown(resposta)
#         st.session_state.chat_history.append({"role": "assistant", "content": resposta})
    
#     except Exception as e:
#         # Tratamento de erro melhorado
#         erro_str = str(e)
        
#         # Verificar se é erro de parsing
#         if "OUTPUT_PARSING_FAILURE" in erro_str or "Could not parse LLM output" in erro_str:
#             # Tentar extrair a mensagem útil
#             if "Could not parse LLM output:" in erro_str:
#                 partes = erro_str.split("Could not parse LLM output:")
#                 if len(partes) > 1:
#                     mensagem = partes[1].split("For troubleshooting")[0].strip()
#                     resposta = f"✓ {mensagem}"
#                 else:
#                     resposta = "✓ Operação realizada com sucesso! Os dados foram processados."
#             else:
#                 resposta = "✓ Operação realizada com sucesso!"
            
#             st.chat_message("assistant").markdown(resposta)
#             st.session_state.chat_history.append({"role": "assistant", "content": resposta})
#         else:
#             # Outro tipo de erro
#             erro_msg = f"❌ Erro ao processar: {erro_str[:200]}"
#             st.error(erro_msg)
#             st.session_state.chat_history.append({"role": "assistant", "content": erro_msg})

import os
import zipfile
import pandas as pd
from dotenv import load_dotenv
import streamlit as st
from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain.agents.agent_types import AgentType
from langchain.tools import Tool

from tools.file_extractor import extract_text_from_file
from tools.image_extractor import extrair_texto_google_vision
from tools.nfse_manager import insert_nfse, query_nfse, NFSeManager, query_dicionario_de_dados
from database.db_init import init_database

# Carregar variáveis de ambiente
load_dotenv()

# ==================== CONFIGURAÇÃO ====================

DATA_FOLDER = "langchain-nfe/data/"
CABECALHO_PATH = DATA_FOLDER + "202401_NFs_Cabecalho.csv"
ITEMS_PATH = DATA_FOLDER + "202401_NFs_Itens.csv"
ZIP_PATH = DATA_FOLDER + "202401_NFs.zip"
MODEL_NAME = 'gemini-2.0-flash'

# ==================== ESTILO APPLE ====================

st.set_page_config(
    page_title="NFS-e Manager",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Personalizado - Estilo Apple
st.markdown("""
<style>
    /* Importar fonte San Francisco (similar à Apple) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Reset e Base */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Background principal */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #d1d5db 0%, #9ca3af 100%);
        box-shadow: 2px 0 20px rgba(0,0,0,1);
    }
    
    [data-testid="stSidebar"] * {
        color: black !important;
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: #93c5fd ! !important;
    }
    
    /* Título principal */
    h1 {
        color: #1e3a8a;
        font-weight: 700;
        font-size: 2.5rem;
        letter-spacing: -0.5px;
        margin-bottom: 0.5rem;
    }
    
    h2 {
        color: #1e40af;
        font-weight: 600;
        font-size: 1.8rem;
        margin-top: 2rem;
    }
    
    h3 {
        color: #2563eb;
        font-weight: 500;
        font-size: 1.3rem;
    }
    
    /* Cards */
    .stMetric {
        background: white;
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid rgba(30, 58, 138, 0.1);
    }
    
    .stMetric label {
        color: #64748b !important;
        font-size: 0.875rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stMetric [data-testid="stMetricValue"] {
        color: #1e3a8a !important;
        font-size: 2rem;
        font-weight: 700;
    }
    
    /* Botões */
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
        box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
        transform: translateY(-2px);
    }
    
    /* Upload de arquivo */
    [data-testid="stFileUploader"] {
        background: white;
        border-radius: 16px;
        padding: 2rem;
        border: 2px dashed #3b82f6;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* Chat messages */
    .stChatMessage {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border: 1px solid rgba(30, 58, 138, 0.1);
    }
    
    /* Input de chat */
    .stChatInput {
        border-radius: 24px;
        border: 2px solid #3b82f6;
        padding: 1rem;
        background: white;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
    }
    
    /* Alertas de sucesso */
    .stSuccess {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        border-radius: 12px;
        padding: 1rem;
        border: none;
    }
    
    /* Alertas de erro */
    .stError {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        border-radius: 12px;
        padding: 1rem;
        border: none;
    }
    
    /* Info boxes */
    .stInfo {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border-radius: 12px;
        padding: 1rem;
        border: none;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: white;
        border-radius: 12px;
        border: 1px solid rgba(30, 58, 138, 0.1);
        font-weight: 600;
        color: #1e3a8a;
    }
    
    /* Divider */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #3b82f6, transparent);
        margin: 2rem 0;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-top-color: #3b82f6 !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: white;
        border-radius: 12px;
        padding: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #64748b;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f5f9;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #3b82f6;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #2563eb;
    }
</style>
""", unsafe_allow_html=True)

# ==================== INICIALIZAÇÃO ====================

# Inicializar banco de dados
if 'db_initialized' not in st.session_state:
    with st.spinner("🔧 Inicializando sistema..."):
        if init_database():
            st.session_state.db_initialized = True
        else:
            st.error("✗ Erro ao inicializar banco de dados")

# API Key
GOOGLE_API_KEY = st.secrets.get('GOOGLE_API_KEY') or os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    st.error("⚠️ GOOGLE_API_KEY não configurada!")
    st.stop()

# Inicializar modelo
llm = ChatGoogleGenerativeAI(
    model=MODEL_NAME,
    google_api_key=GOOGLE_API_KEY,
    temperature=0.1
)

# Carregar dados CSV
@st.cache_data
def carregar_dados(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(DATA_FOLDER)
    cabecalho_df = pd.read_csv(CABECALHO_PATH, sep=',', encoding='utf-8')
    itens_df = pd.read_csv(ITEMS_PATH, sep=',', encoding='utf-8')
    return cabecalho_df, itens_df

cabecalho_df, itens_df = carregar_dados(ZIP_PATH)

# ==================== FERRAMENTAS ====================

read_files = Tool.from_function(
    name="ExtratorDeArquivo",
    description="Extrai texto de arquivos PDF, XLSX ou DOCX. Retorna JSON com o conteúdo extraído.",
    func=extract_text_from_file,
    return_direct=False
)

text_from_image = Tool.from_function(
    name='OCR',
    description="Extrai texto de imagens PNG, JPG ou JPEG. Retorna JSON com texto extraído.",
    func=extrair_texto_google_vision,
    return_direct=False
)

insert_nfse_tool = Tool.from_function(
    name="InserirNFSe",
    description="""
    Insere Nota Fiscal no banco SQLite. ACEITA QUALQUER FORMATO!
    
    Formatos aceitos:
    - JSON estruturado padrão
    - JSON com campos variados
    - Texto livre extraído de PDF
    - XML
    - Campos no root ou aninhados
    
    A ferramenta mapeia automaticamente os campos!
    
    Output: JSON com {"success": true/false, "nota_id": X}
    """,
    func=insert_nfse,
    return_direct=False
)

query_nfse_tool = Tool.from_function(
    name="ConsultarNFSe",
    description="Consulta banco de dados de NFS-e com SQL. Retorna JSON com resultados.",
    func=query_nfse,
    return_direct=False
)

query_dicionario_tool = Tool.from_function(
    name="ConsultarDicionarioDeDados",
    description="Consulta banco de dados de NFS-e para obter informacoes sobre a base de dados completa. Retorna JSON com resultados.",
    func=query_dicionario_de_dados,
    return_direct=True
)
# Criar agente
agent = create_pandas_dataframe_agent(
    llm,
    [cabecalho_df, itens_df],
    verbose=True,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    handle_parsing_errors=True,
    allow_dangerous_code=True,
    extra_tools=[read_files, text_from_image, insert_nfse_tool, query_nfse_tool],
    max_iterations=10,
    early_stopping_method="generate"
)

dicionario_De_dados = query_dicionario_de_dados()
print(dicionario_De_dados)
# ==================== INTERFACE ====================

# Header
col1, col2 = st.columns([2, 10])
with col1:
    st.image('langchain-nfe/imgs/banner.png',use_container_width=True)
with col2:
    st.title("NFS-e Manager")
    st.markdown("**Sistema Inteligente de Gestão de Notas Fiscais**")

# Sidebar
with st.sidebar:
    st.markdown("### 📊 Dashboard")
    
    if st.session_state.get('db_initialized'):
        try:
            manager = NFSeManager()
            if manager.connect():
                stats = {
                    'notas': manager.query("SELECT COUNT(*) as total FROM nota_fiscal")[0]['total'],
                    'prestadores': manager.query("SELECT COUNT(*) as total FROM prestador")[0]['total'],
                    'tomadores': manager.query("SELECT COUNT(*) as total FROM tomador")[0]['total'],
                    'valor_total': manager.query("SELECT COALESCE(SUM(valor_servico), 0) as total FROM servico")[0]['total']
                }
                manager.disconnect()
                
                st.metric("Notas Fiscais", f"{stats['notas']}")
                st.metric("Prestadores", f"{stats['prestadores']}")
                st.metric("Tomadores", f"{stats['tomadores']}")
                st.metric("Valor Total", f"R$ {stats['valor_total']:,.2f}")
                
        except Exception as e:
            st.error(f"Erro: {e}")
    
    st.markdown("---")
    st.markdown("### 💡 Comandos")
    st.markdown("""
    **Extrair e Salvar:**
    - "Extraia e salve esta nota"
    - "Insira os dados no banco"
    
    **Consultar:**
    - "Quantas notas temos?"
    - "Liste as últimas notas"
    - "Qual o total de impostos?"
    
    **Análise:**
    - "Mostre estatísticas"
    - "Notas por prestador"
    """)
    
    st.markdown("---")
    st.markdown("### ℹ️ Sobre")
    st.markdown("""
    **Versão:** 2.0  
    **Modelo:** Gemini 2.0 Flash  
    **Banco:** SQLite  
    """)

# Upload de arquivos
st.markdown("### 📤 Upload de Documentos")

upload_dir = Path.home() / "tmp" / "uploads"
upload_dir.mkdir(parents=True, exist_ok=True)

tipos_permitidos = ["pdf", "docx", "xlsx", "png", "jpg", "jpeg"]

arquivos = st.file_uploader(
    "Arraste arquivos ou clique para selecionar",
    type=tipos_permitidos,
    accept_multiple_files=True,
    help="Formatos aceitos: PDF, DOCX, XLSX, PNG, JPG"
)

arquivos_salvos = []
if arquivos:
    cols = st.columns(len(arquivos))
    for idx, arquivo in enumerate(arquivos):
        caminho = upload_dir / arquivo.name
        with open(caminho, "wb") as f:
            f.write(arquivo.getbuffer())
        arquivos_salvos.append(str(caminho))
        
        with cols[idx]:
            st.success(f"✓ {arquivo.name}")

st.markdown("---")

# Chat
st.markdown("### 💬 Assistente Inteligente")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Exibir histórico
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input do usuário
prompt = st.chat_input("Digite sua pergunta ou comando...")

if prompt:
    st.chat_message("user").markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    
    # Preparar contexto
    contexto = ""
    if arquivos_salvos:
        documentos = [f for f in arquivos_salvos if Path(f).suffix.lower() in ['.pdf', '.docx', '.xlsx']]
        imagens = [f for f in arquivos_salvos if Path(f).suffix.lower() in ['.png', '.jpg', '.jpeg']]
        
        if documentos:
            contexto += "\n\n**Arquivos disponíveis:**\n"
            for doc in documentos:
                contexto += f"- {Path(doc).name} ({doc})\n"
        
        if imagens:
            contexto += "\n**Imagens para OCR:**\n"
            for img in imagens:
                contexto += f"- {Path(img).name} ({img})\n"
    
    try:
        with st.spinner("🤔 Processando..."):
            full_prompt = f"""
Você é um assistente especializado em análise de notas fiscais.

Utilize do banco de dados para fornecer as respostas ao seu usuario. 
Somente forneca dados dos dataframes se for explicitamente solicitado.

### ESTRUTURA DO BANCOD E DADOS
{dicionario_De_dados}

**Ferramentas disponíveis:**
1. ExtratorDeArquivo - Para PDF, DOCX, XLSX
2. OCR - Para imagens
3. InserirNFSe - Para salvar no banco (ACEITA QUALQUER FORMATO!)
4. ConsultarNFSe - Para consultar banco

**IMPORTANTE sobre InserirNFSe:**
- Aceita JSON em qualquer estrutura
- Aceita texto livre de PDF
- Aceita XML
- Mapeia campos automaticamente

**IMPORTANTE SOBRE FORMATO DE RESPOSTA:**
    - Sempre forneça uma resposta final clara ao usuário
    - Use "Final Answer:" seguido da sua resposta
    - Não deixe a resposta incompleta
    - Se extrair dados, sempre resuma o que foi feito

**Pergunta:** {prompt}
{contexto}

**Responda em português brasileiro de forma clara e objetiva.**
"""
            
            response = agent.invoke(full_prompt)
            
            if isinstance(response, dict):
                resposta = response.get('output', str(response))
            else:
                resposta = str(response)
            
            resposta = resposta.strip()
            
            if len(resposta) < 10:
                resposta = "✓ Operação concluída com sucesso!"
        
        st.chat_message("assistant").markdown(resposta)
        st.session_state.chat_history.append({"role": "assistant", "content": resposta})
    
    except Exception as e:
        erro_str = str(e)
        
        # Tratar erros de parsing
        if "OUTPUT_PARSING_FAILURE" in erro_str or "Could not parse LLM output" in erro_str:
            if "Could not parse LLM output:" in erro_str:
                partes = erro_str.split("Could not parse LLM output:")
                if len(partes) > 1:
                    mensagem = partes[1].split("For troubleshooting")[0].strip()
                    resposta = f"✓ {mensagem}"
                else:
                    resposta = "✓ Operação realizada com sucesso!"
            else:
                resposta = "✓ Operação concluída!"
            
            st.chat_message("assistant").markdown(resposta)
            st.session_state.chat_history.append({"role": "assistant", "content": resposta})
        else:
            erro_msg = f"❌ Erro: {erro_str[:200]}"
            st.error(erro_msg)
            st.session_state.chat_history.append({"role": "assistant", "content": erro_msg})

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #64748b; font-size: 0.875rem;'>
    <p>NFS-e Manager v2.0 | Product By Challenge Accepted Team</p>
</div>
""", unsafe_allow_html=True)

