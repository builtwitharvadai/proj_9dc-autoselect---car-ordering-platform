"""
Alembic migration: Enhance vehicle catalog with advanced search capabilities.

This migration adds comprehensive columns to vehicle and inventory tables for
enhanced catalog functionality including specifications, dimensions, features,
and availability tracking. Implements proper indexes for search optimization
and maintains data integrity with constraints.

Revision ID: 002
Revises: 001
Create Date: 2024-01-07 22:23:58.142466
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade database schema to enhance vehicle catalog functionality.
    
    Adds new columns to vehicles and inventory_items tables for comprehensive
    catalog management, search optimization, and availability tracking.
    Creates indexes for efficient querying and enforces data integrity.
    """
    # Enhance vehicles table with additional specifications
    op.add_column(
        'vehicles',
        sa.Column(
            'dimensions',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment='Vehicle dimensions (length, width, height, wheelbase)',
        )
    )
    
    op.add_column(
        'vehicles',
        sa.Column(
            'features',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment='Vehicle features and options',
        )
    )
    
    op.add_column(
        'vehicles',
        sa.Column(
            'safety_ratings',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Safety ratings from various organizations',
        )
    )
    
    op.add_column(
        'vehicles',
        sa.Column(
            'warranty_info',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Warranty information and coverage details',
        )
    )
    
    op.add_column(
        'vehicles',
        sa.Column(
            'availability_date',
            sa.Date(),
            nullable=True,
            comment='Expected availability date for pre-order vehicles',
        )
    )
    
    op.add_column(
        'vehicles',
        sa.Column(
            'is_featured',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
            comment='Whether vehicle is featured in catalog',
        )
    )
    
    op.add_column(
        'vehicles',
        sa.Column(
            'view_count',
            sa.Integer(),
            nullable=False,
            server_default=sa.text('0'),
            comment='Number of times vehicle has been viewed',
        )
    )
    
    op.add_column(
        'vehicles',
        sa.Column(
            'popularity_score',
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default=sa.text('0.00'),
            comment='Calculated popularity score for ranking',
        )
    )
    
    # Create GIN indexes for JSONB columns on vehicles
    op.create_index(
        'ix_vehicles_dimensions_gin',
        'vehicles',
        ['dimensions'],
        unique=False,
        postgresql_using='gin',
    )
    
    op.create_index(
        'ix_vehicles_features_gin',
        'vehicles',
        ['features'],
        unique=False,
        postgresql_using='gin',
    )
    
    op.create_index(
        'ix_vehicles_safety_ratings_gin',
        'vehicles',
        ['safety_ratings'],
        unique=False,
        postgresql_using='gin',
        postgresql_where=sa.text('safety_ratings IS NOT NULL'),
    )
    
    # Create indexes for catalog browsing and filtering
    op.create_index(
        'ix_vehicles_featured_popularity',
        'vehicles',
        ['is_featured', 'popularity_score'],
        unique=False,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )
    
    op.create_index(
        'ix_vehicles_availability_date',
        'vehicles',
        ['availability_date'],
        unique=False,
        postgresql_where=sa.text('availability_date IS NOT NULL AND deleted_at IS NULL'),
    )
    
    op.create_index(
        'ix_vehicles_view_count',
        'vehicles',
        ['view_count'],
        unique=False,
    )
    
    # Add check constraints for vehicles
    op.create_check_constraint(
        'ck_vehicles_view_count_non_negative',
        'vehicles',
        sa.text('view_count >= 0'),
    )
    
    op.create_check_constraint(
        'ck_vehicles_popularity_score_range',
        'vehicles',
        sa.text('popularity_score >= 0.00 AND popularity_score <= 100.00'),
    )
    
    # Enhance inventory_items table with availability tracking
    op.add_column(
        'inventory_items',
        sa.Column(
            'availability_status',
            sa.Enum(
                'AVAILABLE',
                'LOW_STOCK',
                'OUT_OF_STOCK',
                'DISCONTINUED',
                name='availabilitystatus',
                create_type=True,
            ),
            nullable=False,
            server_default='AVAILABLE',
            comment='Catalog availability status',
        )
    )
    
    op.add_column(
        'inventory_items',
        sa.Column(
            'stock_quantity',
            sa.Integer(),
            nullable=False,
            server_default=sa.text('0'),
            comment='Current stock quantity',
        )
    )
    
    op.add_column(
        'inventory_items',
        sa.Column(
            'reserved_quantity',
            sa.Integer(),
            nullable=False,
            server_default=sa.text('0'),
            comment='Quantity reserved for customers',
        )
    )
    
    op.add_column(
        'inventory_items',
        sa.Column(
            'low_stock_threshold',
            sa.Integer(),
            nullable=False,
            server_default=sa.text('5'),
            comment='Threshold for low stock warning',
        )
    )
    
    op.add_column(
        'inventory_items',
        sa.Column(
            'reorder_point',
            sa.Integer(),
            nullable=True,
            comment='Stock level at which to reorder',
        )
    )
    
    op.add_column(
        'inventory_items',
        sa.Column(
            'reorder_quantity',
            sa.Integer(),
            nullable=True,
            comment='Quantity to order when restocking',
        )
    )
    
    op.add_column(
        'inventory_items',
        sa.Column(
            'last_restocked_at',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment='Timestamp of last restock',
        )
    )
    
    op.add_column(
        'inventory_items',
        sa.Column(
            'expected_restock_date',
            sa.Date(),
            nullable=True,
            comment='Expected date for next restock',
        )
    )
    
    # Create indexes for inventory availability queries
    op.create_index(
        'ix_inventory_availability_status',
        'inventory_items',
        ['availability_status', 'dealership_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_inventory_stock_quantity',
        'inventory_items',
        ['stock_quantity', 'availability_status'],
        unique=False,
    )
    
    op.create_index(
        'ix_inventory_low_stock',
        'inventory_items',
        ['dealership_id', 'stock_quantity'],
        unique=False,
        postgresql_where=sa.text(
            'stock_quantity <= low_stock_threshold AND deleted_at IS NULL'
        ),
    )
    
    op.create_index(
        'ix_inventory_restock_needed',
        'inventory_items',
        ['expected_restock_date'],
        unique=False,
        postgresql_where=sa.text(
            'expected_restock_date IS NOT NULL AND deleted_at IS NULL'
        ),
    )
    
    # Add check constraints for inventory
    op.create_check_constraint(
        'ck_inventory_stock_quantity_non_negative',
        'inventory_items',
        sa.text('stock_quantity >= 0'),
    )
    
    op.create_check_constraint(
        'ck_inventory_reserved_quantity_non_negative',
        'inventory_items',
        sa.text('reserved_quantity >= 0'),
    )
    
    op.create_check_constraint(
        'ck_inventory_reserved_not_exceeds_stock',
        'inventory_items',
        sa.text('reserved_quantity <= stock_quantity'),
    )
    
    op.create_check_constraint(
        'ck_inventory_low_stock_threshold_non_negative',
        'inventory_items',
        sa.text('low_stock_threshold >= 0'),
    )
    
    op.create_check_constraint(
        'ck_inventory_reorder_point_positive',
        'inventory_items',
        sa.text('reorder_point IS NULL OR reorder_point > 0'),
    )
    
    op.create_check_constraint(
        'ck_inventory_reorder_quantity_positive',
        'inventory_items',
        sa.text('reorder_quantity IS NULL OR reorder_quantity > 0'),
    )


def downgrade() -> None:
    """
    Downgrade database schema by removing vehicle catalog enhancements.
    
    Removes all columns, indexes, and constraints added in the upgrade.
    This operation is safe as it only removes newly added columns.
    """
    # Drop inventory_items constraints
    op.drop_constraint(
        'ck_inventory_reorder_quantity_positive',
        'inventory_items',
        type_='check',
    )
    
    op.drop_constraint(
        'ck_inventory_reorder_point_positive',
        'inventory_items',
        type_='check',
    )
    
    op.drop_constraint(
        'ck_inventory_low_stock_threshold_non_negative',
        'inventory_items',
        type_='check',
    )
    
    op.drop_constraint(
        'ck_inventory_reserved_not_exceeds_stock',
        'inventory_items',
        type_='check',
    )
    
    op.drop_constraint(
        'ck_inventory_reserved_quantity_non_negative',
        'inventory_items',
        type_='check',
    )
    
    op.drop_constraint(
        'ck_inventory_stock_quantity_non_negative',
        'inventory_items',
        type_='check',
    )
    
    # Drop inventory_items indexes
    op.drop_index(
        'ix_inventory_restock_needed',
        table_name='inventory_items',
        postgresql_where=sa.text(
            'expected_restock_date IS NOT NULL AND deleted_at IS NULL'
        ),
    )
    
    op.drop_index(
        'ix_inventory_low_stock',
        table_name='inventory_items',
        postgresql_where=sa.text(
            'stock_quantity <= low_stock_threshold AND deleted_at IS NULL'
        ),
    )
    
    op.drop_index(
        'ix_inventory_stock_quantity',
        table_name='inventory_items',
    )
    
    op.drop_index(
        'ix_inventory_availability_status',
        table_name='inventory_items',
    )
    
    # Drop inventory_items columns
    op.drop_column('inventory_items', 'expected_restock_date')
    op.drop_column('inventory_items', 'last_restocked_at')
    op.drop_column('inventory_items', 'reorder_quantity')
    op.drop_column('inventory_items', 'reorder_point')
    op.drop_column('inventory_items', 'low_stock_threshold')
    op.drop_column('inventory_items', 'reserved_quantity')
    op.drop_column('inventory_items', 'stock_quantity')
    op.drop_column('inventory_items', 'availability_status')
    
    # Drop availability status enum type
    sa.Enum(name='availabilitystatus').drop(op.get_bind(), checkfirst=True)
    
    # Drop vehicles constraints
    op.drop_constraint(
        'ck_vehicles_popularity_score_range',
        'vehicles',
        type_='check',
    )
    
    op.drop_constraint(
        'ck_vehicles_view_count_non_negative',
        'vehicles',
        type_='check',
    )
    
    # Drop vehicles indexes
    op.drop_index(
        'ix_vehicles_view_count',
        table_name='vehicles',
    )
    
    op.drop_index(
        'ix_vehicles_availability_date',
        table_name='vehicles',
        postgresql_where=sa.text('availability_date IS NOT NULL AND deleted_at IS NULL'),
    )
    
    op.drop_index(
        'ix_vehicles_featured_popularity',
        table_name='vehicles',
        postgresql_where=sa.text('deleted_at IS NULL'),
    )
    
    op.drop_index(
        'ix_vehicles_safety_ratings_gin',
        table_name='vehicles',
        postgresql_using='gin',
        postgresql_where=sa.text('safety_ratings IS NOT NULL'),
    )
    
    op.drop_index(
        'ix_vehicles_features_gin',
        table_name='vehicles',
        postgresql_using='gin',
    )
    
    op.drop_index(
        'ix_vehicles_dimensions_gin',
        table_name='vehicles',
        postgresql_using='gin',
    )
    
    # Drop vehicles columns
    op.drop_column('vehicles', 'popularity_score')
    op.drop_column('vehicles', 'view_count')
    op.drop_column('vehicles', 'is_featured')
    op.drop_column('vehicles', 'availability_date')
    op.drop_column('vehicles', 'warranty_info')
    op.drop_column('vehicles', 'safety_ratings')
    op.drop_column('vehicles', 'features')
    op.drop_column('vehicles', 'dimensions')