import os
from fastapi import FastAPI, File, Form, Response, Request, HTTPException, Depends, UploadFile
from typing import Annotated
from time import time
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.errors import PdfReadError
from starlette.responses import FileResponse
from starlette.background import BackgroundTask
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_200_OK
from googleapiclient.errors import HttpError
import pypdfium2 as pdfium

from tools import ImageReader, cleanup, zip_files, doc_docx_to_pdf, service, get_all_text_from_pages
from auth.auth_handler import HTTPSpecialBearer

app = FastAPI()
WEBHOOK_URL = 'https://google.com'
imageReader = ImageReader('LINUX')


# from typing import List
#
#
# @app.post('test')
# def add_images(images: List[UploadFile] = File(...)):
#     for image in images:
#         print(image)
#     return {"msg": "success"}
#
#
# @app.post('test')
# def add_images(images: List[Annotated[bytes, File()]] = File(...)):
#     for image in images:
#         print(image)
#     return {"msg": "success"}


@app.post('/pdf/cut', dependencies=[Depends(HTTPSpecialBearer())], tags=['pdf'])
async def cut_pdf(file: Annotated[bytes, File()], configuration: Annotated[str, Form()], response: Response):
    """
    Realises cutting functional and returns resulted PDF-file
    :param file: (bytes) file bytes
    :param configuration: (str) configuration string which pages to include in answer. Example: 1,4,5
    :param response: (Response) response object
    :return: error / pdf-file
    """
    try:
        pages = [int(i) for i in configuration.split(",")]
        pages.sort()
    except ValueError:
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'wrong configuration data: incorrect format'}
    pdf_filename = f'tmp_{time()}_{len(os.listdir("."))}.pdf'
    pdf_new_filename = pdf_filename.replace('.pdf', '_new.pdf')
    with open(pdf_filename, 'wb') as f:
        f.write(file)
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
        cleanup(pdf_filename)
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'wrong configuration data: index out of range'}
    response.status_code = HTTP_200_OK
    return response


@app.post('/pdf/cut_save', dependencies=[Depends(HTTPSpecialBearer())], tags=['pdf'])
async def cut_and_save_pdf(
        file: Annotated[bytes, File()],
        configuration: Annotated[str, Form()],
        fileId: Annotated[str, Form()],
        response: Response
):
    """
    Realises cutting functional, saves cut files, send info to webhook and returns info message
    :param file: (bytes) file bytes
    :param configuration: (str) configuration string which pages to include in answer. Example: 1,4,5
    :param fileId: (str) unique id for identification saved file
    :param response: (Response) response object
    :return: error / pdf-file
    """
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


@app.post('/pdf/extract_content', dependencies=[Depends(HTTPSpecialBearer())], tags=['pdf'])
async def extract_content(file: Annotated[bytes, File()], response: Response):
    filename = f'tmp_{time()}_{len(os.listdir("."))}'
    pdf_filename = f'{filename}.pdf'
    with open(pdf_filename, 'wb') as f:
        f.write(file)
    try:
        filePDF = PdfReader(pdf_filename)
    except PdfReadError:
        cleanup(pdf_filename)
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
    cleanup(pdf_filename, *images_filenames)
    response = FileResponse(
        zip_filename,
        media_type="application/x-zip-compressed",
        headers={'Content-Disposition': f'attachment; filename="{zip_filename}"'},
        background=BackgroundTask(cleanup, zip_filename),
    )
    return response


@app.post('/pdf/get_all_text', dependencies=[Depends(HTTPSpecialBearer())], tags=['pdf'])
def pdf_get_all_text(file: Annotated[bytes, File()], response: Response):
    filename = f'tmp_{time()}_{len(os.listdir("."))}'
    pdf_filename = f'{filename}.pdf'
    with open(pdf_filename, 'wb') as f:
        f.write(file)
        f.close()
    try:
        filePDF = PdfReader(pdf_filename)
    except PdfReadError:
        cleanup(pdf_filename)
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'wrong file format'}
    images_filenames, text = get_all_text_from_pages(filename, imageReader, filePDF.pages)
    cleanup(pdf_filename, *images_filenames)
    return {'text': text}


