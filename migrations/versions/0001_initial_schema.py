"""Initial Skynet schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


role_enum = sa.Enum(
    "ADMIN",
    "DISPATCHER",
    "INSTRUCTOR",
    "CFI",
    "CADET",
    "MAINTENANCE_OFFICER",
    name="role_enum",
    native_enum=False,
)
aircraft_status_enum = sa.Enum(
    "READY",
    "SCHEDULED",
    "AIRBORNE",
    "LANDED",
    "GROUNDED",
    "MAINTENANCE",
    name="aircraft_status_enum",
    native_enum=False,
)
sortie_status_enum = sa.Enum(
    "SCHEDULED",
    "RELEASED",
    "AIRBORNE",
    "LANDED",
    "TRAINING_SUBMITTED",
    "TRAINING_APPROVED",
    "CLOSED",
    "CANCELLED",
    "AIRCRAFT_GROUNDED",
    "RECOVERY_REQUIRED",
    name="sortie_status_enum",
    native_enum=False,
)
training_status_enum = sa.Enum(
    "DRAFT",
    "SUBMITTED",
    "APPROVED",
    "REJECTED",
    name="training_status_enum",
    native_enum=False,
)
defect_severity_enum = sa.Enum(
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
    name="defect_severity_enum",
    native_enum=False,
)
defect_status_enum = sa.Enum(
    "OPEN",
    "RESOLVED",
    "DEFERRED",
    name="defect_status_enum",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "bases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("location", sa.String(length=120), nullable=False),
        sa.UniqueConstraint("code", name="uq_bases_code"),
    )
    op.create_index("ix_bases_code", "bases", ["code"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", role_enum, nullable=False),
        sa.Column("base_id", sa.Integer(), sa.ForeignKey("bases.id"), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"], unique=False)
    op.create_index("ix_users_base_id", "users", ["base_id"], unique=False)

    op.create_table(
        "aircraft",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registration", sa.String(length=20), nullable=False),
        sa.Column("aircraft_type", sa.String(length=80), nullable=False),
        sa.Column("base_id", sa.Integer(), sa.ForeignKey("bases.id"), nullable=False),
        sa.Column("status", aircraft_status_enum, nullable=False),
        sa.Column("tbo_remaining_hours", sa.Integer(), nullable=False),
        sa.UniqueConstraint("registration", name="uq_aircraft_registration"),
    )
    op.create_index("ix_aircraft_registration", "aircraft", ["registration"], unique=True)
    op.create_index("ix_aircraft_base_id", "aircraft", ["base_id"], unique=False)
    op.create_index("ix_aircraft_status", "aircraft", ["status"], unique=False)

    op.create_table(
        "sorties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sortie_number", sa.String(length=40), nullable=False),
        sa.Column("cadet_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("instructor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("aircraft_id", sa.Integer(), sa.ForeignKey("aircraft.id"), nullable=False),
        sa.Column("base_id", sa.Integer(), sa.ForeignKey("bases.id"), nullable=False),
        sa.Column("lesson_type", sa.String(length=80), nullable=False),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sortie_status_enum, nullable=False),
        sa.Column("delay_minutes", sa.Integer(), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.UniqueConstraint("sortie_number", name="uq_sortie_number"),
    )
    op.create_index("ix_sorties_sortie_number", "sorties", ["sortie_number"], unique=True)
    op.create_index("ix_sorties_cadet_id", "sorties", ["cadet_id"], unique=False)
    op.create_index("ix_sorties_instructor_id", "sorties", ["instructor_id"], unique=False)
    op.create_index("ix_sorties_aircraft_id", "sorties", ["aircraft_id"], unique=False)
    op.create_index("ix_sorties_base_id", "sorties", ["base_id"], unique=False)
    op.create_index("ix_sorties_status", "sorties", ["status"], unique=False)

    op.create_table(
        "training_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sortie_id", sa.Integer(), sa.ForeignKey("sorties.id"), nullable=False),
        sa.Column("cadet_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("instructor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("base_id", sa.Integer(), sa.ForeignKey("bases.id"), nullable=False),
        sa.Column("lesson_type", sa.String(length=80), nullable=False),
        sa.Column("maneuver_score", sa.Integer(), nullable=True),
        sa.Column("communication_score", sa.Integer(), nullable=True),
        sa.Column("situational_awareness_score", sa.Integer(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("status", training_status_enum, nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.UniqueConstraint("sortie_id", name="uq_training_progress_sortie_id"),
    )
    op.create_index("ix_training_progress_sortie_id", "training_progress", ["sortie_id"], unique=True)
    op.create_index("ix_training_progress_cadet_id", "training_progress", ["cadet_id"], unique=False)
    op.create_index("ix_training_progress_instructor_id", "training_progress", ["instructor_id"], unique=False)
    op.create_index("ix_training_progress_base_id", "training_progress", ["base_id"], unique=False)
    op.create_index("ix_training_progress_status", "training_progress", ["status"], unique=False)

    op.create_table(
        "defects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("aircraft_id", sa.Integer(), sa.ForeignKey("aircraft.id"), nullable=False),
        sa.Column("sortie_id", sa.Integer(), sa.ForeignKey("sorties.id"), nullable=True),
        sa.Column("reported_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("base_id", sa.Integer(), sa.ForeignKey("bases.id"), nullable=False),
        sa.Column("severity", defect_severity_enum, nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", defect_status_enum, nullable=False),
        sa.Column("resolved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
    )
    op.create_index("ix_defects_aircraft_id", "defects", ["aircraft_id"], unique=False)
    op.create_index("ix_defects_sortie_id", "defects", ["sortie_id"], unique=False)
    op.create_index("ix_defects_reported_by", "defects", ["reported_by"], unique=False)
    op.create_index("ix_defects_base_id", "defects", ["base_id"], unique=False)
    op.create_index("ix_defects_severity", "defects", ["severity"], unique=False)
    op.create_index("ix_defects_status", "defects", ["status"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("actor_role", sa.String(length=40), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("old_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"], unique=False)
    op.create_index("ix_audit_logs_actor_role", "audit_logs", ["actor_role"], unique=False)
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"], unique=False)
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"], unique=False)
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_logs_timestamp", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_role", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_defects_status", table_name="defects")
    op.drop_index("ix_defects_severity", table_name="defects")
    op.drop_index("ix_defects_base_id", table_name="defects")
    op.drop_index("ix_defects_reported_by", table_name="defects")
    op.drop_index("ix_defects_sortie_id", table_name="defects")
    op.drop_index("ix_defects_aircraft_id", table_name="defects")
    op.drop_table("defects")

    op.drop_index("ix_training_progress_status", table_name="training_progress")
    op.drop_index("ix_training_progress_base_id", table_name="training_progress")
    op.drop_index("ix_training_progress_instructor_id", table_name="training_progress")
    op.drop_index("ix_training_progress_cadet_id", table_name="training_progress")
    op.drop_index("ix_training_progress_sortie_id", table_name="training_progress")
    op.drop_table("training_progress")

    op.drop_index("ix_sorties_status", table_name="sorties")
    op.drop_index("ix_sorties_base_id", table_name="sorties")
    op.drop_index("ix_sorties_aircraft_id", table_name="sorties")
    op.drop_index("ix_sorties_instructor_id", table_name="sorties")
    op.drop_index("ix_sorties_cadet_id", table_name="sorties")
    op.drop_index("ix_sorties_sortie_number", table_name="sorties")
    op.drop_table("sorties")

    op.drop_index("ix_aircraft_status", table_name="aircraft")
    op.drop_index("ix_aircraft_base_id", table_name="aircraft")
    op.drop_index("ix_aircraft_registration", table_name="aircraft")
    op.drop_table("aircraft")

    op.drop_index("ix_users_base_id", table_name="users")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_bases_code", table_name="bases")
    op.drop_table("bases")
