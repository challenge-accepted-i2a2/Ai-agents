"""
Módulo de Inicialização do Banco de Dados SQLite para NFS-e
Cria automaticamente todas as tabelas necessárias e insere o dicionário de dados
"""

import sqlite3
import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Classe para inicializar o banco de dados SQLite"""
    
    def __init__(self, db_path: str = None):
        """
        Inicializa o gerenciador do banco de dados.
        
        Args:
            db_path: Caminho para o arquivo do banco. Se None, usa 'data/nfse.db'
        """
        if db_path is None:
            # Criar diretório data se não existir
            data_dir = Path(__file__).parent.parent / 'data'
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / 'nfse.db')
        
        self.db_path = db_path
        self.connection = None
    
    def connect(self) -> bool:
        """Conecta ao banco de dados"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.execute("PRAGMA foreign_keys = ON")
            logger.info(f"✓ Conectado ao banco: {self.db_path}")
            return True
        except sqlite3.Error as e:
            logger.error(f"✗ Erro ao conectar: {e}")
            return False
    
    def disconnect(self):
        """Desconecta do banco de dados"""
        if self.connection:
            self.connection.close()
            logger.info("✓ Conexão fechada")
    
    def create_tables(self):
        """Cria todas as tabelas necessárias"""
        logger.info("→ Criando tabelas...")
        
        cursor = self.connection.cursor()
        
        # Tabela: prestador
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prestador (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                razao_social TEXT NOT NULL,
                cnpj TEXT NOT NULL UNIQUE,
                endereco TEXT,
                cep TEXT,
                bairro TEXT,
                municipio TEXT,
                inscricao_municipal TEXT,
                inscricao_estadual TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_prestador_inscricao_municipal 
            ON prestador(inscricao_municipal)
        """)
        
        # Tabela: tomador
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tomador (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_razao_social TEXT NOT NULL,
                cpf_cnpj TEXT NOT NULL,
                inscricao_municipal TEXT,
                endereco TEXT,
                numero TEXT,
                complemento TEXT,
                bairro TEXT,
                cep TEXT,
                cidade_estado TEXT,
                telefone TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tomador_cpf_cnpj ON tomador(cpf_cnpj)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tomador_nome ON tomador(nome_razao_social)")
        
        # Tabela: atividade_municipio
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS atividade_municipio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT NOT NULL UNIQUE,
                descricao TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabela: atividade_nacional
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS atividade_nacional (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT NOT NULL UNIQUE,
                descricao TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabela: local_prestacao
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS local_prestacao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT NOT NULL UNIQUE,
                municipio TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabela: nota_fiscal
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nota_fiscal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT NOT NULL,
                serie TEXT,
                situacao TEXT,
                tipo TEXT,
                identificador TEXT UNIQUE,
                data_fato_gerador DATE,
                data_hora_emissao DATETIME,
                codigo_verificacao TEXT,
                autenticidade_url TEXT,
                prestador_id INTEGER NOT NULL,
                tomador_id INTEGER NOT NULL,
                observacoes TEXT,
                outras_informacoes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (prestador_id) REFERENCES prestador(id),
                FOREIGN KEY (tomador_id) REFERENCES tomador(id)
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nota_numero ON nota_fiscal(numero)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nota_prestador ON nota_fiscal(prestador_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nota_tomador ON nota_fiscal(tomador_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nota_data ON nota_fiscal(data_fato_gerador)")
        
        # Tabela: servico
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS servico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nota_fiscal_id INTEGER NOT NULL,
                codigo_servico TEXT,
                local_prestacao TEXT,
                aliquota REAL,
                valor_servico REAL NOT NULL,
                desconto_incondicionado REAL,
                valor_deducao REAL,
                valor_iss REAL,
                natureza_operacao TEXT,
                descricao_servico TEXT,
                valor_total REAL,
                desconto_incondicional REAL,
                deducao REAL,
                base_calculo REAL,
                issqn REAL,
                issrf REAL,
                ir REAL,
                inss REAL,
                csll REAL,
                cofins REAL,
                pis REAL,
                outras_retencoes REAL,
                total_tributos_federais REAL,
                desconto_condicional REAL,
                valor_liquido REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (nota_fiscal_id) REFERENCES nota_fiscal(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_servico_nota ON servico(nota_fiscal_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_servico_codigo ON servico(codigo_servico)")
        
        # Tabela: servico_atividade
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS servico_atividade (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                servico_id INTEGER NOT NULL,
                atividade_municipio_id INTEGER,
                atividade_nacional_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (servico_id) REFERENCES servico(id) ON DELETE CASCADE,
                FOREIGN KEY (atividade_municipio_id) REFERENCES atividade_municipio(id),
                FOREIGN KEY (atividade_nacional_id) REFERENCES atividade_nacional(id)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_servico_atividade_servico 
            ON servico_atividade(servico_id)
        """)
        
        # Tabela: dicionario_dados
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dicionario_dados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tabela TEXT NOT NULL,
                coluna TEXT NOT NULL,
                tipo_dado TEXT NOT NULL,
                tamanho TEXT,
                permite_nulo TEXT NOT NULL,
                chave TEXT,
                descricao TEXT NOT NULL,
                exemplo TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_dicionario_tabela_coluna 
            ON dicionario_dados(tabela, coluna)
        """)
        
        # Triggers para updated_at
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_prestador_timestamp 
            AFTER UPDATE ON prestador
            BEGIN
                UPDATE prestador SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_tomador_timestamp 
            AFTER UPDATE ON tomador
            BEGIN
                UPDATE tomador SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_nota_fiscal_timestamp 
            AFTER UPDATE ON nota_fiscal
            BEGIN
                UPDATE nota_fiscal SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_servico_timestamp 
            AFTER UPDATE ON servico
            BEGIN
                UPDATE servico SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """)
        
        self.connection.commit()
        logger.info("✓ Tabelas criadas com sucesso")
    
    def insert_dictionary(self):
        """Insere o dicionário de dados"""
        logger.info("→ Inserindo dicionário de dados...")
        
        cursor = self.connection.cursor()
        
        # Verificar se já existe dados
        cursor.execute("SELECT COUNT(*) FROM dicionario_dados")
        if cursor.fetchone()[0] > 0:
            logger.info("  Dicionário já existe, pulando inserção")
            return
        
        # Dados do dicionário (resumido para brevidade)
        dicionario = [
            # Prestador
            ('prestador', 'id', 'INTEGER', None, 'NAO', 'PK', 'Chave primária auto-incremento', '1'),
            ('prestador', 'razao_social', 'TEXT', None, 'NAO', None, 'Razão social do prestador', 'ANY QUESTION PESQUISAS'),
            ('prestador', 'cnpj', 'TEXT', None, 'NAO', 'UK', 'CNPJ do prestador', '02.956.036/0001-07'),
            
            # Tomador
            ('tomador', 'id', 'INTEGER', None, 'NAO', 'PK', 'Chave primária auto-incremento', '1'),
            ('tomador', 'nome_razao_social', 'TEXT', None, 'NAO', 'INDEX', 'Nome ou razão social do tomador', 'JOÃO DA SILVA'),
            ('tomador', 'cpf_cnpj', 'TEXT', None, 'NAO', 'INDEX', 'CPF ou CNPJ do tomador', '123.456.789-00'),
            
            # Nota Fiscal
            ('nota_fiscal', 'id', 'INTEGER', None, 'NAO', 'PK', 'Chave primária auto-incremento', '1'),
            ('nota_fiscal', 'numero', 'TEXT', None, 'NAO', 'INDEX', 'Número da nota fiscal', '104'),
            ('nota_fiscal', 'identificador', 'TEXT', None, 'SIM', 'UK', 'Código identificador único', '87711908...'),
            
            # Serviço
            ('servico', 'id', 'INTEGER', None, 'NAO', 'PK', 'Chave primária auto-incremento', '1'),
            ('servico', 'nota_fiscal_id', 'INTEGER', None, 'NAO', 'FK', 'FK para nota_fiscal', '1'),
            ('servico', 'valor_servico', 'REAL', None, 'NAO', None, 'Valor do serviço', '500.00'),
        ]
        
        cursor.executemany("""
            INSERT INTO dicionario_dados 
            (tabela, coluna, tipo_dado, tamanho, permite_nulo, chave, descricao, exemplo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, dicionario)
        
        self.connection.commit()
        logger.info(f"✓ Dicionário inserido ({len(dicionario)} registros)")
    
    def get_stats(self) -> dict:
        """Retorna estatísticas do banco"""
        cursor = self.connection.cursor()
        stats = {}
        
        tables = ['prestador', 'tomador', 'nota_fiscal', 'servico', 
                  'atividade_municipio', 'atividade_nacional', 'dicionario_dados']
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        
        return stats
    
    def initialize(self):
        """Inicializa o banco completo"""
        logger.info("="*70)
        logger.info("INICIALIZANDO BANCO DE DADOS NFS-e")
        logger.info("="*70)
        
        if not self.connect():
            return False
        
        try:
            self.create_tables()
            self.insert_dictionary()
            
            # Mostrar estatísticas
            stats = self.get_stats()
            logger.info("\n" + "="*70)
            logger.info("ESTATÍSTICAS DO BANCO")
            logger.info("="*70)
            for table, count in stats.items():
                logger.info(f"  {table}: {count} registros")
            
            logger.info("\n✓ Banco de dados inicializado com sucesso!")
            logger.info(f"✓ Localização: {self.db_path}")
            logger.info("="*70 + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Erro na inicialização: {e}")
            return False
        finally:
            self.disconnect()


def init_database(db_path: str = None) -> bool:
    """
    Função auxiliar para inicializar o banco de dados.
    
    Args:
        db_path: Caminho do banco. Se None, usa 'data/nfse.db'
    
    Returns:
        True se inicializado com sucesso
    """
    initializer = DatabaseInitializer(db_path)
    return initializer.initialize()


if __name__ == "__main__":
    # Teste standalone
    init_database()

