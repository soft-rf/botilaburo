"""Módulo de gestión de historial y deduplicación con caché persistente y huella digital."""

from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import re
from typing import Dict, List, Optional
import unicodedata

from src.models.job import JobOffer

logger = logging.getLogger(__name__)

GENERIC_COMPANIES = (
    "confidencial",
    "no especificada",
    "importante empresa",
    "empresa confidencial",
)


def _normalize_key(text: str) -> str:
    """Normaliza texto a minúsculas sin tildes ni signos para generar huellas digitales estables."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c)).lower()
    # Quitar puntos sin agregar espacio para unificar 'S.A.' con 'SA' o 'S.R.L.' con 'SRL'
    no_dots = no_accents.replace(".", "")
    alnum = re.sub(r"[^a-z0-9\s]", " ", no_dots)
    return re.sub(r"\s+", " ", alnum).strip()


class JobDeduplicator:
    """Administra el registro persistente de ofertas vistas para evitar duplicados y reapariciones."""

    def __init__(self, history_file: Path, max_age_hours: int = 24 * 14) -> None:
        """Inicializa el deduplicador con ventana configurable (por defecto 14 días).

        Args:
            history_file: Ruta al archivo JSON donde se almacena el historial.
            max_age_hours: Horas máximas de permanencia en caché antes de expirar (default: 336h = 14 días).
        """
        self.history_file = history_file
        self.max_age_hours = max_age_hours
        self.history: Dict[str, str] = {}  # Formato: {identificador_o_huella: timestamp_iso}
        self._load_history()

    def _load_history(self) -> None:
        """Carga el historial desde el archivo JSON si existe y purga registros antiguos."""
        if not self.history_file.exists():
            self.history = {}
            return

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                self.history = json.load(f)
            self.purge_expired()
        except Exception as e:
            logger.warning("No se pudo cargar el historial desde %s: %s. Se iniciará vacío.", self.history_file, str(e))
            self.history = {}

    def _build_fingerprint(self, job: JobOffer) -> Optional[str]:
        """Genera una huella digital (empresa + título) para detectar avisos republicados o multi-portal.

        Args:
            job: Objeto JobOffer a evaluar.

        Returns:
            Clave normalizada 'fp:empresa|titulo' o None si la empresa es confidencial/genérica.
        """
        norm_company = _normalize_key(job.company)
        norm_title = _normalize_key(job.title)
        if not norm_company or not norm_title:
            return None
        if any(gen in norm_company for gen in GENERIC_COMPANIES):
            return None
        return f"fp:{norm_company}|{norm_title}"

    def purge_expired(self) -> int:
        """Elimina las ofertas registradas hace más de max_age_hours.

        Returns:
            Cantidad de registros purgados del historial.
        """
        now = datetime.now()
        threshold = now - timedelta(hours=self.max_age_hours)
        initial_count = len(self.history)

        valid_history: Dict[str, str] = {}
        for identifier, timestamp_str in self.history.items():
            try:
                registered_at = datetime.fromisoformat(timestamp_str)
                if registered_at >= threshold:
                    valid_history[identifier] = timestamp_str
            except Exception:
                continue

        purged_count = initial_count - len(valid_history)
        if purged_count > 0:
            logger.info("Se purgaron %d registros con más de %d horas del historial.", purged_count, self.max_age_hours)

        self.history = valid_history
        return purged_count

    def is_duplicate(self, job: JobOffer) -> bool:
        """Verifica si una oferta ya fue registrada por ID o por huella (empresa + título).

        Args:
            job: Objeto JobOffer a verificar.

        Returns:
            True si la oferta ya fue procesada previamente; False si es nueva.
        """
        identifier = job.job_id or job.url
        if identifier and identifier in self.history:
            return True
        fingerprint = self._build_fingerprint(job)
        if fingerprint and fingerprint in self.history:
            return True
        return False

    def filter_new_offers(self, offers: List[JobOffer]) -> List[JobOffer]:
        """Filtra y devuelve únicamente las ofertas no vistas previamente, registrándolas.

        Args:
            offers: Lista de ofertas a evaluar.

        Returns:
            Lista de ofertas nuevas que no estaban en el historial.
        """
        self.purge_expired()
        new_offers: List[JobOffer] = []
        now_iso = datetime.now().isoformat()

        for job in offers:
            identifier = job.job_id or job.url
            if not identifier:
                continue

            if not self.is_duplicate(job):
                new_offers.append(job)
                self.history[identifier] = now_iso
                fingerprint = self._build_fingerprint(job)
                if fingerprint:
                    self.history[fingerprint] = now_iso

        if new_offers:
            self.save()

        return new_offers

    def save(self) -> None:
        """Guarda el historial actualizado en disco en formato JSON."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
            logger.debug("Historial actualizado guardado en %s (%d registros).", self.history_file, len(self.history))
        except Exception as e:
            logger.error("Error al guardar el historial en %s: %s", self.history_file, str(e))
