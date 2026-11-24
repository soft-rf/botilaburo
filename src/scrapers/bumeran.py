"""Scraper específico para Bumeran Argentina."""

import logging
import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.models.job import JobOffer
from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class BumeranScraper(BaseScraper):
    """Implementa la extracción de ofertas laborales para Bumeran Argentina."""

    BASE_DOMAIN = "https://www.bumeran.com.ar"

    def __init__(self, headless: bool = True) -> None:
        """Inicializa el scraper de Bumeran con modo visual o headless."""
        super().__init__(headless=headless)

    def extract(self, url: str) -> List[JobOffer]:
        """Extrae ofertas de empleo desde una URL de listado de Bumeran.

        Args:
            url: Enlace de búsqueda en Bumeran (idealmente con ?recientes=true).

        Returns:
            Lista de objetos JobOffer encontrados.
        """
        offers: List[JobOffer] = []
        self.logger.info("Iniciando extracción en Bumeran: %s", url)

        try:
            content = self._fetch_html(url, wait_ms=2200)
            offers = self._parse_html(content)
            self.logger.info("Se extrajeron %d ofertas de Bumeran.", len(offers))
        except Exception as e:
            self.logger.error("Error durante la extracción en Bumeran: %s", str(e), exc_info=True)

        return offers

    def _parse_html(self, html: str) -> List[JobOffer]:
        """Parsea el HTML crudo utilizando BeautifulSoup para obtener las ofertas de Bumeran.

        Args:
            html: Código HTML de la página de resultados de Bumeran.

        Returns:
            Lista de ofertas JobOffer normalizadas.
        """
        soup = BeautifulSoup(html, "html.parser")
        job_offers: List[JobOffer] = []
        seen_ids = set()

        # En Bumeran las ofertas tienen enlaces con formato /empleos/...-<ID>.html
        links = soup.find_all("a", href=lambda h: h and "/empleos/" in h and ".html" in h)

        for a in links:
            try:
                href = a.get("href", "")
                id_match = re.search(r"-(\d+)\.html", href)
                if not id_match:
                    continue

                job_id = id_match.group(1)
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                full_url = urljoin(self.BASE_DOMAIN, href)

                # Buscar el contenedor padre que contiene los datos del aviso
                card = a
                for _ in range(5):
                    if card.parent and card.parent.name in ["div", "article"]:
                        card = card.parent

                # 1. Título
                h2 = card.find("h2")
                if not h2:
                    continue
                title = h2.get_text(strip=True)

                # 2. Tiempo de publicación
                time_keywords = ["publicado", "actualizado"]
                time_tag = card.find(
                    lambda t: t.name in ["h3", "p", "span"]
                    and any(k in t.get_text(strip=True).lower() for k in time_keywords)
                )
                published_time = time_tag.get_text(strip=True) if time_tag else "Desconocido"

                # 3. Ubicación (icono de ubicación o etiqueta con aria-label)
                location = "Argentina"
                loc_icon = card.find("i", attrs={"aria-label": "Ubicación"})
                if loc_icon and loc_icon.parent:
                    loc_h3 = loc_icon.parent.find("h3") or loc_icon.parent.find("span")
                    if loc_h3:
                        location = loc_h3.get_text(strip=True)

                # 4. Empresa
                h3_elements = [h.get_text(strip=True) for h in card.find_all("h3")]
                company_candidates = [
                    h for h in h3_elements
                    if not any(k in h.lower() for k in time_keywords)
                    and h != location
                    and h not in ["Presencial", "Híbrido", "Remoto", "Postulación rápida", "Múltiples vacantes"]
                ]
                company = company_candidates[0] if company_candidates else "Confidencial / No especificada"

                # 5. Modalidad y breve descripción
                modality_icon = card.find("i", attrs={"aria-label": "Modalidad"})
                modality = ""
                if modality_icon and modality_icon.parent:
                    mod_elem = modality_icon.parent.find("h3") or modality_icon.parent.find("span")
                    if mod_elem:
                        modality = mod_elem.get_text(strip=True)

                # Bumeran suele incluir snippets descriptivos en párrafos o spans
                desc_p = card.find("p")
                desc_text = desc_p.get_text(strip=True) if desc_p else ""
                full_description = f"{desc_text} (Modalidad: {modality})".strip() if modality else desc_text

                offer = JobOffer(
                    title=title,
                    company=company,
                    location=location,
                    published_time_text=published_time,
                    url=full_url,
                    job_id=job_id,
                    description=full_description or title,
                    portal="bumeran"
                )
                job_offers.append(offer)

            except Exception as e:
                self.logger.warning("No se pudo parsear una tarjeta de Bumeran: %s", str(e))
                continue

        return job_offers
