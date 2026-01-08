# 📦 Configuración de DigitalOcean Spaces

## ¿Qué es DigitalOcean Spaces?

DigitalOcean Spaces es un servicio de almacenamiento de objetos compatible con S3 que permite almacenar y servir archivos de forma permanente y escalable.

## Ventajas sobre servicios temporales

- ✅ **Almacenamiento permanente**: Las fotos no expiran
- ✅ **Control total**: Tú controlas tus archivos
- ✅ **CDN incluido**: Distribución global rápida
- ✅ **Escalable**: Sin límites de almacenamiento
- ✅ **Económico**: $5/mes por 250GB

## Configuración paso a paso

### 1. Crear un Space en DigitalOcean

1. Ve a [DigitalOcean Spaces](https://cloud.digitalocean.com/spaces)
2. Crea un nuevo Space:
   - Nombre: `tu-nombre-unico`
   - Región: Elige la más cercana
   - CDN: Actívalo (opcional pero recomendado)
   - Permisos: Público para lectura

### 2. Obtener credenciales

1. Ve a [API Tokens](https://cloud.digitalocean.com/account/api/tokens)
2. En la sección "Spaces access keys", crea una nueva llave
3. Guarda:
   - Access Key ID
   - Secret Access Key

### 3. Configurar variables de entorno

#### Opción A: Archivo .env (recomendado)

Crea un archivo `.env` en `demo/realtime-img2img/`:

```env
DO_SPACES_ACCESS_ID=tu_access_key_id
DO_SPACES_SECRET_KEY=tu_secret_key
DO_SPACES_BUCKET=tu-nombre-space
```

#### Opción B: Variables del sistema

Windows (PowerShell):
```powershell
$env:DO_SPACES_ACCESS_ID = "tu_access_key_id"
$env:DO_SPACES_SECRET_KEY = "tu_secret_key"
$env:DO_SPACES_BUCKET = "tu-nombre-space"
```

Linux/Mac:
```bash
export DO_SPACES_ACCESS_ID="tu_access_key_id"
export DO_SPACES_SECRET_KEY="tu_secret_key"
export DO_SPACES_BUCKET="tu-nombre-space"
```

### 4. Activar en la aplicación

El servicio ya está configurado por defecto en `frontend/src/lib/config.ts`:

```javascript
export const ShareConfig = {
  mode: 'external',
  service: 'digitalocean',  // Ya configurado
  autoConfig: true
};
```

### 5. Verificar instalación

Ejecuta el test incluido:

```bash
cd demo/realtime-img2img
python upload_service_cdn.py
```

Deberías ver:
```
✅ Test exitoso! URL: https://tu-space.ams3.digitaloceanspaces.com/snapshots/snapshot_...jpg
```

## Estructura de archivos

Las fotos se organizan automáticamente:
```
tu-space/
  └── snapshots/
      ├── snapshot_20250105_143022_a3b2c1d4.jpg
      ├── snapshot_20250105_143145_b5c6d7e8.jpg
      └── ...
```

## Solución de problemas

### Error: "Credentials not available"
- Verifica que las variables de entorno estén configuradas
- Reinicia tu terminal/IDE después de configurar variables

### Error: "NoSuchBucket"
- Verifica que el nombre del bucket sea correcto
- Asegúrate de que el Space existe en tu cuenta

### Error: "Access Denied"
- Verifica que las credenciales sean correctas
- Asegúrate de que el Space tenga permisos públicos de lectura

## Costos

- **Básico**: $5/mes
  - 250 GB de almacenamiento
  - 1 TB de transferencia
- **CDN**: Incluido sin costo extra
- **Imágenes adicionales**: $0.02/GB después de 250GB

## Seguridad

⚠️ **IMPORTANTE**: 
- Nunca subas tus credenciales a Git
- Añade `.env` a tu `.gitignore`
- Usa variables de entorno en producción
- Considera rotar las llaves periódicamente

## Comparación con otros servicios

| Servicio | Duración | Registro | Costo | Control |
|----------|----------|----------|-------|---------|
| tmpfiles | 1 hora | No | Gratis | Ninguno |
| fileio | 1 día | No | Gratis | Ninguno |
| 0x0 | Variable | No | Gratis | Ninguno |
| **DigitalOcean** | **Permanente** | **Sí** | **$5/mes** | **Total** |

## Soporte

- [Documentación oficial](https://docs.digitalocean.com/products/spaces/)
- [Comunidad DigitalOcean](https://www.digitalocean.com/community)
- [Estado del servicio](https://status.digitalocean.com/)
