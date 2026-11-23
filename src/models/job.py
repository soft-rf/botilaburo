"""Modelo de datos para representar ofertas laborales estructuradas."""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict


@dataclass
class JobOffer:
    """Representa una oferta laboral extraída de un portal de empleo.

    Attributes:
        title: Título de la posición laboral.
        company: Nombre de la empresa ofertante.
        location: Ubicación geográfica reportada (ej. CABA, GBA, Remoto).
        published_time_text: Texto crudo del tiempo de publicación (ej. 'Hace 30 minutos').
        url: Enlace directo a la postulación.
        job_id: Identificador único de la oferta según el portal.
        description: Texto descriptivo o resumen de requisitos de la oferta.
        portal: Nombre del portal de origen (por defecto 'computrabajo').
        extracted_at: Fecha y hora en formato ISO de la extracción.
    """

    title: str
    company: str
    location: str
    published_time_text: str
    url: str
    job_id: str = ""
    description: str = ""
    portal: str = "computrabajo"
    extracted_at: str = ""

    def __post_init__(self) -> None:
        """Asigna fecha y hora actual en ISO si no fue especificada."""
        if not self.extracted_at:
            self.extracted_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la oferta a un diccionario serializable."""
        return asdict(self)
