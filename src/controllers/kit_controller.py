from src.infrastructure.google_api import GoogleApiService
from src.services.document_extraction.models.pasta import Pasta
from src.services.document_extraction.documents.contrato import Contrato
from src.services.kit_editing.editor_kit import EditorKitAcidentario
from src.services.kit_editing.campos_editaveis import CamposKitAcidentario
from src.utils.logger import setup_logger
from src.utils.exceptions import (
    GoogleApiConnectionError,
    ContratoNaoEncontradoError,
    TemplateNaoEncontradoError,
    ArquivoNaoEncontradoError,
    PastaNaoEncontradaError,
    DadosInvalidosError
)

logger = setup_logger(__name__)

class GeracaoKitController:
    def __init__(self):
        self.google_api = GoogleApiService()
        self.editor_kit = EditorKitAcidentario(self.google_api)

    def gerar_kit_from_folder(self, folder_link: str) -> dict:
        try:
            logger.debug("═" * 60)
            logger.debug("Iniciando processo")
            logger.debug(f"Link: {folder_link[:60]}...")

            # Validar link
            if not folder_link or not folder_link.strip():
                logger.error("Link da pasta está vazio")
                return {
                    'success': False,
                    'error': 'Link da pasta está vazio. Por favor, forneça um link válido.'
                }

            folder_id = folder_link.split('/')[-1]
            logger.debug(f"ID: {folder_id[:20]}...")

            # Criar objeto Pasta e buscar contratos
            logger.info("Conectando ao Google Drive")
            pasta_cliente = Pasta(folder_id, "Pasta do Cliente")

            logger.info("Buscando contratos")
            contratos = pasta_cliente.get_file(pasta_cliente.CONTRATO)

            if not contratos:
                logger.error("Nenhum contrato encontrado")
                return {
                    'success': False,
                    'error': 'Nenhum contrato foi encontrado na pasta do cliente. Verifique se existe um arquivo de contrato válido.'
                }

            logger.debug(f"{len(contratos)} contrato(s) encontrado(s)")

            # Extrair dados do contrato
            dados_cliente = Contrato.from_files(contratos)

            if not dados_cliente.nome_completo or not dados_cliente.qualificacao:
                logger.error("Dados incompletos")
                return {
                    'success': False,
                    'error': 'Dados do cliente estão incompletos. Verifique se o contrato contém nome e qualificação.'
                }

            # Preparar substituições
            substituicoes = {
                CamposKitAcidentario.nome_completo: dados_cliente.nome_completo,
                CamposKitAcidentario.qualificacao: dados_cliente.qualificacao
            }
            logger.debug(f"{len(substituicoes)} campo(s)")

            # Gerar kit
            kit_id = self.editor_kit.gerar_kit(folder_link, substituicoes)

            logger.debug("Processo concluído")

            return {
                'success': True,
                'nome_cliente': dados_cliente.nome_completo,
                'kit_id': kit_id,
                'link': f'https://docs.google.com/document/d/{kit_id}/edit'
            }

        except PastaNaoEncontradaError as e:
            logger.error(f"Pasta não encontrada - {e}")
            return {
                'success': False,
                'error': 'Pasta não encontrada. Verifique se o link está correto e se você tem permissão de acesso.'
            }

        except GoogleApiConnectionError as e:
            logger.debug(f"Falha na conexão com Google - {e}")
            return {
                'success': False,
                'error': str(e)
            }

        except ContratoNaoEncontradoError as e:
            logger.error(f"Problema com o contrato - {e}")
            return {
                'success': False,
                'error': str(e)
            }

        except DadosInvalidosError as e:
            logger.error(f"Dados inválidos - {e}")
            return {
                'success': False,
                'error': str(e)
            }

        except TemplateNaoEncontradoError as e:
            logger.error(f"Problema com o template - {e}")
            return {
                'success': False,
                'error': 'Erro ao processar o template do kit. Entre em contato com o suporte técnico.'
            }

        except ArquivoNaoEncontradoError as e:
            logger.error(f"Arquivo não encontrado - {e}")
            return {
                'success': False,
                'error': 'Erro ao buscar arquivos na pasta. Verifique se a pasta contém os documentos necessários.'
            }

        except Exception as e:
            logger.error(f"ERRO INESPERADO: {type(e).__name__} - {e}")
            import traceback
            logger.debug(f"Traceback:\n{traceback.format_exc()}")
            return {
                'success': False,
                'error': f'Erro inesperado: {type(e).__name__}. Entre em contato com o suporte.'
            }