@app.post('/pdf/convert_to_zip_images', dependencies=[Depends(HTTPSpecialBearer())], tags=['pdf'])
def convert_pdf_to_zip_images(file: Annotated[bytes, File()], img_extension: Annotated[str, Form()],
                                    response: Response,
                                    width: Annotated[int, File()] = None, height: Annotated[int, File()] = None):
    if (width is None and height is None) or (width is not None and height is not None):
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'Set one: width or height'}
    supported_image_types = ['jpg', 'png', 'jpeg']
    if img_extension not in supported_image_types:
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'Unsupported image type'}
    filename = f'tmp_{time()}_{len(os.listdir("."))}'
    pdf_filename = f'{filename}.pdf'
    with open(pdf_filename, 'wb') as f:
        f.write(file)
    try:
        filePDF = pdfium.PdfDocument(pdf_filename)
    except pdfium._helpers.misc.PdfiumError as error:
        return {'error': error}
    images_filenames = []
    for page_number in range(len(filePDF)):
        page = filePDF.get_page(page_number)
        pil_image = page.render(scale=1).to_pil()
        old_width, old_height = pil_image.size
        new_width, new_height = 0, 0
        if width is not None:
            new_width = width
            new_height = int(old_height * width / old_width)
        if height is not None:
            new_width = int(old_width * height / old_height)
            new_height = height
        print(f"old:{old_width},{old_height}")
        print(f'new:{new_width},{new_height}')
        pil_image = pil_image.resize((new_width, new_height))
        pil_image.save(f"{filename}_{page_number + 1}.{img_extension}")
        images_filenames.append(f"{filename}_{page_number + 1}.{img_extension}")
    filePDF.close()
    zip_filename = zip_files(images_filenames, filename)
    cleanup(pdf_filename, *images_filenames)
    response = FileResponse(
        zip_filename,
        media_type="application/x-zip-compressed",
        headers={'Content-Disposition': f'attachment; filename="{zip_filename}"'},
        background=BackgroundTask(cleanup, zip_filename)
    )
    return response


@app.post('/doc/convert_to_pdf', dependencies=[Depends(HTTPSpecialBearer())], tags=['docs'])
def convert_doc_or_docx_to_pdf(file: Annotated[bytes, File()], extension: Annotated[str, Form()], response: Response):
    if extension != 'doc' and extension != 'docx':
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'Unsupported extension: write "doc" or "docx"'}
    filename = f'tmp_{time()}_{len(os.listdir("."))}'
    doc_filename = f'{filename}.{extension}'
    pdf_filename = f'{filename}.pdf'
    try:
        with open(doc_filename, 'wb') as f:
            f.write(file)
        doc_docx_to_pdf(doc_filename, pdf_filename, service)
        file_response = FileResponse(
            pdf_filename,
            media_type="application/pdf",
            background=BackgroundTask(cleanup, pdf_filename, doc_filename),
            headers={'Content-Disposition': f'attachment; filename="{pdf_filename}"'},
        )
        response.status_code = HTTP_200_OK
        return file_response
    except HttpError as error:
        cleanup(doc_filename, pdf_filename)
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': error}


@app.post('/doc/cut', dependencies=[Depends(HTTPSpecialBearer())], tags=['docs'])
def cut_doc(file: Annotated[bytes, File()], configuration: Annotated[str, Form()], extension: Annotated[str, Form()],
            response: Response):
    """Realises cutting functional and returns resulted PDF-file"""
    if extension != 'doc' and extension != 'docx':
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'Unsupported extension: write "doc" or "docx"'}
    try:
        pages = [int(i) for i in configuration.split(",")]
        pages.sort()
    except ValueError:
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'wrong configuration data: incorrect format'}
    filename = f'tmp_{time()}_{len(os.listdir("."))}'
    pdf_filename = f'{filename}.pdf'
    doc_filename = f'{filename}.{extension}'
    pdf_new_filename = f'{filename}_new.pdf'
    with open(doc_filename, 'wb') as f:
        f.write(file)
    try:
        doc_docx_to_pdf(doc_filename, pdf_filename, service)
    except HttpError as error:
        cleanup(doc_filename, pdf_filename)
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': error}
    try:
        filePDF = PdfReader(pdf_filename)
    except PdfReadError:
        cleanup(doc_filename, pdf_filename)
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
            background=BackgroundTask(cleanup, doc_filename, pdf_filename, pdf_new_filename),
            headers={'Content-Disposition': f'attachment; filename="{pdf_new_filename}"'},
        )
    except IndexError:
        cleanup(doc_filename, pdf_filename)
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'wrong configuration data: index out of range'}
    response.status_code = HTTP_200_OK
    return response


