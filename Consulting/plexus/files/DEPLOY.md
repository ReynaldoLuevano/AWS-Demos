# Plexus Tech – Guía de despliegue en Amazon S3

## Estructura del proyecto

```
plexus-site/
├── index.html              ← Página principal
├── css/
│   └── styles.css          ← Todos los estilos
├── js/
│   └── main.js             ← Todo el JavaScript
├── images/
│   ├── logo.png            ← Logo header (descargar con script)
│   ├── logo-white.png      ← Logo footer/hero
│   ├── services-tech.png
│   ├── innovation-ai.png
│   ├── product-dennaria.png
│   ├── product-bg.png
│   ├── team-join.png
│   ├── team-fernando.png
│   ├── team-maria.png
│   ├── team-jose.png
│   ├── cert-iso22301.png ... cert-enac.png
├── download-images.sh      ← Script descarga Linux/Mac
├── download-images.ps1     ← Script descarga Windows
└── DEPLOY.md               ← Esta guía
```

---

## Paso 0: Descargar imágenes (OBLIGATORIO antes de subir a S3)

**Linux / Mac:**
```bash
chmod +x download-images.sh
./download-images.sh
```

**Windows (PowerShell):**
```powershell
.\download-images.ps1
```

---

## Paso 1: Crear el bucket S3

```bash
aws s3 mb s3://plexus-site-static --region eu-west-1
```

## Paso 2: Habilitar alojamiento web estático

```bash
aws s3 website s3://plexus-site-static \
  --index-document index.html \
  --error-document index.html
```

## Paso 3: Desbloquear acceso público

```bash
aws s3api put-public-access-block \
  --bucket plexus-site-static \
  --public-access-block-configuration \
    "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"
```

## Paso 4: Política del bucket

Crea `bucket-policy.json`:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::plexus-site-static/*"
  }]
}
```
```bash
aws s3api put-bucket-policy \
  --bucket plexus-site-static \
  --policy file://bucket-policy.json
```

## Paso 5: Subir archivos con cache headers

```bash
# HTML – sin caché
aws s3 cp index.html s3://plexus-site-static/ \
  --content-type "text/html; charset=utf-8" \
  --cache-control "no-cache, no-store, must-revalidate"

# CSS – caché 1 año
aws s3 cp css/ s3://plexus-site-static/css/ \
  --recursive --cache-control "public, max-age=31536000, immutable"

# JS – caché 1 año
aws s3 cp js/ s3://plexus-site-static/js/ \
  --recursive --cache-control "public, max-age=31536000, immutable"

# Imágenes – caché 1 año
aws s3 cp images/ s3://plexus-site-static/images/ \
  --recursive --cache-control "public, max-age=31536000, immutable"
```

## URL del sitio

```
http://plexus-site-static.s3-website.eu-west-1.amazonaws.com
```

## (Opcional) CloudFront + HTTPS

```bash
aws cloudfront create-distribution \
  --origin-domain-name plexus-site-static.s3-website.eu-west-1.amazonaws.com \
  --default-root-object index.html
```
