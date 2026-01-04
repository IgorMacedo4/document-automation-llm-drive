import re
import sys
sys.path.append('.')

import os
import json
import requests
from dotenv import load_dotenv
from src.services.document_extraction.models.arquivo import Arquivo
from src.infrastructure.utils.string_manipulation import StringManipulation as utils
from src.utils.logger import setup_logger
from src.utils.exceptions import ContratoNaoEncontradoError, DadosInvalidosError

load_dotenv()

utils = utils()
logger = setup_logger(__name__)

class Contrato:
    """
    Classe para extrair a qualificação e o nome completo do cliente,
    a partir do contrato de honorários do cliente,ou do documento chamado "Kit",
    o qual pode conter o contrato ou pode conter as procurações, nas quais constam os dados procurados.
    """
    def __init__(self, 
                 nome_completo: str, qualificacao: str,
                #  wpp: str, cep: str, 
                #  logradouro: str, numero: str, complemento: str,
                #  bairro: str, cidade: str, estado: str
                 ):
        # self.wpp = wpp
        # self.cep = cep
        # self.logradouro = logradouro
        # self.numero = numero
        # self.complemento = complemento
        # self.bairro = bairro
        # self.cidade = cidade
        # self.estado = estado
        self.nome_completo = nome_completo
        self.qualificacao = qualificacao

    @staticmethod
    def _fetch(contrato: str) -> dict:
        logger.debug("Enviando contrato para extração via IA")

        TEMPLATE = f'''
            # Objetivos
                - Analise o contrato de honorários advocatícios abaixo e informe os dados de qualificação do(a) contratante dos serviços advocatícios, no formato nome completo e qualificação (nacionalidade, estado civil, profissão, número do RG, número do CPF, endereço completo, incluindo CEP e o número de celular e/ou de telefone do contratante).

            # Instruções
                - A qualificação deve conter os dados na seguinte ordem: nome completo, nacionalidade, estado civil, profissão, número do RG, número do CPF, endereço completo (incluindo CEP) e o número de celular e/ou de telefone.
                - Se algum dado de qualificação não for encontrado, ignore na qualificação.
                - Após extrair os dados, SEMPRE verifique se há algum erro (exemplo de erro: confundir o nome do bairro com o nome da cidade, palavras grudadas sem espaço) e corrija o erro se houver.
                - Não inclua informações adicionais ou explicações na sua resposta nem caracteres extras além do JSON.

                - O endereço deve ser o endereço do(a) contratante dos serviços advocatícios, e não o endereço do advogado ou escritório de advocacia.
                - O endereço deve ser formatado de modo que apenas a primeira letra de cada palavra esteja em maiúscula, e o restante em minúscula. Exemplo: "R. São Paulo, 123, Centro, São Paulo - SP".
                - Abreviações de logradouro devem ter espaço após o ponto: "R. " (não "R."), "Av. " (não "Av."), "Tv. " (não "Tv."). SEMPRE verifique se há espaço após a abreviação.

                - O número de celular/telefone deve ser o número do(a) contratante dos serviços advocatícios, e não o número do advogado ou escritório de advocacia.
                - O número de celular/telefone deve ser formatado APENAS com DDD entre parênteses, SEM o código do país. Use o formato "Telefone: (xx) xxxxx-xxxx". Exemplo: "Telefone: (11) 91234-5678".
                - NÃO use "cel./tel.", use apenas "Telefone:".
                - NÃO inclua o prefixo +55 do país.

                - Responda no formato JSON, com as chaves "nome_completo" e "qualificacao".

            # Exemplo de resposta correta:
            {{"nome_completo":"JOÃO DA SILVA SOUSA", "qualificacao":"brasileiro, solteiro, engenheiro, portador do RG n. 12.345.678-9 SSP/SP, inscrito no CPF sob o n. 123.456.789-00, residente e domiciliado na R. das Flores, 123, Centro, São Paulo - SP, CEP 01000-000, Telefone: (11) 91234-5678"}}

            # Texto do contrato de honorários para análise:
            <contrato>
            {contrato}
            </contrato>
        '''
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("OPENAI_API_KEY não configurada")
            raise ContratoNaoEncontradoError("Chave da API OpenAI não configurada. Configure a variável OPENAI_API_KEY no arquivo .env")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": [{"type": "text", "text": TEMPLATE}]}],
            "response_format": { "type": "json_object" }
        }

        try:
            logger.debug("Enviando requisição para OpenAI API")
            r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30)

            if r.status_code != 200:
                logger.error(f"Erro na API OpenAI (Status {r.status_code})")
                raise ContratoNaoEncontradoError(f"Erro ao processar contrato via IA (Status {r.status_code})")

            response_json = r.json()

            if 'error' in response_json:
                error_msg = response_json['error'].get('message', 'Erro desconhecido')
                logger.error(f"Erro da OpenAI: {error_msg}")
                raise ContratoNaoEncontradoError(f"Erro da OpenAI: {error_msg}")

            content = response_json.get('choices', [{}])[0].get('message', {}).get('content')

            if not content:
                logger.error("Resposta vazia da OpenAI")
                raise ContratoNaoEncontradoError("Não foi possível extrair dados do contrato (resposta vazia)")

            logger.debug("Processando JSON retornado")
            dados = json.loads(content)

            if not dados.get('nome_completo') or not dados.get('qualificacao'):
                logger.error("Dados extraídos estão incompletos")
                raise DadosInvalidosError("Dados extraídos estão incompletos. Verifique se o contrato contém todas as informações necessárias.")

            logger.info(f"Dados extraídos: {dados.get('nome_completo', 'N/A')}")
            logger.debug(f"Qualificação: {dados.get('qualificacao', 'N/A')[:100]}...")

            return dados

        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON: {e}")
            raise ContratoNaoEncontradoError("Erro ao processar resposta da IA (formato inválido)")
        except requests.Timeout:
            logger.error("Timeout ao conectar com OpenAI")
            raise ContratoNaoEncontradoError("Tempo esgotado ao processar contrato. Tente novamente.")
        except requests.RequestException as e:
            logger.error(f"Erro de conexão com OpenAI: {e}")
            raise ContratoNaoEncontradoError("Erro de conexão ao processar contrato. Verifique sua internet.")
        except (ContratoNaoEncontradoError, DadosInvalidosError):
            raise
        except Exception as e:
            logger.error(f"Erro inesperado: {type(e).__name__} - {e}")
            raise ContratoNaoEncontradoError(f"Erro ao processar contrato: {str(e)}")

    @staticmethod
    def _extract_address_data(files: list[Arquivo]) -> dict:
        logger.debug(f"Iniciando extração de {len(files)} arquivo(s)")

        starts = [r'CONTRATANTE', r'CONTRATANTE|inventariante|OUTORGANTES']
        ends = [r'\nCLÁUSULA', r'\nCLÁUSULA|nomeia|OUTORGADOS']

        # Primeira tentativa: arquivos não físicos/assinados
        logger.debug("Primeira tentativa: arquivos não físicos/assinados")
        for start, end in zip(starts, ends):
            for file in files:
                if not re.search(r'físico|assinado', file.file_name.lower()):
                    try:
                        logger.info(f"Analisando arquivo: {file.file_name}")
                        logger.debug("Extraindo texto do PDF")
                        texto = utils.extract_text_from_pdf(file.content, 4)

                        if not re.search(r'\w+', texto):
                            logger.debug(f"Arquivo sem texto legível")
                            continue

                        logger.debug(f"Buscando padrão '{start}'")
                        starts_match = re.search(start, texto)
                        if not starts_match:
                            logger.debug(f"Padrão não encontrado")
                            continue

                        starts_text = starts_match.group(0)
                        logger.debug(f"Padrão inicial: '{starts_text}'")

                        logger.debug(f"Buscando padrão de término '{end}'")
                        ends_match = re.search(end, texto)
                        if not ends_match:
                            logger.debug(f"Padrão de término não encontrado")
                            continue

                        ends_text = ends_match.group(0)
                        logger.debug(f"Padrão de término: '{ends_text}'")

                        trecho_contrato = texto.split(starts_text)[1].split(ends_text)[0]
                        logger.debug(f"Trecho extraído ({len(trecho_contrato)} caracteres)")

                        return Contrato._fetch(trecho_contrato)

                    except Exception as e:
                        logger.debug(f"Erro: {type(e).__name__} - {e}")

        # Segunda tentativa: todos os arquivos exceto físicos
        logger.debug("Segunda tentativa: todos arquivos (exceto físicos)")
        for start, end in zip(starts, ends):
            for file in files:
                if not re.search(r'físico', file.file_name.lower()):
                    try:
                        logger.debug(f"Tentando: {file.file_name}")
                        texto = utils.extract_text_from_pdf(file.content, 4)

                        if not re.search(r'\w+', texto):
                            logger.debug(f"Sem texto legível")
                            continue

                        starts_match = re.search(start, texto)
                        ends_match = re.search(end, texto)

                        if not starts_match or not ends_match:
                            logger.debug(f"Padrões não encontrados")
                            continue

                        trecho_contrato = texto.split(starts_match.group(0))[1].split(ends_match.group(0))[0]
                        logger.debug(f"Trecho encontrado em '{file.file_name}'")

                        return Contrato._fetch(trecho_contrato)

                    except Exception as e:
                        logger.debug(f"Erro: {type(e).__name__} - {e}")

        logger.error("Nenhum contrato legível encontrado")
        raise ContratoNaoEncontradoError('Nenhum contrato legível foi encontrado. Verifique se os arquivos contêm as seções CONTRATANTE e CLÁUSULA.')

    @classmethod
    def from_files(cls, files: list[Arquivo]):
        dados_extraidos = Contrato._extract_address_data(files)
        return cls(dados_extraidos.get('nome_completo', ''), dados_extraidos.get('qualificacao', ''))

    @property
    def qualificacao_sem_telefone(self) -> str:
        """Qualificação sem o número de telefone"""
        return re.sub(r',\s*Telefone:.*$', '', self.qualificacao)

    def __repr__(self):
        return f'Contrato(nome_completo={self.nome_completo}, qualificacao={self.qualificacao})'

if __name__ == "__main__":
    from models.pasta import Pasta

    pasta = {'files': [{'id': '1qYaAHarJ1JSJP0pLtRRlFk2xNQtT4Dpn', 'name': 'Pasta do Cliente'}]}
    pasta = Pasta(pasta['files'][0]['id'], pasta['files'][0]['name'] )

    contratos = pasta.get_file(pasta.CONTRATO)
    contrato = Contrato.from_files(contratos)

    print(contrato)
