# Instalación de PostgreSQL + DBeaver

Guía técnica para montar el entorno de base de datos del proyecto **PlascspBigData** (37,8M registros de contratación pública de España, 2000-2026).

> Este entorno utiliza **PostgreSQL 18.6** (las versiones 16 y superiores son compatibles).

## 1. Requisitos mínimos

| Recurso | Mínimo | Recomendado |
|---|---|---|
| RAM | 8 GB | 16 GB |
| Disco libre | 30 GB | 60 GB |
| SO | Windows 10/11, Linux, macOS | - |
| Motor | PostgreSQL 16.x o superior | - |
| Cliente | DBeaver Community (gratuito) | - |
| Python | 3.10 o superior (`pandas`, `pyarrow`, `psycopg2-binary`) | - |

Espacio necesario estimado en el SGBD: **~17,4 GB** (ver [volumetria.md](volumetria.md)), más espacio temporal para la carga inicial.

## 2. Instalación de PostgreSQL

### 2.1 Descarga

1. Ir a la web oficial: <https://www.postgresql.org/download/>
2. Seleccionar el sistema operativo.
3. Descargar la última versión estable (16.x, 17 o 18, siendo 18 la usada en este entorno).

### 2.2 Windows

1. Ejecutar el instalador (`postgresql-18.x-windows-x64.exe` en este entorno).
2. Rellenar el asistente:

| Paso | Valor |
|---|---|
| Installation Directory | `C:\Program Files\PostgreSQL\18` (por defecto) |
| Data Directory | `C:\Program Files\PostgreSQL\18\data` |
| Password (`postgres`) | Definir una segura y guardarla en un gestor de contraseñas |
| Port | `5432` (por defecto) |
| Locale | `Spanish, Spain` (o el que corresponda) |

3. Finalizar y comprobar que el servicio `postgresql-x64-18` queda **en ejecución** (`services.msc` o `net start`).

### 2.3 Linux (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install postgresql postgresql-client
sudo service postgresql start
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'tu_password';"
```

### 2.4 Verificación de la instalación

```bash
psql --version
psql -U postgres -h localhost
```

> En Windows, `psql` está en `C:\Program Files\PostgreSQL\<version>\bin`.
> Si falla la autenticación, revisar `pg_hba.conf` (debe usar `scram-sha-256` para conexiones locales).

## 3. Instalación de DBeaver

### 3.1 Descarga e instalación

1. Ir a <https://dbeaver.io/download/>.
2. Descargar **DBeaver Community** (gratuito).
   - **Windows**: ejecutar el instalador `.exe` y seguir el asistente.
   - **Linux**: `.deb`/`.rpm` o `snap install dbeaver-ce`.

### 3.2 Nueva conexión a PostgreSQL

1. Abrir DBeaver.
2. **Base de datos > Nueva conexión** (o `Ctrl+Shift+N`).
3. Seleccionar **PostgreSQL**.

| Campo | Valor |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Database | `postgres` (luego se crea la BD del proyecto) |
| Username | `postgres` |
| Password | el definido en la instalación |

4. **Probar conexión** → al aceptar, DBeaver descarga el driver JDBC automáticamente si falta.
5. **Aceptar** para guardar la conexión.

## 4. Creación de la base de datos del proyecto

Desde DBeaver o `psql`:

```sql
CREATE DATABASE placsp_contratacion
  ENCODING 'UTF8'
  LC_COLLATE 'es_ES.UTF-8'
  LC_CTYPE 'es_ES.UTF-8'
  TEMPLATE template0;
```

> En Windows, si el locale `es_ES.UTF-8` no está disponible, usar `C` o `Spanish_Spain.1252`. Lo importante es **UTF8** para acentos y la `ñ`.

## 5. Carga de datos (Parquet -> PostgreSQL con `cargar_parquet.py`)

> Como este entorno tiene **PostgreSQL 18**, `COPY FROM STDIN` se ejecuta con `psycopg2` en streaming (sin generar CSV intermedio en disco). El script `scripts/cargar_parquet.py` crea la tabla a partir del esquema del Parquet, carga por lotes de 250.000 filas y crea los índices.

### 5.1 Pre-requisitos

```bash
cd PlascspBigData
python -m venv .venv
.venv\Scripts\activate        # Windows (Linux/macOS: source .venv/bin/activate)
pip install pandas pyarrow psycopg2-binary
```

### 5.2 Obtener el dataset limpio

```bash
git clone --depth 1 https://github.com/uniparra/licitaciones-espana.git
```

### 5.3 Cargar una tabla

```bash
set PGPASSWORD=tu_password

