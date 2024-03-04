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
from PIL import Image
from pytesseract import pytesseract
# from PIL import Image
# from pydantic import BaseModel
# import requests


class ImageReader:
    def __init__(self, os):
        if os == 'WINDOWS':
            windows_path = r'D:\tesseract\tesseract.exe'
            pytesseract.tesseract_cmd = windows_path
        if os == 'MAC':
            pass
        if os == 'LINUX':
            pass

    @staticmethod
    def extract_text(image_path, language):
        img = Image.open(image_path)
        extracted_text = pytesseract.image_to_string(img, lang=language)
        return extracted_text


app = FastAPI()
WEBHOOK_URL = 'https://google.com'
imageReader = ImageReader('LINUX')


@app.post('/pdf/cut')
async def cut_pdf(file: Annotated[bytes, File()], configuration: Annotated[str, Form()], response: Response):
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
async def cut_and_save_pdf(
        file: Annotated[bytes, File()],
        configuration: Annotated[str, Form()],
        fileId: Annotated[str, Form()],
        response: Response
):
    """Realises cutting functional, saves cut files, send info to webhook and returns info message"""
    if not os.path.isdir('files'):
        os.mkdir('files')
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


@app.post('/pdf/extract_content')
async def extract_content(file: Annotated[bytes, File()], response: Response):
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
    text = ''
    for page in filePDF.pages:
        text += page.extract_text() + '\n'
        for imageFileObject in page.images:
            with open(f'{filename}-{counter}-{imageFileObject.name}', 'wb') as f:
                f.write(imageFileObject.data)
            images_filenames.append(f'{filename}-{counter}-{imageFileObject.name}')
            counter += 1
    with open(f'{filename}.txt', 'w') as f:
        f.write(text)
    images_filenames.append(f'{filename}.txt')
    zip_filename = zip_files(images_filenames, filename)
    cleanup(f'{filename}.pdf', *images_filenames)
    response = FileResponse(
        zip_filename,
        media_type="application/x-zip-compressed",
        headers={'Content-Disposition': f'attachment; filename="{zip_filename}"'},
        background=BackgroundTask(cleanup, zip_filename),
    )
    return response


@app.post('/pdf/get_all_text')
def pdf_get_all_text(file: Annotated[bytes, File()], response: Response):
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
    text = ''
    for page in filePDF.pages:
        text += page.extract_text() + '\n'
        for imageFileObject in page.images:
            with open(f'{filename}-{counter}-{imageFileObject.name}', 'wb') as f:
                f.write(imageFileObject.data)
            images_filenames.append(f'{filename}-{counter}-{imageFileObject.name}')
            textFromImage = imageReader.extract_text(f'{filename}-{counter}-{imageFileObject.name}', language='eng+ukr')
            print(f'text from image: {textFromImage}')
            text += ' '.join(textFromImage.strip().strip('\n').split())
            counter += 1
    cleanup(f'{filename}.pdf', *images_filenames)
    return {'text': text}


# @app.post('/doc/convert_to_pdf')
# def convert_to_pdf(file: Annotated[bytes, File()], response: Response):
#     filename = f'tmp_{time()}_{len(listdir("."))}'
#     with open(f'{filename}.doc', 'wb') as f:
#         f.write(file)
#         f.close()
#     # try:
#     convert2(filename + '.doc', filename + '.pdf')
#     # convert(filename + '.docx', filename + '.pdf')
#     # except
#     # cleanup(filename + '.docx', filename + '.pdf')
#     cleanup(filename + '.doc')
#     return 'success'

# @app.post('/image/extract_text')
# async def image_extract_text(file: Annotated[bytes, File()], response: Response):


@app.get('/pdf/get', tags=['work_with_files'])
def get_pdf_list(response: Response):
    return listdir('files')


@app.get('/pdf/get/{fileId}', tags=['work_with_files'])
def get_pdf_by_id(fileId: str, response: Response):
    if os.path.isfile(f'files/{fileId}.pdf'):
        response.status_code = HTTP_200_OK
        response = FileResponse(
            f'files/{fileId}.pdf',
            media_type="application/pdf",
            headers={'Content-Disposition': f'attachment; filename="{fileId}.pdf"'},
        )
        response.status_code =HTTP_200_OK
        return response
    else:
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'invalid file id'}


@app.delete('/pdf/delete/{fileId}', tags=['work_with_files'])
def delete_pdf_by_id(fileId: str, response: Response):
    if os.path.isfile(f'files/{fileId}.pdf'):
        remove(f'files/{fileId}.pdf')
        response.status_code = HTTP_200_OK
        return {'info': 'Done!'}
    else:
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'invalid file id'}


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
