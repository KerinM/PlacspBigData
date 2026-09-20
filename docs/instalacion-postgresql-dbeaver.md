# Instalación de PostgreSQL 16 + DBeaver

Guía técnica para montar el entorno de base de datos del proyecto **PlascspBigData** (37,8M registros de contratación pública de España).

## 1. Requisitos mínimos

| Recurso | Mínimo | Recomendado |
|---|---|---|
| RAM | 8 GB | 16 GB |
| Disco libre | 30 GB | 60 GB |
| SO | Windows 10/11, Linux, macOS | - |
| Motor | PostgreSQL 16.x | - |
| Cliente | DBeaver Community (gratuito) | - |

Espacio necesario estimado: ~17,4 GB de datos en SGBD + espacio para la carga inicial de CSV/Parquet.

## 2. Instalación de PostgreSQL 16

### 2.1 Descarga

1. Ir a la web oficial: <https://www.postgresql.org/download/>
2. Seleccionar el sistema operativo correspondiente (Windows / Linux / macOS).
3. Descargar la última versión 16.x del instalador (EnterpriseDB / EDB installer en Windows).

### 2.2 Instalación en Windows

1. Ejecutar el instalador descargado (`postgresql-16.x-windows-x64.exe`).
2. Asistente de instalación:
   - **Installation Directory**: por defecto `C:\Program Files\PostgreSQL\16`.
   - **Data Directory**: `C:\Program Files\PostgreSQL\16\data`.
   - **Password** del superusuario `postgres`: anotar y guardar en un lugar seguro.
   - **Port**: `5432` (por defecto).
   - **Locale**: `Spanish, Spain` (o el que corresponda).
3. Finalizar la instalación.
4. Verificar que el servicio `postgresql-x64-16` queda **en ejecución** (Administrador de servicios de Windows o `services.msc`).

### 2.3 Instalación en Linux (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install postgresql-16 postgresql-client-16
sudo service postgresql start
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'tu_password';"
```

### 2.4 Verificación de la instalación

Desde terminal/consola:

```bash
psql --version
```

Debe devolver algo similar a `psql (PostgreSQL) 16.x`.

Conectar por primera vez:

```bash
psql -U postgres -h localhost
```

> En Windows, `psql` está en `C:\Program Files\PostgreSQL\16\bin`.
> Si da error de autenticación, comprobar que el `pg_hba.conf` usa `scram-sha-256` para conexiones locales.

## 3. Instalación de DBeaver

### 3.1 Descarga e instalación

1. Ir a la web oficial: <https://dbeaver.io/download/>
2. Descargar **DBeaver Community** (edición gratuita) compatible con el SO.
3. En Windows: ejecutar el instalador `.exe` y seguir el asistente.
4. En Linux: descargar el `.deb`/`.rpm` o usar el paquete Snap:

```bash
snap install dbeaver-ce
```

### 3.2 Conexión a PostgreSQL

1. Abrir DBeaver.
2. Menú superior: **Base de datos > Nueva conexión** (o icono de enchufe / `Ctrl+Shift+N`).
3. Seleccionar **PostgreSQL**.
4. Rellenar los datos:

| Campo | Valor |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Database | `postgres` (crear luego la BD del proyecto) |
| Username | `postgres` |
| Password | password definido en la instalación |

5. Pulsar **Probar conexión**. Si todo es correcto aparecerá "Conexión exitosa". Si falta el driver JDBC, DBeaver lo descargará automáticamente al aceptar.
6. Pulsar **Aceptar** para guardar la conexión.

## 4. Creación de la base de datos del proyecto

Con DBeaver conectado o desde `psql`:

```sql
CREATE DATABASE placsp_contratacion
  ENCODING 'UTF8'
  LC_COLLATE 'es_ES.UTF-8'
  LC_CTYPE 'es_ES.UTF-8'
  TEMPLATE template0;
```

En Windows, si el locale `es_ES.UTF-8` no está disponible, usar el locale por defecto o `C`/`Spanish_Spain.1252`. Lo importante es **UTF8** para los caracteres de los datos (ñ, acentos).

## 5. Carga de datos (Parquet -> CSV -> COPY)

1. Convertir los `.parquet` a `.csv` con Pandas (ver repositorio de origen):

```python
import pandas as pd
df = pd.read_parquet('nacional/licitaciones_espana.parquet')
df.to_csv('licitaciones.csv', index=False)
```

2. Cargar en PostgreSQL con `COPY`:

```sql
COPY licitaciones(id, expediente, objeto, organo_contratante, importe_sin_iva, fecha_publicacion)
FROM 'C:/data/licitaciones.csv' DELIMITER ',' CSV HEADER;
```

3. Crear índices para la volumetría (imprescindible en 37,8M de filas):

```sql
CREATE INDEX idx_organo       ON licitaciones(organo_contratante);
CREATE INDEX idx_adjudicatario ON licitaciones(nif_adjudicatario);
CREATE INDEX idx_fecha        ON licitaciones(fecha_publicacion);
```

## 6. Configuración recomendada para 37,8M de filas

Ajustar `postgresql.conf`:

```conf
shared_buffers = 2GB          # ~25% de la RAM (8GB)
work_mem = 64MB               # por operación de orden/dictamen
maintenance_work_mem = 512MB  # para CREATE INDEX / VACUUM
effective_cache_size = 6GB
max_connections = 100
```

Recomendable también **particionar por año** sobre `fecha_publicacion` (RANGE por año) para acelerar consultas temporales, y ejecutar `VACUUM` mensual.

Reiniciar el servicio tras el cambio:

```bash
# Windows
net stop postgresql-x64-16
net start postgresql-x64-16

# Linux
sudo systemctl restart postgresql
```

## 7. Solución de problemas rápidos

| Problema | Solución |
|---|---|
| No se puede conectar desde DBeaver | Reiniciar el servicio PostgreSQL y comprobar firewall/puerto 5432 |
| Error `password authentication failed` | Comprobar password en `pg_hba.conf` / `ALTER USER postgres PASSWORD` |
| La carga con COPY es lenta | Eliminar índices antes de cargar y recrearlos después; usar `COMMIT` por lotes |
| Datos con caracteres corruptos | Asegurar BD en UTF8 y CSVs con encoding UTF-8 |

## 8. Enlaces de interés

- PostgreSQL: <https://www.postgresql.org/docs/16/>
- DBeaver: <https://dbeaver.io/docs/>
- Datos de contratación: [PLACSP](https://contrataciondelsectorpublico.gob.es/), [Catalunya](https://analisi.transparenciacatalunya.cat), [Valencia](https://dadesobertes.gva.es)