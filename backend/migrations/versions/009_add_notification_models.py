"""
Alembic migration: Add notification models for automated notification system.

This migration creates notification_logs and notification_preferences tables
with proper indexes, foreign key constraints, and enum types for notification
tracking and user preference management. Implements comprehensive validation
and audit trail support.

Revision ID: 009
Revises: 008
Create Date: 2024-01-07 23:15:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic
revision: str = '009'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade database schema to add notification models.
    
    Creates notification_logs table for tracking all sent notifications with
    delivery status and retry logic, and notification_preferences table for
    managing user notification settings across different channels and types.
    Implements proper indexes for efficient querying and enforces data
    integrity with constraints.
    """
    # Create notification_type enum
    op.execute("""
        CREATE TYPE notification_type AS ENUM (
            'order_created',
            'order_confirmed',
            'order_shipped',
            'order_delivered',
            'order_cancelled',
            'payment_received',
            'payment_failed',
            'delivery_delayed',
            'delivery_reminder'
        )
    """)
    
    # Create notification_channel enum
    op.execute("""
        CREATE TYPE notification_channel AS ENUM (
            'email',
            'sms',
            'push',
            'in_app'
        )
    """)
    
    # Create notification_status enum
    op.execute("""
        CREATE TYPE notification_status AS ENUM (
            'pending',
            'sent',
            'delivered',
            'failed',
            'bounced',
            'retrying'
        )
    """)
    
    # Create notification_logs table
    op.create_table(
        'notification_logs',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique notification identifier',
        ),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='User receiving the notification',
        ),
        sa.Column(
            'notification_type',
            postgresql.ENUM(
                'order_created',
                'order_confirmed',
                'order_shipped',
                'order_delivered',
                'order_cancelled',
                'payment_received',
                'payment_failed',
                'delivery_delayed',
                'delivery_reminder',
                name='notification_type',
                create_type=False,
            ),
            nullable=False,
            comment='Type of notification',
        ),
        sa.Column(
            'channel',
            postgresql.ENUM(
                'email',
                'sms',
                'push',
                'in_app',
                name='notification_channel',
                create_type=False,
            ),
            nullable=False,
            comment='Delivery channel',
        ),
        sa.Column(
            'recipient',
            sa.String(length=255),
            nullable=False,
            comment='Recipient address (email, phone, device token)',
        ),
        sa.Column(
            'subject',
            sa.String(length=500),
            nullable=True,
            comment='Notification subject (for email)',
        ),
        sa.Column(
            'content',
            sa.Text(),
            nullable=False,
            comment='Notification content/body',
        ),
        sa.Column(
            'status',
            postgresql.ENUM(
                'pending',
                'sent',
                'delivered',
                'failed',
                'bounced',
                'retrying',
                name='notification_status',
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'pending'"),
            comment='Current delivery status',
        ),
        sa.Column(
            'sent_at',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment='Timestamp when notification was sent',
        ),
        sa.Column(
            'delivered_at',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment='Timestamp when delivery was confirmed',
        ),
        sa.Column(
            'error_message',
            sa.Text(),
            nullable=True,
            comment='Error details if delivery failed',
        ),
        sa.Column(
            'retry_count',
            sa.Integer(),
            nullable=False,
            server_default=sa.text('0'),
            comment='Number of retry attempts',
        ),
        sa.Column(
            'metadata',
            sa.Text(),
            nullable=True,
            comment='Additional notification metadata (JSON)',
        ),
        sa.Column(
            'created_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
            comment='Record creation timestamp',
        ),
        sa.Column(
            'updated_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
            comment='Last modification timestamp',
        ),
        sa.Column(
            'created_by',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='User who created this record',
        ),
        sa.Column(
            'updated_by',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='User who last modified this record',
        ),
        sa.Column(
            'deleted_at',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment='Soft deletion timestamp',
        ),
        sa.PrimaryKeyConstraint('id', name='pk_notification_logs'),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            name='fk_notification_logs_user_id',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['created_by'],
            ['users.id'],
            name='fk_notification_logs_created_by',
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['updated_by'],
            ['users.id'],
            name='fk_notification_logs_updated_by',
            ondelete='SET NULL',
        ),
        sa.CheckConstraint(
            'retry_count >= 0',
            name='ck_notification_logs_retry_count_non_negative',
        ),
        sa.CheckConstraint(
            "length(recipient) >= 3",
            name='ck_notification_logs_recipient_min_length',
        ),
        sa.CheckConstraint(
            "length(content) >= 1",
            name='ck_notification_logs_content_not_empty',
        ),
        sa.CheckConstraint(
            'delivered_at IS NULL OR delivered_at >= sent_at',
            name='ck_notification_logs_delivered_after_sent',
        ),
        comment='Notification delivery logs with status tracking',
    )
    
    # Create indexes for notification_logs
    op.create_index(
        'ix_notification_logs_user_id',
        'notification_logs',
        ['user_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_notification_logs_notification_type',
        'notification_logs',
        ['notification_type'],
        unique=False,
    )
    
    op.create_index(
        'ix_notification_logs_channel',
        'notification_logs',
        ['channel'],
        unique=False,
    )
    
    op.create_index(
        'ix_notification_logs_status',
        'notification_logs',
        ['status'],
        unique=False,
    )
    
    op.create_index(
        'ix_notification_logs_sent_at',
        'notification_logs',
        ['sent_at'],
        unique=False,
    )
    
    # Composite indexes for common query patterns
    op.create_index(
        'ix_notification_logs_user_type',
        'notification_logs',
        ['user_id', 'notification_type'],
        unique=False,
    )
    
    op.create_index(
        'ix_notification_logs_status_sent',
        'notification_logs',
        ['status', 'sent_at'],
        unique=False,
    )
    
    op.create_index(
        'ix_notification_logs_channel_status',
        'notification_logs',
        ['channel', 'status'],
        unique=False,
    )
    
    # Partial index for pending/retrying notifications
    op.create_index(
        'ix_notification_logs_pending_retrying',
        'notification_logs',
        ['created_at'],
        unique=False,
        postgresql_where=sa.text("status IN ('pending', 'retrying')"),
    )
    
    # Partial index for failed notifications
    op.create_index(
        'ix_notification_logs_failed',
        'notification_logs',
        ['user_id', 'notification_type', 'created_at'],
        unique=False,
        postgresql_where=sa.text("status IN ('failed', 'bounced')"),
    )
    
    # Create notification_preferences table
    op.create_table(
        'notification_preferences',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique preference identifier',
        ),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='User who owns these preferences',
        ),
        sa.Column(
            'notification_type',
            postgresql.ENUM(
                'order_created',
                'order_confirmed',
                'order_shipped',
                'order_delivered',
                'order_cancelled',
                'payment_received',
                'payment_failed',
                'delivery_delayed',
                'delivery_reminder',
                name='notification_type',
                create_type=False,
            ),
            nullable=False,
            comment='Type of notification',
        ),
        sa.Column(
            'email_enabled',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
            comment='Enable email notifications',
        ),
        sa.Column(
            'sms_enabled',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
            comment='Enable SMS notifications',
        ),
        sa.Column(
            'push_enabled',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
            comment='Enable push notifications',
        ),
        sa.Column(
            'in_app_enabled',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
            comment='Enable in-app notifications',
        ),
        sa.Column(
            'created_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
            comment='Record creation timestamp',
        ),
        sa.Column(
            'updated_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
            comment='Last modification timestamp',
        ),
        sa.Column(
            'created_by',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='User who created this record',
        ),
        sa.Column(
            'updated_by',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='User who last modified this record',
        ),
        sa.Column(
            'deleted_at',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment='Soft deletion timestamp',
        ),
        sa.PrimaryKeyConstraint('id', name='pk_notification_preferences'),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            name='fk_notification_preferences_user_id',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['created_by'],
            ['users.id'],
            name='fk_notification_preferences_created_by',
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['updated_by'],
            ['users.id'],
            name='fk_notification_preferences_updated_by',
            ondelete='SET NULL',
        ),
        comment='User notification preferences by type and channel',
    )
    
    # Create unique index for user_id and notification_type combination
    op.create_index(
        'ix_notification_preferences_user_type',
        'notification_preferences',
        ['user_id', 'notification_type'],
        unique=True,
    )
    
    # Create index for user_id for efficient lookups
    op.create_index(
        'ix_notification_preferences_user_id',
        'notification_preferences',
        ['user_id'],
        unique=False,
    )
    
    # Create index for notification_type
    op.create_index(
        'ix_notification_preferences_notification_type',
        'notification_preferences',
        ['notification_type'],
        unique=False,
    )


