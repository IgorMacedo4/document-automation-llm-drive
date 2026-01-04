import unicodedata
import re
import os
from io import BytesIO
from PyPDF2 import PdfReader
from time import time

class StringManipulation:
    
    def cpf_formatado(self, cpf):
        if not cpf:
            return cpf
        cpf_sem_sep = re.sub(r'\.|/|-|( )+|\'|,|;', '', cpf)
        cpf_formatado = cpf_sem_sep
        if len(cpf_sem_sep)<11:
            
            for _ in range(11-len(cpf_sem_sep)):
                cpf_sem_sep = '0' +  cpf_sem_sep
                cpf_formatado = '0' + cpf_formatado
            
        for posicao, sep in {3:'.', 7:'.', 11:'-'}.items(): 
            cpf_formatado = cpf_formatado[:posicao] + sep + cpf_formatado[posicao:] 
        
        return cpf_formatado

    def normalize(self, string):
        sem_acentos = (unicodedata.normalize('NFKD', string)
                                  .encode('ASCII', 'ignore')
                                  .decode('ASCII'))
        return re.sub(r'[ ]+', ' ', sem_acentos.lower()).strip()

    # Calculate the Levenshtein distance
    def levenshtein_distance(self, s1, s2):
        if len(s1) < len(s2):
            return self.levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def partial_match(self, str1, str2, max_diff=3):
        # Normalize the strings
        str1 = self.normalize(str1)
        str2 = self.normalize(str2)

        return self.levenshtein_distance(str1, str2) <= max_diff

    def extract_text_from_pdf(self, file: BytesIO, pages: int = None) -> str:
        try:
            reader = PdfReader(file)
            num_pages = pages if pages else len(reader.pages)
            return ''.join([reader.pages[k].extract_text() for k in range(min(num_pages, len(reader.pages)))])
        except Exception as e:
            print(f"Erro ao extrair texto do arquivo: {e}")
            return ""
