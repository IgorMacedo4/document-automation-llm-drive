import sys
import os
import threading
from datetime import datetime

sys.path.append(os.path.abspath('.'))

import customtkinter as ctk
import logging

from src.controllers.kit_controller import GeracaoKitController

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class TextHandler(logging.Handler):
    def __init__(self, text_widget, progress_callback=None):
        super().__init__()
        self.text_widget = text_widget
        self.progress_callback = progress_callback

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.after(0, self._append_text, msg)

        if self.progress_callback:
            if "Conectando" in msg or "Buscando" in msg:
                self.progress_callback(0.3)
            elif "arquivo(s)" in msg:
                self.progress_callback(0.5)
            elif "Analisando" in msg or "Dados extraídos" in msg:
                self.progress_callback(0.7)

    def _append_text(self, msg):
        current = self.text_widget.get("0.0", "end-1c")
        if current:
            self.text_widget.insert("end", "\n" + msg)
        else:
            self.text_widget.insert("end", msg)
        self.text_widget.see("end")


class KitAcidentarioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Automação Kit Acidentário")
        self.root.geometry("850x650")
        self.root.resizable(False, False)

        self.controller = None
        self.processing = False

        self.setup_ui()
        self.setup_logging()

    def setup_ui(self):
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=40, pady=30)

        title_label = ctk.CTkLabel(main_frame,
                                   text="Automação Kit Acidentário",
                                   font=("Segoe UI", 24, "bold"),
                                   text_color="#2c3e50")
        title_label.pack(pady=(0, 30))

        input_container = ctk.CTkFrame(main_frame, fg_color="transparent")
        input_container.pack(fill="x", pady=(0, 20))

        input_label = ctk.CTkLabel(input_container,
                                   text="Link da Pasta do Cliente",
                                   font=("Segoe UI", 13, "bold"),
                                   text_color="#2c3e50",
                                   anchor="w")
        input_label.pack(fill="x", padx=(60, 0), pady=(0, 8))

        self.link_entry = ctk.CTkEntry(input_container,
                                       height=38,
                                       font=("Segoe UI", 11),
                                       placeholder_text="https://drive.google.com/drive/folders/...",
                                       border_width=1,
                                       corner_radius=6)
        self.link_entry.pack(fill="x", padx=60)
        self.link_entry.bind('<Return>', lambda e: self.gerar_kit())
        self.link_entry.bind('<Control-a>', self._select_all)
        self.link_entry.bind('<Control-A>', self._select_all)

        self.gerar_button = ctk.CTkButton(main_frame,
                                         text="Gerar Kit Acidentário",
                                         font=("Segoe UI", 11, "bold"),
                                         height=38,
                                         width=180,
                                         corner_radius=6,
                                         fg_color="#2c3e50",
                                         hover_color="#34495e",
                                         command=self.gerar_kit)
        self.gerar_button.pack(pady=(0, 25))

        progress_container = ctk.CTkFrame(main_frame, fg_color="transparent")
        progress_container.pack(fill="x", padx=60, pady=(0, 15))

        self.progress_bar = ctk.CTkProgressBar(progress_container,
                                               height=6,
                                               corner_radius=3,
                                               fg_color="#e0e0e0",
                                               progress_color="#2c3e50")
        self.progress_bar.pack(side="left", fill="x", expand=True)
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(progress_container,
                                         text="",
                                         font=("Segoe UI", 14),
                                         width=30)
        self.status_label.pack(side="right", padx=(10, 0))

        progress_container.pack_forget()
        self.progress_container = progress_container

        logs_label = ctk.CTkLabel(main_frame,
                                 text="Log de Execução",
                                 font=("Segoe UI", 13, "bold"),
                                 text_color="#2c3e50",
                                 anchor="w")
        logs_label.pack(fill="x", pady=(0, 8))

        log_container = ctk.CTkFrame(main_frame, fg_color="#fafafa", corner_radius=6, border_width=1, border_color="#d0d0d0")
        log_container.pack(fill="both", expand=True)

        self.log_text = ctk.CTkTextbox(log_container,
                                       font=("Segoe UI", 12),
                                       fg_color="#fafafa",
                                       text_color="#2c3e50",
                                       corner_radius=0,
                                       border_width=0,
                                       wrap="word",
                                       activate_scrollbars=True)
        self.log_text.pack(fill="both", expand=True, padx=1, pady=1)

        copyright_label = ctk.CTkLabel(self.root,
                                      text="Automação de Documentos",
                                      font=("Segoe UI", 9),
                                      text_color="#95a5a6")
        copyright_label.pack(side="bottom", pady=(0, 10))

    def setup_logging(self):
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                             datefmt='%H:%M:%S')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        text_handler = TextHandler(self.log_text, self._update_progress)
        text_handler.setLevel(logging.INFO)
        text_handler.addFilter(lambda record: 'file_cache is only supported' not in record.getMessage())
        formatter = logging.Formatter('%(asctime)s - %(message)s',
                                     datefmt='%H:%M:%S')
        text_handler.setFormatter(formatter)
        logger.addHandler(text_handler)

    def _update_progress(self, value):
        self.root.after(0, self.progress_bar.set, value)

    def _select_all(self, event):
        self.link_entry.select_range(0, 'end')
        self.link_entry.icursor('end')
        return 'break'

    def log_message(self, message, level='INFO'):
        timestamp = datetime.now().strftime('%H:%M:%S')

        colors = {
            'SUCCESS': '#27ae60',
            'ERROR': '#e74c3c',
            'WARNING': '#f39c12',
            'INFO': '#2c3e50'
        }

        current = self.log_text.get("0.0", "end-1c")
        if current:
            self.log_text.insert("end", f"\n{timestamp} - {message}")
        else:
            self.log_text.insert("end", f"{timestamp} - {message}")

        self.log_text.see("end")

    def gerar_kit(self):
        if self.processing:
            return

        link = self.link_entry.get().strip()

        if not link:
            self.log_message("Por favor, insira o link da pasta do cliente", 'ERROR')
            return

        if not link.startswith("https://drive.google.com/drive/folders/"):
            self.log_message("Link inválido. Use um link do Google Drive", 'ERROR')
            return

        self.processing = True
        self.gerar_button.configure(state='disabled', fg_color='#95a5a6', text="Processando...")
        self.progress_container.pack(fill="x", padx=60, pady=(0, 15))
        self.progress_bar.set(0.1)
        self.status_label.configure(text="", text_color="#2c3e50")

        self.log_message("=" * 50, 'INFO')
        self.log_message("Iniciando nova geração de kit...", 'INFO')
        self.log_message("=" * 50, 'INFO')

        thread = threading.Thread(target=self._processar_kit, args=(link,))
        thread.daemon = True
        thread.start()

    def _processar_kit(self, link):
        try:
            if not self.controller:
                self.controller = GeracaoKitController()

            resultado = self.controller.gerar_kit_from_folder(link)

            self.root.after(0, self.progress_bar.set, 0.9)
            self.root.after(0, self._exibir_resultado, resultado)

        except Exception as e:
            self.root.after(0, self._exibir_erro, str(e))

    def _exibir_resultado(self, resultado):
        self.log_message("=" * 50, 'INFO')

        if resultado['success']:
            self.progress_bar.set(1.0)
            self.status_label.configure(text="✓", text_color="#27ae60")
            self.log_message(f"✓ Kit gerado com sucesso!", 'SUCCESS')
            self.log_message(f"Cliente: {resultado['nome_cliente']}", 'SUCCESS')
            self.log_message(f"Link: {resultado['link']}", 'INFO')
        else:
            self.status_label.configure(text="✗", text_color="#e74c3c")
            self.log_message(f"✗ Erro ao gerar kit", 'ERROR')
            self.log_message(f"Mensagem: {resultado['error']}", 'ERROR')

        self.log_message("=" * 50, 'INFO')
        self.log_message("", 'INFO')

        self.processing = False
        self.gerar_button.configure(state='normal', fg_color='#2c3e50', text="Gerar Kit Acidentário")

    def _exibir_erro(self, erro):
        self.status_label.configure(text="✗", text_color="#e74c3c")
        self.log_message("=" * 50, 'INFO')
        self.log_message(f"✗ Erro fatal: {erro}", 'ERROR')
        self.log_message("=" * 50, 'INFO')
        self.log_message("", 'INFO')

        self.processing = False
        self.gerar_button.configure(state='normal', fg_color='#2c3e50', text="Gerar Kit Acidentário")


if __name__ == "__main__":
    root = ctk.CTk()
    app = KitAcidentarioApp(root)
    root.mainloop()
