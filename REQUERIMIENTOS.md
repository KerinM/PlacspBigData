# Requerimientos del Proyecto - PlascspBigData

**Proyecto:** Base de datos relacional de contratación pública española (PLACSP Nacional + Catalunya + Valencia).
**Volumetría:** 37,8M registros (2000-2026), ~1,1 GB en Parquet, ~21,4 GB en PostgreSQL.
**Motor:** PostgreSQL 16+ (entorno: 18.6) + DBeaver + Python (pandas/pyarrow/psycopg2) + Power BI.

**Equipo (3):**

| Miembro | Rol | Responsabilidades |
|---|---|---|
| **Kerin** | ETL / Analista técnico | Extracción, transformación y carga (Parquet -> PostgreSQL) y optimización del pipeline |
| **Jose** | Análisis (Analista de datos) | Consultas analíticas de negocio, análisis de calidad de datos y vistas de soporte |
| **Isabella** | QA + Representación de datos en Power BI | Validación de integridad, KPIs y dashboards en Power BI |

**Reparto:** Jose → RF-01 a RF-06 y RNF-01 a RNF-04 (10) · Kerin → RF-07 a RF-13 y RNF-05 a RNF-07 (10) · Isabella → RF-14 a RF-20 y RNF-08 a RNF-10 (10).

---

## 1. Requisitos funcionales (RF-01 a RF-20)

### 1.1 Responsable: Jose (ETL / Analista técnico)

**RF-01 — Carga automatizada multicuenta.**
El sistema debe cargar los datasets de las 3 fuentes (PLACSP Nacional, Catalunya y Valencia) desde Parquet a PostgreSQL mediante el script `scripts/cargar_parquet.py`, sin intervención manual por tabla.

**RF-02 — Mapeo automático de esquema.**
El sistema debe inferir el esquema del Parquet y mapear los tipos a SQL automáticamente: `string/dictionary → text`, `int64 → bigint`, `float64 → double precision`, `bool → boolean`, `timestamp → timestamp`, `date → date`.

**RF-03 — Normalización de fechas.**
El sistema debe convertir las columnas de fecha en formato `DD/MM/YYYY` a tipo `date` con `pd.to_datetime(dayfirst=True)`, aceptando valores nulos/erróneos sin abortar la carga.

**RF-04 — Carga en streaming por lotes.**
El sistema debe insertar los datos por lotes de 250.000 filas mediante `COPY ... FROM STDIN` (formato CSV en memoria, sin generar archivos CSV intermedios en disco), haciendo `commit` por lote.

**RF-05 — Unificación multi-parquet.**
El sistema debe concatenar los múltiples archivos Parquet de una misma categoría (p. ej. `valencia/contratacion/` 12 archivos, `valencia/paro/` 283, `valencia/subvenciones/` 52) en una única tabla, salvando los esquemas con columnas namespace.

**RF-06 — Modelo relacional con claves.**
El sistema debe estructurar los datos en tablas relacionales con PK/FK a partir de `id`, `expediente`, `nif_adjudicatario` y `dir3_organo` (ORGANO_CONTRATANTE 1-N LICITACION 1-N ADJUDICACION + CPV + UBICACION NUTS).

### 1.2 Responsable: Kerin (Análisis)

**RF-07 — Consultas analíticas de negocio.**
El sistema debe permitir consultas analíticas: top adjudicatarios por `importe_sin_iva`, contratos menores por órgano, subvenciones RAISC por entidad, evolución ERE/ERTE por año y lobbies REGIA por sector (Valencia).

**RF-08 — Análisis de evolución temporal.**
El sistema debe permitir analizar la contratación por año/trimestre y calcular tasas de variación, sobre `fecha_publicacion` y por tipo de procedimiento.

**RF-09 — Análisis de concentración de mercado.**
El sistema debe permitir medir la concentración del importe adjudicado por órgano y por adjudicatario (PYME vs gran empresa) mediante rankings y porcentajes de acumulación.

**RF-10 — Análisis de fraude por fraccionamiento.**
El sistema debe permitir detectar contratos menores fraccionados: agrupaciones del mismo `nif_adjudicatario` + `organo_contratante` con importes cercanos, para flag de auditoría.

**RF-11 — Análisis por sector/CPV.**
El sistema debe permitir desglosar volúmenes e importes por código `cpv_principal` y agrupaciones de sector para comparar categorías de gasto.

**RF-12 — Análisis geográfico por CCAA/NUTS.**
El sistema debe permitir agregar importes y nº de contratos por `ubicacion`/`nuts` para comparativas territoriales entre fuentes.

**RF-13 — Vistas de consulta recurrente.**
El sistema debe exponer vistas (o materialized views) normalizadas y reutilizables por Power BI para los análisis RF-07 a RF-12 (por año, por CCAA, por CPV, por PYME).

### 1.3 Responsable: Isabella (QA + Power BI)

**RF-14 — Verificación de integridad de carga.**
El sistema debe comparar el conteo de filas cargado (`n_live_tup`) contra el esperado por fuente y reportar fugas de carga, duplicados y proporción de NULL en columnas críticas (`importe_sin_iva`, `fecha_publicacion`, `nif_adjudicatario`).

