#!/bin/bash
# =============================================
# PLEXUS TECH – Script de descarga de imágenes
# Ejecutar desde la raíz del proyecto:
#   chmod +x download-images.sh
#   ./download-images.sh
# =============================================

IMAGES_DIR="$(dirname "$0")/images"
BASE_URL="https://www.plexus.es/wp-content/uploads"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

download() {
  local url="$1"
  local dest="$IMAGES_DIR/$2"
  printf "  Descargando %-35s " "$2"
  if curl -s -L --max-time 30 "$url" -o "$dest" && [ -s "$dest" ]; then
    echo -e "${GREEN}OK${NC}"
  else
    echo -e "${RED}FALLO${NC}"
  fi
}

echo ""
echo "================================================"
echo "  Plexus Tech – Descarga de imágenes"
echo "================================================"
echo ""

mkdir -p "$IMAGES_DIR"

echo -e "${YELLOW}Logos:${NC}"
download "$BASE_URL/2021/07/logo_cropped.png"                                              "logo.png"
download "$BASE_URL/2022/03/LOGO-PLEXUS-2020_WHITE-300x104.png"                            "logo-white.png"

echo ""
echo -e "${YELLOW}Secciones:${NC}"
download "$BASE_URL/2024/03/Home_Servicios-600x400-1.png"                                  "services-tech.png"
download "$BASE_URL/2024/01/240124_RRSS_USC-Citius-IA_948x600-1.png"                       "innovation-ai.png"
download "$BASE_URL/2023/03/Dennaria_App.png"                                              "product-dennaria.png"
download "$BASE_URL/2022/06/web-plexus_imagenes-10.png"                                    "product-bg.png"
download "$BASE_URL/2022/07/Home_Unete.png"                                                "team-join.png"

echo ""
echo -e "${YELLOW}Avatares ¿Sabía que?:${NC}"
download "$BASE_URL/2022/07/sabias_fernando_gonzalez.png"                                  "team-fernando.png"
download "$BASE_URL/2022/07/sabias_maria_diaz.png"                                         "team-maria.png"
download "$BASE_URL/2022/07/sabias_jose_vilas.png"                                         "team-jose.png"

echo ""
echo -e "${YELLOW}Certificaciones:${NC}"
download "$BASE_URL/2025/08/thumbnail_RGB_EN-1.png"                                        "cert-iso22301.png"
download "$BASE_URL/2025/06/thumbnail_RGB_EN-27001-1.png"                                  "cert-iso27001.png"
download "$BASE_URL/2025/06/thumbnail_RGB_EN-27701-2.png"                                  "cert-iso27701.png"
download "$BASE_URL/2025/06/thumbnail_RGB_ES-DORA.png"                                     "cert-dora.png"
download "$BASE_URL/2025/06/thumbnail_RGB_EN-NIS2.png"                                     "cert-nis2.png"
download "$BASE_URL/2025/06/thumbnail_distintivo_ens_certificacion_ALTA_RD311-2022.png"    "cert-ens.png"
download "$BASE_URL/2025/11/ENAC-1.png"                                                    "cert-enac.png"

echo ""
echo "================================================"
echo -e "  ${GREEN}Descarga completada.${NC}"
echo "  Imágenes guardadas en: $IMAGES_DIR"
echo "================================================"
echo ""
