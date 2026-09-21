import io
import os
import sys

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import psycopg2
from psycopg2 import sql

ARROW_SQL = {
    pa.bool_(): "boolean",
    pa.int8(): "smallint",
    pa.int16(): "smallint",
    pa.int32(): "integer",
    pa.int64(): "bigint",
    pa.float32(): "real",
    pa.float64(): "double precision",
    pa.date32(): "date",
    pa.date64(): "date",
}

SQL_BY_ARROW_KIND = {
    "string": "text",
    "large_string": "text",
    "timestamp": "timestamp",
    "date": "date",
    "decimal": "numeric",
    "dictionary": "text",
    "null": "text",
}


def arrow_to_sql(t):
    if pa.types.is_dictionary(t):
        return "text"
    if pa.types.is_decimal(t):
        return "numeric(%d,%d)" % (t.precision, t.scale)
    if pa.types.is_timestamp(t):
        return "timestamp"
    if pa.types.is_date(t):
        return "date"
    if t in ARROW_SQL:
        return ARROW_SQL[t]
    return "text"


def quote_id(name):
    return '"%s"' % name.replace('"', '""')


def main():
    path = os.path.abspath(sys.argv[1])
    table = sys.argv[2]
    date_cols = [c for c in (sys.argv[3].split(",") if len(sys.argv) > 3 and sys.argv[3] else []) if c]
    index_cols = [c for c in (sys.argv[4].split(",") if len(sys.argv) > 4 and sys.argv[4] else []) if c]

    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="placsp_contratacion",
        user="postgres",
        password=os.environ.get("PGPASSWORD", ""),
    )
    conn.autocommit = False

    pf = pq.ParquetFile(path)
    schema = pf.schema_arrow
    cols = schema.names

    ddl_cols = []
    for c in cols:
        t = schema.field(c).type
        if c in date_cols:
            pg_type = "date"
        else:
            pg_type = arrow_to_sql(t)
        ddl_cols.append("%s %s" % (quote_id(c), pg_type))

    col_list = sql.SQL(",").join(sql.Identifier(c) for c in cols)
    copy_sql = sql.SQL("COPY {tbl} ({cols}) FROM STDIN WITH (FORMAT csv, NULL '', QUOTE '\"', ESCAPE '\"', HEADER false)").format(
        tbl=sql.Identifier(table), cols=col_list
    )

    cur = conn.cursor()
    cur.execute(sql.SQL("DROP TABLE IF EXISTS {tbl}").format(tbl=sql.Identifier(table)))
    cur.execute(sql.SQL("CREATE TABLE {tbl} ({cols})").format(tbl=sql.Identifier(table), cols=sql.SQL(", ").join(sql.SQL(x) for x in ddl_cols)))
    conn.commit()

    total = 0
    batch = 250_000
    print(f"tabla [{table}] desde {os.path.basename(path)}")
    for i, b in enumerate(pf.iter_batches(batch_size=batch), 1):
        df = b.to_pandas()
        for c in date_cols:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce", dayfirst=True)
        for c in df.columns:
            dt = df[c].dtype
            if isinstance(dt, pd.DatetimeTZDtype):
                df[c] = df[c].dt.tz_localize(None)
        buf = io.StringIO()
        df.to_csv(buf, index=False, header=False, na_rep="")
        buf.seek(0)
        cur.copy_expert(copy_sql, buf)
        conn.commit()
        total += len(df)
        print(f"  lote {i}: acumulado {total:,} filas")

    conn.commit()

    for c in index_cols:
        idx = "idx_%s_%s" % (table, c[:20])
        cur.execute(
            sql.SQL("CREATE INDEX {idx} ON {tbl} ({col})").format(
                idx=sql.Identifier(idx), tbl=sql.Identifier(table), col=sql.Identifier(c)
            )
        )
        conn.commit()
        print(f"  índice {idx} creado")

    cur.close()
    conn.close()
    print(f"TOTAL {total:,} filas en {table}")


if __name__ == "__main__":
    main()