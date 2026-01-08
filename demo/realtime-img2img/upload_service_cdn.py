import os
import base64
import logging
from datetime import datetime
import uuid
from boto3 import session
from botocore.client import Config
from botocore.exceptions import ClientError, NoCredentialsError

# Configuración - Usa variables de entorno para seguridad
ACCESS_ID = 'DO801PM73T4439VE4RUY'
SECRET_KEY = '2DMVzXLw0oSgrAsvMGfOMYRexETwXAlrOfkqo3Lo+e8'
BUCKET_NAME = 'no-madproject'
REGION = 'ams3'
ENDPOINT_URL = f'https://{REGION}.digitaloceanspaces.com'

# Inicializar cliente una sola vez (más eficiente)
try:
    s3_session = session.Session()
    client = s3_session.client(
        's3',
        region_name=REGION,
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=ACCESS_ID,
        aws_secret_access_key=SECRET_KEY
    )
    logging.info("DigitalOcean Spaces client initialized successfully")
except Exception as e:
    logging.error(f"Error initializing DigitalOcean Spaces client: {e}")
    client = None


def upload_to_digitalocean_spaces(image_data, filename=None, folder="snapshots"):
    """
    Sube una imagen a DigitalOcean Spaces
    
    Args:
        image_data: String base64 o bytes de la imagen
        filename: Nombre opcional del archivo (se genera automático si no se proporciona)
        folder: Carpeta donde guardar en el bucket
    
    Returns:
        dict: {
            'success': bool,
            'url': str (URL pública si success=True),
            'filename': str (nombre del archivo usado),
            'error': str (mensaje de error si success=False)
        }
    """
    
    if not client:
        return {
            'success': False,
            'error': 'DigitalOcean Spaces client not initialized'
        }
    
    try:
        # Procesar la imagen si viene en base64
        if isinstance(image_data, str):
            # Remover el prefijo data URL si existe
            if 'base64,' in image_data:
                image_data = image_data.split('base64,')[1]
            
            # Decodificar de base64 a bytes
            image_bytes = base64.b64decode(image_data)
        else:
            # Ya son bytes
            image_bytes = image_data
        
        # Generar nombre único si no se proporciona
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = uuid.uuid4().hex[:8]
            filename = f"snapshot_{timestamp}_{unique_id}.jpg"
        
        # Construir la ruta completa en el bucket
        object_key = f"{folder}/{filename}" if folder else filename
        
        # Subir la imagen usando put_object (más directo que upload_file)
        response = client.put_object(
            Bucket=BUCKET_NAME,
            Key=object_key,
            Body=image_bytes,
            ACL='public-read',  # Hacer público para acceso por URL
            ContentType='image/jpeg',  # Especificar tipo de contenido
            ContentDisposition='inline'  # Para que se muestre en el navegador
        )
        
        # Construir la URL pública
        public_url = f"https://{BUCKET_NAME}.{REGION}.digitaloceanspaces.com/{object_key}"
        
        logging.info(f"Successfully uploaded to DigitalOcean Spaces: {public_url}")
        
        return {
            'success': True,
            'url': public_url,
            'filename': filename,
            'service': 'digitalocean'
        }
        
    except NoCredentialsError:
        error_msg = "Credentials not available for DigitalOcean Spaces"
        logging.error(error_msg)
        return {
            'success': False,
            'error': error_msg
        }
    
    except ClientError as e:
        error_msg = f"Client error uploading to DigitalOcean Spaces: {e}"
        logging.error(error_msg)
        return {
            'success': False,
            'error': str(e)
        }
    
    except Exception as e:
        error_msg = f"Unexpected error uploading to DigitalOcean Spaces: {e}"
        logging.error(error_msg)
        return {
            'success': False,
            'error': str(e)
        }


# Función de prueba opcional
def test_upload():
    """Función para probar el upload con un archivo de prueba"""
    try:
        # Crear una imagen de prueba simple
        test_image = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAAAAAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAr/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCwAA8A/9k="
        
        result = upload_to_digitalocean_spaces(test_image)
        
        if result['success']:
            print(f"✅ Test exitoso! URL: {result['url']}")
        else:
            print(f"❌ Test falló: {result['error']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error en test: {e}")
        return None


# Si se ejecuta directamente, hacer prueba
if __name__ == "__main__":
    test_upload()