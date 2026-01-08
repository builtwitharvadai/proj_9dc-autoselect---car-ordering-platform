"""
Alembic migration: Add payment models for secure payment processing.

This migration creates comprehensive payment tables with encryption support,
status tracking, and audit trails. Implements PCI DSS compliance through
tokenization and proper indexing for efficient payment processing.

Revision ID: 007
Revises: 006
Create Date: 2024-01-07 23:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade database schema to add payment models.
    
    Creates payments and payment_status_history tables with comprehensive
    fields for payment processing, encryption support, and audit trails.
    Implements proper indexes for efficient querying and enforces data
    integrity with constraints.
    """
    # Create payment_status enum
    op.execute("""
        CREATE TYPE payment_status AS ENUM (
            'pending',
            'processing',
            'requires_action',
            'succeeded',
            'failed',
            'cancelled',
            'refunded',
            'partially_refunded'
        )
    """)
    
    # Create payment_method_type enum
    op.execute("""
        CREATE TYPE payment_method_type AS ENUM (
            'card',
            'ach',
            'wire',
            'financing'
        )
    """)
    
    # Create payments table
    op.create_table(
        'payments',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique payment identifier',
        ),
        sa.Column(
            'order_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Associated order identifier',
        ),
        sa.Column(
            'stripe_payment_intent_id',
            sa.String(length=255),
            nullable=False,
            comment='Stripe payment intent identifier',
        ),
        sa.Column(
            'amount',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment='Payment amount in cents',
        ),
        sa.Column(
            'currency',
            sa.String(length=3),
            nullable=False,
            server_default=sa.text("'usd'"),
            comment='Payment currency code (ISO 4217)',
        ),
        sa.Column(
            'status',
            postgresql.ENUM(
                'pending',
                'processing',
                'requires_action',
                'succeeded',
                'failed',
                'cancelled',
                'refunded',
                'partially_refunded',
                name='payment_status',
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'pending'"),
            comment='Current payment status',
        ),
        sa.Column(
            'payment_method_type',
            postgresql.ENUM(
                'card',
                'ach',
                'wire',
                'financing',
                name='payment_method_type',
                create_type=False,
            ),
            nullable=False,
            comment='Type of payment method used',
        ),
        sa.Column(
            'payment_method_token',
            sa.Text(),
            nullable=True,
            comment='Tokenized payment method (encrypted)',
        ),
        sa.Column(
            'last_four',
            sa.String(length=4),
            nullable=True,
            comment='Last 4 digits of card/account',
        ),
        sa.Column(
            'card_brand',
            sa.String(length=50),
            nullable=True,
            comment='Card brand (Visa, Mastercard, etc.)',
        ),
        sa.Column(
            'failure_code',
            sa.String(length=100),
            nullable=True,
            comment='Payment failure code',
        ),
        sa.Column(
            'failure_message',
            sa.String(length=500),
            nullable=True,
            comment='Payment failure message',
        ),
        sa.Column(
            'refund_amount',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default=sa.text('0.00'),
            comment='Total amount refunded',
        ),
        sa.Column(
            'metadata',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Additional payment metadata',
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
        sa.PrimaryKeyConstraint('id', name='pk_payments'),
        sa.ForeignKeyConstraint(
            ['order_id'],
            ['orders.id'],
            name='fk_payments_order_id',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['created_by'],
            ['users.id'],
            name='fk_payments_created_by',
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['updated_by'],
            ['users.id'],
            name='fk_payments_updated_by',
            ondelete='SET NULL',
        ),
        sa.UniqueConstraint(
            'stripe_payment_intent_id',
            name='uq_payments_stripe_payment_intent_id',
        ),
        sa.CheckConstraint(
            "amount >= 0",
            name='ck_payments_amount_non_negative',
        ),
        sa.CheckConstraint(
            "amount <= 10000000.00",
            name='ck_payments_amount_max',
        ),
        sa.CheckConstraint(
            "refund_amount >= 0",
            name='ck_payments_refund_amount_non_negative',
        ),
        sa.CheckConstraint(
            "refund_amount <= amount",
            name='ck_payments_refund_not_exceed_amount',
        ),
        sa.CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name='ck_payments_currency_format',
        ),
        sa.CheckConstraint(
            "last_four IS NULL OR last_four ~ '^[0-9]{4}$'",
            name='ck_payments_last_four_format',
        ),
        comment='Payment transactions with encryption and audit trail',
    )
    
    # Create indexes for payments
    op.create_index(
        'ix_payments_order_id',
        'payments',
        ['order_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_payments_stripe_payment_intent_id',
        'payments',
        ['stripe_payment_intent_id'],
        unique=True,
    )
    
    op.create_index(
        'ix_payments_status',
        'payments',
        ['status'],
        unique=False,
    )
    
    op.create_index(
        'ix_payments_payment_method_type',
        'payments',
        ['payment_method_type'],
        unique=False,
    )
    
    op.create_index(
        'ix_payments_created_at',
        'payments',
        ['created_at'],
        unique=False,
    )
    
    # Composite index for order payments
    op.create_index(
        'ix_payments_order_status',
        'payments',
        ['order_id', 'status'],
        unique=False,
    )
    
    # Composite index for status-based queries
    op.create_index(
        'ix_payments_status_created',
        'payments',
        ['status', 'created_at'],
        unique=False,
    )
    
    # Partial index for active (non-deleted) payments
    op.create_index(
        'ix_payments_active_only',
        'payments',
        ['order_id', 'status', 'created_at'],
        unique=False,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )
    
    # GIN index for metadata JSONB queries
    op.create_index(
        'ix_payments_metadata_gin',
        'payments',
        ['metadata'],
        unique=False,
        postgresql_using='gin',
    )
    
    # Create payment_status_history table
    op.create_table(
        'payment_status_history',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique history record identifier',
        ),
        sa.Column(
            'payment_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Payment identifier',
        ),
        sa.Column(
            'from_status',
            postgresql.ENUM(
                'pending',
                'processing',
                'requires_action',
                'succeeded',
                'failed',
                'cancelled',
                'refunded',
                'partially_refunded',
                name='payment_status',
                create_type=False,
            ),
            nullable=True,
            comment='Previous payment status',
        ),
        sa.Column(
            'to_status',
            postgresql.ENUM(
                'pending',
                'processing',
                'requires_action',
                'succeeded',
                'failed',
                'cancelled',
                'refunded',
                'partially_refunded',
                name='payment_status',
                create_type=False,
            ),
            nullable=False,
            comment='New payment status',
        ),
        sa.Column(
            'reason',
            sa.String(length=500),
            nullable=True,
            comment='Reason for status change',
        ),
        sa.Column(
            'metadata',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Additional context',
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
        sa.PrimaryKeyConstraint('id', name='pk_payment_status_history'),
        sa.ForeignKeyConstraint(
            ['payment_id'],
            ['payments.id'],
            name='fk_payment_status_history_payment_id',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['created_by'],
            ['users.id'],
            name='fk_payment_status_history_created_by',
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['updated_by'],
            ['users.id'],
            name='fk_payment_status_history_updated_by',
            ondelete='SET NULL',
        ),
        comment='Payment status change audit trail',
    )
    
    # Create indexes for payment_status_history
    op.create_index(
        'ix_payment_status_history_payment_id',
        'payment_status_history',
        ['payment_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_payment_status_history_created_at',
        'payment_status_history',
        ['created_at'],
        unique=False,
    )
    
    # Composite index for payment history lookup
    op.create_index(
        'ix_payment_status_history_payment_created',
        'payment_status_history',
        ['payment_id', 'created_at'],
        unique=False,
    )
    
    # Composite index for status-based queries
    op.create_index(
        'ix_payment_status_history_to_status',
        'payment_status_history',
        ['to_status', 'created_at'],
        unique=False,
    )
    
    # GIN index for metadata JSONB queries
    op.create_index(
        'ix_payment_status_history_metadata_gin',
        'payment_status_history',
        ['metadata'],
        unique=False,
        postgresql_using='gin',
    )


def downgrade() -> None:
    """
    Downgrade database schema by removing payment models.
    
    Removes all indexes, constraints, and tables added in the upgrade.
    This operation is safe as it only removes newly added structures.
    """
    # Drop payment_status_history table
    op.drop_index(
        'ix_payment_status_history_metadata_gin',
        table_name='payment_status_history',
        postgresql_using='gin',
    )
    
    op.drop_index(
        'ix_payment_status_history_to_status',
        table_name='payment_status_history',
    )
    
    op.drop_index(
        'ix_payment_status_history_payment_created',
        table_name='payment_status_history',
    )
    
    op.drop_index(
        'ix_payment_status_history_created_at',
        table_name='payment_status_history',
    )
    
    op.drop_index(
        'ix_payment_status_history_payment_id',
        table_name='payment_status_history',
    )
    
    op.drop_table('payment_status_history')
    
    # Drop payments table
    op.drop_index(
        'ix_payments_metadata_gin',
        table_name='payments',
        postgresql_using='gin',
    )
    
    op.drop_index(
        'ix_payments_active_only',
        table_name='payments',
        postgresql_where=sa.text('deleted_at IS NULL'),
    )
    
    op.drop_index(
        'ix_payments_status_created',
        table_name='payments',
    )
    
    op.drop_index(
        'ix_payments_order_status',
        table_name='payments',
    )
    
    op.drop_index(
        'ix_payments_created_at',
        table_name='payments',
    )
    
    op.drop_index(
        'ix_payments_payment_method_type',
        table_name='payments',
    )
    
    op.drop_index(
        'ix_payments_status',
        table_name='payments',
    )
    
    op.drop_index(
        'ix_payments_stripe_payment_intent_id',
        table_name='payments',
    )
    
    op.drop_index(
        'ix_payments_order_id',
        table_name='payments',
    )
    
    op.drop_table('payments')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS payment_method_type')
    op.execute('DROP TYPE IF EXISTS payment_status')