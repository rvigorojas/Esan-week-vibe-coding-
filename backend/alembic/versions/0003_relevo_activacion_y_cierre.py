"""0003 relevo_activacion_y_cierre -- Paso 14 de la bitacora

Cierra 2 de los 4 huecos detectados al escribir FRONTEND-SPEC.md:

1. RelevoMando.activacion_id: la tabla ya se crea con esta columna via
   Base.metadata.create_all() (migracion 0001, que es un espejo vivo de los
   modelos) -- NO se agrega aca con ADD COLUMN. Intentarlo da
   DuplicateColumnError contra una base creada con la 0001 ya actualizada
   (detectado corriendo la migracion contra Postgres real). Si tu base viene
   de una version de 0001 anterior a que el modelo tuviera esta columna,
   descomenta el ADD COLUMN de abajo.

2. Cierre de activacion: reemplaza el trigger insert-only "todo bloqueado"
   de activacion (0002) por uno dedicado que permite UNICAMENTE la
   transicion estado 'ACTIVA' -> 'CERRADA', verificando que ningun otro
   campo cambie en el mismo UPDATE. Preserva la intencion real del ADR-2
   sin bloquear /activaciones/{id}/desactivar, y queda auditado via
   app/db/audit.py (listener after_update de Activacion).

   Bug real detectado y corregido al verificar contra Postgres: el primer
   intento comparaba OLD.estado = 'activa' (el .value del enum de Python,
   minusculas) y fallaba con "invalid input syntax for enum" -- SQLAlchemy
   guarda el NOMBRE del enum ('ACTIVA', mayusculas), no su .value. Se
   corrigio comparando contra 'ACTIVA'/'CERRADA' tras confirmar los labels
   reales con `SELECT enumlabel FROM pg_enum ...`.

Revision ID: 0003_relevo_activacion_y_cierre
Revises: 0002_insert_only_triggers
Create Date: 2026-07-30
"""
from alembic import op

revision = "0003_relevo_activacion_y_cierre"
down_revision = "0002_insert_only_triggers"
branch_labels = None
depends_on = None

# Descomentar solo si tu 0001 se corrio ANTES de que el modelo tuviera
# activacion_id en RelevoMando:
# from alembic import op
# import sqlalchemy as sa
# def _add_activacion_id_if_missing():
#     op.add_column(
#         "relevo_mando",
#         sa.Column("activacion_id", sa.Integer(), sa.ForeignKey("activacion.id"), nullable=True),
#     )

_DROP_OLD_TRIGGER = "DROP TRIGGER IF EXISTS trg_activacion_insert_only ON activacion;"

_NEW_FUNC_SQL = """
CREATE OR REPLACE FUNCTION prevent_activacion_edit_except_cierre() RETURNS trigger AS $$
BEGIN
    -- Unica transicion permitida: ACTIVA -> CERRADA, sin cambiar ningun otro campo.
    IF OLD.estado = 'ACTIVA' AND NEW.estado = 'CERRADA'
       AND OLD.categoria_emergencia = NEW.categoria_emergencia
       AND OLD.nivel_alerta = NEW.nivel_alerta
       AND OLD.tipo_alerta IS NOT DISTINCT FROM NEW.tipo_alerta
       AND OLD.clasificacion_origen IS NOT DISTINCT FROM NEW.clasificacion_origen
       AND OLD.tipo_incidente = NEW.tipo_incidente
       AND OLD.hora_evento = NEW.hora_evento
       AND OLD.creado_por_usuario_id = NEW.creado_por_usuario_id
    THEN
        RETURN NEW;
    END IF;

    RAISE EXCEPTION
        'activacion es insert-only salvo la transicion ACTIVA -> CERRADA sin otros cambios (ADR-2, Paso 14).';
END;
$$ LANGUAGE plpgsql;
"""


def upgrade():
    # (1) activacion_id de RelevoMando ya viene de 0001 -- ver nota arriba.

    # (2) Trigger dedicado de cierre, reemplaza el bloqueo total de 0002 solo
    # para la tabla activacion (evaluacion_inicial, relevo_mando y
    # marcador_incidente siguen 100% insert-only via 0002).
    op.execute(_DROP_OLD_TRIGGER)
    op.execute(_NEW_FUNC_SQL)
    op.execute(
        """
        CREATE TRIGGER trg_activacion_solo_cierre
        BEFORE UPDATE ON activacion
        FOR EACH ROW EXECUTE FUNCTION prevent_activacion_edit_except_cierre();
        """
    )
    # DELETE sigue bloqueado por completo.
    op.execute(
        """
        CREATE TRIGGER trg_activacion_no_delete
        BEFORE DELETE ON activacion
        FOR EACH ROW EXECUTE FUNCTION prevent_update_delete();
        """
    )


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS trg_activacion_solo_cierre ON activacion;")
    op.execute("DROP TRIGGER IF EXISTS trg_activacion_no_delete ON activacion;")
    op.execute("DROP FUNCTION IF EXISTS prevent_activacion_edit_except_cierre();")
    op.execute(
        """
        CREATE TRIGGER trg_activacion_insert_only
        BEFORE UPDATE OR DELETE ON activacion
        FOR EACH ROW EXECUTE FUNCTION prevent_update_delete();
        """
    )
