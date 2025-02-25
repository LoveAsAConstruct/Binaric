class BinaricFile:
    def __init__(self, file_id, file_type, content, dynamic):
        self.header = {
            "file_id": file_id,
            "file_type": file_type,
            "dynamic" : dynamic, # If true represents a dynamic instance (can respond to requests, etc) if fals then represents prerecorded instance. 
            "checksum": None
        }
        self.content = content
        self.footer = {"end_flag": True}
    
    def compute_checksum(self):
        pass  # Generate checksum
    
    def to_wav(self, filename):
        pass  # Convert file to a BINARIC WAV format