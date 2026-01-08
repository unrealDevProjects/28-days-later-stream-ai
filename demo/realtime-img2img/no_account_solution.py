"""
Solución sin necesidad de cuentas ni túneles
Usa servicios de almacenamiento temporal 100% anónimos
"""

import base64
import requests
import json
import os

def test_services():
    """Prueba qué servicios funcionan sin cuenta"""
    print("[*] Probando servicios que NO requieren cuenta ni registro...")
    print("="*60)
    
    # Imagen de prueba pequeña
    test_img = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
    
    working_services = []
    
    # 1. Probar tmpfiles.org (NO requiere cuenta)
    print("\n[>] tmpfiles.org (sin cuenta, 1 hora)...")
    try:
        files = {"file": ("test.jpg", base64.b64decode(test_img), "image/jpeg")}
        response = requests.post("https://tmpfiles.org/api/v1/upload", files=files, timeout=5)
        if response.status_code == 200:
            url = response.json()["data"]["url"].replace("/api/v1/download/", "/dl/")
            print(f"[OK] Funciona! URL ejemplo: {url}")
            working_services.append("tmpfiles")
    except Exception as e:
        print(f"[X] No disponible: {e}")
    
    # 2. Probar file.io (NO requiere cuenta)
    print("\n[>] file.io (sin cuenta, 1 dia)...")
    try:
        files = {"file": ("test.jpg", base64.b64decode(test_img), "image/jpeg")}
        data = {"expires": "1d"}
        response = requests.post("https://file.io", files=files, data=data, timeout=5)
        if response.status_code == 200:
            url = response.json()["link"]
            print(f"[OK] Funciona! URL ejemplo: {url}")
            working_services.append("fileio")
    except Exception as e:
        print(f"[X] No disponible: {e}")
    
    # 3. Probar 0x0.st (NO requiere cuenta)
    print("\n[>] 0x0.st (sin cuenta, duracion variable)...")
    try:
        files = {"file": ("test.jpg", base64.b64decode(test_img), "image/jpeg")}
        response = requests.post("https://0x0.st", files=files, timeout=5)
        if response.status_code == 200:
            url = response.text.strip()
            print(f"[OK] Funciona! URL ejemplo: {url}")
            working_services.append("0x0")
    except Exception as e:
        print(f"[X] No disponible: {e}")
    
    return working_services

def configure_external_mode():
    """Configura el modo externo en la aplicación"""
    config = {
        "mode": "external",
        "services": test_services()
    }
    
    if not config["services"]:
        print("\n[X] Ningun servicio externo esta disponible")
        return False
    
    print("\n" + "="*60)
    print("[OK] CONFIGURACION EXITOSA")
    print("="*60)
    print(f"\n[*] Servicios disponibles: {', '.join(config['services'])}")
    
    # Guardar configuración
    with open(".external_config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    # Crear archivo .env
    with open(".env", "w") as f:
        f.write("SHARE_MODE=external\n")
        f.write(f"EXTERNAL_SERVICES={','.join(config['services'])}\n")
    
    print("\n>>> COMO USAR:")
    print("1. Ejecuta tu aplicación: python main.py")
    print("2. Las fotos se subirán automáticamente a servicios temporales")
    print("3. Los QR contendrán URLs públicas temporales")
    print("\n[!] NOTA: Las fotos se borran automaticamente despues de 1-24 horas")
    
    return True

def main():
    print(">>> SOLUCION SIN CUENTAS NI REGISTROS")
    print("="*60)
    print("Esta solucion NO requiere:")
    print("  [X] Crear cuentas")
    print("  [X] Registrarse")
    print("  [X] Dar email")
    print("  [X] Instalar software adicional")
    print("="*60)
    
    if configure_external_mode():
        print("\n[OK] Todo listo! Ahora ejecuta:")
        print("   python main.py")
    else:
        print("\n[i] Alternativa: Crea una cuenta gratis en ngrok.com")
        print("   Es rapido y te da mejores limites")

if __name__ == "__main__":
    main()
