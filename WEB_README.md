# Job Hunter Web - Documento de Arquitectura y Especificación de Producto

Este documento define la arquitectura técnica, el modelo de datos, la experiencia de usuario y el roadmap de monetización para la plataforma web **Mobile-First** del ecosistema **Job Hunter Bot**, diseñada para ser desplegada en **Vercel** y escalar hacia un modelo SaaS (Software as a Service).

---

## 1. Visión General del Producto

La aplicación web es un **Centro de Comando Personal de Empleo** accesible desde cualquier dispositivo móvil o de escritorio. Su función es centralizar las ofertas laborales pre-filtradas en tiempo real de múltiples portales, permitiendo revisar descripciones completas sin publicidad invasiva de terceros y postularse con un solo toque.

```
┌─────────────────────────────────┐
│     Scrapers / Workers          │
│  (Computrabajo, LinkedIn, etc.) │
└────────────────┬────────────────┘
                 │ (Inserta ofertas aprobadas)
                 ▼
┌─────────────────────────────────┐
│     Base de Datos Cloud         │
│     Supabase (PostgreSQL)       │
└────────────────┬────────────────┘
                 │ (API REST / Server Actions en tiempo real)
                 ▼
┌─────────────────────────────────┐
│     Web App en Vercel           │
│     (Next.js + TailwindCSS)     │
└────────────────┬────────────────┘
                 │ (Acceso móvil PWA)
                 ▼
┌─────────────────────────────────┐
│   📱 Celular / Desktop Usuario   │
└─────────────────────────────────┘
```

---

## 2. Stack Tecnológico

* **Frontend & Serverless Backend:** Next.js (App Router) + React.
* **Estilos & Diseño:** TailwindCSS (enfoque 100% *Mobile-First*, optimizado para pantallas táctiles).
* **Base de Datos & Tiempo Real:** Supabase (PostgreSQL administrado con capa gratuita permanente).
* **Hosting & CI/CD:** Vercel (despliegue continuo conectado al repositorio Git).
* **Worker de Extracción:** Python 3.11+ con Playwright (en PC local o automatizado en GitHub Actions).

---

## 3. Modelo de Base de Datos (PostgreSQL / Supabase)

El esquema está estructurado para soportar múltiples fuentes de empleo y evolucionar hacia multi-usuario.

### Tabla: `jobs` (Ofertas Laborales)

```sql
-- Extensión para generar identificadores UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tipo de estado de la oferta
CREATE TYPE job_status AS ENUM ('new', 'applied', 'discarded');

CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source VARCHAR(50) NOT NULL,              -- 'computrabajo', 'linkedin', 'bumeran'
    external_id VARCHAR(150) NOT NULL,        -- ID original del portal (evita duplicados)
    title VARCHAR(255) NOT NULL,
    company VARCHAR(255) NOT NULL,
    location VARCHAR(255) NOT NULL,
    published_time_text VARCHAR(100),         -- 'Hace 30 minutos'
    url TEXT NOT NULL,
    full_description TEXT,                    -- Texto íntegro de la postulación para vista previa
    category VARCHAR(100),                    -- 'IT', 'Farmacia', 'Administrativo'
    status job_status DEFAULT 'new',
    status_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Restricción para garantizar que una oferta no se repita por portal
    CONSTRAINT unique_source_job UNIQUE (source, external_id)
);

-- Índices para velocidad de consulta en móvil
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_source ON jobs(source);
CREATE INDEX idx_jobs_created_at ON jobs(created_at DESC);
```

### Política de Limpieza Automática (Ventana de 24 Horas)
Para mantener la pantalla limpia y no saturar la base de datos, las ofertas descartadas o ya postuladas que superen las 24 horas se purgan automáticamente:

```sql
-- Función de purga de historial antiguo
CREATE OR REPLACE FUNCTION purge_old_history() 
RETURNS void AS $$
BEGIN
    DELETE FROM jobs
    WHERE status IN ('applied', 'discarded')
      AND status_updated_at < NOW() - INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql;
```

