# PlascspBigData

Base de datos relacional de contratación pública española (PLACSP Nacional + Catalunya + Valencia). **37,8M registros (2000-2026) ~1,1 GB en Parquet**.

## Índice de la documentación

| Documento | Contenido |
|---|---|
| [docs/instalacion-postgresql-dbeaver.md](docs/instalacion-postgresql-dbeaver.md) | Instalación de PostgreSQL + DBeaver, conexión, creación de BD |
| [docs/volumetria.md](docs/volumetria.md) | Distribución por fuente, estimación de volumen, índices, particionado, mantenimiento |
| [volumetria_placsp.md](volumetria_placsp.md) | Resumen técnico original del proyecto |
| [scripts/cargar_parquet.py](scripts/cargar_parquet.py) | Script de carga Parquet → PostgreSQL (streaming `COPY`) |

## Cómo montar el entorno completo (paso a paso)

### 1. Requisitos

| Recurso | Mínimo | Recomendado |
|---|---|---|
| RAM | 8 GB | 16 GB |
| Disco libre | 30 GB | 60 GB |
| SO | Windows 10/11, Linux, macOS | - |
| PostgreSQL | 16.x o superior (aquí: 18.6) | - |
| DBeaver | Community (gratuito) | - |
| Python | 3.10+ con `pandas`, `pyarrow`, `psycopg2-binary` | - |

### 2. Instalación de PostgreSQL + DBeaver

Detalle completo en [docs/instalacion-postgresql-dbeaver.md](docs/instalacion-postgresql-dbeaver.md).

Resumen:

1. **PostgreSQL**: descargar de <https://www.postgresql.org/download/> e instalar (puerto `5432`, definir la contraseña del usuario `postgres`). Verificar el servicio en ejecución y `psql --version`.
2. **DBeaver**: descargar de <https://dbeaver.io/download/> → **Nueva conexión** → **PostgreSQL** → `localhost:5432`, usuario `postgres`.
3. **Crear la BD del proyecto** (psql o DBeaver):

```sql
CREATE DATABASE placsp_contratacion
  ENCODING 'UTF8'
  TEMPLATE template0;  -- en Windows con locale es_ES.UTF-8 disponible, añadir LC_COLLATE/LC_CTYPE
```

### 3. Descargar el dataset limpio

```bash
git clone --depth 1 https://github.com/uniparra/licitaciones-espana.git
```

### 4. Cargar los datos en PostgreSQL

Pre-requisitos de Python:

```bash
pip install pandas pyarrow psycopg2-binary
```

Cargar cada dataset:

```bash
set PGPASSWORD=tu_password

# PLACSP Nacional (8,7M filas)
python scripts/cargar_parquet.py "licitaciones-espana\nacional\licitaciones_espana.parquet" licitaciones "fecha_limite,fecha_adjudicacion,fecha_publicacion,fecha_planificada,fecha_limite_respuestas" "organo_contratante,nif_adjudicatario,fecha_publicacion"

# Catalunya Subvenciones RAISC (9,6M filas)
python scripts/cargar_parquet.py "licitaciones-espana\catalunya\subvenciones\raisc_concesiones.parquet" subvenciones_raisc "Data concessió"
```

> El script crea la tabla a partir del esquema del Parquet, carga por lotes de 250.000 filas con `COPY FROM STDIN` y crea los índices al final. Para el resto de archivos ver la sección completa en [docs/instalacion-postgresql-dbeaver.md](docs/instalacion-postgresql-dbeaver.md).

### 5. Estado actual de la carga (este entorno)

| Tabla | Origen | Filas |
|---|---|---|
| licitaciones | `nacional/licitaciones_espana.parquet` | 8.693.891 |
| subvenciones_raisc | `catalunya/subvenciones/raisc_concesiones.parquet` | 9.630.023 |
| contratos_registro | `catalunya/contratacion/contratos_registro.parquet` | 3.453.519 |
| contractacio_menors | `catalunya/contratacion/contractacio_menors.parquet` | 3.023.802 |
| publicaciones_pscp | `catalunya/contratacion/publicaciones_pscp.parquet` | 1.607.361 |
| valencia_contratacion | `valencia/contratacion/` (12 archivos concatenados) | 245.545 |
| adjudicaciones_generalitat | `catalunya/contratacion/adjudicaciones_generalitat.parquet` | 73.895 |
| **TOTAL** | | **~26,7M** |

Tamaño en el SGBD: **~21,4 GB** | Índices en `licitaciones`: `organo_contratante`, `nif_adjudicatario`, `fecha_publicacion`.

### 6. Verificación

```sql
SELECT relname AS tabla, pg_size_pretty(pg_total_relation_size(relid)) AS tamanio
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

ANALYZE;
SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;
```

### 7. Configuración recomendada para ~37,8M de filas

En `postgresql.conf`:

```conf
shared_buffers = 2GB
work_mem = 64MB
maintenance_work_mem = 512MB
effective_cache_size = 6GB
max_connections = 100
```

Recomendado: **particionar por año** sobre `fecha_publicacion` y **VACUUM (ANALYZE)** mensual (ver [docs/volumetria.md](docs/volumetria.md)).

## Licencia y fuentes

- Datos: [PLACSP](https://contrataciondelsectorpublico.gob.es/), [Catalunya](https://analisi.transparenciacatalunya.cat), [Valencia](https://dadesobertes.gva.es) bajo [Reutilización de la información del sector público](https://datos.gob.es/es/aviso-legal).