# Job Hunter Bot - Asistente Inteligente y Multi-Portal de Búsqueda Laboral

Sistema automatizado de ingeniería en Python diseñado para recolectar, filtrar y sincronizar ofertas de empleo recién publicadas en tiempo real. Su objetivo es maximizar la tasa de respuesta permitiendo postularse dentro de las primeras horas de publicación, filtrando el 90% del ruido mediante reglas geográficas estrictas, ventanas temporales (< 2 horas) y filtros semánticos adaptables al perfil del postulante.

---

## 1. Visión y Funcionamiento del Ecosistema

El sistema opera como un pipeline de datos desacoplado y multi-portal:

```
┌─────────────────────────────────┐
│       Scrapers / Workers        │
│  (Computrabajo, Bumeran, etc.)  │
└────────────────┬────────────────┘
                 │ (Aplica filtros locales: Zona + Tiempo 2h + Keywords + Deduplicador 24h)
                 ▼
┌─────────────────────────────────┐
│     Base de Datos Cloud         │
│     Supabase (PostgreSQL)       │ ◀── Respaldo local en data/ofertas_filtradas.csv
└────────────────┬────────────────┘
                 │ (Sincronización en tiempo real)
                 ▼
┌─────────────────────────────────┐
│     Web App Mobile-First        │
│   (Next.js + Tailwind / Vercel) │
└────────────────┬────────────────┘
                 │ (PWA en el celular con PIN de acceso)
                 ▼
┌─────────────────────────────────┐
│   📱 Celular / Desktop Usuario   │
└─────────────────────────────────┘
```

1. **Extracción Multi-Portal:** Monitorea portales líderes (**Computrabajo**, **Bumeran** e **Indeed Argentina**) con orden cronológico (`?by=publication_date`, `?recientes=true`, `&sort=date`).
2. **Filtro Geográfico Quirúrgico:** Limita la búsqueda exclusivamente a **CABA** (todos los barrios reconocidos), **San Martín / Villa Maipú**, **Caseros / Sáenz Peña**, **Zona Norte (Vicente López a San Isidro)** y **Remoto / Híbrido**.
3. **Ventana Temporal Estricta (< 2 Horas):** Convierte marcas relativas de tiempo a minutos y conserva solo vacantes con menos de 120 minutos de antigüedad.
4. **Filtro Semántico Local (Sin APIs Externas):** Analiza títulos y descripciones según [`config/profile.json`](config/profile.json) buscando áreas de interés (IT/Soporte/Redes, Farmacia Comercial, Administración) y descartando al instante avisos de ventas en frío, telemarketers, choferes, gastronomía, operarios, depósitos, logística o perfiles senior/universitarios avanzados.
5. **Deduplicador con Ventana Deslizante (24 Horas):** Memoria local (`data/history_24h.json`) que evita re-procesar ofertas ya vistas en el día.
6. **Doble Persistencia:** Exporta a [`data/ofertas_filtradas.csv`](data/ofertas_filtradas.csv) para respaldo y sincroniza con **Supabase (PostgreSQL)** en la nube.
7. **Centro de Comando Web Mobile-First:** Panel responsive listo para **Vercel** ([`web/`](web)) con PIN de seguridad, filtro por portal (Computrabajo, Bumeran, Indeed), vista previa detallada de requisitos y botones directos para postulación o descarte.

---

## 2. Estructura del Repositorio

