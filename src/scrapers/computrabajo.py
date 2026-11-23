"""Scraper específico para Computrabajo Argentina."""

import logging
import re
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Browser, Page

from src.models.job import JobOffer
from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class ComputrabajoScraper(BaseScraper):
    """Implementa la extracción de ofertas laborales para Computrabajo Argentina."""

    BASE_DOMAIN = "https://ar.computrabajo.com"

    def __init__(self, headless: bool = False) -> None:
        """Inicializa el scraper con modo de visualización configurable."""
        super().__init__(headless=headless)

    def extract(self, url: str) -> List[JobOffer]:
        """Extrae ofertas de empleo desde una URL de listado de Computrabajo.

        Args:
            url: Enlace de búsqueda ordenado por fecha de publicación.

        Returns:
            Lista de objetos JobOffer encontrados.
        """
        offers: List[JobOffer] = []
        self.logger.info("Iniciando extracción en Computrabajo: %s", url)

        try:
            with sync_playwright() as p:
                browser: Browser = p.chromium.launch(
                    headless=self.headless,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 800}
                )
                page: Page = context.new_page()

                # Cargar página con tiempo prudente
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3000)  # Breve pausa para asegurar renderizado

                content = page.content()
                browser.close()

                offers = self._parse_html(content)
                self.logger.info("Se extrajeron %d ofertas de Computrabajo.", len(offers))

        except Exception as e:
            self.logger.error("Error durante la extracción en Computrabajo: %s", str(e), exc_info=True)

        return offers

    def _parse_html(self, html: str) -> List[JobOffer]:
        """Parsea el HTML crudo utilizando BeautifulSoup para obtener las ofertas.

        Args:
            html: Código HTML de la página de resultados.

        Returns:
            Lista de ofertas JobOffer.
        """
        soup = BeautifulSoup(html, "html.parser")
        job_offers: List[JobOffer] = []

        articles = soup.find_all("article", class_=lambda c: c and "box_offer" in c)
        if not articles:
            articles = soup.find_all("article")

        for article in articles:
            try:
                # 0. ID de la oferta
                job_id = article.get("data-id") or article.get("id") or ""

                # 1. Título y Enlace
                title_elem = article.find("h2") or article.find("h1")
                link_elem = title_elem.find("a") if title_elem else article.find("a", class_=lambda c: c and "js-o-link" in c)

                if not link_elem:
                    continue

                title = link_elem.get_text(strip=True)
                relative_url = link_elem.get("href", "")
                full_url = urljoin(self.BASE_DOMAIN, relative_url)

                # 2. Empresa (omitiendo puntajes de calificación si existen)
                company = "Confidencial / No especificada"
                company_link = article.find("a", attrs={"offer-grid-article-company-url": True}) or article.find("a", class_=lambda c: c and "t_ellipsis" in c)
                if company_link:
                    company = company_link.get_text(strip=True)
                else:
                    company_p = article.find("p", class_=lambda c: c and "fs16" in c and "fc_base" in c)
                    if company_p:
                        raw_company = company_p.get_text(strip=True)
                        # Limpiar posible puntaje inicial como '4,1Empresa'
                        company = re.sub(r"^\d+,\d+", "", raw_company).strip() or raw_company

                # 3. Ubicación (omitiendo etiquetas de puntajes como '4,1')
                location = "Argentina"
                for span in article.find_all("span", class_="mr10"):
                    text = span.get_text(strip=True)
                    if text and not re.match(r"^\d+,\d+$", text) and "star" not in span.get("class", []):
                        location = text
                        break

                # 4. Tiempo de publicación
                published_time = "Desconocido"
                time_p = article.find("p", class_=lambda c: c and "fs13" in c and "fc_aux" in c)
                if time_p:
                    # Limpia espacios dobles internos: 'Hace  8  horas' -> 'Hace 8 horas'
                    raw_time = time_p.get_text(strip=True)
                    published_time = re.sub(r"\s+", " ", raw_time)

                # 5. Breve descripción o requisitos
                desc_elem = article.find("p", class_=lambda c: c and ("w100" in c or "disc" in c))
                description = desc_elem.get_text(strip=True) if desc_elem else ""

                offer = JobOffer(
                    title=title,
                    company=company,
                    location=location,
                    published_time_text=published_time,
                    url=full_url,
                    job_id=job_id,
                    description=description,
                    portal="computrabajo"
                )
                job_offers.append(offer)

            except Exception as e:
                self.logger.warning("No se pudo parsear una tarjeta de oferta: %s", str(e))
                continue

        return job_offers
