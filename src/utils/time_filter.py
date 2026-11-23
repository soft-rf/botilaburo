"""Módulo de normalización y filtrado temporal de publicaciones laborales."""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def parse_time_to_minutes(time_text: str) -> Optional[int]:
    """Convierte textos de tiempo relativo a minutos totales transcurridos.

    Ejemplos:
        'Recién publicado' -> 0
        'Hace 35 minutos'  -> 35
        'Hace 1 hora'      -> 60
        'Hace 2 horas'     -> 120
        'Ayer'             -> 1440
        'Hace 3 días'      -> 4320

    Args:
        time_text: Cadena de texto con el tiempo relativo extraído del portal.

    Returns:
        Cantidad entera de minutos transcurridos, o None si no se reconoce el formato.
    """
    if not time_text:
        return None

    clean_text = time_text.strip().lower()

    # Publicaciones inmediatas
    if any(term in clean_text for term in ["recién", "recientemente", "momento", "ahora", "instantes", "primeras horas"]):
        return 0

    # Minutos: "Hace 15 minutos", "Hace 45 min"
    match_min = re.search(r"hace\s+(\d+)\s+min", clean_text)
    if match_min:
        return int(match_min.group(1))

    # Horas: "Hace 1 hora", "Hace 2 horas", "Hace 8 horas"
    match_hours = re.search(r"hace\s+(\d+)\s+hora", clean_text)
    if match_hours:
        return int(match_hours.group(1)) * 60

    # Ayer
    if "ayer" in clean_text:
        return 24 * 60

    # Días: "Hace 2 días", "Hace 3 dias"
    match_days = re.search(r"hace\s+(\d+)\s+d[ií]a", clean_text)
    if match_days:
        return int(match_days.group(1)) * 24 * 60

    logger.debug("No se pudo interpretar el texto de tiempo: '%s'", time_text)
    return None


def is_within_time_window(time_text: str, max_minutes: int = 120) -> bool:
    """Verifica si una oferta fue publicada dentro del umbral de tiempo permitido.

    Args:
        time_text: Cadena que indica cuándo se publicó la oferta.
        max_minutes: Umbral máximo en minutos (por defecto 120 minutos = 2 horas).

    Returns:
        True si la oferta tiene una antigüedad menor o igual a max_minutes; False en caso contrario.
    """
    minutes = parse_time_to_minutes(time_text)
    if minutes is None:
        return False
    return minutes <= max_minutes
