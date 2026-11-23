"""Módulo base para scrapers de portales de empleo."""

from abc import ABC, abstractmethod
import logging
from typing import List

from src.models.job import JobOffer


class BaseScraper(ABC):
    """Clase abstracta que define la interfaz común para los scrapers de empleo."""

    def __init__(self, headless: bool = False) -> None:
        """Inicializa el scraper base.

        Args:
            headless: Indica si el navegador debe ejecutarse en segundo plano (True) o visible (False).
        """
        self.headless: bool = headless
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def extract(self, url: str) -> List[JobOffer]:
        """Extrae ofertas de empleo desde una URL dada.

        Args:
            url: Enlace al listado de ofertas ordenado por más reciente.

        Returns:
            Lista de ofertas estructuradas JobOffer.
        """
        pass
