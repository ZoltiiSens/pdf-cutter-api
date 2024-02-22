from os import remove, listdir
from fastapi import FastAPI, File, Form
from typing import Annotated
from time import time
from PyPDF2 import PdfReader, PdfWriter
from starlette.responses import FileResponse
from starlette.background import BackgroundTask
import requests


app = FastAPI()

WEBHOOK_URL = 'https://google.com'


@app.post("/cut_pdf")
async def create_file(file: Annotated[bytes, File()], configuration: Annotated[str, Form()]):
    try:
        pages = [int(i) for i in configuration.split(",")]
        pages.sort()
    except ValueError:
        return {'error': 'wrong configuration data: incorrect format'}
    filename = f'tmp_{time()}_{len(listdir("."))}.pdf'
    with open(filename, 'wb') as f:
        f.write(file)
        f.close()
    filePDF = PdfReader(filename)
    pdfWriter = PdfWriter()
    try:
        for page in pages:
            pdfWriter.add_page(filePDF.pages[page])
        with open(filename.replace('.pdf', '_new.pdf'), 'wb') as f:
            pdfWriter.write(f)
            f.close()
        response = FileResponse(
            filename.replace('.pdf', '_new.pdf'),
            media_type="application/pdf",
            background=BackgroundTask(cleanup, filename),
        )
    except IndexError:
        remove(filename)
        return {'error': 'wrong configuration data: index out of range'}
    return response


@app.post("/save_pdf")
async def save_pdf(file: Annotated[bytes, File()], configuration: Annotated[str, Form()], fileId: Annotated[str, Form()]):
    try:
        pages = [int(i) for i in configuration.split(",")]
        pages.sort()
    except ValueError:
        return {'error': 'wrong configuration data: incorrect format'}
    path = f'files/{fileId}.pdf'
    with open(path, 'wb') as f:
        f.write(file)
        f.close()
    filePDF = PdfReader(path)
    pdfWriter = PdfWriter()
    try:
        for page in pages:
            pdfWriter.add_page(filePDF.pages[page])
        with open(path, 'wb') as f:
            pdfWriter.write(f)
            f.close()
        # print(requests.post(WEBHOOK_URL, data={'id': f'{fileId}'}).content)                                           # place to put webhook
    except IndexError:
        return {'error': 'wrong configuration data: index out of range'}
    return {'info': 'Done!'}


def cleanup(filename):
    remove(filename)
    remove(filename.replace('.pdf', '_new.pdf'))





# @app.post("/files/")
# async def create_file(file: Annotated[bytes, File()], configuration: Annotated[list, Form()]):
#     print(configuration)
#     return {"file_size": len(file)}





# from fastapi import FastAPI, File, UploadFile
# from typing import Annotated
#
# app = FastAPI()
#
#
# @app.get('/')
# def index():
#     return 'hello'
#
#
# @app.post('/recombine_pdf')
# def recombine_pdf(file: Annotated[bytes, File()]):
#     return {'file': file}
#
#
# @app.post("/files/")
# async def create_file(file: Annotated[bytes, File()]):
#     print(file)
#     filePDF = open('new.pdf', 'wb')
#     filePDF.write(file)
#     # for line in open('code.txt', 'rb').readlines():
#     #     file.write(line)
#
#
#     filePDF.close()
#     return {"file_size": len(file)}
#
#
# @app.post('/recombine_pdf_new')
# def recombine_pdf_new(file: UploadFile):
#     print(file)
#     return {'file': file}
#







#
# from fastapi import FastAPI, File, UploadFile
# from pydantic import BaseModel
#
#
# class DocumentCutModel(BaseModel):
#     configuration: str
#
#
# app = FastAPI()
#
#
# @app.post("/uploadfile/")
# async def create_upload_file(file: UploadFile, configuration: str):
#     print(file)
#     return "123"
#     # contents = await data.file.read()
#     # filePDF = open('new.pdf', 'wb')
#     # print(data.configuration)
#     # filePDF.write(contents)
#     # filePDF.close()
#     # print(contents)
#     # return {"file": data.file}
