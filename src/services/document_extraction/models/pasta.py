import re
from io import BytesIO
from src.services.document_extraction.models.arquivo import Arquivo
from src.infrastructure.utils.string_manipulation import StringManipulation
from src.infrastructure.google_api import GoogleApiService
from src.utils.logger import setup_logger
from src.utils.exceptions import ArquivoNaoEncontradoError, PastaNaoEncontradaError

logger = setup_logger(__name__)

class FileNames:
    CONTRATO = 'Contrato'

class Pasta(FileNames):

    arquivos = {
        FileNames.CONTRATO: {
            "is_required": False,
            "regras_captura": [
                {
                    "name_contains": [r'contrato|contratos|kit|assinar|cliente|prestacao de servicos'],
                    "not_name_contains": [r'\.png|\.mp4|\.jpg|\.jpeg|auditoria|analise'],
                    "text_contains": [r'\w+'],
                    "not_text_contains": [],
                },
            ]
        },
    }

    def __init__(self, folder_id: str, folder_name: str, documents: list[Arquivo] = None):
        self.folder_id = folder_id
        self.folder_name = folder_name
        self.documents = documents
        self.drive_api = GoogleApiService()
        self.utils = StringManipulation()

    def list_files(self, recursive: bool = False, folder_id: str = None, with_content: bool = True) -> list[Arquivo]:
        folder_id = self.folder_id if not folder_id else folder_id

        logger.debug(f"Listando arquivos da pasta (ID: {folder_id[:15]}...)")

        try:
            query = f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed = false"
            result = self.drive_api.search(query)
            files = result.get('files', [])

            if result.get('files') is None:
                logger.error("Pasta não encontrada ou sem permissão de acesso")
                raise PastaNaoEncontradaError("Pasta não encontrada. Verifique se o link está correto e se você tem permissão de acesso.")

            logger.debug(f"Encontrados {len(files)} arquivo(s) na pasta")

            if recursive:
                for folder in self.drive_api.search(query.replace('!=','=')).get('files', []):
                    files.extend({"id":f.file_id, "name":f.file_name, "mimeType":f.mime_type} for f in self.list_files(recursive=True, folder_id=folder['id']))

            if with_content:
                patterns = r'entrevista|relatorio|relatoiro|relatorio( do)? (acidente|acidental)|resumo_dos_fatos-\d{8,10}\.pdf|questionario|contrato|contratos|kit|assinar|cliente|prestacao de servicos|ctps|carteira de trabalho|cnis|extrato'
                logger.debug("Filtrando arquivos por padrões de nome")
                files_before = len(files)
                files = [f for f in files if re.search(patterns, self.utils.normalize(f['name']))]
                files = [f for f in files if not re.search(r'video|audio', str(f['mimeType']))]
                logger.info(f"{len(files)} arquivo(s) encontrado(s)")

                if files:
                    logger.debug(f"Arquivos: {', '.join([f['name'] for f in files])}")
                    contents = self.drive_api.batch_download_file([f['id'] for f in files])
                    self.documents = [Arquivo(file['id'], file['name'], folder_id, file['mimeType'], BytesIO(content)) for file, content in zip(files, contents)]
                else:
                    logger.warning("Nenhum arquivo relevante encontrado")
                    self.documents = []
            else:
                self.documents = [Arquivo(file['id'], file['name'], self.folder_id, file['mimeType'], None) for file in files]

            return self.documents

        except PastaNaoEncontradaError:
            raise
        except Exception as e:
            logger.debug(f"Erro ao listar arquivos: {type(e).__name__} - {e}")
            raise

    def get_file(self, file_name: str) -> list[Arquivo]:
        logger.debug(f"Buscando arquivo(s) do tipo: {file_name}")

        if file_name not in self.arquivos:
            logger.error(f"Tipo de arquivo inválido: {file_name}")
            raise ArquivoNaoEncontradoError(f'Nome de arquivo "{file_name}" é inválido')

        if not self.documents:
            logger.debug("Listando arquivos da pasta")
            self.list_files()

        logger.debug(f"Aplicando regras em {len(self.documents)} documento(s)")

        filtered_files = []
        for regra_idx, regra in enumerate(self.arquivos[file_name]['regras_captura']):
            logger.debug(f"Aplicando regra {regra_idx + 1}/{len(self.arquivos[file_name]['regras_captura'])}")

            for file in self.documents:
                normalized_name = self.utils.normalize(file.file_name)
                if (
                    all(re.search(term, normalized_name) for term in regra['name_contains']) and
                    all(not re.search(term, normalized_name) for term in regra['not_name_contains'])
                    ):
                    if not regra['text_contains'] and not regra['not_text_contains']:
                        logger.debug(f"'{file.file_name}' corresponde às regras")
                        filtered_files.append(file)
                    else:
                        logger.info(f"Analisando arquivo: {file.file_name}")
                        text = self.utils.extract_text_from_pdf(file.content, 1).lower()
                        if (
                            all(re.search(term, text) for term in regra['text_contains']) and
                            all(not re.search(term, text) for term in regra['not_text_contains'])
                            ):
                            logger.debug(f"'{file.file_name}' corresponde às regras de conteúdo")
                            filtered_files.append(file)

            if filtered_files:
                logger.debug(f"Regra {regra_idx + 1} retornou {len(filtered_files)} arquivo(s)")
                break

        filtrados_unicos = []
        for file in filtered_files:
            if all(file.file_name.replace('Cópia de', '') != filtrado.file_name.replace('Cópia de', '') for filtrado in filtrados_unicos):
                filtrados_unicos.append(file)

        duplicados_removidos = len(filtered_files) - len(filtrados_unicos)
        if duplicados_removidos > 0:
            logger.debug(f"Removidos {duplicados_removidos} duplicado(s)")

        if not filtrados_unicos:
            logger.warning(f"Nenhum arquivo '{file_name}' encontrado")
        else:
            logger.debug(f"{len(filtrados_unicos)} arquivo(s) '{file_name}': {', '.join([f.file_name for f in filtrados_unicos])}")

        return filtrados_unicos