**RF-15 — Panel de KPIs globales.**
Power BI debe mostrar KPIs: total de registros (26,7M cargados / 37,8M objetivo), importe total adjudicado, número de adjudicatarios y de órganos de contratación.

**RF-16 — Dashboard de evolución temporal.**
Power BI debe visualizar la evolución de contratación por año y trimestre desglosada por tipo de contrato y procedimiento, con comparativa entre fuentes (Nacional / Catalunya / Valencia).

**RF-17 — Mapa geográfico.**
Power BI debe representar en mapa el importe adjudicado por CCAA/NUTS e identificar PYME vs gran empresa.

**RF-18 — Reporte comparativo entre fuentes.**
El sistema debe generar un reporte que compare volumetría, periodos e importes de las tres fuentes para detectar solapamientos o incoherencias.

**RF-19 — Panel de fraude para auditoría.**
Power BI debe listar los NIF reincidentes por órgano y rango de importe detectados en RF-10, con drill-down al detalle de cada contrato.

**RF-20 — Filtros interactivos.**
El dashboard debe permitir filtrar por año, CCAA, tipo de contrato, tamaño de empresa y sector/CPV, manteniendo la coherencia entre todas las páginas del informe.

---

## 2. Requisitos no funcionales (RNF-01 a RNF-10)

### 2.1 Responsable: Jose (ETL / Analista técnico)

**RNF-01 — Rendimiento de la carga.**
La carga completa de 37,8M de registros debe completarse en menos de 60 minutos en un equipo de 8 GB de RAM, priorizando el streaming sin ficheros intermedios.

**RNF-02 — Latencia de consultas.**
Las consultas analíticas sobre las tablas indexadas (~26,7M filas) deben devolver resultados en menos de 5 segundos.

**RNF-03 — Consumo eficiente de recursos.**
El sistema debe funcionar con 8-16 GB RAM y ~60 GB de disco, sin degradar el resto de aplicaciones del equipo.

**RNF-04 — Escalabilidad del pipeline.**
El sistema debe soportar un crecimiento de +2,5M de filas/año (~+1,1 GB/año) sin rediseño del proceso de carga, añadiendo nuevas fuentes o particiones anuales sin cambios de código.

### 2.2 Responsable: Kerin (Análisis)

**RNF-05 — Integridad de la información.**
Toda la carga debe realizarse en codificación UTF-8 (acentos y ñ) con locales españoles (`es_ES.UTF-8` o `Spanish_Spain.1252`), sin pérdida de caracteres, y ser verificable desde el análisis.

**RNF-06 — Seguridad de credenciales.**
El script no debe contener contraseñas en el código; las credenciales se leen de variables de entorno (`PGPASSWORD`) y no se versionan en el repositorio.

**RNF-07 — Portabilidad.**
El entorno debe poder instalarse en Windows, Linux y macOS con PostgreSQL 16 o superior, tras seguir la guía `docs/instalacion-postgresql-dbeaver.md`, y reproducir los mismos resultados de análisis.

### 2.3 Responsable: Isabella (QA + Power BI)

**RNF-08 — Fiabilidad y verificación.**
El sistema debe incluir un procedimiento de verificación automatizado (tamaño por tabla, conteo `ANALYZE`, reporte de integridad) ejecutable tras cada carga.

**RNF-09 — Usabilidad y reproducibilidad.**
La documentación (README + docs) debe permitir reproducir el entorno completo paso a paso por un tercero sin conocimiento previo del proyecto, e interpretar el informe de Power BI.

**RNF-10 — Mantenibilidad.**
El código debe ser modular, con argumentos claros (archivo, tabla, columnas de fecha, columnas de índice), permitiendo actualizar mensualmente los datos y refrescar el dashboard de Power BI sin cambios de código.

---

## 3. Roles, actividades y definición de "hecho"

| Miembro | Rol | Actividades principales | Entregable | Criterio de aceptación |
|---|---|---|---|---|
| **Jose** | ETL / Analista técnico | Implementar y ejecutar la carga multi-fuente (RF-01 a RF-05), definir el modelo relacional (RF-06), tuning del pipeline (RNF-01 a RNF-04) | Scripts funcionales + tablas cargadas en PostgreSQL + catálogo de carga | 26,7M filas cargadas (bloque actual) en <60 min; proceso reproducible sin CSV intermedios |
| **Kerin** | Análisis | Preparar consultas y vistas analíticas de negocio (RF-07 a RF-13), asegurar calidad/integridad de datos (RNF-05 a RNF-07) | Documento de análisis + vistas/materialized views + consultas reutilizables | Consultas <5 s sobre datos indexados; vistas consumibles por Power BI; sin pérdida de caracteres UTF-8 |
| **Isabella** | QA + Power BI | Validar integridad de carga (RF-14, RNF-08), diseñar KPIs y dashboards (RF-15 a RF-20), documentar reproducibilidad (RNF-09, RNF-10) | Informe Power BI (4-6 páginas) + reporte de validación + documentación final | Todos los KPIs coinciden con la volumetría real; sin duplicados/NULL no reportados; informe revisado por el equipo |

**Definición de "hecho" común:** cada requisito se marca como completado cuando su entregable existe, se verifica con datos reales y es revisado por los otros dos miembros (Pull Request / revisión cruzada comentada en el repositorio).