```text
botilabu/
├── config/
│   ├── urls.json               # URLs configuradas por portal, zona y rol
│   └── profile.json            # Palabras clave positivas, exclusiones y perfil
├── data/                       # Salidas locales y caché (ignorado en Git)
│   ├── .gitkeep
│   ├── history_24h.json        # Caché de IDs vistos en las últimas 24 horas
│   └── ofertas_filtradas.csv   # Historial CSV de ofertas aprobadas
├── src/
│   ├── models/
│   │   ├── __init__.py
│   │   └── job.py              # Esquema tipado JobOffer
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base.py             # Clase abstracta BaseScraper
│   │   ├── computrabajo.py     # Scraper específico para Computrabajo
│   │   ├── bumeran.py          # Scraper específico para Bumeran
│   │   └── indeed.py           # Scraper específico para Indeed Argentina
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── time_filter.py      # Normalizador y filtro temporal (< 120 min)
│   │   ├── location_filter.py  # Filtro geográfico estricto (CABA, GBA Norte/Oeste)
│   │   ├── keyword_filter.py   # Filtro semántico local (inclusiones y exclusiones)
│   │   ├── deduplicator.py     # Gestor de caché deslizante de 24 horas
│   │   └── database.py         # Cliente de sincronización con Supabase Cloud
│   └── main.py                 # Orquestador del pipeline con soporte para bucle (--loop)
├── web/                        # Aplicación Web Mobile-First (Vercel)
│   ├── preview.html            # Visor local independiente (abre directo en Chrome)
│   ├── package.json            # Dependencias Next.js, React, Tailwind, Supabase
│   ├── src/
│   │   ├── app/                # App Router: layout, globals.css y page.tsx (dashboard)
│   │   └── lib/supabase.ts     # Cliente y tipos de Supabase
│   └── .env.local              # Variables públicas de conexión web
├── .env                        # Credenciales secretas (ignorado en Git)
├── .gitignore                  # Protección de venv, secrets, logs y data
├── requirements.txt            # Dependencias de Python
├── WEB_README.md               # Especificación técnica, DDL SQL y monetización web
└── README.md                   # Documentación principal
```

---

## 3. Puesta en Marcha Rápida

### Prerrequisitos
* Python 3.11+ instalado.
* Git.

### Paso 1: Activar Entorno Virtual
```powershell
.\venv\Scripts\Activate.ps1
```

### Paso 2: Instalar Dependencias y Navegador
```powershell
pip install -r requirements.txt
playwright install chromium
```

### Paso 3: Configurar Credenciales (.env)
Crea o edita tu archivo `.env` en la raíz:
```env
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_SERVICE_ROLE_KEY=tu-service-role-key-secreta
SUPABASE_ANON_KEY=tu-anon-key-publica
```

### Paso 4: Ejecutar el Scraper

* **Ejecución única:**
  ```powershell
  .\venv\Scripts\python.exe src/main.py
  ```

* **Modo continuo automático (cada 60 minutos):**
  ```powershell
  .\venv\Scripts\python.exe src/main.py --loop
  ```

### Paso 5: Abrir la Web en tu Celular o PC
* **Localmente:** Haz doble clic en [`web/preview.html`](web/preview.html) para abrir la interfaz conectada a Supabase (PIN por defecto: `1234`).
* **En Producción:** Conecta este repositorio en **Vercel** apuntando a la carpeta raíz `web`.

---

## 4. Estado de Implementación (Roadmap)

- [x] **Fase 1: Infraestructura y Modelos Base**
  - Entorno virtual, `JobOffer` dataclass tipada y configuración modular en `config/`.
- [x] **Fase 2: Scraper Computrabajo Argentina**
  - Playwright headless/visual, bypass de protecciones básicas y extracción con BeautifulSoup.
- [x] **Fase 3: Batería de Filtros Locales (Rendimiento Extremo)**
  - `time_filter.py`: Umbral de 120 minutos.
  - `location_filter.py`: Restricción estricta a CABA y zonas definidas de GBA.
  - `keyword_filter.py`: Coincidencia positiva y listas negras de exclusión rápida.
  - `deduplicator.py`: Ventana deslizante de 24 horas (`history_24h.json`).
- [x] **Fase 4: Persistencia en la Nube (Supabase)**
  - Esquema PostgreSQL con RLS y conector `database.py`.
- [x] **Fase 5: Frontend Web Mobile-First (Next.js / Vercel)**
  - Dashboard interactivo, control de acceso por PIN, vista previa de ofertas y visor `preview.html`.
- [x] **Fase 6: Modo Continuo Automático**
  - Soporte para ejecución periódica desatendida mediante flag `--loop`.
- [x] **Fase 7: Multi-Portal (Bumeran Argentina)**
  - [x] Scraper base `src/scrapers/bumeran.py` implementado y validado en vivo.
  - [x] Adaptación de marcas temporales de Bumeran en `time_filter.py`.
  - [x] Mapeo de URLs de Bumeran en `config/urls.json` (zonas y roles).
  - [x] Orquestación en `src/main.py` y sincronización en la nube con `source: "bumeran"`.
- [ ] **Fase 8: Siguientes Portales (LinkedIn / Zonajobs)**
  - Expansión modular hacia nuevos portales de empleo siguiendo el contrato `BaseScraper`.