# Uso:
#   python scripts/cargar_parquet.py <archivo.parquet> <nombre_tabla> [columnas_fecha] [columnas_indice]
#
# PLACSP Nacional (8,7M filas, 48 columnas, 3 índices)
python scripts/cargar_parquet.py "ruta\licitaciones-espana\nacional\licitaciones_espana.parquet" licitaciones "fecha_limite,fecha_adjudicacion,fecha_publicacion,fecha_planificada,fecha_limite_respuestas" "organo_contratante,nif_adjudicatario,fecha_publicacion"

# Catalunya Subvenciones RAISC (9,6M filas, 42 columnas)
python scripts/cargar_parquet.py "ruta\licitaciones-espana\catalunya\subvenciones\raisc_concesiones.parquet" subvenciones_raisc "Data concessió"
```

El script:
1. Lee el esquema del Parquet y genera el `CREATE TABLE` (tipos mapeados: `string→text`, `int64→bigint`, `float64→double precision`, `bool→boolean`, `timestamp→timestamp`, `dictionary/category→text`).
2. Inserta en lotes de 250.000 filas con `COPY ... FROM STDIN WITH (FORMAT csv, NULL '', QUOTE '"')` y hace `commit` por lote.
3. Las columnas indicadas como `columnas_fecha` se convierten con `pd.to_datetime(dayfirst=True)` para las fechas `DD/MM/YYYY`.
4. Crea los índices indicados en `columnas_indice` después de la carga (nunca antes, para no ralentizar el `COPY`).

### 5.4 Tabla cargada en este entorno

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

### 5.5 Carga manual alternativa (psql)

Si se prefiere el flujo clásico **Parquet → CSV → COPY**:

```python
import pandas as pd
df = pd.read_parquet('nacional/licitaciones_espana.parquet')
df.to_csv('licitaciones.csv', index=False)
```

```sql
COPY licitaciones(id, expediente, objeto, organo_contratante, importe_sin_iva, fecha_publicacion)
FROM 'C:/data/licitaciones.csv' DELIMITER ',' CSV HEADER;
```

### 5.6 Índices (equivalente manual)

```sql
CREATE INDEX idx_organo        ON licitaciones(organo_contratante);
CREATE INDEX idx_adjudicatario ON licitaciones(nif_adjudicatario);
CREATE INDEX idx_fecha         ON licitaciones(fecha_publicacion);
```

### 5.7 Verificación de la carga

```sql
-- Tamaño real por tabla
SELECT relname AS tabla, pg_size_pretty(pg_total_relation_size(relid)) AS tamanio
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

-- Actualizar estadísticas y comprobar filas
ANALYZE;
SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;
```

> Si `n_live_tup` no refleja bien el total hasta ejecutar `ANALYZE`.

## 6. Configuración recomendada para 37,8M de filas

Ajustar `postgresql.conf`:

```conf
shared_buffers = 2GB          # ~25% de la RAM (8GB)
work_mem = 64MB               # por operación de orden/agregación
maintenance_work_mem = 512MB  # para CREATE INDEX / VACUUM
effective_cache_size = 6GB
max_connections = 100
```

Recomendado también **particionar por año** sobre `fecha_publicacion` (RANGE por año) y ejecutar `VACUUM (ANALYZE)` mensual (detalle en [volumetria.md](volumetria.md)).

En este entorno el servicio se llama `postgresql-x64-18`. Reiniciar tras los cambios de configuración:

```bash
# Windows
net stop postgresql-x64-18
net start postgresql-x64-18

# Linux
sudo systemctl restart postgresql
```

## 7. Solución de problemas rápidos

| Problema | Solución |
|---|---|
| No se conecta desde DBeaver | Reiniciar el servicio PostgreSQL y comprobar firewall/puerto 5432 |
| `password authentication failed` | Revisar `pg_hba.conf` / `ALTER USER postgres PASSWORD ...` |
| `COPY` es lento | Eliminar índices antes de cargar y recrearlos después; cargar por lotes |
| Caracteres corruptos en los datos | BD y CSV en UTF-8 |

## 8. Enlaces de interés

- PostgreSQL: <https://www.postgresql.org/docs/current/>
- DBeaver: <https://dbeaver.io/docs/>
- [Volumetría y carga de datos](volumetria.md)
- PLACSP: <https://contrataciondelsectorpublico.gob.es/>, Catalunya: <https://analisi.transparenciacatalunya.cat>, Valencia: <https://dadesobertes.gva.es>