@app.post('/doc/get_all_text', dependencies=[Depends(HTTPSpecialBearer())], tags=['docs'])
def doc_get_all_text(file: Annotated[bytes, File()], extension: Annotated[str, Form()], response: Response):
    if extension not in ['doc', 'docx']:
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'Unsupported extension: write "doc" or "docx"'}
    filename = f'tmp_{time()}_{len(os.listdir("."))}'
    doc_filename = f'{filename}.{extension}'
    pdf_filename = f'{filename}.pdf'
    with open(doc_filename, 'wb') as f:
        f.write(file)
    try:
        doc_docx_to_pdf(doc_filename, pdf_filename, service)
    except HttpError as error:
        cleanup(doc_filename, pdf_filename)
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': error}
    try:
        filePDF = PdfReader(pdf_filename)
    except PdfReadError:
        cleanup(doc_filename, pdf_filename)
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'wrong file format'}
    images_filenames, text = get_all_text_from_pages(filename, imageReader, filePDF.pages)
    cleanup(doc_filename, pdf_filename, *images_filenames)
    return {'text': text}


@app.post('/doc/convert_to_zip_images', dependencies=[Depends(HTTPSpecialBearer())], tags=['docs'])
def convert_doc_to_zip_images(file: Annotated[bytes, File()], img_extension: Annotated[str, Form()],
                                    doc_extension: Annotated[str, Form()], response: Response,
                                    width: Annotated[int, File()] = None, height: Annotated[int, File()] = None):
    if doc_extension not in ['doc', 'docx']:
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'Unsupported extension: write "doc" or "docx"'}
    if (width is None and height is None) or (width is not None and height is not None):
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'Set one: width or height'}
    supported_image_types = ['jpg', 'png', 'jpeg']
    if img_extension not in supported_image_types:
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'Unsupported image type'}
    filename = f'tmp_{time()}_{len(os.listdir("."))}'
    doc_filename = f'{filename}.{doc_extension}'
    pdf_filename = f'{filename}.pdf'
    with open(doc_filename, 'wb') as f:
        f.write(file)
    try:
        doc_docx_to_pdf(doc_filename, pdf_filename, service)
        cleanup(doc_filename)
    except HttpError as error:
        cleanup(doc_filename, pdf_filename)
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': error}
    try:
        filePDF = pdfium.PdfDocument(pdf_filename)
    except pdfium._helpers.misc.PdfiumError as error:
        return {'error': error}
    images_filenames = []
    for page_number in range(len(filePDF)):
        page = filePDF.get_page(page_number)
        pil_image = page.render(scale=1).to_pil()
        old_width, old_height = pil_image.size
        new_width, new_height = 0, 0
        if width is not None:
            new_width = width
            new_height = int(old_height * width / old_width)
        if height is not None:
            new_width = int(old_width * height / old_height)
            new_height = height
        pil_image = pil_image.resize((new_width, new_height))
        pil_image.save(f"{filename}_{page_number + 1}.{img_extension}")
        images_filenames.append(f"{filename}_{page_number + 1}.{img_extension}")
    filePDF.close()
    zip_filename = zip_files(images_filenames, filename)
    cleanup(pdf_filename, *images_filenames)
    response = FileResponse(
        zip_filename,
        media_type="application/x-zip-compressed",
        headers={'Content-Disposition': f'attachment; filename="{zip_filename}"'},
        background=BackgroundTask(cleanup, zip_filename)
    )
    return response


@app.get('/pdf/get', dependencies=[Depends(HTTPSpecialBearer())], tags=['technical_endpoints'])
def get_pdf_list(response: Response):
    return os.listdir('files')


@app.get('/pdf/get/{fileId}', dependencies=[Depends(HTTPSpecialBearer())], tags=['technical_endpoints'])
def get_pdf_by_id(fileId: str, response: Response):
    if os.path.isfile(f'files/{fileId}.pdf'):
        response.status_code = HTTP_200_OK
        response = FileResponse(
            f'files/{fileId}.pdf',
            media_type="application/pdf",
            headers={'Content-Disposition': f'attachment; filename="{fileId}.pdf"'},
        )
        response.status_code = HTTP_200_OK
        return response
    else:
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'invalid file id'}


@app.delete('/pdf/delete/{fileId}', dependencies=[Depends(HTTPSpecialBearer())], tags=['technical_endpoints'])
def delete_pdf_by_id(fileId: str, response: Response):
    if os.path.isfile(f'files/{fileId}.pdf'):
        cleanup(f'files/{fileId}.pdf')
        response.status_code = HTTP_200_OK
        return {'info': 'Done!'}
    else:
        response.status_code = HTTP_400_BAD_REQUEST
        return {'error': 'invalid file id'}
