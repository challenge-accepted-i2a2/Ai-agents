import os
import zipfile
import pandas as pd
from dotenv import load_dotenv
import streamlit as st

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain.agents.agent_types import AgentType

# Carregar variáveis de ambiente
load_dotenv()

# Constantes globais
DATA_FOLDER = 'data'
CABECALHO_PATH = os.path.join(DATA_FOLDER, '202401_NFs_Cabecalho.csv')
ITEMS_PATH = os.path.join(DATA_FOLDER, '202401_NFs_Itens.csv')
ZIP_PATH = os.path.join(DATA_FOLDER, '202401_NFs.zip')
MODEL_NAME = 'gemini-2.0-flash'

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

# Criar o agente com os DataFrames
agent = create_pandas_dataframe_agent(
    llm,
    [cabecalho_df, itens_df],
    verbose=True,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    handle_parsing_errors=True,
    allow_dangerous_code=True
)

PROMPT_PREFIX = """
You are an invoice analyzer.
The provided dataframes represents different invoice detail level, being identified unically by the 'CHAVE DE ACESSO' column. The first dataframe have consolidated invoice information, that is, each line represents a unique invoice. The second dataframe details each invoice item.
First set the pandas display options to show all columns.
Get the column names, then answer the question.
"""

PROMPT_SUFFIX = """
- Before giving the final answer, try other methods. Reflect on the results of the two methods and then ask yourself if it answers correctly the original question.
- Do not make up an answer or use your prior knowledge, only use the results of the calculations you have done.
- The final answer should be user oriented and friendly, so, you don't have to explain your thought chain.
- Do not use special characters in the final answer
"""

def main():
    print("Invoice Analyzer Agent is running. Type 'exit' to quit.")
    while True:
        question = input("\nAsk a question: ")
        if question.lower() in ['exit', 'quit']:
            print("Goodbye!")
            break
        try:
            response = agent.invoke(PROMPT_PREFIX + question + PROMPT_SUFFIX)
            print("\nAnswer:", response['output'])
        except Exception as e:
            print("Error:", str(e))

if __name__ == "__main__":
    main()
