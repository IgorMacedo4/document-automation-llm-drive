import sys
import os

sys.path.append(os.path.abspath('.'))

from src.controllers.kit_controller import GeracaoKitController
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

if __name__ == "__main__":
    try:
        controller = GeracaoKitController()
        folder_link = "https://drive.google.com/drive/folders/1m44U3rukbASLFWon8ewunDZbwF_47Ns-"

        resultado = controller.gerar_kit_from_folder(folder_link)

        if resultado['success']:
            print(f"\nCliente: {resultado['nome_cliente']}")
            print(f"Link: {resultado['link']}\n")
        else:
            print(f"\nErro: {resultado['error']}\n")

    except KeyboardInterrupt:
        print("\nOperação cancelada pelo usuário")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        sys.exit(1)
