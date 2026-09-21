# Documentación Técnica - PlascspBigData

Documentación técnica del proyecto de base de datos relacional de contratación pública española (PLACSP + Catalunya + Valencia). **37,8M registros (2000-2026) ~1,1 GB en Parquet**.

## Índice

| Documento | Contenido |
|---|---|
| [README principal (../README.md)](../README.md) | Guía resumida "cómo montar todo": instalación, carga y estado actual de la BD |
| [Instalación de PostgreSQL + DBeaver](instalacion-postgresql-dbeaver.md) | Guía técnica paso a paso: requisitos, instalación, configuración, conexión, carga de datos y tuning para 37,8M de registros |
| [Volumetría de datos](volumetria.md) | Distribución por fuente, estimación de tamaño en PostgreSQL, esquema relacional, índices, particionado, mantenimiento y origen de los datos |

## Resumen del proyecto

- **Alcance**: 37,8M registros de contratación pública de España (2000-2026).
- **Fuentes**: PLACSP Nacional (8,7M), Catalunya Contratación (4,3M), Catalunya Subvenciones RAISC (9,6M), Valencia (8,5M).
- **Almacenamiento**: ~1,1 GB en Parquet → ~17,4 GB estimado / **~21,4 GB real medido** en PostgreSQL.
- **Estado actual**: 7 tablas cargadas, **~26,7M filas** (ver [README principal](../README.md)).
- **Motor recomendado**: PostgreSQL 16+ (aquí 18.6) + DBeaver Community.