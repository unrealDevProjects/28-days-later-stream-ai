"""
Almacenamiento en DigitalOcean Spaces
Solo mantiene el adaptador para DigitalOcean, removiendo servicios temporales
"""
import logging
from typing import Optional

class DigitalOceanAdapter:
    """
    DigitalOcean Spaces - Almacenamiento permanente en la nube
    Límite: Según tu plan de DigitalOcean
    Duración: Permanente
    Requiere: Credenciales de DigitalOcean Spaces
    """
    
    def upload(self, image_base64: str) -> Optional[str]:
        try:
            from upload_service_cdn import upload_to_digitalocean_spaces
            result = upload_to_digitalocean_spaces(image_base64)
            if result['success']:
                return result['url']
            else:
                logging.error(f"Error en DigitalOcean: {result.get('error', 'Unknown error')}")
                return None
        except ImportError:
            logging.error("No se pudo importar upload_service_cdn. Asegúrate de que boto3 esté instalado.")
            return None
        except Exception as e:
            logging.error(f"Error inesperado con DigitalOcean: {e}")
            return None

# Función helper simplificada
def upload_to_external(image_base64: str, service: str = "digitalocean") -> Optional[str]:
    """
    Sube imagen a DigitalOcean Spaces
    
    Args:
        image_base64: String base64 de la imagen
        service: Solo soporta 'digitalocean' ahora
    
    Returns:
        URL de la imagen subida o None si falla
    """
    
    if service != "digitalocean":
        logging.error(f"Servicio no soportado: {service}. Solo 'digitalocean' está disponible.")
        return None
    
    adapter = DigitalOceanAdapter()
    return adapter.upload(image_base64)

# Prueba opcional
if __name__ == "__main__":
    # Imagen de prueba (muy pequeña)
    test_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    
    print("🧪 Probando DigitalOcean Spaces...")
    
    url = upload_to_external(test_image, "digitalocean")
    if url:
        print(f"✅ DigitalOcean Spaces: {url}")
    else:
        print(f"❌ DigitalOcean Spaces falló")