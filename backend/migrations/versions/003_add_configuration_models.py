"""
Alembic migration: Add configuration models for vehicle options and packages.

This migration creates comprehensive tables for vehicle configuration management
including options, packages, and enhanced vehicle_configurations table with
proper indexes, foreign key constraints, and enum types for categories and statuses.

Revision ID: 003
Revises: 002
Create Date: 2024-01-07 22:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade database schema to add configuration models.
    
    Creates vehicle_options, packages, and enhances vehicle_configurations
    tables with comprehensive fields for configuration management, pricing
    calculations, and compatibility validation. Implements proper indexes
    for efficient querying and enforces data integrity with constraints.
    """
    # Create option_category_enum type
    op.execute("""
        CREATE TYPE option_category_enum AS ENUM (
            'exterior',
            'interior',
            'technology',
            'safety',
            'performance',
            'comfort',
            'package'
        )
    """)
    
    # Create configuration_status_enum type
    op.execute("""
        CREATE TYPE configuration_status_enum AS ENUM (
            'draft',
            'pending_validation',
            'validated',
            'invalid',
            'finalized'
        )
    """)
    
    # Create vehicle_options table
    op.create_table(
        'vehicle_options',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique option identifier',
        ),
        sa.Column(
            'vehicle_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Reference to base vehicle',
        ),
        sa.Column(
            'category',
            postgresql.ENUM(
                'exterior',
                'interior',
                'technology',
                'safety',
                'performance',
                'comfort',
                'package',
                name='option_category_enum',
                create_type=False,
            ),
            nullable=False,
            comment='Option category',
        ),
        sa.Column(
            'name',
            sa.String(length=255),
            nullable=False,
            comment='Option name',
        ),
        sa.Column(
            'description',
            sa.String(length=1000),
            nullable=False,
            comment='Detailed option description',
        ),
        sa.Column(
            'price',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment='Option price',
        ),
        sa.Column(
            'is_required',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
            comment='Whether option is required for vehicle',
        ),
        sa.Column(
            'mutually_exclusive_with',
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
            comment='Array of option IDs that cannot be selected together',
        ),
        sa.Column(
            'required_options',
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
            comment='Array of option IDs that must be selected with this option',
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
        sa.PrimaryKeyConstraint('id', name='pk_vehicle_options'),
        sa.ForeignKeyConstraint(
            ['vehicle_id'],
            ['vehicles.id'],
            name='fk_vehicle_options_vehicle_id',
            ondelete='CASCADE',
        ),
        sa.CheckConstraint(
            "length(name) >= 1",
            name='ck_vehicle_options_name_min_length',
        ),
        sa.CheckConstraint(
            "length(description) >= 1",
            name='ck_vehicle_options_description_min_length',
        ),
        sa.CheckConstraint(
            "price >= 0",
            name='ck_vehicle_options_price_non_negative',
        ),
        sa.CheckConstraint(
            "price <= 100000.00",
            name='ck_vehicle_options_price_max',
        ),
        comment='Vehicle options with categories, compatibility rules, and pricing',
    )
    
    # Create indexes for vehicle_options
    op.create_index(
        'ix_vehicle_options_vehicle_id',
        'vehicle_options',
        ['vehicle_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_vehicle_options_category',
        'vehicle_options',
        ['category'],
        unique=False,
    )
    
    op.create_index(
        'ix_vehicle_options_vehicle_category',
        'vehicle_options',
        ['vehicle_id', 'category'],
        unique=False,
    )
    
    op.create_index(
        'ix_vehicle_options_required',
        'vehicle_options',
        ['vehicle_id', 'is_required'],
        unique=False,
    )
    
    op.create_index(
        'ix_vehicle_options_price',
        'vehicle_options',
        ['price'],
        unique=False,
    )
    
    op.create_index(
        'ix_vehicle_options_mutually_exclusive_gin',
        'vehicle_options',
        ['mutually_exclusive_with'],
        unique=False,
        postgresql_using='gin',
    )
    
    op.create_index(
        'ix_vehicle_options_required_options_gin',
        'vehicle_options',
        ['required_options'],
        unique=False,
        postgresql_using='gin',
    )
    
    # Create packages table
    op.create_table(
        'packages',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique package identifier',
        ),
        sa.Column(
            'vehicle_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Reference to base vehicle',
        ),
        sa.Column(
            'name',
            sa.String(length=255),
            nullable=False,
            comment='Package name',
        ),
        sa.Column(
            'description',
            sa.String(length=1000),
            nullable=False,
            comment='Detailed package description',
        ),
        sa.Column(
            'base_price',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment='Package base price before discount',
        ),
        sa.Column(
            'discount_percentage',
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default=sa.text('0.00'),
            comment='Discount percentage applied to bundled options',
        ),
        sa.Column(
            'included_options',
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
            comment='Array of option IDs included in package',
        ),
        sa.Column(
            'trim_compatibility',
            postgresql.ARRAY(sa.String(length=100)),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
            comment='Array of compatible trim levels',
        ),
        sa.Column(
            'model_year_compatibility',
            postgresql.ARRAY(sa.Integer()),
            nullable=False,
            server_default=sa.text("'{}'::integer[]"),
            comment='Array of compatible model years',
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
        sa.PrimaryKeyConstraint('id', name='pk_packages'),
        sa.ForeignKeyConstraint(
            ['vehicle_id'],
            ['vehicles.id'],
            name='fk_packages_vehicle_id',
            ondelete='CASCADE',
        ),
        sa.CheckConstraint(
            "length(name) >= 1",
            name='ck_packages_name_min_length',
        ),
        sa.CheckConstraint(
            "length(description) >= 1",
            name='ck_packages_description_min_length',
        ),
        sa.CheckConstraint(
            "base_price >= 0",
            name='ck_packages_base_price_non_negative',
        ),
        sa.CheckConstraint(
            "base_price <= 100000.00",
            name='ck_packages_base_price_max',
        ),
        sa.CheckConstraint(
            "discount_percentage >= 0",
            name='ck_packages_discount_percentage_non_negative',
        ),
        sa.CheckConstraint(
            "discount_percentage <= 100.00",
            name='ck_packages_discount_percentage_max',
        ),
        sa.CheckConstraint(
            "array_length(included_options, 1) >= 1",
            name='ck_packages_included_options_min_length',
        ),
        comment='Option packages with bundled options and discount pricing',
    )
    
    # Create indexes for packages
    op.create_index(
        'ix_packages_vehicle_id',
        'packages',
        ['vehicle_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_packages_name',
        'packages',
        ['name'],
        unique=False,
    )
    
    op.create_index(
        'ix_packages_base_price',
        'packages',
        ['base_price'],
        unique=False,
    )
    
    op.create_index(
        'ix_packages_included_options_gin',
        'packages',
        ['included_options'],
        unique=False,
        postgresql_using='gin',
    )
    
    op.create_index(
        'ix_packages_trim_compatibility_gin',
        'packages',
        ['trim_compatibility'],
        unique=False,
        postgresql_using='gin',
    )
    
    op.create_index(
        'ix_packages_model_year_compatibility_gin',
        'packages',
        ['model_year_compatibility'],
        unique=False,
        postgresql_using='gin',
    )
    
    # Enhance vehicle_configurations table
    op.add_column(
        'vehicle_configurations',
        sa.Column(
            'selected_packages',
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
            comment='Array of package IDs included in configuration',
        ),
    )
    
    op.add_column(
        'vehicle_configurations',
        sa.Column(
            'base_price',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default=sa.text('0.00'),
            comment='Base vehicle price',
        ),
    )
    
    op.add_column(
        'vehicle_configurations',
        sa.Column(
            'options_price',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default=sa.text('0.00'),
            comment='Total price of selected options',
        ),
    )
    
    op.add_column(
        'vehicle_configurations',
        sa.Column(
            'packages_price',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default=sa.text('0.00'),
            comment='Total price of selected packages',
        ),
    )
    
    op.add_column(
        'vehicle_configurations',
        sa.Column(
            'discount_amount',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default=sa.text('0.00'),
            comment='Total discount amount applied',
        ),
    )
    
    op.add_column(
        'vehicle_configurations',
        sa.Column(
            'tax_amount',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default=sa.text('0.00'),
            comment='Tax amount calculated',
        ),
    )
    
    op.add_column(
        'vehicle_configurations',
        sa.Column(
            'destination_charge',
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default=sa.text('0.00'),
            comment='Destination and delivery charge',
        ),
    )
    
    op.add_column(
        'vehicle_configurations',
        sa.Column(
            'configuration_status',
            postgresql.ENUM(
                'draft',
                'pending_validation',
                'validated',
                'invalid',
                'finalized',
                name='configuration_status_enum',
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'draft'"),
            comment='Current status of configuration',
        ),
    )
    
    op.add_column(
        'vehicle_configurations',
        sa.Column(
            'is_valid',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
            comment='Whether configuration passes validation rules',
        ),
    )
    
    op.add_column(
        'vehicle_configurations',
        sa.Column(
            'validation_errors',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment='JSONB field storing validation error details',
        ),
    )
    
    # Create indexes for vehicle_configurations
    op.create_index(
        'ix_vehicle_configurations_packages_gin',
        'vehicle_configurations',
        ['selected_packages'],
        unique=False,
        postgresql_using='gin',
    )
    
    op.create_index(
        'ix_vehicle_configurations_validation_errors_gin',
        'vehicle_configurations',
        ['validation_errors'],
        unique=False,
        postgresql_using='gin',
    )
    
    op.create_index(
        'ix_vehicle_configurations_status',
        'vehicle_configurations',
        ['configuration_status'],
        unique=False,
    )
    
    op.create_index(
        'ix_vehicle_configurations_valid',
        'vehicle_configurations',
        ['is_valid'],
        unique=False,
    )
    
    op.create_index(
        'ix_vehicle_configurations_status_valid',
        'vehicle_configurations',
        ['configuration_status', 'is_valid'],
        unique=False,
    )
    
    # Add check constraints for vehicle_configurations
    op.create_check_constraint(
        'ck_vehicle_configurations_base_price_non_negative',
        'vehicle_configurations',
        sa.text('base_price >= 0'),
    )
    
    op.create_check_constraint(
        'ck_vehicle_configurations_base_price_max',
        'vehicle_configurations',
        sa.text('base_price <= 10000000.00'),
    )
    
    op.create_check_constraint(
        'ck_vehicle_configurations_options_price_non_negative',
        'vehicle_configurations',
        sa.text('options_price >= 0'),
    )
    
    op.create_check_constraint(
        'ck_vehicle_configurations_packages_price_non_negative',
        'vehicle_configurations',
        sa.text('packages_price >= 0'),
    )
    
    op.create_check_constraint(
        'ck_vehicle_configurations_discount_amount_non_negative',
        'vehicle_configurations',
        sa.text('discount_amount >= 0'),
    )
    
    op.create_check_constraint(
        'ck_vehicle_configurations_tax_amount_non_negative',
        'vehicle_configurations',
        sa.text('tax_amount >= 0'),
    )
    
    op.create_check_constraint(
        'ck_vehicle_configurations_destination_charge_non_negative',
        'vehicle_configurations',
        sa.text('destination_charge >= 0'),
    )


def downgrade() -> None:
    """
    Downgrade database schema by removing configuration models.
    
    Removes all columns, indexes, constraints, and tables added in the upgrade.
    This operation is safe as it only removes newly added structures.
    """
    # Drop check constraints from vehicle_configurations
    op.drop_constraint(
        'ck_vehicle_configurations_destination_charge_non_negative',
        'vehicle_configurations',
        type_='check',
    )
    
    op.drop_constraint(
        'ck_vehicle_configurations_tax_amount_non_negative',
        'vehicle_configurations',
        type_='check',
    )
    
    op.drop_constraint(
        'ck_vehicle_configurations_discount_amount_non_negative',
        'vehicle_configurations',
        type_='check',
    )
    
    op.drop_constraint(
        'ck_vehicle_configurations_packages_price_non_negative',
        'vehicle_configurations',
        type_='check',
    )
    
    op.drop_constraint(
        'ck_vehicle_configurations_options_price_non_negative',
        'vehicle_configurations',
        type_='check',
    )
    
    op.drop_constraint(
        'ck_vehicle_configurations_base_price_max',
        'vehicle_configurations',
        type_='check',
    )
    
    op.drop_constraint(
        'ck_vehicle_configurations_base_price_non_negative',
        'vehicle_configurations',
        type_='check',
    )
    
    # Drop indexes from vehicle_configurations
    op.drop_index(
        'ix_vehicle_configurations_status_valid',
        table_name='vehicle_configurations',
    )
    
    op.drop_index(
        'ix_vehicle_configurations_valid',
        table_name='vehicle_configurations',
    )
    
    op.drop_index(
        'ix_vehicle_configurations_status',
        table_name='vehicle_configurations',
    )
    
    op.drop_index(
        'ix_vehicle_configurations_validation_errors_gin',
        table_name='vehicle_configurations',
        postgresql_using='gin',
    )
    
    op.drop_index(
        'ix_vehicle_configurations_packages_gin',
        table_name='vehicle_configurations',
        postgresql_using='gin',
    )
    
    # Drop columns from vehicle_configurations
    op.drop_column('vehicle_configurations', 'validation_errors')
    op.drop_column('vehicle_configurations', 'is_valid')
    op.drop_column('vehicle_configurations', 'configuration_status')
    op.drop_column('vehicle_configurations', 'destination_charge')
    op.drop_column('vehicle_configurations', 'tax_amount')
    op.drop_column('vehicle_configurations', 'discount_amount')
    op.drop_column('vehicle_configurations', 'packages_price')
    op.drop_column('vehicle_configurations', 'options_price')
    op.drop_column('vehicle_configurations', 'base_price')
    op.drop_column('vehicle_configurations', 'selected_packages')
    
    # Drop packages table
    op.drop_index(
        'ix_packages_model_year_compatibility_gin',
        table_name='packages',
        postgresql_using='gin',
    )
    
    op.drop_index(
        'ix_packages_trim_compatibility_gin',
        table_name='packages',
        postgresql_using='gin',
    )
    
    op.drop_index(
        'ix_packages_included_options_gin',
        table_name='packages',
        postgresql_using='gin',
    )
    
    op.drop_index('ix_packages_base_price', table_name='packages')
    op.drop_index('ix_packages_name', table_name='packages')
    op.drop_index('ix_packages_vehicle_id', table_name='packages')
    
    op.drop_table('packages')
    
    # Drop vehicle_options table
    op.drop_index(
        'ix_vehicle_options_required_options_gin',
        table_name='vehicle_options',
        postgresql_using='gin',
    )
    
    op.drop_index(
        'ix_vehicle_options_mutually_exclusive_gin',
        table_name='vehicle_options',
        postgresql_using='gin',
    )
    
    op.drop_index('ix_vehicle_options_price', table_name='vehicle_options')
    op.drop_index('ix_vehicle_options_required', table_name='vehicle_options')
    op.drop_index('ix_vehicle_options_vehicle_category', table_name='vehicle_options')
    op.drop_index('ix_vehicle_options_category', table_name='vehicle_options')
    op.drop_index('ix_vehicle_options_vehicle_id', table_name='vehicle_options')
    
    op.drop_table('vehicle_options')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS configuration_status_enum')
    op.execute('DROP TYPE IF EXISTS option_category_enum')