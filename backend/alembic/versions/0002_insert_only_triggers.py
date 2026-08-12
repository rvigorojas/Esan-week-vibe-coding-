"""0002 insert-only triggers

Refuerzo a nivel DB (segunda capa, ADR-2: "sin edicion retroactiva no
auditada" en dos capas -- API sin UPDATE/DELETE + trigger de base de datos
como respaldo) para las tablas offline insert-only: activacion,
evaluacion_inicial, relevo_mando, marcador_incidente.

En esta version, `activacion` bloquea TODO update/delete sin excepcion --
la excepcion para la transicion ACTIVA -> CERRADA se agrega en la migracion
0003, una vez que el backend soporto /desactivar (Paso 14 de la bitacora).

Revision ID: 0002_insert_only_triggers
Revises: 0001_initial
Create Date: 2026-07-21
"""
from alembic import op

revision = "0002_insert_only_triggers"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

_INSERT_ONLY_TABLES = ("activacion", "evaluacion_inicial", "relevo_mando", "marcador_incidente")

_FUNC_SQL = """
CREATE OR REPLACE FUNCTION prevent_update_delete() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Tabla % es insert-only: UPDATE/DELETE no permitido (ADR-2).', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade():
    op.execute(_FUNC_SQL)
    for table in _INSERT_ONLY_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_insert_only
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION prevent_update_delete();
            """
        )


def downgrade():
    for table in _INSERT_ONLY_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_insert_only ON {table};")
    op.execute("DROP FUNCTION IF EXISTS prevent_update_delete();")
