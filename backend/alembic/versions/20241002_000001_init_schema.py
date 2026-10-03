"""Initial schema

Revision ID: 20241002_000001
Revises: 
Create Date: 2024-10-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20241002_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="PARENT"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("phone"),
    )
    op.create_index(op.f("ix_parents_id"), "parents", ["id"], unique=False)
    op.create_index(op.f("ix_parents_email"), "parents", ["email"], unique=False)
    op.create_index(op.f("ix_parents_phone"), "parents", ["phone"], unique=False)

    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("grade", sa.String(length=30), nullable=False),
        sa.Column("school_id", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_students_id"), "students", ["id"], unique=False)
    op.create_index(op.f("ix_students_school_id"), "students", ["school_id"], unique=False)

    op.create_table(
        "parent_student",
        sa.Column("parent_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["parents.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("parent_id", "student_id"),
    )

    op.create_table(
        "buses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plate_no", sa.String(length=32), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("route_name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id"),
        sa.UniqueConstraint("plate_no"),
    )
    op.create_index(op.f("ix_buses_id"), "buses", ["id"], unique=False)
    op.create_index(op.f("ix_buses_device_id"), "buses", ["device_id"], unique=False)
    op.create_index(op.f("ix_buses_plate_no"), "buses", ["plate_no"], unique=False)

    op.create_table(
        "bus_locations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bus_id", sa.Integer(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("speed", sa.Float(), nullable=True),
        sa.Column("heading", sa.Float(), nullable=True),
        sa.Column("gps_time", sa.DateTime(), nullable=True),
        sa.Column("server_time", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["bus_id"], ["buses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bus_locations_id"), "bus_locations", ["id"], unique=False)
    op.create_index(op.f("ix_bus_locations_bus_id"), "bus_locations", ["bus_id"], unique=False)

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("bus_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.Enum("BOARDED", "ALIGHTED", name="eventtype"), nullable=False),
        sa.Column("event_time", sa.DateTime(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="DEVICE"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["bus_id"], ["buses.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_events_id"), "events", ["id"], unique=False)
    op.create_index(op.f("ix_events_student_id"), "events", ["student_id"], unique=False)
    op.create_index(op.f("ix_events_bus_id"), "events", ["bus_id"], unique=False)

    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bus_id", sa.Integer(), nullable=False),
        sa.Column("api_key_hash", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["bus_id"], ["buses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("api_key_hash"),
        sa.UniqueConstraint("bus_id"),
    )
    op.create_index(op.f("ix_devices_id"), "devices", ["id"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="SENT"),
        sa.Column("provider_response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["parents.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_id"), "notifications", ["id"], unique=False)
    op.create_index(op.f("ix_notifications_parent_id"), "notifications", ["parent_id"], unique=False)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["parents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_refresh_tokens_id"), "refresh_tokens", ["id"], unique=False)
    op.create_index(op.f("ix_refresh_tokens_token_hash"), "refresh_tokens", ["token_hash"], unique=False)

    op.create_table(
        "drivers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("license_no", sa.String(length=80), nullable=False),
        sa.Column("nic", sa.String(length=30), nullable=False),
        sa.Column("bus_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["parents.id"]),
        sa.ForeignKeyConstraint(["bus_id"], ["buses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_drivers_id"), "drivers", ["id"], unique=False)
    op.create_index(op.f("ix_drivers_user_id"), "drivers", ["user_id"], unique=False)
    op.create_index(op.f("ix_drivers_bus_id"), "drivers", ["bus_id"], unique=False)

    op.create_table(
        "driver_pay_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("driver_id", sa.Integer(), nullable=False),
        sa.Column("pay_type", sa.String(length=32), nullable=False, server_default="MONTHLY_SALARY"),
        sa.Column("base_salary", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("per_trip_rate", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("per_km_rate", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("overtime_rate", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("bank_name", sa.String(length=120), nullable=True),
        sa.Column("bank_account_no_encrypted", sa.String(length=255), nullable=True),
        sa.Column("effective_from", sa.DateTime(), nullable=False),
        sa.Column("effective_to", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_driver_pay_profiles_id"), "driver_pay_profiles", ["id"], unique=False)
    op.create_index(op.f("ix_driver_pay_profiles_driver_id"), "driver_pay_profiles", ["driver_id"], unique=False)

    op.create_table(
        "trips",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bus_id", sa.Integer(), nullable=False),
        sa.Column("driver_id", sa.Integer(), nullable=False),
        sa.Column("route_name", sa.String(length=120), nullable=False),
        sa.Column("shift", sa.String(length=20), nullable=False, server_default="MORNING"),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("distance_km", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="COMPLETED"),
        sa.ForeignKeyConstraint(["bus_id"], ["buses.id"]),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trips_id"), "trips", ["id"], unique=False)
    op.create_index(op.f("ix_trips_bus_id"), "trips", ["bus_id"], unique=False)
    op.create_index(op.f("ix_trips_driver_id"), "trips", ["driver_id"], unique=False)

    op.create_table(
        "driver_attendance",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("driver_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("check_in", sa.DateTime(), nullable=True),
        sa.Column("check_out", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PRESENT"),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_driver_attendance_id"), "driver_attendance", ["id"], unique=False)
    op.create_index(op.f("ix_driver_attendance_driver_id"), "driver_attendance", ["driver_id"], unique=False)

    op.create_table(
        "pay_periods",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pay_periods_id"), "pay_periods", ["id"], unique=False)

    op.create_table(
        "payroll_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("driver_id", sa.Integer(), nullable=False),
        sa.Column("pay_period_id", sa.Integer(), nullable=False),
        sa.Column("base_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("trip_earnings", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("distance_earnings", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("overtime_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("bonus", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("allowances", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("advance_deduction", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("penalty_deduction", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("other_deduction", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("gross", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("net", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("payment_method", sa.String(length=20), nullable=True),
        sa.Column("payment_reference", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"]),
        sa.ForeignKeyConstraint(["pay_period_id"], ["pay_periods.id"]),
        sa.ForeignKeyConstraint(["approved_by"], ["parents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payroll_records_id"), "payroll_records", ["id"], unique=False)
    op.create_index(op.f("ix_payroll_records_driver_id"), "payroll_records", ["driver_id"], unique=False)
    op.create_index(op.f("ix_payroll_records_pay_period_id"), "payroll_records", ["pay_period_id"], unique=False)

    op.create_table(
        "driver_advances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("driver_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("issued_date", sa.DateTime(), nullable=False),
        sa.Column("remaining_balance", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("monthly_recovery", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_driver_advances_id"), "driver_advances", ["id"], unique=False)

    op.create_table(
        "driver_adjustments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("driver_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["parents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_driver_adjustments_id"), "driver_adjustments", ["id"], unique=False)

    op.create_table(
        "payslips",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payroll_record_id", sa.Integer(), nullable=False),
        sa.Column("pdf_url", sa.String(length=255), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["payroll_record_id"], ["payroll_records.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payroll_record_id"),
    )
    op.create_index(op.f("ix_payslips_id"), "payslips", ["id"], unique=False)
    op.create_index(op.f("ix_payslips_payroll_record_id"), "payslips", ["payroll_record_id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("before_json", sa.Text(), nullable=True),
        sa.Column("after_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["parents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_id"), "audit_logs", ["id"], unique=False)

    op.create_table(
        "emergency_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bus_id", sa.Integer(), nullable=False),
        sa.Column("driver_id", sa.Integer(), nullable=True),
        sa.Column("triggered_by_user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False, server_default="SOS"),
        sa.Column("severity", sa.String(length=16), nullable=False, server_default="CRITICAL"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="OPEN"),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="DRIVER_APP"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("acknowledged_by", sa.Integer(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by", sa.Integer(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["bus_id"], ["buses.id"]),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"]),
        sa.ForeignKeyConstraint(["triggered_by_user_id"], ["parents.id"]),
        sa.ForeignKeyConstraint(["acknowledged_by"], ["parents.id"]),
        sa.ForeignKeyConstraint(["resolved_by"], ["parents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_emergency_alerts_id"), "emergency_alerts", ["id"], unique=False)
    op.create_index(op.f("ix_emergency_alerts_bus_id"), "emergency_alerts", ["bus_id"], unique=False)
    op.create_index(op.f("ix_emergency_alerts_driver_id"), "emergency_alerts", ["driver_id"], unique=False)
    op.create_index(op.f("ix_emergency_alerts_triggered_by_user_id"), "emergency_alerts", ["triggered_by_user_id"], unique=False)

    op.create_table(
        "emergency_alert_updates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["emergency_alerts.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["parents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_emergency_alert_updates_id"), "emergency_alert_updates", ["id"], unique=False)
    op.create_index(op.f("ix_emergency_alert_updates_alert_id"), "emergency_alert_updates", ["alert_id"], unique=False)

    op.create_table(
        "emergency_contacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False, server_default="COORDINATOR"),
        sa.Column("priority_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_emergency_contacts_id"), "emergency_contacts", ["id"], unique=False)
    op.create_index(op.f("ix_emergency_contacts_school_id"), "emergency_contacts", ["school_id"], unique=False)

    op.create_table(
        "emergency_notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("recipient_user_id", sa.Integer(), nullable=True),
        sa.Column("recipient_phone", sa.String(length=32), nullable=True),
        sa.Column("channel", sa.String(length=12), nullable=False, server_default="PUSH"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("attempt_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("provider_response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["emergency_alerts.id"]),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["parents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_emergency_notifications_id"), "emergency_notifications", ["id"], unique=False)
    op.create_index(op.f("ix_emergency_notifications_recipient_user_id"), "emergency_notifications", ["recipient_user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("emergency_notifications")
    op.drop_table("emergency_contacts")
    op.drop_table("emergency_alert_updates")
    op.drop_table("emergency_alerts")
    op.drop_table("audit_logs")
    op.drop_table("payslips")
    op.drop_table("driver_adjustments")
    op.drop_table("driver_advances")
    op.drop_table("payroll_records")
    op.drop_table("pay_periods")
    op.drop_table("driver_attendance")
    op.drop_table("trips")
    op.drop_table("driver_pay_profiles")
    op.drop_table("drivers")
    op.drop_table("refresh_tokens")
    op.drop_table("notifications")
    op.drop_table("devices")
    op.drop_table("events")
    op.drop_table("bus_locations")
    op.drop_table("buses")
    op.drop_table("parent_student")
    op.drop_table("students")
    op.drop_table("parents")
