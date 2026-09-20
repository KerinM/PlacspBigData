# Volumetría de datos - CONTRATACIÓN ESPAÑA (PLACSP + Catalunya + Valencia)

Base de datos relacional abierta de contratación pública española. Unifica 3 fuentes oficiales en formato Parquet relacional (tablas con PK/FK por `id`, `expediente`, `nif_adjudicatario`, `dir3_organo`).

**Total: 37,8M registros (2000-2026) ~1,1 GB en Parquet**

## 1. Distribución por fuente y periodo

| Bloque | Registros | Periodo | Tamaño |
|---|---|---|---|
| Nacional PLACSP | 8,7M | 2012-2026 | 780 MB |
| ↳ Licitaciones | 3,6M | 2012-act | - |
| ↳ Agregación CCAA | 1,7M | 2016-act | - |
| ↳ Contratos menores | 3,3M | 2018-act | - |
| Catalunya Contratación | 4,3M | 2014-2025 | ~60 MB |
| ↳ Regulares | 1,3M | 2014-2025 | - |
| ↳ Menores | 3,0M | 2014-2025 | - |
| Catalunya Subvenciones RAISC | 9,6M | 2014-2025 | ~120 MB |
| Valencia (14 categorías) | 8,5M | 2000-2026 | 156 MB |
| **TOTAL** | **37,8M** | **2000-2026** | **~1,1 GB** |

## 2. Esquema relacional sugerido

```
ORGANO_CONTRATANTE (dir3, nombre, ciudad)
  │ 1-N
LICITACION (id, expediente, objeto, tipo, procedimiento, importe_sin_iva, fecha_pub)
  │ 1-N
ADJUDICACION (nif_adjudicatario, adjudicatario, importe_adj, num_ofertas, es_pyme)
+ CPV
+ UBICACION (nuts)
```

### 2.1 Columnas principales (48 en total)

`id, expediente, objeto, organo_contratante, nif_organo, tipo_contrato, procedimiento, estado, importe_sin_iva, importe_con_iva, importe_adjudicacion, adjudicatario, nif_adjudicatario, num_ofertas, cpv_principal, fecha_publicacion, fecha_adjudicacion`

## 3. Estimación de volumetría en PostgreSQL

Fórmula: `Volumen = Nº Filas x Longitud media + 40% índices`

| Tabla | Filas | Long. media | Datos | Índices 40% | Total |
|---|---|---|---|---|---|
| LICITACIONES_PLACSP | 8.700.000 | 650 bytes | 5,65 GB | 2,26 GB | **7,91 GB** |
| CONTRACTACIO_CAT | 4.300.000 | 400 bytes | 1,72 GB | 0,69 GB | **2,41 GB** |
| SUBVENCIONES_RAISC | 9.600.000 | 250 bytes | 2,40 GB | 0,96 GB | **3,36 GB** |
| VALENCIA_ALL | 8.500.000 | 300 bytes | 2,55 GB | 1,02 GB | **3,57 GB** |
| DIM_ORGANO + DIM_EMPRESA | ~500.000 | 200 bytes | 0,10 GB | 0,04 GB | **0,14 GB** |
| **TOTAL AÑO 2026** | **37,8M** | - | **12,42 GB** | **4,97 GB** | **~17,4 GB en SGBD** |
| **Crecimiento** | +2,5M/año | - | +1,1 GB/año | - | **~23 GB a 5 años** |

### 3.1 Interpretación

- En **Parquet** los datos ocupan solo **1,1 GB** (comprimido por columnas).
- En **PostgreSQL** ocupan **~17,4 GB** por el factor de llenado, cabeceras de filas, `TOAST` y, sobre todo, los **índices**.
- Con índices adicionales o replicas el tamaño puede crecer hasta **~23 GB a 5 años**.

## 4. Índices y particionado

### 4.1 Índices recomendados

```sql
CREATE INDEX idx_organo       ON licitaciones(organo_contratante);
CREATE INDEX idx_adjudicatario ON licitaciones(nif_adjudicatario);
CREATE INDEX idx_fecha        ON licitaciones(fecha_publicacion);
```

Los dos primeros aceleran los análisis de fraude (agrupación por NIF u órgano) y el de fecha es clave para consultas temporales.

