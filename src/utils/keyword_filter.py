"""Módulo de filtrado semántico y de relevancia basado en palabras clave locales."""

import json
import logging
from pathlib import Path
import re
import unicodedata
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """Normaliza texto eliminando acentos, caracteres especiales y convirtiendo a minúsculas."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    clean = "".join(c for c in nfkd if not unicodedata.combining(c))
    return clean.lower().strip()


class KeywordFilter:
    """Filtra ofertas laborales evaluando coincidencia de palabras clave positivas y negativas."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """Inicializa el filtro cargando palabras clave desde el archivo de configuración.

        Args:
            config_path: Ruta a config/profile.json con listas de palabras positivas y negativas.
        """
        self.positive_keywords: List[str] = []
        self.negative_keywords: List[str] = []

        if config_path and config_path.exists():
            self._load_from_config(config_path)
        else:
            self._load_defaults()

    def _load_from_config(self, config_path: Path) -> None:
        """Carga listas de palabras clave desde un archivo JSON."""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                keywords = data.get("keywords", {})
                self.positive_keywords = [normalize_text(kw) for kw in keywords.get("positive", []) if kw]
                self.negative_keywords = [normalize_text(kw) for kw in keywords.get("negative", []) if kw]
                logger.info(
                    "Filtro de palabras clave cargado: %d positivas, %d negativas.",
                    len(self.positive_keywords), len(self.negative_keywords)
                )
        except Exception as e:
            logger.error("Error al cargar %s: %s. Se usarán valores predeterminados.", config_path, str(e))
            self._load_defaults()

    def _load_defaults(self) -> None:
        """Valores por defecto en caso de no encontrar archivo de configuración."""
        self.positive_keywords = [
            "soporte", "help desk", "mesa de ayuda", "tecnico", "redes", "it", "farmacia", "administrativ"
        ]
        self.negative_keywords = [
            "telemarketer", "ventas", "cobranza", "chofer", "camarer", "cociner", "limpieza", "senior", "sr"
        ]

    def _matches_keyword(self, text: str, keyword: str) -> bool:
        """Determina si una palabra clave coincide en el texto usando límites de palabra si es corta."""
        # Palabras de 3 letras o menos (ej: 'sr', 'it', 'noc') requieren límite exacto de palabra
        if len(keyword) <= 3:
            pattern = rf"\b{re.escape(keyword)}\b"
            return bool(re.search(pattern, text))
        return keyword in text

    def is_relevant(self, title: str, description: str = "", is_general_search: bool = False) -> Tuple[bool, str]:
        """Evalúa si una oferta es relevante para el perfil.

        Reglas:
        1. Si contiene alguna palabra negativa (en título) -> DESCARTADA inmediatamente.
        2. Si proviene de búsqueda general -> DEBE contener al menos una palabra positiva.
        3. Si proviene de búsqueda específica -> Se asume positiva a menos que contenga palabra negativa.

        Args:
            title: Título de la oferta de empleo.
            description: Resumen o descripción de la oferta.
            is_general_search: Indica si la búsqueda fue general (ej: CABA sin filtrar categoría).

        Returns:
            Tupla (es_relevante: bool, razon: str).
        """
        norm_title = normalize_text(title)
        norm_desc = normalize_text(description)
        combined_text = f"{norm_title} {norm_desc}"

        # 1. Comprobación de palabras negativas (descarte prioritario)
        for neg in self.negative_keywords:
            if self._matches_keyword(norm_title, neg):
                return False, f"Descarte por término excluido: '{neg}'"

        # 2. Comprobación para búsquedas generales (requiere coincidencia positiva)
        if is_general_search:
            for pos in self.positive_keywords:
                if self._matches_keyword(combined_text, pos):
                    return True, f"Coincidencia con término: '{pos}'"
            return False, "Búsqueda general: no contiene palabras clave requeridas"

        # 3. Búsquedas específicas: ya vienen pre-filtradas por la categoría
        return True, "Aprobada por categoría específica sin términos negativos"
