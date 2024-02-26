import os
from os import remove, listdir
from fastapi import FastAPI, File, Form
from typing import Annotated
from time import time
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.errors import PdfReadError
from starlette.responses import FileResponse
from starlette.background import BackgroundTask
from zipfile import ZipFile
# from PIL import Image
# from pydantic import BaseModel
# import requests


app = FastAPI()
WEBHOOK_URL = 'https://google.com'


# class PdfExtractContentModel(BaseModel):
#     getText: bool = True
#     getImage: bool = True


@app.post('/cut_pdf')
async def create_file(file: Annotated[bytes, File()], configuration: Annotated[str, Form()]):
    """Realises cutting functional and returns resulted PDF-file"""
    try:
        pages = [int(i) for i in configuration.split(",")]
        pages.sort()
    except ValueError:
        return {'error': 'wrong configuration data: incorrect format'}
    filename = f'tmp_{time()}_{len(listdir("."))}.pdf'
    pdf_filename = filename.replace('.pdf', '_new.pdf')
    with open(filename, 'wb') as f:
        f.write(file)
        f.close()
    try:
        filePDF = PdfReader(filename)
    except PdfReadError:
        cleanup(filename)
        return {'error': 'wrong file format'}
    pdfWriter = PdfWriter()
    try:
        for page in pages:
            pdfWriter.add_page(filePDF.pages[page])
        with open(pdf_filename, 'wb') as f:
            pdfWriter.write(f)
            f.close()
        response = FileResponse(
            pdf_filename,
            media_type="application/pdf",
            background=BackgroundTask(cleanup, filename, pdf_filename),
            headers={'Content-Disposition': f'attachment; filename="{pdf_filename}"'},
        )
    except IndexError:
        remove(filename)
        return {'error': 'wrong configuration data: index out of range'}
    return response


@app.post('/save_pdf')
async def save_pdf(file: Annotated[bytes, File()], configuration: Annotated[str, Form()], fileId: Annotated[str, Form()]):
    """Realises cutting functional, saves cut files, send info to webhook and returns info message"""
    try:
        pages = [int(i) for i in configuration.split(",")]
        pages.sort()
    except ValueError:
        return {'error': 'wrong configuration data: incorrect format'}
    path = f'files/{fileId}.pdf'
    with open(path, 'wb') as f:
        f.write(file)
        f.close()
    try:
        filePDF = PdfReader(path)
    except PdfReadError:
        cleanup(path)
        return {'error': 'wrong file format'}
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


@app.post('/pdf/extract_images')
async def extract_images(file: Annotated[bytes, File()]):
    filename = f'tmp_{time()}_{len(listdir("."))}'
    with open(f'{filename}.pdf', 'wb') as f:
        f.write(file)
        f.close()
    try:
        filePDF = PdfReader(f'{filename}.pdf')
    except PdfReadError:
        cleanup(f'{filename}.pdf')
        return {'error': 'wrong file format'}
    pages = filePDF.pages
    counter = 0
    images_filenames = []
    for page in pages:
        for imageFileObject in page.images:
            with open(f'{filename}-{counter}-{imageFileObject.name}', 'wb') as f:
                f.write(imageFileObject.data)
            images_filenames.append(f'{filename}-{counter}-{imageFileObject.name}')
            counter += 1
    if counter:
        zip_filename = zip_files(images_filenames, filename)
        cleanup(f'{filename}.pdf', *images_filenames)
        response = FileResponse(
            zip_filename,
            media_type="application/x-zip-compressed",
            headers={'Content-Disposition': f'attachment; filename="{zip_filename}"'},
            background=BackgroundTask(cleanup, zip_filename),
        )
    else:
        response = {'info': 'there is no images'}
    return response


def zip_files(images_filenames, base_filename):
    zip_filename = f'{base_filename}.zip'
    with ZipFile(zip_filename, 'w') as f:
        for image_filename in images_filenames:
            fdir, fname = os.path.split(image_filename)
            f.write(image_filename, fname)
    return zip_filename


def cleanup(*filenames):
    for filename in filenames:
        remove(filename)





