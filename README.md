# Job Hunter Bot - Asistente Inteligente de Búsqueda Laboral

Sistema automatizado en Python diseñado para recolectar, filtrar y evaluar ofertas de empleo recién publicadas en tiempo real. Su objetivo es maximizar la tasa de respuesta permitiendo postularse dentro de las primeras horas de publicación, filtrando el 90% del ruido mediante coincidencia inteligente con el perfil del postulante.

---

## 1. Visión y Funcionamiento del Sistema

El bot no busca reemplazar la postulación humana, sino eliminar el tiempo improductivo de revisar cientos de ofertas irrelevantes a lo largo del día:

1. **Extracción Rápida (Ventana de 2 Horas):** Extrae periódicamente (ej. cada 1 hora) las ofertas publicadas recientemente (menos de 120 minutos) en portales seleccionados (Computrabajo Argentina, enfocado en CABA, GBA y Remoto).
2. **Control de Duplicados (Memoria de 24 Horas):** Un registro local temporal almacena los enlaces o identificadores ya analizados durante las últimas 24 horas para no re-procesar postulaciones repetidas entre corridas.
3. **Filtro de Relevancia Adaptable (IA + Perfil CV):** En lugar de reglas rígidas de código, un modelo de lenguaje (Google Gemini API - capa gratuita) compara la descripción del puesto con el perfil de experiencia del usuario (`config/profile.json` o CV).
   * **Perfil Flexible:** Permite buscar simultáneamente en áreas prioritarias (Soporte Técnico / Help Desk) y secundarias (Farmacia Comercial, Administrativo), sin modificar el código fuente.
4. **Salida Limpia para Inspección Humana:** Las ofertas que superan el filtro se exportan con enlace directo en formato **CSV** (Fase 1) y posteriormente a **Google Sheets** (Fase 2) para revisión manual y postulación inmediata.

---

## 2. Estructura del Proyecto

El código está organizado bajo principios de arquitectura limpia y modular, separando la recolección, el procesamiento y la configuración:

```text
botilabu/
├── config/
│   ├── urls.json               # URLs de búsqueda configuradas (regiones y puestos)
│   └── profile.json            # Experiencias, habilidades y preferencias del CV
├── data/                       # Salida de datos y caché (ignorado en Git)
│   ├── .gitkeep
│   ├── history_24h.json        # Caché de ofertas procesadas en las últimas 24hs
│   └── ofertas_filtradas.csv   # Ofertas recomendadas para postular
├── src/
│   ├── models/
│   │   ├── __init__.py
│   │   └── job.py              # Esquema tipado de datos de la oferta (JobOffer)
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base.py             # Clase abstracta base para todos los portales
│   │   └── computrabajo.py     # Scraper específico de Computrabajo
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── time_filter.py      # Normalizador y filtro temporal ("Hace X min/horas")
│   │   ├── location_filter.py  # Filtro geográfico estricto (CABA, San Martín, Zona Norte, etc.)
│   │   ├── keyword_filter.py   # Filtro semántico local (inclusión de perfiles y exclusión de ventas/seniors)
│   │   └── deduplicator.py     # Gestor de caché deslizante de 24 horas
│   └── main.py                 # Orquestador del flujo completo
├── .gitignore                  # Exclusión de venv, datos locales y secretos
├── requirements.txt            # Dependencias del proyecto
└── README.md                   # Documentación principal
```

---

## 4. Guía de Instalación y Puesta en Marcha

### Prerrequisitos
* Python 3.11 o superior instalado.
* Git (opcional pero recomendado para control de versiones).

### Paso 1: Activar el Entorno Virtual
Abre tu terminal (PowerShell en Windows) en la carpeta raíz del proyecto:
```powershell
.\venv\Scripts\Activate.ps1
```
*(Si PowerShell bloquea la ejecución de scripts, ejecuta antes: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*.

### Paso 2: Instalar Dependencias
Instala las librerías básicas del proyecto:
```powershell
pip install -r requirements.txt
```

### Paso 3: Instalar el Navegador para Playwright
Playwright requiere descargar los binarios de los navegadores que utilizará:
```powershell
playwright install chromium
```

### Paso 4: Ejecutar el Proyecto
```powershell
python src/main.py
```

---

## 5. Roadmap de Implementación (Paso a Paso)

- [x] **Paso 1: Entorno y Configuración Base**
  - Dependencias instaladas en `requirements.txt` (`playwright`, `beautifulsoup4`).
  - Modelo estructurado `src/models/job.py` y configuración de objetivos en `config/urls.json`.
- [x] **Paso 2: Conexión con Computrabajo (Playwright)**
  - Implementación de `src/scrapers/base.py` y `src/scrapers/computrabajo.py`.
  - Navegación anti-bloqueo y extracción validada con BeautifulSoup.
- [x] **Paso 3: Filtro Temporal de 2 Horas**
  - Módulo `src/utils/time_filter.py` para parsear marcas de tiempo ("Hace X minutos", "Hace 1 hora") y limitar a 120 min.
- [x] **Paso 4: Filtro Geográfico Estricto**
  - Módulo `src/utils/location_filter.py` limitando a CABA, San Martín, Tres de Febrero, Zona Norte y Remoto.
- [x] **Paso 5: Filtro Semántico Local (Sin APIs Externas)**
  - Módulo `src/utils/keyword_filter.py` con palabras positivas (IT, Farmacia, Admin) y descarte inmediato de negativas (ventas, telemarketers, choferes, seniors).
- [x] **Paso 6: Memoria de 24 Horas (Deduplicación)**
  - Módulo `src/utils/deduplicator.py` con ventana deslizante de 24h para evitar re-procesar ofertas repetidas.
- [x] **Paso 7: Exportación Local a CSV**
  - Volcado ordenado en `data/ofertas_filtradas.csv` con título, empresa, ubicación, enlace directo y fecha.
- [ ] **Paso 8: Conexión con Google Sheets (Opcional - Próxima Fase)**
  - Sincronización automática de las ofertas seleccionadas directamente a una hoja de cálculo en la nube.
