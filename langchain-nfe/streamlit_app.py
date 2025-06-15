import streamlit as st
import requests

# Ative ou desative o modo de depuração
modo_debug = True  # Altere para False em produção

st.title("Análise de CSV")

# Inicializa o histórico de mensagens
if "messages" not in st.session_state:
    st.session_state.messages = []

# Exibe o histórico
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Função para chamar a API e processar a resposta
def get_api_response(question):
    try:

        response = requests.post(
            "http://localhost:8000/ask",
            headers={"Content-Type": "application/json"},
            json={"question": question}
        )
        if response.status_code == 200:
            return response.json().get("answer", "Resposta não encontrada.")
        else:
            try:
                error_detail = response.json().get("detail", "")
                if "Could not parse LLM output:" in error_detail:
                    parsed_message = error_detail.split("Could not parse LLM output:")[-1].strip()
                    if modo_debug:
                        return (
                            "**⚠️ Erro na resposta do modelo de linguagem.**\n\n"
                            "O conteúdo retornado não pôde ser interpretado corretamente:\n\n"
                            f"```\n{parsed_message}\n```"
                        )
                    else:
                        return "⚠️ Ocorreu um problema ao interpretar a resposta. Tente novamente mais tarde."
                else:
                    if modo_debug:
                        return f"**Erro na API ({response.status_code})**: {error_detail}"
                    else:
                        return "⚠️ A API retornou um erro. Tente novamente mais tarde."
            except Exception as parse_error:
                return f"Erro ao processar erro da API: {parse_error}"
    except Exception as e:
        return f"Erro ao conectar com a API: {e}"

# Interface de chat
if prompt := st.chat_input("Faça uma pergunta para a API..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response = get_api_response(prompt)
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
