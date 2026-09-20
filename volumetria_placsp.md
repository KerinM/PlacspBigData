# BASE DE DATOS RELACIONAL 37,8M REGISTROS - Contratación España (PLACSP + Catalunya + Valencia)

## 1. INICIO / DESCRIPCIÓN

Base de datos relacional abierta de contratación pública española. Unifica 3 fuentes oficiales en formato Parquet relacional (tablas con PK/FK por `id`, `expediente`, `nif_adjudicatario`, `dir3_organo`).

**Total: 37,8M registros (2000-2026) ~1,1 GB en Parquet**

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

Esquema relacional sugerido:

`ORGANO_CONTRATANTE (dir3, nombre, ciudad) 1-N LICITACION (id, expediente, objeto, tipo, procedimiento, importe_sin_iva, fecha_pub) 1-N ADJUDICACION (nif_adjudicatario, adjudicatario, importe_adj, num_ofertas, es_pyme) + CPV + UBICACION (nuts)`

48 columnas principales: `id, expediente, objeto, organo_contratante, nif_organo, tipo_contrato, procedimiento, estado, importe_sin_iva, importe_con_iva, importe_adjudicacion, adjudicatario, nif_adjudicatario, num_ofertas, cpv_principal, fecha_publicacion, fecha_adjudicacion`.

## 2. DÓNDE DESCARGAR

### Opción A - Dataset ya limpio (recomendado)

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

### Opción B - Fuentes oficiales

* PLACSP Nacional: https://contrataciondelsectorpublico.gob.es/ > Datos Abiertos > ATOM/XML mensual + herramienta OpenPLACSP a Excel
* Catalunya: https://analisi.transparenciacatalunya.cat (API Socrata)
* Valencia: https://dadesobertes.gva.es (API CKAN)
* Licencia: Reutilización Gobierno España https://datos.gob.es/es/aviso-legal

## 3. CÓMO CARGAR

```python
import pandas as pd
df = pd.read_parquet('nacional/licitaciones_espana.parquet')
print(df.shape) # (8700000, 48)

# Top adjudicatarios
df.groupby('adjudicatario')['importe_sin_iva'].sum().nlargest(10)
```

A Postgres:

```sql
-- usar COPY desde CSV o pgAdmin > Import + script *_parquet.py del repo
COPY licitaciones(id, expediente, objeto, organo_contratante, importe_sin_iva, fecha_publicacion)
FROM '/data/licitaciones.csv' DELIMITER ',' CSV HEADER;
CREATE INDEX idx_organo ON licitaciones(organo_contratante);
CREATE INDEX idx_adjudicatario ON licitaciones(nif_adjudicatario);
CREATE INDEX idx_fecha ON licitaciones(fecha_publicacion);
```

## 4. QUÉ MOTOR USAR

| Motor | Cuándo | Por qué |
|---|---|---|
| **PostgreSQL 16 + DBeaver (RECOMENDADO proyecto univ.)** | 10-40M filas, relacional puro | Gratis, soporta 37,8M sin problema, FK, índices, particionado por año, PostGIS para NUTS |
| DuckDB | Análisis rápido en laptop sin servidor | Lee Parquet directo `SELECT * FROM 'lic.parquet'`, 10x más rápido que Pandas |
| ClickHouse / Spark + Parquet | Proyecto Big Data real | Si quieres demostrar Big Data: Spark 3.5 + 1,1GB Parquet + Zeppelin |
| MySQL 8 | Alternativa si tu profe lo exige | Funciona, pero peor para particionado y JSON/CPV |

> Recomendación: **PostgreSQL para volumetría + DuckDB/Python para análisis**. 8GB RAM basta.

## 5. VOLUMETRÍA

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

En Parquet son solo 1,1 GB (comprimido). En Postgres son ~17,4 GB por índices y tipos sin comprimir. Particionar por `fecha_publicacion` (RANGE yearly) + vacuum mensual.

## 6. IDEAS BIG DATA

1. Fraude: contratos menores fraccionados mismo NIF + mismo órgano
2. Mapa: importe por CCAA/NUTS + PYME vs grande
3. ML: predecir `importe_adjudicacion` vs `importe_licitacion` (baja temeraria)
