"""Módulo base para scrapers de portales de empleo con sesión reutilizable de Playwright."""

from abc import ABC, abstractmethod
import logging
from typing import Any, List, Optional

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, Route, sync_playwright

from src.models.job import JobOffer

BLOCKED_RESOURCE_TYPES = ("image", "media", "font")


class BaseScraper(ABC):
    """Clase abstracta que define la interfaz y el motor optimizado de navegación."""

    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    def __init__(self, headless: bool = True, block_assets: bool = True) -> None:
        """Inicializa el scraper base.

        Args:
            headless: Indica si el navegador debe ejecutarse en segundo plano (True) o visible (False).
            block_assets: Si es True, bloquea imágenes, videos y fuentes para acelerar la carga.
        """
        self.headless: bool = headless
        self.block_assets: bool = block_assets
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    def start(self) -> None:
        """Inicia una instancia reutilizable de Chromium y su contexto."""
        if self._browser is not None:
            return

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        self._context = self._browser.new_context(
            user_agent=self.DEFAULT_USER_AGENT,
            viewport={"width": 1280, "height": 800},
            locale="es-419",
        )
        # Bloquear imágenes, videos y fuentes si el portal lo tolera sin disparar anti-bot
        if self.block_assets:
            self._context.route("**/*", self._route_interceptor)

    def close(self) -> None:
        """Cierra de forma segura el contexto, el navegador y la sesión de Playwright."""
        try:
            if self._context is not None:
                self._context.close()
        except Exception:
            pass
        finally:
            self._context = None

        try:
            if self._browser is not None:
                self._browser.close()
        except Exception:
            pass
        finally:
            self._browser = None

        try:
            if self._playwright is not None:
                self._playwright.stop()
        except Exception:
            pass
        finally:
            self._playwright = None

    def __enter__(self) -> "BaseScraper":
        """Soporte para uso con 'with scraper:' reutilizando el navegador."""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Cierra la sesión automáticamente al salir del bloque 'with'."""
        self.close()

    @staticmethod
    def _route_interceptor(route: Route) -> None:
        """Aborta recursos multimedia innecesarios para scraping de texto HTML."""
        if route.request.resource_type in BLOCKED_RESOURCE_TYPES:
            route.abort()
        else:
            route.continue_()

    def _fetch_html(self, url: str, wait_ms: int = 2000, timeout_ms: int = 30000) -> str:
        """Obtiene el HTML renderizado de una URL reutilizando el navegador si está abierto.

        Args:
            url: URL a visitar.
            wait_ms: Espera breve tras domcontentloaded para hidratación SPA.
            timeout_ms: Tiempo máximo de espera de navegación.

        Returns:
            Contenido HTML completo de la página.
        """
        owns_session = self._browser is None
        if owns_session:
            self.start()

        page: Optional[Page] = None
        try:
            assert self._context is not None
            page = self._context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            if wait_ms > 0:
                page.wait_for_timeout(wait_ms)
            return page.content()
        finally:
            if page is not None:
                try:
                    page.close()
                except Exception:
                    pass
            if owns_session:
                self.close()

    @abstractmethod
    def extract(self, url: str) -> List[JobOffer]:
        """Extrae ofertas de empleo desde una URL dada.

        Args:
            url: Enlace al listado de ofertas ordenado por más reciente.

        Returns:
            Lista de ofertas estructuradas JobOffer.
        """
        pass