def downgrade() -> None:
    """
    Downgrade database schema by removing notification models.
    
    Removes notification_preferences and notification_logs tables, drops
    indexes, and removes enum types. This operation is safe as it only
    removes newly added structures.
    """
    # Drop notification_preferences table
    op.drop_index(
        'ix_notification_preferences_notification_type',
        table_name='notification_preferences',
    )
    
    op.drop_index(
        'ix_notification_preferences_user_id',
        table_name='notification_preferences',
    )
    
    op.drop_index(
        'ix_notification_preferences_user_type',
        table_name='notification_preferences',
    )
    
    op.drop_table('notification_preferences')
    
    # Drop notification_logs table
    op.drop_index(
        'ix_notification_logs_failed',
        table_name='notification_logs',
        postgresql_where=sa.text("status IN ('failed', 'bounced')"),
    )
    
    op.drop_index(
        'ix_notification_logs_pending_retrying',
        table_name='notification_logs',
        postgresql_where=sa.text("status IN ('pending', 'retrying')"),
    )
    
    op.drop_index(
        'ix_notification_logs_channel_status',
        table_name='notification_logs',
    )
    
    op.drop_index(
        'ix_notification_logs_status_sent',
        table_name='notification_logs',
    )
    
    op.drop_index(
        'ix_notification_logs_user_type',
        table_name='notification_logs',
    )
    
    op.drop_index(
        'ix_notification_logs_sent_at',
        table_name='notification_logs',
    )
    
    op.drop_index(
        'ix_notification_logs_status',
        table_name='notification_logs',
    )
    
    op.drop_index(
        'ix_notification_logs_channel',
        table_name='notification_logs',
    )
    
    op.drop_index(
        'ix_notification_logs_notification_type',
        table_name='notification_logs',
    )
    
    op.drop_index(
        'ix_notification_logs_user_id',
        table_name='notification_logs',
    )
    
    op.drop_table('notification_logs')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS notification_status')
    op.execute('DROP TYPE IF EXISTS notification_channel')
    op.execute('DROP TYPE IF EXISTS notification_type')