"""0001 initial -- crea el esquema completo

Esta migracion delega en Base.metadata.create_all(): es un espejo vivo de
los modelos en app/models/models.py, no DDL congelado. Si agregas o cambias
una columna en los modelos, esta migracion la reflejara al correr contra una
base vacia -- para una base ya existente, agrega una migracion incremental
en vez de editar esta (ver 0003 como ejemplo de columna agregada sin
romper `alembic upgrade` en una base con datos).

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-21
"""
from alembic import op

from app.db.base import Base
from app.models import models  # noqa: F401

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade():
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
