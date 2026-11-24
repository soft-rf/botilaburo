"""Módulo de normalización y filtrado temporal de publicaciones laborales."""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def parse_time_to_minutes(time_text: str) -> Optional[int]:
    """Convierte textos de tiempo relativo a minutos totales transcurridos.

    Soporta formatos de Computrabajo y Bumeran:
        'Recién publicado'                 -> 0
        'Hace 35 minutos'                  -> 35
        'Publicado hace 45 minutos'        -> 45
        'Hace 1 hora'                      -> 60
        'Publicado hace 1 hora'            -> 60
        'Publicado hace 2 horas'           -> 120
        'Actualizado hace 10 horas'        -> 600
        'Publicado ayer' / 'Ayer'          -> 1440
        'Publicado hace 3 días'            -> 4320
        'Actualizado hace más de 15 días'  -> 21600

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

    # Minutos: "Hace 15 minutos", "Publicado hace 15 min", "15 minutos"
    match_min = re.search(r"(?:hace\s+)?(\d+)\s+min", clean_text)
    if match_min:
        return int(match_min.group(1))

    # Horas: "Hace 1 hora", "Publicado hace 2 horas", "Actualizado hace 10 horas"
    match_hours = re.search(r"(?:hace\s+)?(\d+)\s+hora", clean_text)
    if match_hours:
        return int(match_hours.group(1)) * 60

    # Hoy / Publicado hoy
    if "hoy" in clean_text:
        return 60

    # Ayer
    if "ayer" in clean_text:
        return 24 * 60

    # Días: "Hace 2 días", "Publicado hace 3 días", "hace más de 15 días"
    match_days = re.search(r"(?:hace\s+(?:más\s+de\s+)?)?(\d+)\s+d[ií]a", clean_text)
    if match_days:
        return int(match_days.group(1)) * 24 * 60

    # Semanas
    if "semana" in clean_text:
        match_w = re.search(r"(\d+)\s+semana", clean_text)
        weeks = int(match_w.group(1)) if match_w else 1
        return weeks * 7 * 24 * 60

    # Meses
    if "mes" in clean_text:
        match_m = re.search(r"(\d+)\s+mes", clean_text)
        months = int(match_m.group(1)) if match_m else 1
        return months * 30 * 24 * 60

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
