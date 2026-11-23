"""Módulo de conexión y persistencia en la base de datos Supabase."""

import logging
import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from supabase import Client, create_client

from src.models.job import JobOffer

logger = logging.getLogger(__name__)


class JobDatabase:
    """Administra la sincronización de ofertas laborales con la base de datos en Supabase."""

    def __init__(self, env_path: Optional[Path] = None) -> None:
        """Inicializa el cliente de Supabase cargando credenciales de entorno.

        Args:
            env_path: Ruta opcional al archivo .env.
        """
        if env_path and env_path.exists():
            load_dotenv(dotenv_path=env_path)
        else:
            load_dotenv()

        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        # Si la URL viene con '/rest/v1', la limpiamos para el SDK
        if self.url.endswith("/rest/v1"):
            self.url = self.url[:-8]

        self.service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.client: Optional[Client] = None

        if self.url and self.service_key:
            try:
                self.client = create_client(self.url, self.service_key)
                logger.info("Conexión con Supabase inicializada correctamente en %s", self.url)
            except Exception as e:
                logger.error("Error al inicializar el cliente de Supabase: %s", str(e))
        else:
            logger.warning("Faltan variables SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en el entorno.")

    def is_connected(self) -> bool:
        """Indica si el cliente está listo para realizar operaciones."""
        return self.client is not None

    def save_jobs(self, offers: List[JobOffer]) -> int:
        """Inserta o actualiza ofertas en la tabla 'jobs' de Supabase evitando duplicados.

        Args:
            offers: Lista de objetos JobOffer a persistir.

        Returns:
            Cantidad de ofertas insertadas exitosamente.
        """
        if not self.is_connected() or not offers:
            return 0

        saved_count = 0
        records = []

        for offer in offers:
            external_id = offer.job_id or offer.url
            if not external_id:
                continue

            records.append({
                "source": offer.portal,
                "external_id": external_id,
                "title": offer.title,
                "company": offer.company,
                "location": offer.location,
                "published_time_text": offer.published_time_text,
                "url": offer.url,
                "full_description": offer.description or offer.title,
                "status": "new"
            })

        try:
            # Usamos upsert basado en la restricción única (source, external_id)
            response = self.client.table("jobs").upsert(
                records,
                on_conflict="source, external_id"
            ).execute()

            if response.data:
                saved_count = len(response.data)
                logger.info("Se sincronizaron %d ofertas con la base de datos Supabase.", saved_count)

        except Exception as e:
            logger.error("Error al guardar ofertas en Supabase: %s", str(e), exc_info=True)

        return saved_count