---

## 4. Especificaciones de UI/UX (Experiencia Móvil)

### Pantalla Principal (Feed de Ofertas)
* **Barra Superior:**
  * Selector por Fuente: `[ Todas ]` `[ Computrabajo ]` `[ LinkedIn ]` `[ Bumeran ]`.
  * Contador de ofertas frescas pendientes de revisión.
* **Tarjetas de Empleo (Job Cards):**
  * Título del aviso destacado (negrita, legible).
  * Badge de la empresa y etiqueta de ubicación (ej. *CABA - Retiro* o *San Martín*).
  * Tiempo relativo con ícono (*"Hace 45 min"*).
  * **Botón "Vista Previa":** Abre una hoja inferior deslizable (*Drawer/Modal*) con la descripción y requisitos completos.
  * **Acciones Rápidas:**
    * Botón verde destacado: `[ 🔗 Ir a Postularme ]` (abre el portal oficial en pestaña nueva y marca como *Postulado*).
    * Botón secundario: `[ ❌ Descartar ]`.

### Pestañas de Navegación Móvil
1. **🔥 Nuevas:** Ofertas pendientes de decisión (tiempo < 2 horas).
2. **✅ Postuladas:** Historial temporal (24h) de vacantes a las que te postulaste para control propio.
3. **🗑️ Descartadas:** Ofertas ignoradas (por si descartaste alguna por error).

---

## 5. Control de Acceso y Seguridad

### Fase 1: PIN de Acceso Privado (MVP)
* Protección inicial mediante un PIN simple de 4 a 6 dígitos en una pantalla de bienvenida.
* El PIN se valida contra una variable de entorno (`APP_ACCESS_PIN`) en Vercel.
* Al ingresar correctamente, se guarda una sesión segura en una cookie `httpOnly` para no tener que tipear el PIN constantemente desde el celular.

### Fase 2: Autenticación Multi-usuario (Escalabilidad SaaS)
* Integración nativa de **Supabase Auth** con proveedor de **Google OAuth** (inicio de sesión con 1 toque usando cuenta de Google).
* Cada usuario tendrá su propio perfil, palabras clave y su propio feed de postulaciones.

---

## 6. Modelo de Negocio y Monetización (Estrategia Freemium)

Para monetizar la herramienta en el futuro ofreciéndola a otros postulantes:

### Nivel Gratuito (Plan Free con Anuncios)
* Acceso completo al feed con límite estándar de actualizaciones (cada 1 o 2 horas).
* **Publicidad Discreta y No Invasiva:**
  * Integración con **Google AdSense** o **Carbon Ads** (banners nativos intercalados cada 5 ofertas laborales).
  * Modelo de ingresos por impresiones (CPM) y clics (CPC).
* Acceso a portales básicos (Computrabajo).

### Nivel Premium (Suscripción Paga - Pro)
* **100% libre de anuncios.**
* **Alertas Inmediatas:** Notificaciones push en tiempo real en el celular (vía Web Push o Telegram) en el minuto exacto de publicación de una oferta.
* **Filtros Personalizados Ilimitados:** Posibilidad de subir su propio CV en PDF para que la herramienta autoconfigure sus palabras clave.
* **Multi-Portal Completo:** Acceso a ofertas exclusivas de LinkedIn, Bumeran y Zonajobs.
* Pasarela de cobro: Integración con **Mercado Pago** (Argentina) o **Stripe** (Internacional).

---

## 7. Variables de Entorno Requeridas en Vercel

```env
# Conexión a la Base de Datos Cloud (Supabase)
NEXT_PUBLIC_SUPABASE_URL=https://tu-proyecto.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=tu-anon-key-publica
SUPABASE_SERVICE_ROLE_KEY=tu-service-role-key-privada

# Seguridad MVP
APP_ACCESS_PIN=1234
```
