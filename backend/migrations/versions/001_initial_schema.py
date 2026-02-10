"""
Alembic migration: Initial database schema creation.

This migration creates the foundational database tables for the car ordering
platform including users, vehicles, vehicle configurations, inventory items,
and orders. Implements proper indexing, constraints, and relationships.

Revision ID: 001
Revises: None
Create Date: 2024-01-07 20:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create initial database schema.
    
    Creates the foundational tables for the car ordering platform:
    - users: User accounts with authentication and authorization
    - vehicles: Vehicle catalog with specifications and pricing
    - vehicle_configurations: Custom vehicle configurations
    - inventory_items: Inventory tracking across dealerships
    - orders: Customer orders and fulfillment tracking
    
    Note: Enum types are NOT created as PostgreSQL native enums because the models
    use native_enum=False, which stores values as VARCHAR with check constraints.
    """
    # =========================================================================
    # Create users table
    # =========================================================================
    op.create_table(
        'users',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique user identifier',
        ),
        sa.Column(
            'email',
            sa.String(255),
            nullable=False,
            unique=True,
            comment='User email address (unique, case-insensitive)',
        ),
        sa.Column(
            'password_hash',
            sa.String(255),
            nullable=False,
            comment='Bcrypt hashed password',
        ),
        sa.Column(
            'first_name',
            sa.String(100),
            nullable=False,
            comment='User first name',
        ),
        sa.Column(
            'last_name',
            sa.String(100),
            nullable=False,
            comment='User last name',
        ),
        sa.Column(
            'role',
            sa.Enum('customer', 'sales', 'admin', 'super_admin', name='user_role', native_enum=False, create_constraint=True),
            nullable=False,
            server_default='customer',
            comment='User role for access control',
        ),
        sa.Column(
            'is_active',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
            comment='Account active status',
        ),
        sa.Column(
            'is_verified',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
            comment='Email verification status',
        ),
        sa.Column(
            'last_login_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Timestamp of last successful login',
        ),
        sa.Column(
            'failed_login_attempts',
            sa.Integer(),
            nullable=False,
            server_default=sa.text('0'),
            comment='Counter for failed login attempts',
        ),
        sa.Column(
            'locked_until',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Account lock timestamp for security',
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment='Timestamp when record was created',
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            comment='Timestamp when record was last updated',
        ),
        sa.Column(
            'created_by',
            sa.String(255),
            nullable=True,
            comment='User ID who created the record',
        ),
        sa.Column(
            'updated_by',
            sa.String(255),
            nullable=True,
            comment='User ID who last updated the record',
        ),
        sa.Column(
            'deleted_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Timestamp when record was soft deleted',
        ),
        comment='User accounts with authentication and authorization',
    )
    
    # Users table indexes
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_role', 'users', ['role'])
    op.create_index('ix_users_is_active', 'users', ['is_active'])
    op.create_index('ix_users_is_verified', 'users', ['is_verified'])
    op.create_index('ix_users_locked_until', 'users', ['locked_until'])
    op.create_index(
        'ix_users_email_lower',
        'users',
        ['email'],
        postgresql_ops={'email': 'text_pattern_ops'},
    )
    op.create_index('ix_users_role_active', 'users', ['role', 'is_active'])
    op.create_index('ix_users_active_verified', 'users', ['is_active', 'is_verified'])
    
    # Users table check constraints
    op.create_check_constraint(
        'ck_users_email_min_length',
        'users',
        sa.text('length(email) >= 3'),
    )
    op.create_check_constraint(
        'ck_users_first_name_min_length',
        'users',
        sa.text('length(first_name) >= 1'),
    )
    op.create_check_constraint(
        'ck_users_last_name_min_length',
        'users',
        sa.text('length(last_name) >= 1'),
    )
    op.create_check_constraint(
        'ck_users_failed_attempts_non_negative',
        'users',
        sa.text('failed_login_attempts >= 0'),
    )
    op.create_check_constraint(
        'ck_users_locked_until_after_creation',
        'users',
        sa.text('locked_until IS NULL OR locked_until > created_at'),
    )
    
    # =========================================================================
    # Create vehicles table
    # =========================================================================
    op.create_table(
        'vehicles',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique vehicle identifier',
        ),
        sa.Column(
            'make',
            sa.String(100),
            nullable=False,
            comment='Vehicle manufacturer',
        ),
        sa.Column(
            'model',
            sa.String(100),
            nullable=False,
            comment='Vehicle model name',
        ),
        sa.Column(
            'year',
            sa.Integer(),
            nullable=False,
            comment='Manufacturing year',
        ),
        sa.Column(
            'trim',
            sa.String(100),
            nullable=False,
            comment='Trim level or package',
        ),
        sa.Column(
            'vin',
            sa.String(17),
            nullable=True,
            unique=True,
            comment='Vehicle Identification Number',
        ),
        sa.Column(
            'body_style',
            sa.String(50),
            nullable=False,
            comment='Body style (Sedan, SUV, Truck, etc.)',
        ),
        sa.Column(
            'exterior_color',
            sa.String(50),
            nullable=False,
            comment='Exterior color name',
        ),
        sa.Column(
            'interior_color',
            sa.String(50),
            nullable=False,
            comment='Interior color name',
        ),
        sa.Column(
            'fuel_type',
            sa.String(50),
            nullable=False,
            comment='Fuel type (Gasoline, Diesel, Electric, Hybrid)',
        ),
        sa.Column(
            'transmission',
            sa.String(50),
            nullable=False,
            comment='Transmission type',
        ),
        sa.Column(
            'drivetrain',
            sa.String(20),
            nullable=False,
            comment='Drivetrain type (FWD, RWD, AWD, 4WD)',
        ),
        sa.Column(
            'engine',
            sa.String(100),
            nullable=False,
            comment='Engine specifications',
        ),
        sa.Column(
            'horsepower',
            sa.Integer(),
            nullable=True,
            comment='Engine horsepower',
        ),
        sa.Column(
            'torque',
            sa.Integer(),
            nullable=True,
            comment='Engine torque in lb-ft',
        ),
        sa.Column(
            'mpg_city',
            sa.Integer(),
            nullable=True,
            comment='City fuel economy in MPG',
        ),
        sa.Column(
            'mpg_highway',
            sa.Integer(),
            nullable=True,
            comment='Highway fuel economy in MPG',
        ),
        sa.Column(
            'seating_capacity',
            sa.Integer(),
            nullable=False,
            comment='Number of seats',
        ),
        sa.Column(
            'cargo_capacity',
            sa.Numeric(precision=6, scale=1),
            nullable=True,
            comment='Cargo capacity in cubic feet',
        ),
        sa.Column(
            'towing_capacity',
            sa.Integer(),
            nullable=True,
            comment='Towing capacity in pounds',
        ),
        sa.Column(
            'specifications',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment='Vehicle specifications in JSONB format',
        ),
        sa.Column(
            'base_price',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment='Base price before options',
        ),
        sa.Column(
            'msrp',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment='Manufacturer Suggested Retail Price',
        ),
        sa.Column(
            'invoice_price',
            sa.Numeric(precision=10, scale=2),
            nullable=True,
            comment='Dealer invoice price',
        ),
        sa.Column(
            'destination_charge',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default=sa.text('0.00'),
            comment='Destination and delivery charge',
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment='Timestamp when record was created',
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            comment='Timestamp when record was last updated',
        ),
        sa.Column(
            'created_by',
            sa.String(255),
            nullable=True,
            comment='User ID who created the record',
        ),
        sa.Column(
            'updated_by',
            sa.String(255),
            nullable=True,
            comment='User ID who last updated the record',
        ),
        sa.Column(
            'deleted_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Timestamp when record was soft deleted',
        ),
        comment='Vehicle inventory with specifications and pricing',
    )
    
    # Vehicles table indexes
    op.create_index('ix_vehicles_make', 'vehicles', ['make'])
    op.create_index('ix_vehicles_model', 'vehicles', ['model'])
    op.create_index('ix_vehicles_year', 'vehicles', ['year'])
    op.create_index('ix_vehicles_vin', 'vehicles', ['vin'], unique=True)
    op.create_index('ix_vehicles_body_style', 'vehicles', ['body_style'])
    op.create_index('ix_vehicles_fuel_type', 'vehicles', ['fuel_type'])
    op.create_index('ix_vehicles_base_price', 'vehicles', ['base_price'])
    op.create_index(
        'ix_vehicles_make_model_year',
        'vehicles',
        ['make', 'model', 'year'],
    )
    op.create_index(
        'ix_vehicles_year_make',
        'vehicles',
        ['year', 'make'],
    )
    op.create_index(
        'ix_vehicles_specifications_gin',
        'vehicles',
        ['specifications'],
        unique=False,
        postgresql_using='gin',
    )
    op.create_index(
        'ix_vehicles_active_search',
        'vehicles',
        ['make', 'model', 'year', 'deleted_at'],
    )
    op.create_index(
        'ix_vehicles_catalog_browse',
        'vehicles',
        ['body_style', 'fuel_type', 'year', 'base_price'],
    )
    
    # Vehicles table check constraints
    op.create_check_constraint(
        'ck_vehicles_make_min_length',
        'vehicles',
        sa.text('length(make) >= 1'),
    )
    op.create_check_constraint(
        'ck_vehicles_model_min_length',
        'vehicles',
        sa.text('length(model) >= 1'),
    )
    op.create_check_constraint(
        'ck_vehicles_trim_min_length',
        'vehicles',
        sa.text('length(trim) >= 1'),
    )
    op.create_check_constraint(
        'ck_vehicles_year_range',
        'vehicles',
        sa.text('year >= 1900 AND year <= 2100'),
    )
    op.create_check_constraint(
        'ck_vehicles_base_price_non_negative',
        'vehicles',
        sa.text('base_price >= 0'),
    )
    op.create_check_constraint(
        'ck_vehicles_base_price_max',
        'vehicles',
        sa.text('base_price <= 10000000.00'),
    )
    op.create_check_constraint(
        'ck_vehicles_msrp_non_negative',
        'vehicles',
        sa.text('msrp >= 0'),
    )
    op.create_check_constraint(
        'ck_vehicles_msrp_max',
        'vehicles',
        sa.text('msrp <= 10000000.00'),
    )
    op.create_check_constraint(
        'ck_vehicles_invoice_price_non_negative',
        'vehicles',
        sa.text('invoice_price IS NULL OR invoice_price >= 0'),
    )
    op.create_check_constraint(
        'ck_vehicles_destination_charge_non_negative',
        'vehicles',
        sa.text('destination_charge >= 0'),
    )
    op.create_check_constraint(
        'ck_vehicles_vin_length',
        'vehicles',
        sa.text('vin IS NULL OR length(vin) = 17'),
    )
    op.create_check_constraint(
        'ck_vehicles_horsepower_positive',
        'vehicles',
        sa.text('horsepower IS NULL OR horsepower > 0'),
    )
    op.create_check_constraint(
        'ck_vehicles_torque_positive',
        'vehicles',
        sa.text('torque IS NULL OR torque > 0'),
    )
    op.create_check_constraint(
        'ck_vehicles_mpg_city_positive',
        'vehicles',
        sa.text('mpg_city IS NULL OR mpg_city > 0'),
    )
    op.create_check_constraint(
        'ck_vehicles_mpg_highway_positive',
        'vehicles',
        sa.text('mpg_highway IS NULL OR mpg_highway > 0'),
    )
    op.create_check_constraint(
        'ck_vehicles_seating_capacity_range',
        'vehicles',
        sa.text('seating_capacity > 0 AND seating_capacity <= 20'),
    )
    op.create_check_constraint(
        'ck_vehicles_cargo_capacity_non_negative',
        'vehicles',
        sa.text('cargo_capacity IS NULL OR cargo_capacity >= 0'),
    )
    op.create_check_constraint(
        'ck_vehicles_towing_capacity_non_negative',
        'vehicles',
        sa.text('towing_capacity IS NULL OR towing_capacity >= 0'),
    )
    
    # =========================================================================
    # Create vehicle_configurations table
    # =========================================================================
    op.create_table(
        'vehicle_configurations',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique configuration identifier',
        ),
        sa.Column(
            'vehicle_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('vehicles.id', ondelete='CASCADE'),
            nullable=False,
            comment='Reference to base vehicle',
        ),
        sa.Column(
            'configuration_data',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment='Configuration details in JSONB format',
        ),
        sa.Column(
            'total_price',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment='Total price including all options',
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment='Timestamp when record was created',
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            comment='Timestamp when record was last updated',
        ),
        sa.Column(
            'created_by',
            sa.String(255),
            nullable=True,
            comment='User ID who created the record',
        ),
        sa.Column(
            'updated_by',
            sa.String(255),
            nullable=True,
            comment='User ID who last updated the record',
        ),
        sa.Column(
            'deleted_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Timestamp when record was soft deleted',
        ),
        comment='Vehicle configurations with custom options',
    )
    
    # Vehicle configurations table indexes
    op.create_index(
        'ix_vehicle_configurations_vehicle_id',
        'vehicle_configurations',
        ['vehicle_id'],
    )
    op.create_index(
        'ix_vehicle_configurations_data_gin',
        'vehicle_configurations',
        ['configuration_data'],
        unique=False,
        postgresql_using='gin',
    )
    
    # Vehicle configurations table check constraints
    op.create_check_constraint(
        'ck_vehicle_configurations_total_price_non_negative',
        'vehicle_configurations',
        sa.text('total_price >= 0'),
    )
    
    # =========================================================================
    # Create inventory_items table
    # =========================================================================
    op.create_table(
        'inventory_items',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique inventory item identifier',
        ),
        sa.Column(
            'vehicle_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('vehicles.id', ondelete='RESTRICT'),
            nullable=False,
            comment='Vehicle identifier',
        ),
        sa.Column(
            'dealership_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Dealership identifier',
        ),
        sa.Column(
            'vin',
            sa.String(17),
            nullable=False,
            unique=True,
            comment='Vehicle Identification Number',
        ),
        sa.Column(
            'status',
            sa.Enum(
                'available',
                'reserved',
                'sold',
                'in_transit',
                'in_preparation',
                'maintenance',
                'unavailable',
                name='inventory_status',
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            server_default='available',
            comment='Current inventory status',
        ),
        sa.Column(
            'location',
            sa.String(200),
            nullable=True,
            comment='Physical location within dealership',
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment='Timestamp when record was created',
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            comment='Timestamp when record was last updated',
        ),
        sa.Column(
            'created_by',
            sa.String(255),
            nullable=True,
            comment='User ID who created the record',
        ),
        sa.Column(
            'updated_by',
            sa.String(255),
            nullable=True,
            comment='User ID who last updated the record',
        ),
        sa.Column(
            'deleted_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Timestamp when record was soft deleted',
        ),
        comment='Vehicle inventory tracking across dealerships',
    )
    
    # Inventory items table indexes
    op.create_index('ix_inventory_items_vehicle_id', 'inventory_items', ['vehicle_id'])
    op.create_index('ix_inventory_items_dealership_id', 'inventory_items', ['dealership_id'])
    op.create_index('ix_inventory_items_vin', 'inventory_items', ['vin'], unique=True)
    op.create_index('ix_inventory_items_status', 'inventory_items', ['status'])
    op.create_index(
        'ix_inventory_dealership_status',
        'inventory_items',
        ['dealership_id', 'status'],
    )
    op.create_index(
        'ix_inventory_vehicle_status',
        'inventory_items',
        ['vehicle_id', 'status'],
    )
    op.create_index(
        'ix_inventory_available',
        'inventory_items',
        ['dealership_id', 'status', 'deleted_at'],
    )
    op.create_index(
        'ix_inventory_status_created',
        'inventory_items',
        ['status', 'created_at'],
    )
    op.create_index(
        'ix_inventory_dealership_location',
        'inventory_items',
        ['dealership_id', 'location'],
    )
    op.create_index(
        'ix_inventory_vehicle_availability',
        'inventory_items',
        ['vehicle_id', 'status', 'deleted_at'],
    )
    
    # Inventory items table check constraints
    op.create_check_constraint(
        'ck_inventory_vin_length',
        'inventory_items',
        sa.text('length(vin) = 17'),
    )
    op.create_check_constraint(
        'ck_inventory_vin_format',
        'inventory_items',
        sa.text("vin ~ '^[A-HJ-NPR-Z0-9]{17}$'"),
    )
    op.create_check_constraint(
        'ck_inventory_location_not_empty',
        'inventory_items',
        sa.text('location IS NULL OR length(location) > 0'),
    )
    
    # =========================================================================
    # Create orders table
    # =========================================================================
    op.create_table(
        'orders',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique order identifier',
        ),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            comment='User who placed the order',
        ),
        sa.Column(
            'vehicle_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('vehicles.id', ondelete='RESTRICT'),
            nullable=False,
            comment='Ordered vehicle identifier',
        ),
        sa.Column(
            'configuration_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('vehicle_configurations.id', ondelete='RESTRICT'),
            nullable=False,
            comment='Vehicle configuration identifier',
        ),
        sa.Column(
            'status',
            sa.Enum(
                'pending',
                'confirmed',
                'processing',
                'in_production',
                'ready_for_delivery',
                'in_transit',
                'delivered',
                'cancelled',
                'refunded',
                name='order_status',
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            server_default='pending',
            comment='Current order status',
        ),
        sa.Column(
            'total_amount',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment='Total order amount including all charges',
        ),
        sa.Column(
            'subtotal',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment='Subtotal before taxes and fees',
        ),
        sa.Column(
            'tax_amount',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default=sa.text('0.00'),
            comment='Tax amount',
        ),
        sa.Column(
            'order_number',
            sa.String(50),
            nullable=False,
            unique=True,
            comment='Human-readable order number',
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment='Timestamp when record was created',
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            comment='Timestamp when record was last updated',
        ),
        sa.Column(
            'created_by',
            sa.String(255),
            nullable=True,
            comment='User ID who created the record',
        ),
        sa.Column(
            'updated_by',
            sa.String(255),
            nullable=True,
            comment='User ID who last updated the record',
        ),
        sa.Column(
            'deleted_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Timestamp when record was soft deleted',
        ),
        comment='Customer orders and fulfillment tracking',
    )
    
    # Orders table indexes
    op.create_index('ix_orders_user_id', 'orders', ['user_id'])
    op.create_index('ix_orders_vehicle_id', 'orders', ['vehicle_id'])
    op.create_index('ix_orders_configuration_id', 'orders', ['configuration_id'])
    op.create_index('ix_orders_status', 'orders', ['status'])
    op.create_index('ix_orders_order_number', 'orders', ['order_number'], unique=True)
    op.create_index(
        'ix_orders_user_status',
        'orders',
        ['user_id', 'status'],
    )
    op.create_index(
        'ix_orders_user_created',
        'orders',
        ['user_id', 'created_at'],
    )
    op.create_index(
        'ix_orders_status_created',
        'orders',
        ['status', 'created_at'],
    )
    
    # Orders table check constraints
    op.create_check_constraint(
        'ck_orders_total_amount_non_negative',
        'orders',
        sa.text('total_amount >= 0'),
    )
    op.create_check_constraint(
        'ck_orders_subtotal_non_negative',
        'orders',
        sa.text('subtotal >= 0'),
    )
    op.create_check_constraint(
        'ck_orders_tax_amount_non_negative',
        'orders',
        sa.text('tax_amount >= 0'),
    )
    op.create_check_constraint(
        'ck_orders_order_number_not_empty',
        'orders',
        sa.text('length(order_number) >= 1'),
    )


def downgrade() -> None:
    """
    Drop all tables and enum types created in the upgrade.
    
    Drops tables in reverse order of creation to maintain referential integrity.
    """
    # Drop tables in reverse order of creation
    op.drop_table('orders')
    op.drop_table('inventory_items')
    op.drop_table('vehicle_configurations')
    op.drop_table('vehicles')
    op.drop_table('users')
    
    # Note: No enum types to drop since native_enum=False stores values as VARCHAR
