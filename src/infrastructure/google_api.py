import sys
import os
import warnings
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from pathlib import Path
from src.utils.logger import setup_logger
from src.utils.exceptions import GoogleApiConnectionError

warnings.filterwarnings("ignore", message="file_cache is only supported with oauth2client")

logger = setup_logger(__name__)

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_writable_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(os.path.dirname(sys.executable), filename)
    return str(Path(__file__).parent / f'tokens/{filename}')

class GoogleApiService:
    SCOPES = ['https://www.googleapis.com/auth/drive']
    PATH_CREDENTIALS = resource_path('src/infrastructure/tokens/credentials.json')
    PATH_TOKEN = get_writable_path('token.json')

    acess_token = None
    service = None
    docs_service = None

    def __init__(self):
        if not GoogleApiService.acess_token:
            self._get_acess_token()

    def _get_acess_token(self):
        try:
            logger.info("Conectando ao Google Drive")
            creds = None

            if os.path.exists(GoogleApiService.PATH_TOKEN):
                creds = Credentials.from_authorized_user_file(
                    GoogleApiService.PATH_TOKEN, GoogleApiService.SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(GoogleApiService.PATH_CREDENTIALS):
                        logger.error("Arquivo credentials.json não encontrado")
                        raise GoogleApiConnectionError("Arquivo de credenciais não encontrado")

                    flow = InstalledAppFlow.from_client_secrets_file(
                        GoogleApiService.PATH_CREDENTIALS, GoogleApiService.SCOPES)
                    creds = flow.run_local_server(port=0)

                with open(GoogleApiService.PATH_TOKEN, 'w') as token:
                    token.write(creds.to_json())

            GoogleApiService.acess_token = creds.token
            GoogleApiService.service = build('drive', 'v3', credentials=creds)
            GoogleApiService.docs_service = build('docs', 'v1', credentials=creds)

        except Exception as e:
            logger.error(f"Erro ao conectar com Google Drive: {e}")
            raise GoogleApiConnectionError(f"Falha na conexão com Google Drive: {str(e)}")

    def search(self, query, fields="nextPageToken, files(id, name, parents, mimeType)", page_size=1000):
        import requests
        try:
            logger.debug("Buscando arquivos no Drive")
            url = f'https://www.googleapis.com/drive/v3/files?q={query}&pageSize={page_size}&fields={fields}'
            headers = {'Authorization': f'Bearer {GoogleApiService.acess_token}'}
            response = requests.get(url, headers=headers)

            if response.status_code == 404:
                logger.error(f"Pasta não encontrada no Drive")
                raise GoogleApiConnectionError("Pasta não encontrada. Verifique se o link está correto e se você tem permissão de acesso.")

            if response.status_code != 200:
                logger.error(f"Erro ao acessar Google Drive (Status {response.status_code})")
                raise GoogleApiConnectionError(f"Erro ao acessar Google Drive (Status {response.status_code})")

            result = response.json()

            if 'error' in result:
                logger.error(f"Erro do Google Drive: {result['error'].get('message', 'Erro desconhecido')}")
                raise GoogleApiConnectionError(f"Erro do Google Drive: {result['error'].get('message', 'Erro desconhecido')}")

            files_count = len(result.get('files', []))
            logger.debug(f"Busca concluída: {files_count} arquivo(s) encontrado(s)")

            return result
        except GoogleApiConnectionError:
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar arquivos: {type(e).__name__} - {e}")
            raise GoogleApiConnectionError(f"Erro ao buscar arquivos no Drive: {str(e)}")

    def batch_download_file(self, file_ids: list[str]) -> list[bytes]:
        import aiohttp
        import asyncio

        if not file_ids:
            logger.debug("Nenhum arquivo para download")
            return []

        logger.debug(f"Iniciando download de {len(file_ids)} arquivo(s)")

        async def download(session, file_id, index):
            url = f'https://www.googleapis.com/drive/v3/files/{file_id}?alt=media'
            headers = {'Authorization': f'Bearer {GoogleApiService.acess_token}'}
            try:
                async with session.get(url, headers=headers) as r:
                    if r.status != 200:
                        logger.error(f"Erro ao baixar arquivo: Status {r.status}")
                        raise GoogleApiConnectionError(f"Erro ao baixar arquivo (Status {r.status})")
                    content = await r.read()
                    logger.debug(f"Arquivo {index + 1}/{len(file_ids)} baixado ({len(content)} bytes)")
                    return content
            except Exception as e:
                logger.error(f"Erro ao baixar arquivo: {e}")
                raise

        async def main():
            async with aiohttp.ClientSession() as session:
                tasks = [download(session, file_id, idx) for idx, file_id in enumerate(file_ids)]
                return await asyncio.gather(*tasks)

        try:
            loop = asyncio.get_running_loop()
            import nest_asyncio
            nest_asyncio.apply()
        except RuntimeError:
            pass

        try:
            result = asyncio.run(main())
            logger.debug(f"Download concluído: {len(result)} arquivo(s)")
            return result
        except Exception as e:
            logger.error(f"Erro ao baixar arquivos: {type(e).__name__} - {e}")
            raise GoogleApiConnectionError(f"Erro ao baixar arquivos do Drive: {str(e)}")
