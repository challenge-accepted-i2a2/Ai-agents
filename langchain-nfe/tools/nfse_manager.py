import sqlite3
import json
import logging
import re
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, Union
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NFSeManager:
    """Gerenciador completo de NFS-e com inserção flexível e consultas"""
    
    def __init__(self, db_path: str = None):
        """
        Inicializa o gerenciador.
        
        Args:
            db_path: Caminho do banco. Se None, usa 'data/nfse.db'
        """
        if db_path is None:
            data_dir = Path(__file__).parent.parent / 'data'
            db_path = str(data_dir / 'nfse.db')
        
        self.db_path = db_path
        self.connection = None
    
    # ==================== CONEXÃO ====================
    
    def connect(self) -> bool:
        """Conecta ao banco de dados"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.execute("PRAGMA foreign_keys = ON")
            return True
        except sqlite3.Error as e:
            logger.error(f"Erro ao conectar: {e}")
            return False
    
    def disconnect(self):
        """Desconecta do banco"""
        if self.connection:
            self.connection.close()
    
    # ==================== NORMALIZAÇÃO ====================
    
    def _normalize_data(self, data: Union[str, Dict, Any]) -> Dict[str, Any]:
        """
        Normaliza dados de entrada para estrutura padrão.
        Aceita: JSON, XML, texto, dicionário, etc.
        """
        if isinstance(data, dict):
            if 'nota_fiscal' in data:
                return data
            return self._auto_map_fields(data)
        
        if isinstance(data, str):
            data = self._clean_input(data)
            
            # Tentar JSON
            try:
                parsed = json.loads(data)
                return self._normalize_data(parsed)
            except json.JSONDecodeError:
                pass
            
            # Tentar XML
            try:
                root = ET.fromstring(data)
                parsed = self._xml_to_dict(root)
                return self._normalize_data(parsed)
            except ET.ParseError:
                pass
            
            # Texto livre
            return self._text_to_structure(data)
        
        # Fallback
        return {
            'nota_fiscal': {
                'prestador': {},
                'tomador': {},
                'nota': {},
                'servico': {}
            }
        }
    
    def _clean_input(self, text: str) -> str:
        """Remove marcadores de código e limpa texto"""
        cleaned = re.sub(r'```json\s*', '', text)
        cleaned = re.sub(r'```xml\s*', '', cleaned)
        cleaned = re.sub(r'```\s*', '', cleaned)
        return cleaned.strip()
    
    def _xml_to_dict(self, element: ET.Element) -> Dict:
        """Converte XML para dicionário"""
        result = {}
        
        if element.attrib:
            result.update(element.attrib)
        
        if element.text and element.text.strip():
            if len(element) == 0:
                return element.text.strip()
            result['_text'] = element.text.strip()
        
        for child in element:
            child_data = self._xml_to_dict(child)
            if child.tag in result:
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
        
        return result
    
    def _text_to_structure(self, text: str) -> Dict[str, Any]:
        """Extrai informações de texto livre usando regex"""
        structure = {
            'nota_fiscal': {
                'prestador': {},
                'tomador': {},
                'nota': {},
                'servico': {}
            }
        }
        
        patterns = {
            'cnpj': r'CNPJ[:\s]*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})',
            'cpf': r'CPF[:\s]*(\d{3}\.\d{3}\.\d{3}-\d{2})',
            'numero_nota': r'(?:N[FºoO]|Nota|NOTA)[:\s#]*(\d+)',
            'valor': r'(?:VALOR|Total|R\$)[:\s]*R?\$?\s*([\d.,]+)',
            'data': r'(?:Data|Emissão)[:\s]*(\d{2}/\d{2}/\d{4})',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1)
                
                if key == 'cnpj':
                    structure['nota_fiscal']['prestador']['cnpj'] = value
                elif key == 'cpf':
                    structure['nota_fiscal']['tomador']['cpf_cnpj'] = value
                elif key == 'numero_nota':
                    structure['nota_fiscal']['nota']['numero'] = value
                elif key == 'valor':
                    structure['nota_fiscal']['servico']['valor_servico'] = value
                elif key == 'data':
                    structure['nota_fiscal']['nota']['data_fato_gerador'] = value
        
        return structure
    
    def _auto_map_fields(self, data: Dict) -> Dict[str, Any]:
        """Mapeia automaticamente campos de estruturas variadas"""
        mapped = {
            'nota_fiscal': {
                'prestador': {},
                'tomador': {},
                'nota': {},
                'servico': {}
            }
        }
        
        field_mapping = {
            'razao_social': ['razao_social', 'razaoSocial', 'nome_prestador', 'prestador_nome'],
            'cnpj': ['cnpj', 'CNPJ', 'cnpj_prestador', 'prestador_cnpj'],
            'nome_razao_social': ['nome', 'razao_social', 'razaoSocial', 'tomador_nome'],
            'cpf_cnpj': ['cpf', 'cnpj', 'CPF', 'CNPJ', 'documento'],
            'numero': ['numero', 'numero_nota', 'nf', 'nota'],
            'data_fato_gerador': ['data', 'data_emissao', 'dataEmissao', 'dt_emissao'],
            'valor_servico': ['valor', 'valor_total', 'valorTotal', 'total'],
            'descricao_servico': ['descricao', 'discriminacao', 'servico', 'desc_servico'],
        }
        
        def find_field(data: Any, possible_keys: list) -> Optional[Any]:
            if isinstance(data, dict):
                for key in possible_keys:
                    if key in data:
                        return data[key]
                for value in data.values():
                    result = find_field(value, possible_keys)
                    if result:
                        return result
            return None
        
        for target_field, source_fields in field_mapping.items():
            value = find_field(data, source_fields)
            if value:
                if target_field in ['razao_social', 'cnpj']:
                    mapped['nota_fiscal']['prestador'][target_field] = value
                elif target_field in ['nome_razao_social', 'cpf_cnpj']:
                    mapped['nota_fiscal']['tomador'][target_field] = value
                elif target_field in ['numero', 'data_fato_gerador']:
                    mapped['nota_fiscal']['nota'][target_field] = value
                elif target_field in ['valor_servico', 'descricao_servico']:
                    mapped['nota_fiscal']['servico'][target_field] = value
        
        return mapped
    
    # ==================== CONVERSÕES ====================
    
    def _parse_decimal(self, value: Any) -> Optional[float]:
        """Converte valor para decimal"""
        if value is None or value == '':
            return None
        try:
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                value = value.replace('R$', '').replace(',', '.').strip()
                if value.count('.') > 1:
                    value = value.replace('.', '', value.count('.') - 1)
                return float(value)
        except (ValueError, AttributeError):
            logger.warning(f"Valor decimal inválido: {value}")
        return None
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Converte data para formato SQLite"""
        if not date_str:
            return None
        
        formats = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(str(date_str), fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        logger.warning(f"Formato de data não reconhecido: {date_str}")
        return None
    
    def _parse_datetime(self, datetime_str: str) -> Optional[str]:
        """Converte string de data/hora para formato SQLite"""
        if not datetime_str:
            return None
        try:
            dt = datetime.strptime(datetime_str, "%d/%m/%Y %H:%M")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            logger.warning(f"Formato de data/hora inválido: {datetime_str}")
            return None
    
    # ==================== INSERÇÃO ====================
    
    def _insert_or_get_prestador(self, prestador_data: Dict[str, Any]) -> Optional[int]:
        """Insere ou recupera ID de um prestador"""
        try:
            cursor = self.connection.cursor()
            
            cnpj = prestador_data.get('cnpj', 'Não informado')
            cursor.execute("SELECT id FROM prestador WHERE cnpj = ?", (cnpj,))
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
            query = """
                INSERT INTO prestador (razao_social, cnpj, endereco, cep, bairro, municipio, 
                                      inscricao_municipal, inscricao_estadual)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            values = (
                prestador_data.get('razao_social', 'Não informado'),
                cnpj,
                prestador_data.get('endereco'),
                prestador_data.get('cep'),
                prestador_data.get('bairro'),
                prestador_data.get('municipio'),
                prestador_data.get('inscricao_municipal'),
                prestador_data.get('inscricao_estadual')
            )
            
            cursor.execute(query, values)
            self.connection.commit()
            return cursor.lastrowid
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao inserir prestador: {e}")
            self.connection.rollback()
            return None
    
    def _insert_or_get_tomador(self, tomador_data: Dict[str, Any]) -> Optional[int]:
        """Insere ou recupera ID de um tomador"""
        try:
            cursor = self.connection.cursor()
            
            cpf_cnpj = tomador_data.get('cpf_cnpj', 'Não informado')
            nome = tomador_data.get('nome_razao_social', 'Não informado')
            
            cursor.execute(
                "SELECT id FROM tomador WHERE cpf_cnpj = ? AND nome_razao_social = ?",
                (cpf_cnpj, nome)
            )
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
            query = """
                INSERT INTO tomador (nome_razao_social, cpf_cnpj, inscricao_municipal, endereco, 
                                    numero, complemento, bairro, cep, cidade_estado, telefone, email)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            values = (
                nome,
                cpf_cnpj,
                tomador_data.get('inscricao_municipal'),
                tomador_data.get('endereco'),
                tomador_data.get('numero'),
                tomador_data.get('complemento'),
                tomador_data.get('bairro'),
                tomador_data.get('cep'),
                tomador_data.get('cidade_estado'),
                tomador_data.get('telefone'),
                tomador_data.get('email')
            )
            
            cursor.execute(query, values)
            self.connection.commit()
            return cursor.lastrowid
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao inserir tomador: {e}")
            self.connection.rollback()
            return None
    
    def insert_nota_fiscal(self, data: Union[str, Dict, Any]) -> Optional[int]:
        """
        Insere nota fiscal de qualquer formato.
        
        Args:
            data: Dados em qualquer formato (JSON, XML, texto, dict)
        
        Returns:
            ID da nota inserida ou None
        """
        try:
            if not self.connection:
                if not self.connect():
                    return None
            
            # Normalizar dados
            normalized = self._normalize_data(data)
            
            # Extrair informações
            nota_info = normalized.get('nota_fiscal', {})
            prestador_data = nota_info.get('prestador', {})
            tomador_data = nota_info.get('tomador', {})
            nota_data = nota_info.get('nota', {})
            servico_data = nota_info.get('servico', {})
            
            # Inserir prestador
            prestador_id = self._insert_or_get_prestador(prestador_data)
            if not prestador_id:
                return None
            
            # Inserir tomador
            tomador_id = self._insert_or_get_tomador(tomador_data)
            if not tomador_id:
                return None
            
            # Verificar duplicata
            cursor = self.connection.cursor()
            identificador = nota_data.get('identificador')
            if identificador:
                cursor.execute("SELECT id FROM nota_fiscal WHERE identificador = ?", (identificador,))
                result = cursor.fetchone()
                if result:
                    logger.warning(f"Nota já existe com ID: {result[0]}")
                    return result[0]
            
            # Inserir nota fiscal
            query_nota = """
                INSERT INTO nota_fiscal (numero, serie, situacao, tipo, identificador, 
                                        data_fato_gerador, data_hora_emissao, codigo_verificacao, 
                                        autenticidade_url, prestador_id, tomador_id, observacoes, 
                                        outras_informacoes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            values_nota = (
                nota_data.get('numero', 'SN'),
                nota_data.get('serie'),
                nota_data.get('situacao'),
                nota_data.get('tipo'),
                identificador,
                self._parse_date(nota_data.get('data_fato_gerador')),
                self._parse_datetime(nota_data.get('data_hora_emissao')),
                nota_data.get('codigo_verificacao'),
                nota_data.get('autenticidade_url'),
                prestador_id,
                tomador_id,
                nota_info.get('observacoes'),
                nota_info.get('outras_informacoes')
            )
            
            cursor.execute(query_nota, values_nota)
            self.connection.commit()
            nota_fiscal_id = cursor.lastrowid
            
            # Inserir serviço
            query_servico = """
                INSERT INTO servico (nota_fiscal_id, codigo_servico, local_prestacao, aliquota, 
                                    valor_servico, desconto_incondicionado, valor_deducao, valor_iss, 
                                    natureza_operacao, descricao_servico, valor_total, desconto_incondicional, 
                                    deducao, base_calculo, issqn, issrf, ir, inss, csll, cofins, pis, 
                                    outras_retencoes, total_tributos_federais, desconto_condicional, valor_liquido)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            aliquota_str = servico_data.get('aliquota', '0')
            if isinstance(aliquota_str, str):
                aliquota_str = aliquota_str.replace('%', '')
            aliquota = self._parse_decimal(aliquota_str)
            
            values_servico = (
                nota_fiscal_id,
                servico_data.get('codigo_servico'),
                servico_data.get('local_prestacao'),
                aliquota,
                self._parse_decimal(servico_data.get('valor_servico')),
                self._parse_decimal(servico_data.get('desconto_incondicionado')),
                self._parse_decimal(servico_data.get('valor_deducao')),
                self._parse_decimal(servico_data.get('valor_iss')),
                servico_data.get('natureza_operacao'),
                servico_data.get('descricao_servico'),
                self._parse_decimal(servico_data.get('valor_total')),
                self._parse_decimal(servico_data.get('desconto_incondicional')),
                self._parse_decimal(servico_data.get('deducao')),
                self._parse_decimal(servico_data.get('base_calculo')),
                self._parse_decimal(servico_data.get('issqn')),
                self._parse_decimal(servico_data.get('issrf')),
                self._parse_decimal(servico_data.get('ir')),
                self._parse_decimal(servico_data.get('inss')),
                self._parse_decimal(servico_data.get('csll')),
                self._parse_decimal(servico_data.get('cofins')),
                self._parse_decimal(servico_data.get('pis')),
                self._parse_decimal(servico_data.get('outras_retencoes')),
                self._parse_decimal(servico_data.get('total_tributos_federais')),
                self._parse_decimal(servico_data.get('desconto_condicional')),
                self._parse_decimal(servico_data.get('valor_liquido'))
            )
            
            cursor.execute(query_servico, values_servico)
            self.connection.commit()
            
            logger.info(f"✓ Nota fiscal {nota_data.get('numero', 'SN')} inserida com ID: {nota_fiscal_id}")
            return nota_fiscal_id
            
        except Exception as e:
            logger.error(f"Erro ao inserir nota fiscal: {e}")
            if self.connection:
                self.connection.rollback()
            return None
    
    # ==================== CONSULTAS ====================
    
    def query(self, sql: str) -> list:
        """
        Executa consulta SQL no banco.
        
        Args:
            sql: Query SQL
        
        Returns:
            Lista de resultados
        """
        try:
            if not self.connection:
                if not self.connect():
                    return []
            
            cursor = self.connection.cursor()
            cursor.execute(sql)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            data = []
            for row in results:
                data.append(dict(zip(columns, row)))
            
            return data
            
        except Exception as e:
            logger.error(f"Erro ao executar query: {e}")
            return []


# ==================== FUNÇÕES PARA AGENTE ====================

def insert_nfse(data: Union[str, Dict, Any]) -> str:
    """
    Função para agente LangChain inserir NFS-e.
    Aceita QUALQUER formato.
    
    Args:
        data: Nota fiscal em qualquer formato
    
    Returns:
        JSON com resultado
    """
    try:
        manager = NFSeManager()
        
        if not manager.connect():
            return json.dumps({
                "success": False,
                "error": "Não foi possível conectar ao banco",
                "nota_id": None
            }, ensure_ascii=False)
        
        nota_id = manager.insert_nota_fiscal(data)
        manager.disconnect()
        
        if nota_id:
            return json.dumps({
                "success": True,
                "message": "Nota fiscal inserida com sucesso!",
                "nota_id": nota_id
            }, ensure_ascii=False, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": "Erro ao processar nota fiscal",
                "nota_id": None
            }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Erro: {str(e)}",
            "nota_id": None
        }, ensure_ascii=False)


