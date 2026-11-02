"""Add immutable public release IDs and an explicit active-release pointer.

Revision ID: 8bb934a110d2
Revises: 24d9c72cc7f1
"""
from uuid import uuid4

from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa


revision = "8bb934a110d2"
down_revision = "24d9c72cc7f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    release_columns = {column["name"] for column in inspect(connection).get_columns("curriculum_release")}
    if "public_id" not in release_columns:
        # SQLite cannot add a computed UUID NOT NULL column in place. Keep the
        # physical column additive and enforce non-null/immutability with triggers.
        op.add_column("curriculum_release", sa.Column("public_id", sa.String(length=36), nullable=True))
    for (release_id,) in connection.execute(
        sa.text("SELECT id FROM curriculum_release WHERE public_id IS NULL OR public_id = ''")
    ).all():
        connection.execute(
            sa.text("UPDATE curriculum_release SET public_id = :public_id WHERE id = :id"),
            {"public_id": str(uuid4()), "id": release_id},
        )

    index_names = {index["name"] for index in inspect(connection).get_indexes("curriculum_release")}
    if "uq_curriculum_release_public_id" not in index_names:
        op.create_index("uq_curriculum_release_public_id", "curriculum_release", ["public_id"], unique=True)

    if "active_curriculum_release" not in inspect(connection).get_table_names():
        op.create_table(
            "active_curriculum_release",
            sa.Column("singleton_id", sa.Integer(), nullable=False),
            sa.Column("release_id", sa.Integer(), nullable=False),
            sa.CheckConstraint("singleton_id = 1", name="ck_active_curriculum_release_singleton"),
            sa.ForeignKeyConstraint(["release_id"], ["curriculum_release.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("singleton_id"),
            sa.UniqueConstraint("release_id", name="uq_active_curriculum_release_release_id"),
        )
    op.execute(
        "CREATE TRIGGER IF NOT EXISTS trg_curriculum_release_public_id_required_insert "
        "BEFORE INSERT ON curriculum_release "
        "WHEN NEW.public_id IS NULL OR NEW.public_id = '' "
        "BEGIN SELECT RAISE(ABORT, 'public release id is required'); END"
    )
    op.execute(
        "CREATE TRIGGER IF NOT EXISTS trg_curriculum_release_public_id_required_update "
        "BEFORE UPDATE OF public_id ON curriculum_release "
        "WHEN NEW.public_id IS NULL OR NEW.public_id = '' "
        "BEGIN SELECT RAISE(ABORT, 'public release id is required'); END"
    )
    op.execute(
        "CREATE TRIGGER IF NOT EXISTS trg_curriculum_release_public_id_immutable "
        "BEFORE UPDATE OF public_id ON curriculum_release "
        "WHEN OLD.public_id <> NEW.public_id "
        "BEGIN SELECT RAISE(ABORT, 'public release id is immutable'); END"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_curriculum_release_public_id_immutable")
    op.execute("DROP TRIGGER IF EXISTS trg_curriculum_release_public_id_required_update")
    op.execute("DROP TRIGGER IF EXISTS trg_curriculum_release_public_id_required_insert")
    op.drop_table("active_curriculum_release")
    op.drop_index("uq_curriculum_release_public_id", table_name="curriculum_release")
    op.drop_column("curriculum_release", "public_id")
