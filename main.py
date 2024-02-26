import os
from os import remove, listdir
from fastapi import FastAPI, File, Form, Response
from typing import Annotated
from time import time
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.errors import PdfReadError
from starlette.responses import FileResponse
from starlette.background import BackgroundTask
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_200_OK
from zipfile import ZipFile
# from PIL import Image
# from pydantic import BaseModel
# import requests


app = FastAPI()
WEBHOOK_URL = 'https://google.com'


@app.post('/pdf/cut')
async def create_file(file: Annotated[bytes, File()], configuration: Annotated[str, Form()], response: Response):
    """Realises cutting functional and returns resulted PDF-file"""
    try:
        pages = [int(i) for i in configuration.split(",")]
        pages.sort()
    except ValueError:
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'wrong configuration data: incorrect format'}
    pdf_filename = f'tmp_{time()}_{len(listdir("."))}.pdf'
    pdf_new_filename = pdf_filename.replace('.pdf', '_new.pdf')
    with open(pdf_filename, 'wb') as f:
        f.write(file)
        f.close()
    try:
        filePDF = PdfReader(pdf_filename)
    except PdfReadError:
        cleanup(pdf_filename)
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'wrong file format'}
    pdfWriter = PdfWriter()
    try:
        for page in pages:
            pdfWriter.add_page(filePDF.pages[page])
        with open(pdf_new_filename, 'wb') as f:
            pdfWriter.write(f)
            f.close()
        response = FileResponse(
            pdf_new_filename,
            media_type="application/pdf",
            background=BackgroundTask(cleanup, pdf_filename, pdf_new_filename),
            headers={'Content-Disposition': f'attachment; filename="{pdf_new_filename}"'},
        )
    except IndexError:
        remove(pdf_filename)
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'wrong configuration data: index out of range'}
    response.status_code = HTTP_200_OK
    return response


@app.post('/pdf/cut_save')
async def save_pdf(
        file: Annotated[bytes, File()],
        configuration: Annotated[str, Form()],
        fileId: Annotated[str, Form()],
        response: Response
):
    """Realises cutting functional, saves cut files, send info to webhook and returns info message"""
    try:
        pages = [int(i) for i in configuration.split(",")]
        pages.sort()
    except ValueError:
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'wrong configuration data: incorrect format'}
    path = f'files/{fileId}.pdf'
    with open(path, 'wb') as f:
        f.write(file)
        f.close()
    try:
        filePDF = PdfReader(path)
    except PdfReadError:
        cleanup(path)
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'wrong file format'}
    pdfWriter = PdfWriter()
    try:
        for page in pages:
            pdfWriter.add_page(filePDF.pages[page])
        with open(path, 'wb') as f:
            pdfWriter.write(f)
            f.close()
        # print(requests.post(WEBHOOK_URL, data={'id': f'{fileId}'}).content)                     # place to put webhook
    except IndexError:
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'wrong configuration data: index out of range'}
    response.status_code = HTTP_200_OK
    return {'info': 'Done!'}


@app.post('/pdf/extract_images')
async def extract_images(file: Annotated[bytes, File()], response: Response):
    filename = f'tmp_{time()}_{len(listdir("."))}'
    with open(f'{filename}.pdf', 'wb') as f:
        f.write(file)
        f.close()
    try:
        filePDF = PdfReader(f'{filename}.pdf')
    except PdfReadError:
        cleanup(f'{filename}.pdf')
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'wrong file format'}
    counter = 0
    images_filenames = []
    for page in filePDF.pages:
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
        response.status_code = HTTP_200_OK
        response = {'info': 'there is no images'}
    return response


@app.post('/pdf/extract_text')
async def extract_images(file: Annotated[bytes, File()], response: Response):
    pdf_filename = f'tmp_{time()}_{len(listdir("."))}.pdf'
    with open(pdf_filename, 'wb') as f:
        f.write(file)
        f.close()
    try:
        filePDF = PdfReader(pdf_filename)
    except PdfReadError:
        cleanup(pdf_filename)
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'wrong file format'}
    text = ''
    for page in filePDF.pages:
        text += page.extract_text() + '\n'
    cleanup(pdf_filename)
    response.status_code = HTTP_200_OK
    return text


def zip_files(images_filenames, base_filename):
    """
    Function creates zip archive with images
    :param images_filenames: (list) list of images file names
    :param base_filename: (str) base name(without format) for zip archive
    :return: (str) archive name
    """
    zip_filename = f'{base_filename}.zip'
    with ZipFile(zip_filename, 'w') as f:
        for image_filename in images_filenames:
            _, image_file_name = os.path.split(image_filename)
            f.write(image_filename, image_file_name)
    return zip_filename


def cleanup(*filenames):
    """
    Deletes all the files given as arguments
    :param filenames: (...str) names of files
    :return: _
    """
    for filename in filenames:
        remove(filename)
