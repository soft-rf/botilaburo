"""Módulo de gestión de historial y deduplicación con ventana deslizante de 24 horas."""

from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
from typing import Dict, List

from src.models.job import JobOffer

logger = logging.getLogger(__name__)


class JobDeduplicator:
    """Administra el registro de ofertas vistas en las últimas 24 horas para evitar duplicados."""

    def __init__(self, history_file: Path, max_age_hours: int = 24) -> None:
        """Inicializa el deduplicador.

        Args:
            history_file: Ruta al archivo JSON donde se almacena el historial.
            max_age_hours: Horas máximas de permanencia en el historial antes de expirar.
        """
        self.history_file = history_file
        self.max_age_hours = max_age_hours
        self.history: Dict[str, str] = {}  # Formato: {identificador: timestamp_iso}
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

    def purge_expired(self) -> int:
        """Elimina las ofertas registradas hace más de max_age_hours.

        Returns:
            Cantidad de ofertas purgadas del historial.
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
            logger.info("Se purgaron %d ofertas con más de %d horas del historial.", purged_count, self.max_age_hours)

        self.history = valid_history
        return purged_count

    def is_duplicate(self, job: JobOffer) -> bool:
        """Verifica si una oferta ya fue registrada en la ventana activa.

        Args:
            job: Objeto JobOffer a verificar.

        Returns:
            True si la oferta ya fue procesada previamente; False si es nueva.
        """
        identifier = job.job_id or job.url
        return identifier in self.history

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

            if identifier not in self.history:
                new_offers.append(job)
                self.history[identifier] = now_iso

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