def query_dicionario_de_dados():
    """
    Função para agente LangChain consultar dicionario de dados do banco.
    
    Args:
        No arguments
    
    Returns:
        JSON com resultados
    """
    try:
        manager = NFSeManager()
        
        if not manager.connect():
            return json.dumps({
                "success": False,
                "error": "Não foi possível conectar ao banco",
                "data": []
            }, ensure_ascii=False)
        
        sql = "SELECT * FROM dicionario_dados"
      
        results = manager.query(sql)
        manager.disconnect()
        
        return json.dumps({
            "success": True,
            "count": len(results),
            "data": results
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "data": []
        }, ensure_ascii=False)
    

def query_nfse(sql)->str:
    """
    Função para agente LangChain consultar dicionario de dados do banco.
    
    Args:
       sql (str) -> Query sql para ser executada no banco de dados
    
    Returns:
        JSON com resultados
    """
    try:
        manager = NFSeManager()
        
        if not manager.connect():
            return json.dumps({
                "success": False,
                "error": "Não foi possível conectar ao banco",
                "data": []
            }, ensure_ascii=False)

        results = manager.query(sql)
        manager.disconnect()
        
        return json.dumps({
            "success": True,
            "count": len(results),
            "data": results
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "data": []
        }, ensure_ascii=False)


