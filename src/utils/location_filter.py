"""Módulo de validación y filtrado geográfico estricto."""

import logging
import unicodedata
from typing import List

logger = logging.getLogger(__name__)

# Palabras clave y localidades permitidas (normalizadas en minúsculas y sin acentos)
ALLOWED_LOCATION_KEYWORDS: List[str] = [
    # CABA / Capital Federal
    "capital federal",
    "caba",
    "buenos aires (capital federal)",
    "buenos aires, buenos aires",
    "buenos aires, provincia de buenos aires",
    "buenos aires y alrededores",
    # Barrios reconocidos de CABA
    "microcentro",
    "palermo",
    "belgrano",
    "recoleta",
    "puerto madero",
    "retiro",
    "caballito",
    "almagro",
    "villa crespo",
    "villa urquiza",
    "nunez",
    "colegiales",
    "chacarita",
    "barracas",
    "balvanera",
    "san telmo",
    "monserrat",
    "parque patricios",
    "villa devoto",
    "villa del parque",
    "saavedra",
    "coghlan",
    "flores",
    "floresta",
    # San Martín y alrededores
    "san martin",
    "general san martin",
    "villa maipu",
    # Tres de Febrero (Caseros y Sáenz Peña)
    "tres de febrero",
    "caseros",
    "saenz pena",
    # Zona Norte (Corredor Vicente López y San Isidro)
    "vicente lopez",
    "florida",
    "olivos",
    "la lucila",
    "martinez",
    "san isidro",
    # Modalidades a distancia
    "remoto",
    "hibrido",
    "desde casa",
    "teletrabajo"
]


def normalize_text(text: str) -> str:
    """Normaliza una cadena eliminando acentos, caracteres especiales y convirtiendo a minúsculas.

    Args:
        text: Texto de entrada.

    Returns:
        Cadena limpia en minúsculas y sin tildes.
    """
    if not text:
        return ""
    # Descompone caracteres con tilde (ej: 'é' -> 'e' + acento) y elimina las marcas de acentuación
    nfkd = unicodedata.normalize("NFKD", text)
    clean_chars = [c for c in nfkd if not unicodedata.combining(c)]
    return "".join(clean_chars).lower().strip()


def is_allowed_location(location_text: str) -> bool:
    """Verifica si una ubicación coincide estrictamente con las zonas geográficas permitidas.

    Zonas permitidas:
    - CABA / Capital Federal (cualquier barrio o mención)
    - San Martín y Villa Maipú
    - Tres de Febrero (Caseros, Sáenz Peña)
    - Zona Norte (Vicente López, Florida, Olivos, La Lucila, Martínez, San Isidro)
    - Remoto / Híbrido

    Args:
        location_text: Ubicación reportada en la oferta de empleo.

    Returns:
        True si pertenece a una zona habilitada; False si queda fuera de los límites.
    """
    if not location_text:
        return False

    normalized_loc = normalize_text(location_text)

    # Si contiene explícitamente mención a Capital Federal o CABA, se acepta
    if "capital federal" in normalized_loc or "caba" in normalized_loc:
        return True

    # Verificar coincidencia con alguna de las palabras clave permitidas
    for keyword in ALLOWED_LOCATION_KEYWORDS:
        if keyword in normalized_loc:
            return True

    return False
