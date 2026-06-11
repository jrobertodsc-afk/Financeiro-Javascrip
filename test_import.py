import sys
import os
import asyncio
import io
from fastapi import UploadFile

sys.path.append(os.path.dirname(__file__))
from backend.main import api_importar_xml

async def test():
    file_path = r'C:\Users\Roberto\Downloads\33260505097747000123550010000133751821006164 (1).xml'
    with open(file_path, 'rb') as f:
        content = f.read()
    
    upload_file = UploadFile(filename='test.xml', file=io.BytesIO(content))
    res = await api_importar_xml([upload_file])
    print("Result:", res)

asyncio.run(test())
