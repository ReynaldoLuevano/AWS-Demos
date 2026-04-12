# =============================================
# PLEXUS TECH – Script de descarga de imágenes (Windows / PowerShell)
# Ejecutar desde la raíz del proyecto:
#   .\download-images.ps1
# =============================================

$ImagesDir = Join-Path $PSScriptRoot "images"
$BaseUrl   = "https://www.plexus.es/wp-content/uploads"

if (-not (Test-Path $ImagesDir)) {
    New-Item -ItemType Directory -Path $ImagesDir | Out-Null
}

function Download-Image {
    param([string]$Url, [string]$FileName)
    $dest = Join-Path $ImagesDir $FileName
    Write-Host "  Descargando $FileName ... " -NoNewline
    try {
        Invoke-WebRequest -Uri $Url -OutFile $dest -UseBasicParsing -ErrorAction Stop
        Write-Host "OK" -ForegroundColor Green
    } catch {
        Write-Host "FALLO" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Plexus Tech - Descarga de imagenes" -ForegroundColor Cyan
Write-Host "================================================"
Write-Host ""

Write-Host "Logos:" -ForegroundColor Yellow
Download-Image "$BaseUrl/2021/07/logo_cropped.png"                                            "logo.png"
Download-Image "$BaseUrl/2022/03/LOGO-PLEXUS-2020_WHITE-300x104.png"                          "logo-white.png"

Write-Host ""
Write-Host "Secciones:" -ForegroundColor Yellow
Download-Image "$BaseUrl/2024/03/Home_Servicios-600x400-1.png"                                "services-tech.png"
Download-Image "$BaseUrl/2024/01/240124_RRSS_USC-Citius-IA_948x600-1.png"                     "innovation-ai.png"
Download-Image "$BaseUrl/2023/03/Dennaria_App.png"                                            "product-dennaria.png"
Download-Image "$BaseUrl/2022/06/web-plexus_imagenes-10.png"                                  "product-bg.png"
Download-Image "$BaseUrl/2022/07/Home_Unete.png"                                              "team-join.png"

Write-Host ""
Write-Host "Avatares Sabia que:" -ForegroundColor Yellow
Download-Image "$BaseUrl/2022/07/sabias_fernando_gonzalez.png"                                "team-fernando.png"
Download-Image "$BaseUrl/2022/07/sabias_maria_diaz.png"                                       "team-maria.png"
Download-Image "$BaseUrl/2022/07/sabias_jose_vilas.png"                                       "team-jose.png"

Write-Host ""
Write-Host "Certificaciones:" -ForegroundColor Yellow
Download-Image "$BaseUrl/2025/08/thumbnail_RGB_EN-1.png"                                      "cert-iso22301.png"
Download-Image "$BaseUrl/2025/06/thumbnail_RGB_EN-27001-1.png"                                "cert-iso27001.png"
Download-Image "$BaseUrl/2025/06/thumbnail_RGB_EN-27701-2.png"                                "cert-iso27701.png"
Download-Image "$BaseUrl/2025/06/thumbnail_RGB_ES-DORA.png"                                   "cert-dora.png"
Download-Image "$BaseUrl/2025/06/thumbnail_RGB_EN-NIS2.png"                                   "cert-nis2.png"
Download-Image "$BaseUrl/2025/06/thumbnail_distintivo_ens_certificacion_ALTA_RD311-2022.png"  "cert-ens.png"
Download-Image "$BaseUrl/2025/11/ENAC-1.png"                                                  "cert-enac.png"

Write-Host ""
Write-Host "================================================"
Write-Host "  Completado. Imagenes en: $ImagesDir" -ForegroundColor Green
Write-Host "================================================"
Write-Host ""
