"""Punto de entrada principal y orquestador del prototipo Job Hunter Bot."""

import csv
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Asegurar que la raíz del proyecto esté en el PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.job import JobOffer
from src.scrapers.bumeran import BumeranScraper
from src.scrapers.computrabajo import ComputrabajoScraper
from src.scrapers.indeed import IndeedScraper
from src.scrapers.zonajobs import ZonaJobsScraper
from src.utils.database import JobDatabase
from src.utils.deduplicator import JobDeduplicator
from src.utils.keyword_filter import KeywordFilter
from src.utils.location_filter import is_allowed_location
from src.utils.time_filter import is_within_time_window

# Configuración de logging estructurado
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("JobHunterBot")


def load_config_urls(config_path: Path) -> List[dict]:
    """Carga y retorna las URLs habilitadas de todos los portales configurados.

    Args:
        config_path: Ruta al archivo urls.json.

    Returns:
        Lista de diccionarios con la configuración de cada búsqueda y su portal asociado.
    """
    if not config_path.exists():
        logger.error("No se encontró el archivo de configuración en: %s", config_path)
        return []

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        targets: List[dict] = []
        for portal_name, urls in data.items():
            if not isinstance(urls, list):
                continue
            for item in urls:
                if item.get("enabled", False):
                    item_copy = dict(item)
                    item_copy["portal"] = portal_name
                    targets.append(item_copy)

        return targets
    except Exception as e:
        logger.error("Error al leer %s: %s", config_path, str(e))
        return []


def save_offers_to_csv(offers: List[JobOffer], output_path: Path) -> None:
    """Exporta las ofertas filtradas a un archivo CSV.

    Args:
        offers: Lista de ofertas laborales que superaron los filtros.
        output_path: Ruta del archivo CSV destino.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["title", "company", "location", "published_time_text", "url", "job_id", "portal", "extracted_at"]

    file_exists = output_path.exists() and output_path.stat().st_size > 0

    try:
        with open(output_path, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction="ignore")
            if not file_exists:
                writer.writeheader()
            for offer in offers:
                writer.writerow(offer.to_dict())
        logger.info("Se guardaron exitosamente %d ofertas en %s", len(offers), output_path)
    except Exception as e:
        logger.error("Error al guardar el CSV en %s: %s", output_path, str(e))


def main(headless: bool = True) -> None:
    """Función principal de ejecución.
    
    Args:
        headless: Si es True, ejecuta los navegadores en segundo plano sin ventana gráfica.
    """
    logger.info("=== Iniciando ciclo de búsqueda de ofertas laborales (Silencioso/Headless: %s) ===", headless)

    project_root = Path(__file__).resolve().parent.parent
    config_file = project_root / "config" / "urls.json"
    profile_file = project_root / "config" / "profile.json"
    output_csv = project_root / "data" / "ofertas_filtradas.csv"
    history_file = project_root / "data" / "history_24h.json"

    search_targets = load_config_urls(config_file)
    if not search_targets:
        logger.warning("No hay URLs configuradas o habilitadas para procesar.")
        return

    logger.info("Se procesarán %d búsquedas/categorías configuradas.", len(search_targets))

    # Inicializamos el deduplicador (memoria de 24 horas), filtro de palabras clave y cliente de BD
    deduplicator = JobDeduplicator(history_file=history_file, max_age_hours=24)
    keyword_filter = KeywordFilter(config_path=profile_file)
    db = JobDatabase()

    # Inicializamos los scrapers disponibles para cada portal
    scrapers: Dict[str, Any] = {
        "computrabajo": ComputrabajoScraper(headless=headless),
        "bumeran": BumeranScraper(headless=headless),
        "indeed": IndeedScraper(headless=headless),
        "zonajobs": ZonaJobsScraper(headless=headless)
    }

    all_fresh_offers: List[JobOffer] = []

    for target in search_targets:
        category = target.get("category", "General")
        url = target.get("url", "")
        is_general = target.get("type") == "general"
        portal = target.get("portal", "computrabajo")

        scraper = scrapers.get(portal)
        if not scraper:
            logger.warning("No hay scraper registrado para el portal '%s'. Omitiendo.", portal)
            continue

        logger.info("--> Escaneando [%s]: '%s' (tipo: %s)", portal.upper(), category, "General" if is_general else "Específica")
        extracted_offers = scraper.extract(url)

        # 1. Filtro geográfico estricto (CABA, San Martín, Tres de Febrero, Zona Norte, Remoto)
        valid_loc_offers = [o for o in extracted_offers if is_allowed_location(o.location)]

        # 2. Filtro temporal de las 2 horas (120 minutos)
        fresh_offers = [o for o in valid_loc_offers if is_within_time_window(o.published_time_text, max_minutes=120)]

        # 3. Filtro semántico de palabras clave (inclusión de perfiles y exclusión de telemarketers/ventas/seniors)
        relevant_offers: List[JobOffer] = []
        for o in fresh_offers:
            is_rel, reason = keyword_filter.is_relevant(o.title, o.description, is_general_search=is_general)
            if is_rel:
                relevant_offers.append(o)
            else:
                logger.info("  [DESCARTADA] %s -> %s", o.title, reason)

        # 4. Filtro de duplicados (evita las ya vistas en las últimas 24 horas)
        new_offers = deduplicator.filter_new_offers(relevant_offers)

        logger.info(
            "[%s] %d encontradas | %d en zona | %d < 2h | %d relevantes | %d nuevas a guardar",
            category, len(extracted_offers), len(valid_loc_offers), len(fresh_offers), len(relevant_offers), len(new_offers)
        )

        # Mostrar detalle de las ofertas aceptadas
        for offer in new_offers:
            logger.info("  [ACEPTADA] %s | %s | %s | %s", offer.title, offer.company, offer.location, offer.published_time_text)
            logger.info("    Link directo: %s", offer.url)

        all_fresh_offers.extend(new_offers)

    # Resumen y guardado local y en la nube
    if all_fresh_offers:
        logger.info("Total de ofertas que superaron todos los filtros: %d", len(all_fresh_offers))
        save_offers_to_csv(all_fresh_offers, output_csv)
        logger.info("Archivo CSV actualizado en: %s", output_csv)

        # Sincronización en la nube (Supabase)
        if db.is_connected():
            synced = db.save_jobs(all_fresh_offers)
            logger.info("Sincronizadas %d ofertas con la base de datos Supabase en la nube.", synced)
    else:
        logger.info("No se encontraron ofertas dentro de la ventana de 2 horas en esta corrida.")

    logger.info("=== Ciclo de búsqueda finalizado exitosamente ===")


if __name__ == "__main__":
    import time
    is_loop = "--loop" in sys.argv or "-l" in sys.argv
    is_visible = "--visible" in sys.argv or "--headed" in sys.argv
    run_headless = not is_visible
    interval_seconds = 3600  # 60 minutos

    if is_loop:
        logger.info(
            "Modo continuo (--loop) activado: se ejecutará cada %d minutos (Navegador en segundo plano: %s).",
            interval_seconds // 60,
            run_headless
        )
        try:
            while True:
                main(headless=run_headless)
                logger.info("--> Próxima búsqueda en %d minutos. Presiona Ctrl+C para detener.", interval_seconds // 60)
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Ejecución continua detenida por el usuario.")
    else:
        main(headless=run_headless)
