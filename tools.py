import os
from zipfile import ZipFile
from googleapiclient.http import MediaFileUpload

from PIL import Image
from pytesseract import pytesseract

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


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
        if os.path.exists(filename):
            os.remove(filename)


def doc_docx_to_pdf(input_filename, output_filename, service):
    '''
    Creates pdf file from doc or docx file
    :param input_filename: path to doc/docx file
    :param output_filename: path to output pdf file
    :param service: Google Drive api service
    :return:
    '''
    file_media_body = MediaFileUpload(input_filename, resumable=True)
    word_file_id = service.files().create(
        body={'name': input_filename},
        media_body=file_media_body,
        fields='id').execute()['id']
    googledoc_file_id = service.files().copy(
        fileId=word_file_id,
        body={'mimeType': 'application/vnd.google-apps.document'},
        fields='id').execute()['id']
    pdf_file = service.files().export(fileId=googledoc_file_id, mimeType='application/pdf').execute()
    with open(output_filename, 'wb') as f:
        f.write(pdf_file)
    service.files().delete(fileId=word_file_id).execute()
    service.files().delete(fileId=googledoc_file_id).execute()
    service.files().emptyTrash().execute()


def get_all_text_from_pages(filename, imageReader, pagesIterator):
    """
    Returns all text from iterator pagesIterator using imageReader and name of base file
    :param filename: name of file which working with
    :param imageReader: object of imageReader class
    :param pagesIterator: iterator through pages (PdfReader().pages)
    :return:
    """
    counter = 0
    images_filenames = []
    text = ''
    for page in pagesIterator:
        text += page.extract_text() + '\n'
        for imageFileObject in page.images:
            with open(f'{filename}-{counter}-{imageFileObject.name}', 'wb') as f:
                f.write(imageFileObject.data)
            images_filenames.append(f'{filename}-{counter}-{imageFileObject.name}')
            textFromImage = imageReader.extract_text(f'{filename}-{counter}-{imageFileObject.name}', language='eng+ukr')
            # print(f'text from image: {textFromImage}')
            text += textFromImage
            counter += 1
    return images_filenames, text


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




GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/drive'
]
CREDS = None
if os.path.exists("token.json"):
    CREDS = Credentials.from_authorized_user_file("token.json", GOOGLE_SCOPES)
if not CREDS or not CREDS.valid:
    if CREDS and CREDS.expired and CREDS.refresh_token:
        CREDS.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secrets_file="credentials.json",
            scopes=GOOGLE_SCOPES
        )
        CREDS = flow.run_local_server(port=0)
    with open("token.json", "w") as token:
        token.write(CREDS.to_json())
service = build("drive", "v3", credentials=CREDS)