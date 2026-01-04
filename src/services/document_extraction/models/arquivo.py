from io import BytesIO

class Arquivo:
    
    def __init__(self,
                 file_id: str,
                 file_name: str,
                 parents: list[str],
                 mime_type: str,
                 content: BytesIO = None,
                 ):
        
        self.file_id = file_id
        self.file_name = file_name
        self.parents = parents
        self.mime_type = mime_type
        self.content = content
        self.file_size = None
    