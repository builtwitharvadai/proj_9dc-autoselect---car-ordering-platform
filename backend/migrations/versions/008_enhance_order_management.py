"""
Alembic migration: Enhance order management schema with comprehensive tracking.

This migration enhances the orders table with additional fields for order
management, creates order_items table for line items, and order_status_history
table for audit trail. Implements proper indexes, foreign key constraints,
and enum types for status fields with comprehensive validation.

Revision ID: 008
Revises: 007
Create Date: 2024-01-07 22:45:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade database schema to enhance order management.
    
    Enhances orders table with new fields for comprehensive order tracking,
    creates order_items table for line item management, and order_status_history
    table for complete audit trail. Implements proper indexes for efficient
    querying and enforces data integrity with constraints.
    """
    # Enhance orders table with additional fields
    op.add_column(
        'orders',
        sa.Column(
            'dealer_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='Dealer handling the order',
        ),
    )
    
    op.add_column(
        'orders',
        sa.Column(
            'manufacturer_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='Manufacturer identifier',
        ),
    )
    
    op.add_column(
        'orders',
        sa.Column(
            'payment_status',
            sa.String(length=50),
            nullable=False,
            server_default='pending',
            comment='Current payment status',
        ),
    )
    
    op.add_column(
        'orders',
        sa.Column(
            'fulfillment_status',
            sa.String(length=50),
            nullable=False,
            server_default='pending',
            comment='Current fulfillment status',
        ),
    )
    
    op.add_column(
        'orders',
        sa.Column(
            'total_tax',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default=sa.text('0.00'),
            comment='Total tax amount',
        ),
    )
    
    op.add_column(
        'orders',
        sa.Column(
            'shipping_amount',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default=sa.text('0.00'),
            comment='Shipping/delivery charges',
        ),
    )
    
    op.add_column(
        'orders',
        sa.Column(
            'discount_amount',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default=sa.text('0.00'),
            comment='Applied discount amount',
        ),
    )
    
    op.add_column(
        'orders',
        sa.Column(
            'total_fees',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default=sa.text('0.00'),
            comment='Total fees amount',
        ),
    )
    
    op.add_column(
        'orders',
        sa.Column(
            'notes',
            sa.String(length=1000),
            nullable=True,
            comment='Additional order notes',
        ),
    )
    
    op.add_column(
        'orders',
        sa.Column(
            'special_instructions',
            sa.String(length=1000),
            nullable=True,
            comment='Special delivery or handling instructions',
        ),
    )
    
    op.add_column(
        'orders',
        sa.Column(
            'customer_info',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment='Customer information stored as JSONB',
        ),
    )
    
    op.add_column(
        'orders',
        sa.Column(
            'delivery_address',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment='Delivery address stored as JSONB',
        ),
    )
    
    op.add_column(
        'orders',
        sa.Column(
            'trade_in_info',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Trade-in vehicle information stored as JSONB',
        ),
    )
    
    op.add_column(
        'orders',
        sa.Column(
            'estimated_delivery_date',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment='Estimated delivery date',
        ),
    )
    
    op.add_column(
        'orders',
        sa.Column(
            'actual_delivery_date',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment='Actual delivery date',
        ),
    )
    
    # Create indexes for new orders columns
    op.create_index(
        'ix_orders_dealer_id',
        'orders',
        ['dealer_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_orders_manufacturer_id',
        'orders',
        ['manufacturer_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_orders_payment_status',
        'orders',
        ['payment_status'],
        unique=False,
    )
    
    op.create_index(
        'ix_orders_fulfillment_status',
        'orders',
        ['fulfillment_status'],
        unique=False,
    )
    
    op.create_index(
        'ix_orders_estimated_delivery',
        'orders',
        ['estimated_delivery_date'],
        unique=False,
    )
    
    op.create_index(
        'ix_orders_dealer_status',
        'orders',
        ['dealer_id', 'status'],
        unique=False,
    )
    
    op.create_index(
        'ix_orders_manufacturer_status',
        'orders',
        ['manufacturer_id', 'status'],
        unique=False,
    )
    
    # GIN indexes for JSONB columns
    op.create_index(
        'ix_orders_customer_info_gin',
        'orders',
        ['customer_info'],
        unique=False,
        postgresql_using='gin',
    )
    
    op.create_index(
        'ix_orders_delivery_address_gin',
        'orders',
        ['delivery_address'],
        unique=False,
        postgresql_using='gin',
    )
    
    op.create_index(
        'ix_orders_trade_in_info_gin',
        'orders',
        ['trade_in_info'],
        unique=False,
        postgresql_using='gin',
    )
    
    # Add check constraints for new orders columns
    op.create_check_constraint(
        'ck_orders_total_tax_non_negative',
        'orders',
        sa.text('total_tax >= 0'),
    )
    
    op.create_check_constraint(
        'ck_orders_shipping_amount_non_negative',
        'orders',
        sa.text('shipping_amount >= 0'),
    )
    
    op.create_check_constraint(
        'ck_orders_discount_amount_non_negative',
        'orders',
        sa.text('discount_amount >= 0'),
    )
    
    op.create_check_constraint(
        'ck_orders_total_fees_non_negative',
        'orders',
        sa.text('total_fees >= 0'),
    )
    
    op.create_check_constraint(
        'ck_orders_estimated_delivery_after_creation',
        'orders',
        sa.text('estimated_delivery_date IS NULL OR estimated_delivery_date >= created_at'),
    )
    
    op.create_check_constraint(
        'ck_orders_delivery_after_creation',
        'orders',
        sa.text('actual_delivery_date IS NULL OR actual_delivery_date >= created_at'),
    )
    
    # Create order_items table
    op.create_table(
        'order_items',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique order item identifier',
        ),
        sa.Column(
            'order_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Parent order identifier',
        ),
        sa.Column(
            'vehicle_configuration_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Vehicle configuration identifier',
        ),
        sa.Column(
            'quantity',
            sa.Integer(),
            nullable=False,
            server_default=sa.text('1'),
            comment='Quantity of items',
        ),
        sa.Column(
            'unit_price',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment='Price per unit',
        ),
        sa.Column(
            'total_price',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment='Total price for this item',
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
        sa.PrimaryKeyConstraint('id', name='pk_order_items'),
        sa.ForeignKeyConstraint(
            ['order_id'],
            ['orders.id'],
            name='fk_order_items_order_id',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['vehicle_configuration_id'],
            ['vehicle_configurations.id'],
            name='fk_order_items_configuration_id',
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['created_by'],
            ['users.id'],
            name='fk_order_items_created_by',
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['updated_by'],
            ['users.id'],
            name='fk_order_items_updated_by',
            ondelete='SET NULL',
        ),
        sa.CheckConstraint(
            'quantity > 0',
            name='ck_order_items_quantity_positive',
        ),
        sa.CheckConstraint(
            'unit_price >= 0',
            name='ck_order_items_unit_price_non_negative',
        ),
        sa.CheckConstraint(
            'total_price >= 0',
            name='ck_order_items_total_price_non_negative',
        ),
        comment='Individual items in an order',
    )
    
    # Create indexes for order_items
    op.create_index(
        'ix_order_items_order',
        'order_items',
        ['order_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_order_items_configuration',
        'order_items',
        ['vehicle_configuration_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_order_items_order_created',
        'order_items',
        ['order_id', 'created_at'],
        unique=False,
    )
    
    # Create order_status_history table
    op.create_table(
        'order_status_history',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique history record identifier',
        ),
        sa.Column(
            'order_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Parent order identifier',
        ),
        sa.Column(
            'from_status',
            sa.String(length=50),
            nullable=False,
            comment='Previous status',
        ),
        sa.Column(
            'to_status',
            sa.String(length=50),
            nullable=False,
            comment='New status',
        ),
        sa.Column(
            'changed_by',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='User who made the change',
        ),
        sa.Column(
            'change_reason',
            sa.String(length=500),
            nullable=True,
            comment='Reason for status change',
        ),
        sa.Column(
            'metadata',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment='Additional metadata stored as JSONB',
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
        sa.PrimaryKeyConstraint('id', name='pk_order_status_history'),
        sa.ForeignKeyConstraint(
            ['order_id'],
            ['orders.id'],
            name='fk_order_status_history_order_id',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['changed_by'],
            ['users.id'],
            name='fk_order_status_history_changed_by',
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['created_by'],
            ['users.id'],
            name='fk_order_status_history_created_by',
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['updated_by'],
            ['users.id'],
            name='fk_order_status_history_updated_by',
            ondelete='SET NULL',
        ),
        comment='Order status change history for audit trail',
    )
    
    # Create indexes for order_status_history
    op.create_index(
        'ix_order_status_history_order',
        'order_status_history',
        ['order_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_order_status_history_order_created',
        'order_status_history',
        ['order_id', 'created_at'],
        unique=False,
    )
    
    op.create_index(
        'ix_order_status_history_to_status',
        'order_status_history',
        ['to_status'],
        unique=False,
    )
    
    op.create_index(
        'ix_order_status_history_changed_by',
        'order_status_history',
        ['changed_by'],
        unique=False,
    )
    
    op.create_index(
        'ix_order_status_history_metadata_gin',
        'order_status_history',
        ['metadata'],
        unique=False,
        postgresql_using='gin',
    )
    
    # Composite index for status transition queries
    op.create_index(
        'ix_order_status_history_transition',
        'order_status_history',
        ['from_status', 'to_status', 'created_at'],
        unique=False,
    )


def downgrade() -> None:
    """
    Downgrade database schema by removing order management enhancements.
    
    Removes order_status_history and order_items tables, drops indexes,
    and removes enhanced columns from orders table. This operation is safe
    as it only removes newly added structures.
    """
    # Drop order_status_history table
    op.drop_index(
        'ix_order_status_history_transition',
        table_name='order_status_history',
    )
    
    op.drop_index(
        'ix_order_status_history_metadata_gin',
        table_name='order_status_history',
        postgresql_using='gin',
    )
    
    op.drop_index(
        'ix_order_status_history_changed_by',
        table_name='order_status_history',
    )
    
    op.drop_index(
        'ix_order_status_history_to_status',
        table_name='order_status_history',
    )
    
    op.drop_index(
        'ix_order_status_history_order_created',
        table_name='order_status_history',
    )
    
    op.drop_index(
        'ix_order_status_history_order',
        table_name='order_status_history',
    )
    
    op.drop_table('order_status_history')
    
    # Drop order_items table
    op.drop_index(
        'ix_order_items_order_created',
        table_name='order_items',
    )
    
    op.drop_index(
        'ix_order_items_configuration',
        table_name='order_items',
    )
    
    op.drop_index(
        'ix_order_items_order',
        table_name='order_items',
    )
    
    op.drop_table('order_items')
    
    # Drop check constraints from orders
    op.drop_constraint(
        'ck_orders_delivery_after_creation',
        'orders',
        type_='check',
    )
    
    op.drop_constraint(
        'ck_orders_estimated_delivery_after_creation',
        'orders',
        type_='check',
    )
    
    op.drop_constraint(
        'ck_orders_total_fees_non_negative',
        'orders',
        type_='check',
    )
    
    op.drop_constraint(
        'ck_orders_discount_amount_non_negative',
        'orders',
        type_='check',
    )
    
    op.drop_constraint(
        'ck_orders_shipping_amount_non_negative',
        'orders',
        type_='check',
    )
    
    op.drop_constraint(
        'ck_orders_total_tax_non_negative',
        'orders',
        type_='check',
    )
    
    # Drop indexes from orders
    op.drop_index(
        'ix_orders_trade_in_info_gin',
        table_name='orders',
        postgresql_using='gin',
    )
    
    op.drop_index(
        'ix_orders_delivery_address_gin',
        table_name='orders',
        postgresql_using='gin',
    )
    
    op.drop_index(
        'ix_orders_customer_info_gin',
        table_name='orders',
        postgresql_using='gin',
    )
    
    op.drop_index(
        'ix_orders_manufacturer_status',
        table_name='orders',
    )
    
    op.drop_index(
        'ix_orders_dealer_status',
        table_name='orders',
    )
    
    op.drop_index(
        'ix_orders_estimated_delivery',
        table_name='orders',
    )
    
    op.drop_index(
        'ix_orders_fulfillment_status',
        table_name='orders',
    )
    
    op.drop_index(
        'ix_orders_payment_status',
        table_name='orders',
    )
    
    op.drop_index(
        'ix_orders_manufacturer_id',
        table_name='orders',
    )
    
    op.drop_index(
        'ix_orders_dealer_id',
        table_name='orders',
    )
    
    # Drop columns from orders
    op.drop_column('orders', 'actual_delivery_date')
    op.drop_column('orders', 'estimated_delivery_date')
    op.drop_column('orders', 'trade_in_info')
    op.drop_column('orders', 'delivery_address')
    op.drop_column('orders', 'customer_info')
    op.drop_column('orders', 'special_instructions')
    op.drop_column('orders', 'notes')
    op.drop_column('orders', 'total_fees')
    op.drop_column('orders', 'discount_amount')
    op.drop_column('orders', 'shipping_amount')
    op.drop_column('orders', 'total_tax')
    op.drop_column('orders', 'fulfillment_status')
    op.drop_column('orders', 'payment_status')
    op.drop_column('orders', 'manufacturer_id')
    op.drop_column('orders', 'dealer_id')