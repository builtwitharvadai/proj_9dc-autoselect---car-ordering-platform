"""
Alembic migration: Add shopping cart models for session management.

This migration creates comprehensive tables for shopping cart functionality
including carts, cart_items, and promotional_codes tables with proper indexes,
foreign key constraints, and check constraints for data integrity.

Revision ID: 004
Revises: 003
Create Date: 2024-01-07 22:35:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade database schema to add shopping cart models.
    
    Creates carts, cart_items, and promotional_codes tables with comprehensive
    fields for cart management, inventory reservations, and promotional code
    handling. Implements proper indexes for efficient querying and enforces
    data integrity with constraints.
    """
    # Create carts table
    op.create_table(
        'carts',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique cart identifier',
        ),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='Foreign key to authenticated user (null for anonymous)',
        ),
        sa.Column(
            'session_id',
            sa.String(length=255),
            nullable=True,
            comment='Session identifier for anonymous users (null for authenticated)',
        ),
        sa.Column(
            'expires_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            comment='Cart expiration timestamp (7 days anonymous, 30 days authenticated)',
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
            'deleted_at',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment='Soft deletion timestamp',
        ),
        sa.PrimaryKeyConstraint('id', name='pk_carts'),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            name='fk_carts_user_id',
            ondelete='CASCADE',
        ),
        sa.CheckConstraint(
            "(user_id IS NOT NULL AND session_id IS NULL) OR "
            "(user_id IS NULL AND session_id IS NOT NULL)",
            name='ck_carts_user_or_session',
        ),
        sa.CheckConstraint(
            "expires_at > created_at",
            name='ck_carts_expires_after_created',
        ),
        sa.CheckConstraint(
            "session_id IS NULL OR length(session_id) >= 1",
            name='ck_carts_session_id_min_length',
        ),
        comment='Shopping carts with session management and expiration',
    )
    
    # Create indexes for carts
    op.create_index(
        'ix_carts_user_id',
        'carts',
        ['user_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_carts_session_id',
        'carts',
        ['session_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_carts_expires_at',
        'carts',
        ['expires_at'],
        unique=False,
    )
    
    op.create_index(
        'ix_carts_user_expires',
        'carts',
        ['user_id', 'expires_at'],
        unique=False,
    )
    
    op.create_index(
        'ix_carts_session_expires',
        'carts',
        ['session_id', 'expires_at'],
        unique=False,
    )
    
    # Create cart_items table
    op.create_table(
        'cart_items',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique cart item identifier',
        ),
        sa.Column(
            'cart_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Foreign key to parent cart',
        ),
        sa.Column(
            'vehicle_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Foreign key to vehicle',
        ),
        sa.Column(
            'configuration_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Foreign key to vehicle configuration',
        ),
        sa.Column(
            'quantity',
            sa.Integer(),
            nullable=False,
            server_default=sa.text('1'),
            comment='Number of items (default 1)',
        ),
        sa.Column(
            'price',
            sa.Numeric(precision=10, scale=2),
            nullable=True,
            comment='Cached price at time of addition',
        ),
        sa.Column(
            'reserved_until',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment='Inventory reservation expiration timestamp (15 minutes)',
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
            'deleted_at',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment='Soft deletion timestamp',
        ),
        sa.PrimaryKeyConstraint('id', name='pk_cart_items'),
        sa.ForeignKeyConstraint(
            ['cart_id'],
            ['carts.id'],
            name='fk_cart_items_cart_id',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['vehicle_id'],
            ['vehicles.id'],
            name='fk_cart_items_vehicle_id',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['configuration_id'],
            ['vehicle_configurations.id'],
            name='fk_cart_items_configuration_id',
            ondelete='CASCADE',
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name='ck_cart_items_quantity_positive',
        ),
        sa.CheckConstraint(
            "quantity <= 100",
            name='ck_cart_items_quantity_max',
        ),
        sa.CheckConstraint(
            "price IS NULL OR price >= 0",
            name='ck_cart_items_price_non_negative',
        ),
        sa.CheckConstraint(
            "price IS NULL OR price <= 10000000.00",
            name='ck_cart_items_price_max',
        ),
        sa.CheckConstraint(
            "reserved_until IS NULL OR reserved_until > created_at",
            name='ck_cart_items_reserved_after_created',
        ),
        comment='Cart items with inventory reservations and price caching',
    )
    
    # Create indexes for cart_items
    op.create_index(
        'ix_cart_items_cart_id',
        'cart_items',
        ['cart_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_cart_items_vehicle_id',
        'cart_items',
        ['vehicle_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_cart_items_configuration_id',
        'cart_items',
        ['configuration_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_cart_items_reserved_until',
        'cart_items',
        ['reserved_until'],
        unique=False,
    )
    
    op.create_index(
        'ix_cart_items_cart_vehicle',
        'cart_items',
        ['cart_id', 'vehicle_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_cart_items_vehicle_reserved',
        'cart_items',
        ['vehicle_id', 'reserved_until'],
        unique=False,
    )
    
    # Create promotional_codes table
    op.create_table(
        'promotional_codes',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique promotional code identifier',
        ),
        sa.Column(
            'code',
            sa.String(length=50),
            nullable=False,
            comment='Unique promotional code string',
        ),
        sa.Column(
            'discount_type',
            sa.String(length=20),
            nullable=False,
            comment='Type of discount: percentage or fixed_amount',
        ),
        sa.Column(
            'discount_value',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment='Discount value (percentage or fixed amount)',
        ),
        sa.Column(
            'minimum_order_amount',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default=sa.text('0.00'),
            comment='Minimum order amount required to use code',
        ),
        sa.Column(
            'maximum_discount',
            sa.Numeric(precision=10, scale=2),
            nullable=True,
            comment='Maximum discount amount (for percentage discounts)',
        ),
        sa.Column(
            'valid_from',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            comment='Start date of validity period',
        ),
        sa.Column(
            'valid_until',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            comment='End date of validity period',
        ),
        sa.Column(
            'usage_limit',
            sa.Integer(),
            nullable=True,
            comment='Maximum number of times code can be used (NULL = unlimited)',
        ),
        sa.Column(
            'usage_count',
            sa.Integer(),
            nullable=False,
            server_default=sa.text('0'),
            comment='Current number of times code has been used',
        ),
        sa.Column(
            'applicable_vehicles',
            postgresql.ARRAY(postgresql.UUID(as_uuid=False)),
            nullable=True,
            comment='List of vehicle IDs code applies to (NULL = all vehicles)',
        ),
        sa.Column(
            'is_active',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
            comment='Whether code is currently active',
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
            'deleted_at',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment='Soft deletion timestamp',
        ),
        sa.PrimaryKeyConstraint('id', name='pk_promotional_codes'),
        sa.UniqueConstraint('code', name='uq_promotional_codes_code'),
        sa.CheckConstraint(
            "discount_value > 0",
            name='ck_promotional_codes_discount_value_positive',
        ),
        sa.CheckConstraint(
            "minimum_order_amount >= 0",
            name='ck_promotional_codes_minimum_order_amount_non_negative',
        ),
        sa.CheckConstraint(
            "maximum_discount IS NULL OR maximum_discount > 0",
            name='ck_promotional_codes_maximum_discount_positive',
        ),
        sa.CheckConstraint(
            "usage_limit IS NULL OR usage_limit > 0",
            name='ck_promotional_codes_usage_limit_positive',
        ),
        sa.CheckConstraint(
            "usage_count >= 0",
            name='ck_promotional_codes_usage_count_non_negative',
        ),
        sa.CheckConstraint(
            "valid_until > valid_from",
            name='ck_promotional_codes_valid_date_range',
        ),
        sa.CheckConstraint(
            "(discount_type = 'percentage' AND discount_value <= 100) OR "
            "(discount_type = 'fixed_amount')",
            name='ck_promotional_codes_percentage_max_100',
        ),
        comment='Promotional codes for order discounts',
    )
    
    # Create indexes for promotional_codes
    op.create_index(
        'ix_promotional_codes_code',
        'promotional_codes',
        ['code'],
        unique=True,
    )
    
    op.create_index(
        'ix_promotional_codes_is_active',
        'promotional_codes',
        ['is_active'],
        unique=False,
    )
    
    op.create_index(
        'ix_promotional_codes_valid_from',
        'promotional_codes',
        ['valid_from'],
        unique=False,
    )
    
    op.create_index(
        'ix_promotional_codes_valid_until',
        'promotional_codes',
        ['valid_until'],
        unique=False,
    )
    
    op.create_index(
        'ix_promotional_codes_active_valid',
        'promotional_codes',
        ['is_active', 'valid_from', 'valid_until'],
        unique=False,
    )
    
    op.create_index(
        'ix_promotional_codes_applicable_vehicles_gin',
        'promotional_codes',
        ['applicable_vehicles'],
        unique=False,
        postgresql_using='gin',
    )


def downgrade() -> None:
    """
    Downgrade database schema by removing shopping cart models.
    
    Removes all tables, indexes, and constraints added in the upgrade.
    This operation is safe as it only removes newly added structures.
    """
    # Drop promotional_codes table
    op.drop_index(
        'ix_promotional_codes_applicable_vehicles_gin',
        table_name='promotional_codes',
        postgresql_using='gin',
    )
    
    op.drop_index(
        'ix_promotional_codes_active_valid',
        table_name='promotional_codes',
    )
    
    op.drop_index(
        'ix_promotional_codes_valid_until',
        table_name='promotional_codes',
    )
    
    op.drop_index(
        'ix_promotional_codes_valid_from',
        table_name='promotional_codes',
    )
    
    op.drop_index(
        'ix_promotional_codes_is_active',
        table_name='promotional_codes',
    )
    
    op.drop_index(
        'ix_promotional_codes_code',
        table_name='promotional_codes',
    )
    
    op.drop_table('promotional_codes')
    
    # Drop cart_items table
    op.drop_index(
        'ix_cart_items_vehicle_reserved',
        table_name='cart_items',
    )
    
    op.drop_index(
        'ix_cart_items_cart_vehicle',
        table_name='cart_items',
    )
    
    op.drop_index(
        'ix_cart_items_reserved_until',
        table_name='cart_items',
    )
    
    op.drop_index(
        'ix_cart_items_configuration_id',
        table_name='cart_items',
    )
    
    op.drop_index(
        'ix_cart_items_vehicle_id',
        table_name='cart_items',
    )
    
    op.drop_index(
        'ix_cart_items_cart_id',
        table_name='cart_items',
    )
    
    op.drop_table('cart_items')
    
    # Drop carts table
    op.drop_index(
        'ix_carts_session_expires',
        table_name='carts',
    )
    
    op.drop_index(
        'ix_carts_user_expires',
        table_name='carts',
    )
    
    op.drop_index(
        'ix_carts_expires_at',
        table_name='carts',
    )
    
    op.drop_index(
        'ix_carts_session_id',
        table_name='carts',
    )
    
    op.drop_index(
        'ix_carts_user_id',
        table_name='carts',
    )
    
    op.drop_table('carts')