"""Scraper ligero para LinkedIn Argentina usando el endpoint público sin login (jobs-guest)."""

import logging
import re
import time
import urllib.error
import urllib.request
from typing import List

from bs4 import BeautifulSoup

from src.models.job import JobOffer
from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    """Extrae ofertas públicas de LinkedIn sin abrir navegador ni usar credenciales."""

    BASE_DOMAIN = "https://www.linkedin.com"

    def __init__(self, headless: bool = True, delay_seconds: float = 2.0) -> None:
        """Inicializa el scraper HTTP ligero de LinkedIn.

        Args:
            headless: Parámetro mantenido por compatibilidad con BaseScraper.
            delay_seconds: Pausa cortés entre consultas consecutivas para evitar HTTP 429.
        """
        super().__init__(headless=headless, block_assets=True)
        self.delay_seconds: float = delay_seconds
        self._last_request_ts: float = 0.0

    def start(self) -> None:
        """No requiere abrir Chromium; mantiene compatibilidad con el context manager."""
        return

    def close(self) -> None:
        """No requiere cerrar Chromium; mantiene compatibilidad con el context manager."""
        return

    def extract(self, url: str) -> List[JobOffer]:
        """Extrae ofertas desde el endpoint público jobs-guest de LinkedIn.

        Args:
            url: URL de búsqueda en /jobs-guest/jobs/api/seeMoreJobPostings/search.

        Returns:
            Lista de ofertas JobOffer normalizadas.
        """
        offers: List[JobOffer] = []
        self.logger.info("Iniciando extracción en LinkedIn (Guest API): %s", url)

        # Pausa cortés entre requests consecutivos
        elapsed = time.time() - self._last_request_ts
        if self._last_request_ts > 0 and elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": self.DEFAULT_USER_AGENT,
                    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
            self._last_request_ts = time.time()
            with urllib.request.urlopen(req, timeout=20) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            offers = self._parse_html(html)
            self.logger.info("Se extrajeron %d ofertas de LinkedIn.", len(offers))

        except urllib.error.HTTPError as e:
            if e.code == 429:
                self.logger.warning("LinkedIn devolvió 429 (límite temporal de velocidad). Se omite esta consulta.")
            else:
                self.logger.error("Error HTTP %d en LinkedIn: %s", e.code, str(e))
        except Exception as e:
            self.logger.error("Error durante la extracción en LinkedIn: %s", str(e), exc_info=True)

        return offers

    def _parse_html(self, html: str) -> List[JobOffer]:
        """Parsea las tarjetas HTML devueltas por el endpoint público de LinkedIn.

        Args:
            html: Fragmento HTML con elementos <li> de ofertas laborales.

        Returns:
            Lista de objetos JobOffer.
        """
        soup = BeautifulSoup(html, "html.parser")
        job_offers: List[JobOffer] = []
        seen_ids = set()

        for card in soup.select("li"):
            try:
                title_el = card.select_one("h3.base-search-card__title")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)

                # Extraer ID numérico desde data-entity-urn="urn:li:jobPosting:1234567890"
                base_card = card.select_one("div.base-card")
                urn = base_card.get("data-entity-urn", "") if base_card else ""
                id_match = re.search(r"(\d+)$", urn)

                link_el = card.select_one("a.base-card__full-link")
                raw_href = link_el.get("href", "") if link_el else ""
                if not id_match and raw_href:
                    id_match = re.search(r"-(\d+)(?:\?|$)", raw_href)

                if not id_match:
                    continue

                job_id = id_match.group(1)
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                # URL canónica limpia (compatible con la app móvil y web de LinkedIn)
                full_url = f"{self.BASE_DOMAIN}/jobs/view/{job_id}"

                comp_el = card.select_one("h4.base-search-card__subtitle")
                company = comp_el.get_text(strip=True) if comp_el else "Confidencial / No especificada"

                loc_el = card.select_one("span.job-search-card__location")
                location = loc_el.get_text(strip=True) if loc_el else "Argentina"

                time_el = card.select_one("time")
                published_time = time_el.get_text(strip=True) if time_el else "Recién publicado"

                description = f"{title} en {company} ({location}). Ver detalles completos y postularse en LinkedIn."

                offer = JobOffer(
                    title=title,
                    company=company,
                    location=location,
                    published_time_text=published_time,
                    url=full_url,
                    job_id=job_id,
                    description=description,
                    portal="linkedin",
                )
                job_offers.append(offer)

            except Exception as e:
                self.logger.warning("No se pudo parsear una tarjeta de LinkedIn: %s", str(e))
                continue

        return job_offers
