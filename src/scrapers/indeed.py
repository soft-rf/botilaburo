"""Scraper específico para Indeed Argentina (ar.indeed.com)."""

import json
import logging
import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.models.job import JobOffer
from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class IndeedScraper(BaseScraper):
    """Implementa la extracción de ofertas laborales para Indeed Argentina."""

    BASE_DOMAIN = "https://ar.indeed.com"

    def __init__(self, headless: bool = True) -> None:
        """Inicializa el scraper de Indeed (sin bloqueo de assets para evitar filtros anti-bot)."""
        super().__init__(headless=headless, block_assets=False)

    def extract(self, url: str) -> List[JobOffer]:
        """Extrae ofertas de empleo desde una URL de búsqueda de Indeed Argentina.

        Args:
            url: Enlace de búsqueda en Indeed (idealmente ordenado con &sort=date).

        Returns:
            Lista de objetos JobOffer normalizados.
        """
        offers: List[JobOffer] = []
        self.logger.info("Iniciando extracción en Indeed: %s", url)

        try:
            content = self._fetch_html(url, wait_ms=2500)
            offers = self._parse_html(content)
            self.logger.info("Se extrajeron %d ofertas de Indeed.", len(offers))
        except Exception as e:
            self.logger.error("Error durante la extracción en Indeed: %s", str(e), exc_info=True)

        return offers

    def _parse_html(self, html: str) -> List[JobOffer]:
        """Parsea el HTML de Indeed extrayendo ofertas vía JSON inicial o selectores DOM de respaldo.

        Args:
            html: Código fuente HTML de la página de resultados de Indeed.

        Returns:
            Lista de ofertas JobOffer normalizadas.
        """
        # Estrategia 1: Intentar extraer datos estructurados desde window.mosaic.providerData
        offers = self._extract_from_mosaic_json(html)
        if offers:
            return offers

        # Estrategia 2: Respaldo mediante selectores DOM clásicos de BeautifulSoup
        self.logger.warning("No se detectó bloque JSON de mosaic. Intentando parseo directo del DOM...")
        return self._extract_from_dom(html)

    def _extract_from_mosaic_json(self, html: str) -> List[JobOffer]:
        """Extrae ofertas del payload JSON inyectado por Indeed en window.mosaic.providerData.

        Args:
            html: Código HTML completo de la página.

        Returns:
            Lista de ofertas parseadas o lista vacía si no se localiza el bloque JSON.
        """
        job_offers: List[JobOffer] = []
        try:
            match = re.search(
                r'window\.mosaic\.providerData\["mosaic-provider-jobcards"\]\s*=\s*(\{.*?\});\s*(?:window|\n|</script>)',
                html,
                re.DOTALL,
            )
            if not match:
                return []

            data = json.loads(match.group(1))
            results = (
                data.get("metaData", {})
                .get("mosaicProviderJobCardsModel", {})
                .get("results", [])
            )

            for item in results:
                job_id = item.get("jobkey")
                title = item.get("title")
                if not job_id or not title:
                    continue

                company = item.get("company") or "Confidencial / No especificada"
                location = item.get("formattedLocation") or "Argentina"
                pub_time = item.get("formattedRelativeTime") or "Recién publicado"

                # Limpieza de snippet descriptivo
                raw_snippet = item.get("snippet", "")
                clean_snippet = BeautifulSoup(raw_snippet, "html.parser").get_text(" ", strip=True)
                full_description = clean_snippet if clean_snippet else title

                full_url = f"{self.BASE_DOMAIN}/viewjob?jk={job_id}"

                offer = JobOffer(
                    title=title.strip(),
                    company=company.strip(),
                    location=location.strip(),
                    published_time_text=pub_time.strip(),
                    url=full_url,
                    job_id=job_id.strip(),
                    description=full_description,
                    portal="indeed",
                )
                job_offers.append(offer)

        except Exception as e:
            self.logger.warning("Fallo al procesar JSON de mosaic en Indeed: %s", str(e))

        return job_offers

    def _extract_from_dom(self, html: str) -> List[JobOffer]:
        """Extrae ofertas parseando directamente las tarjetas HTML del DOM.

        Args:
            html: Código HTML de la página.

        Returns:
            Lista de ofertas extraídas mediante selectores CSS.
        """
        soup = BeautifulSoup(html, "html.parser")
        job_offers: List[JobOffer] = []
        seen_ids = set()

        cards = soup.select("div.cardOutline, div.job_seen_beacon")
        for card in cards:
            try:
                title_el = card.select_one("a.jcs-JobTitle")
                if not title_el:
                    continue

                job_id = title_el.get("data-jk")
                if not job_id:
                    href = title_el.get("href", "")
                    jk_match = re.search(r"jk=([a-zA-Z0-9]+)", href)
                    if jk_match:
                        job_id = jk_match.group(1)

                if not job_id or job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                title = title_el.get_text(strip=True)

                # Empresa
                comp_el = card.find(attrs={"data-testid": "company-name"})
                company = comp_el.get_text(strip=True) if comp_el else "Confidencial / No especificada"

                # Ubicación
                loc_el = card.find(attrs={"data-testid": "text-location"})
                location = loc_el.get_text(strip=True) if loc_el else "Argentina"

                # Fecha / Antigüedad
                date_el = card.find(attrs={"data-testid": "myJobsStateDate"}) or card.select_one("span.date")
                pub_time = date_el.get_text(strip=True) if date_el else "Recién publicado"

                # Snippet
                snippet_el = card.find(attrs={"data-testid": "belowJobSnippet"})
                snippet = snippet_el.get_text(" ", strip=True) if snippet_el else title

                full_url = f"{self.BASE_DOMAIN}/viewjob?jk={job_id}"

                offer = JobOffer(
                    title=title,
                    company=company,
                    location=location,
                    published_time_text=pub_time,
                    url=full_url,
                    job_id=job_id,
                    description=snippet,
                    portal="indeed",
                )
                job_offers.append(offer)

            except Exception as e:
                self.logger.warning("Error al parsear tarjeta DOM de Indeed: %s", str(e))
                continue

        return job_offers
