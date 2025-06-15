<!-- PROJECT LOGO -->
<br />
<div align="center">

  <h3 align="center">Agente NFE com Langchain</h3>

  <p align="center">
    Tutorial de como subir a aplicação
  </p>
</div>

<p align="center">
  <img src="./imgs/banner.png" >
</p>

## Estrutura dos arquivos

<p align="justify">
&ensp;&ensp;&ensp;&ensp;Abaixo é apresentada a estrutura de arquivos e diretórios. Note que há dois arquivos Python principais:
</p>

- `app.py`: para subir uma API que recebe a pergunta e retorna a resposta
- `main.py`: execução independente sem a API. Ou seja, basta preencher a pergunta no arquivo e executar.


```
├── app.py                              ## Arquivo principal para subir aplicação FastAPI
├── call.sh                             ## Arquivo auxiliar para fazer requisição CURL na API
├── data                                ## Diretório para armazenamento dos dados
│   ├── 202401_NFs_Cabecalho.csv        ## Arquivo do Cabeçalho das notas fiscais
│   ├── 202401_NFs_Itens.csv            ## Arquivo dos Items das notas fiscais
│   └── 202401_NFs.zip                  ## Arquivo compactado com os dois CSVs
├── main.py                             ## Arquivo para a execução sem o uso de API
├── README.md                           ## Arquivo com explicação e tutorial para executar
└── requirements.txt                    ## Dependências Python
```


## Pré-Requisitos
- Python >= 3.12
- API Key Google Gemini

## Configurando o Ambiente
**0. ⚠️ Crie um arquivo de env para armazenar a API Key do modelo ⚠️**
<p align="justify">
&ensp;&ensp;&ensp;&ensp;Crie um arquivo chamado `.env` no diretório da aplicação e coloque chave da API do modelo. Não se preocupe, pois o `.env` está no .gitignore e não será versionado. Segue um exemplo:
</p>

```txt
GOOGLE_API_KEY=cole_aqui_sua_chave
```

**1. Criação da env python e instalação de dependências**
<p align="justify">
&ensp;&ensp;&ensp;&ensp;esta etapa cada um pode fazer do seu jeito (usando virtualenv, conda, poetry, etc.). A maneira a seguir é utilizando o venv:
</p>

```bash
# criar o ambiente virtual com o nome venv
python3 -m venv venv 

# ativar o ambiente virtual
source venv/bin/activate 

# instalar dependências
pip install -r requirements.txt

``` 

**2. Executando e testando**

<p align="justify">
&ensp;&ensp;&ensp;&ensp;Há duas maneiras de executar. Se você quiser executar pelo arquivo simples,  executar com <code>python3 main.py</code> e será solicitado o envio da pergunta. Em seguida, basta digitar.
</p>

<p align="justify">
&ensp;&ensp;&ensp;&ensp;Por outro lado, se quiser subir a API para que ela receba as requisições, siga os passos a seguir:
</p>

1. Subir a API ( o reload permite atualizar a aplicação caso o código seja editado. Bom para testes):
    ```
    uvicorn app:app --reload
    ```

2. Realizar requisições
    
    Neste momento, a API já deverá estar de pé. Aqui, é possível testar usando o `requests` no python, Postman ou via CURL em um terminal. O arquivo `call.sh` possui um exemplo via CURL. Basta colocar sua pergunta no campo `question` e executar:

    ```
    bash call.sh
    ```

    Se seu sistema não permitir a execução do script bash, você pode testar outra maneira (ou então copiar o comando CURL e testar no terminal)
