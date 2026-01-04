import os
from dotenv import load_dotenv
from src.infrastructure.google_api import GoogleApiService
from src.utils.logger import setup_logger
from src.utils.exceptions import TemplateNaoEncontradoError

load_dotenv()

logger = setup_logger(__name__)

class EditorKitAcidentario:

    def __init__(self, google_api_service: GoogleApiService):
        self.google_api_service = google_api_service
        self.modelo_doc_id = os.getenv('TEMPLATE_ID', '1gxntpnK68RYiNQTXKDacyobYbBOhSlYj')

        if not self.modelo_doc_id or self.modelo_doc_id == 'your_google_drive_template_id_here':
            logger.warning("TEMPLATE_ID não configurado, usando valor padrão")
            self.modelo_doc_id = '1gxntpnK68RYiNQTXKDacyobYbBOhSlYj'

    def _editar_kit(self, doc_id: str, substituicoes: dict):
        try:
            logger.debug(f"Editando kit com {len(substituicoes)} substituição(ões)")

            all_requests = []
            if substituicoes:
                for antigo, novo in substituicoes.items():
                    logger.debug(f"'{antigo}' → '{novo[:50]}{'...' if len(novo) > 50 else ''}'")
                    all_requests.append({
                        'replaceAllText': {
                            'containsText': {'text': antigo, 'matchCase': False},
                            'replaceText': novo
                        }
                    })

            if all_requests:
                logger.debug(f"Enviando {len(all_requests)} substituição(ões)")
                self.google_api_service.docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': all_requests}
                ).execute()
                logger.debug("Substituições aplicadas")
            else:
                logger.warning("Nenhuma substituição para aplicar")

        except Exception as e:
            logger.error(f"Erro ao editar kit: {type(e).__name__} - {e}")
            raise TemplateNaoEncontradoError(f"Erro ao editar o kit: {str(e)}")

    def _copiar_modelo_kit(self, pasta_destino_id: str) -> str:
        try:
            logger.debug(f"Copiando template (ID: {self.modelo_doc_id[:15]}...)")

            file_metadata = {
                'parents': [pasta_destino_id],
                'name': 'Kit Acidentário - Automação',
                'mimeType': 'application/vnd.google-apps.document'
            }

            logger.debug("Executando cópia via API")
            novo_arquivo = self.google_api_service.service.files().copy(
                fileId=self.modelo_doc_id,
                body=file_metadata
            ).execute()

            novo_id = novo_arquivo.get('id')
            if not novo_id:
                logger.error("API não retornou ID do arquivo")
                raise TemplateNaoEncontradoError("Erro ao copiar template: ID não retornado")

            logger.debug(f"Template copiado (ID: {novo_id[:15]}...)")
            return novo_id

        except Exception as e:
            logger.error(f"Erro ao copiar template: {type(e).__name__} - {e}")
            raise TemplateNaoEncontradoError(f"Erro ao copiar template do kit: {str(e)}")

    def gerar_kit(self, folder_link: str, substituicoes: dict) -> str:
        try:
            logger.debug("Iniciando geração do kit")
            folder_id = folder_link.split('/')[-1]
            logger.debug(f"Pasta destino: {folder_id[:15]}...")

            doc_id = self._copiar_modelo_kit(folder_id)

            if doc_id:
                self._editar_kit(doc_id, substituicoes)
                logger.info("Kit gerado com sucesso")
            else:
                logger.error("Template não foi copiado")
                raise TemplateNaoEncontradoError("Erro ao gerar kit: template não foi copiado")

            return doc_id

        except TemplateNaoEncontradoError:
            raise
        except Exception as e:
            logger.error(f"Erro ao gerar kit: {type(e).__name__} - {e}")
            raise TemplateNaoEncontradoError(f"Erro ao gerar kit: {str(e)}")