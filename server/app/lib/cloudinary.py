import os
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Load environment variables from .env
load_dotenv()

# Configure Cloudinary using environment variables
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

def upload_image_from_url(image_url, public_id=None, folder=None):
    options = {}
    if public_id:
        options['public_id'] = public_id
    if folder:
        options['folder'] = folder
    result = cloudinary.uploader.upload(image_url, **options)
    return result.get('secure_url')

def delete_image_by_url(image_url):

    from urllib.parse import urlparse
    import os
    parsed = urlparse(image_url)
    public_id_with_ext = os.path.splitext(parsed.path)[0].lstrip('/')
    return cloudinary.uploader.destroy(public_id_with_ext)

def upload_image_file(file, public_id=None, folder=None):
    """
    Uploads an image file (from a form) to Cloudinary and returns the public URL.
    file: a file-like object (e.g., from FastAPI UploadFile.file or Flask request.files['file'])
    """
    options = {}
    if public_id:
        options['public_id'] = public_id
    if folder:
        options['folder'] = folder
    result = cloudinary.uploader.upload(file, **options)
    return result.get('secure_url')