### 4.2 Particionado

Se recomienda **particionar por `fecha_publicacion`** (RANGE por año):

```sql
CREATE TABLE licitaciones (
    id bigint,
    expediente text,
    objeto text,
    organo_contratante text,
    importe_sin_iva numeric,
    fecha_publicacion date
) PARTITION BY RANGE (fecha_publicacion);

CREATE TABLE licitaciones_2012 PARTITION OF licitaciones FOR VALUES FROM ('2012-01-01') TO ('2013-01-01');
CREATE TABLE licitaciones_2013 PARTITION OF licitaciones FOR VALUES FROM ('2013-01-01') TO ('2014-01-01');
-- ... sucesivamente hasta 2026
CREATE TABLE licitaciones_2026 PARTITION OF licitaciones FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
```

Ventajas: consultas por año solo tocan la partición correspondiente, `DELETE`/purga por año inmediata y mantenimiento de índices por partición.

## 5. Mantenimiento

- **VACUUM mensual** para recuperar espacio y refrescar estadísticas del planner:

```sql
VACUUM (ANALYZE, VERBOSE) licitaciones;
```

- **ANALYZE** tras cada carga masiva.
- Monitorizar tamaño real por tabla:

```sql
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

## 6. Origen de los datos

### 6.1 Dataset ya limpio (recomendado)

```bash
git clone https://github.com/uniparra/licitaciones-espana.git
cd licitaciones-espana
pip install pandas pyarrow requests
```

Archivos:

```text
nacional/licitaciones_espana.parquet (641 MB - última versión)
nacional/licitaciones_completo_2012_2026.parquet (780 MB - histórico)
catalunya/contratacion/contractacio_publica.parquet (1,3M)
catalunya/contratacion/contractacio_menors.parquet (3,0M)
catalunya/subvenciones/raisc_subvenciones.parquet (9,6M)
valencia/contratacion/ (13 archivos, 42 MB)
```

### 6.2 Fuentes oficiales

- PLACSP Nacional: <https://contrataciondelsectorpublico.gob.es/> > Datos Abiertos > ATOM/XML mensual + herramienta OpenPLACSP a Excel
- Catalunya: <https://analisi.transparenciacatalunya.cat> (API Socrata)
- Valencia: <https://dadesobertes.gva.es> (API CKAN)
- Licencia: [Reutilización Gobierno España](https://datos.gob.es/es/aviso-legal)

## 7. Carga de datos (Parquet a Postgres)

```python
import pandas as pd
df = pd.read_parquet('nacional/licitaciones_espana.parquet')
print(df.shape)  # (8700000, 48)

# Top adjudicatarios
df.groupby('adjudicatario')['importe_sin_iva'].sum().nlargest(10)
```

A Postgres (COPY desde CSV):

```sql
COPY licitaciones(id, expediente, objeto, organo_contratante, importe_sin_iva, fecha_publicacion)
FROM '/data/licitaciones.csv' DELIMITER ',' CSV HEADER;
```

## 8. Comparativa de motores

| Motor | Cuándo | Por qué |
|---|---|---|
| **PostgreSQL 16 + DBeaver (RECOMENDADO proyecto univ.)** | 10-40M filas, relacional puro | Gratis, soporta 37,8M sin problema, FK, índices, particionado por año, PostGIS para NUTS |
| DuckDB | Análisis rápido en laptop sin servidor | Lee Parquet directo `SELECT * FROM 'lic.parquet'`, 10x más rápido que Pandas |
| ClickHouse / Spark + Parquet | Proyecto Big Data real | Spark 3.5 + 1,1GB Parquet + Zeppelin |
| MySQL 8 | Alternativa si el profesor lo exige | Funciona, pero peor para particionado y JSON/CPV |

> Recomendación: **PostgreSQL para volumetría + DuckDB/Python para análisis**. 8GB RAM basta.

## 9. Ideas de análisis Big Data

1. **Fraude**: contratos menores fraccionados mismo NIF + mismo órgano.
2. **Mapa**: importe por CCAA/NUTS + PYME vs grande.
3. **ML**: predecir `importe_adjudicacion` vs `importe_licitacion` (baja temeraria).