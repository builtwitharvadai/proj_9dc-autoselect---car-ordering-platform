"""
Alembic migration: Add recommendation and dealer management tables.

This migration creates comprehensive tables for package recommendations and
dealer configuration management including recommendation events tracking,
popular configurations analytics, and dealer-specific option/package settings
with proper indexes, foreign key constraints, and data validation.

Revision ID: 006
Revises: 005
Create Date: 2024-01-07 22:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade database schema to add recommendation and dealer management tables.
    
    Creates dealer_option_configs, dealer_package_configs, recommendation_events,
    and popular_configurations tables with comprehensive fields for analytics,
    dealer customization, and recommendation tracking. Implements proper indexes
    for efficient querying and enforces data integrity with constraints.
    """
    # Create recommendation_event_type enum
    op.execute("""
        CREATE TYPE recommendation_event_type AS ENUM (
            'viewed',
            'clicked',
            'added_to_cart',
            'purchased',
            'dismissed',
            'shared'
        )
    """)
    
    # Create dealer_option_configs table
    op.create_table(
        'dealer_option_configs',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique configuration identifier',
        ),
        sa.Column(
            'dealer_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Reference to dealer',
        ),
        sa.Column(
            'option_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Reference to vehicle option',
        ),
        sa.Column(
            'is_available',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
            comment='Whether option is available for this dealer',
        ),
        sa.Column(
            'custom_price',
            sa.Numeric(precision=10, scale=2),
            nullable=True,
            comment='Dealer-specific price override',
        ),
        sa.Column(
            'effective_from',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
            comment='Start date for configuration validity',
        ),
        sa.Column(
            'effective_to',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment='End date for configuration validity',
        ),
        sa.Column(
            'region',
            sa.String(length=100),
            nullable=True,
            comment='Geographic region for availability',
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
        sa.PrimaryKeyConstraint('id', name='pk_dealer_option_configs'),
        sa.ForeignKeyConstraint(
            ['option_id'],
            ['vehicle_options.id'],
            name='fk_dealer_option_configs_option_id',
            ondelete='CASCADE',
        ),
        sa.UniqueConstraint(
            'dealer_id',
            'option_id',
            'effective_from',
            name='uq_dealer_option_configs_dealer_option_effective',
        ),
        sa.CheckConstraint(
            "custom_price IS NULL OR custom_price >= 0",
            name='ck_dealer_option_configs_custom_price_non_negative',
        ),
        sa.CheckConstraint(
            "custom_price IS NULL OR custom_price <= 100000.00",
            name='ck_dealer_option_configs_custom_price_max',
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name='ck_dealer_option_configs_effective_dates_valid',
        ),
        sa.CheckConstraint(
            "region IS NULL OR length(region) >= 1",
            name='ck_dealer_option_configs_region_min_length',
        ),
        comment='Dealer-specific option configurations with pricing and availability',
    )
    
    # Create indexes for dealer_option_configs
    op.create_index(
        'ix_dealer_option_configs_dealer_id',
        'dealer_option_configs',
        ['dealer_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_dealer_option_configs_option_id',
        'dealer_option_configs',
        ['option_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_dealer_option_configs_dealer_available',
        'dealer_option_configs',
        ['dealer_id', 'is_available'],
        unique=False,
    )
    
    op.create_index(
        'ix_dealer_option_configs_effective_dates',
        'dealer_option_configs',
        ['effective_from', 'effective_to'],
        unique=False,
    )
    
    op.create_index(
        'ix_dealer_option_configs_region',
        'dealer_option_configs',
        ['region'],
        unique=False,
    )
    
    op.create_index(
        'ix_dealer_option_configs_active',
        'dealer_option_configs',
        ['dealer_id', 'is_available', 'effective_from', 'effective_to'],
        unique=False,
    )
    
    # Create dealer_package_configs table
    op.create_table(
        'dealer_package_configs',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique configuration identifier',
        ),
        sa.Column(
            'dealer_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Reference to dealer',
        ),
        sa.Column(
            'package_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Reference to vehicle package',
        ),
        sa.Column(
            'is_available',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
            comment='Whether package is available for this dealer',
        ),
        sa.Column(
            'custom_price',
            sa.Numeric(precision=10, scale=2),
            nullable=True,
            comment='Dealer-specific price override',
        ),
        sa.Column(
            'effective_from',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
            comment='Start date for configuration validity',
        ),
        sa.Column(
            'effective_to',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment='End date for configuration validity',
        ),
        sa.Column(
            'region',
            sa.String(length=100),
            nullable=True,
            comment='Geographic region for availability',
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
        sa.PrimaryKeyConstraint('id', name='pk_dealer_package_configs'),
        sa.ForeignKeyConstraint(
            ['package_id'],
            ['packages.id'],
            name='fk_dealer_package_configs_package_id',
            ondelete='CASCADE',
        ),
        sa.UniqueConstraint(
            'dealer_id',
            'package_id',
            'effective_from',
            name='uq_dealer_package_configs_dealer_package_effective',
        ),
        sa.CheckConstraint(
            "custom_price IS NULL OR custom_price >= 0",
            name='ck_dealer_package_configs_custom_price_non_negative',
        ),
        sa.CheckConstraint(
            "custom_price IS NULL OR custom_price <= 100000.00",
            name='ck_dealer_package_configs_custom_price_max',
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name='ck_dealer_package_configs_effective_dates_valid',
        ),
        sa.CheckConstraint(
            "region IS NULL OR length(region) >= 1",
            name='ck_dealer_package_configs_region_min_length',
        ),
        comment='Dealer-specific package configurations with pricing and availability',
    )
    
    # Create indexes for dealer_package_configs
    op.create_index(
        'ix_dealer_package_configs_dealer_id',
        'dealer_package_configs',
        ['dealer_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_dealer_package_configs_package_id',
        'dealer_package_configs',
        ['package_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_dealer_package_configs_dealer_available',
        'dealer_package_configs',
        ['dealer_id', 'is_available'],
        unique=False,
    )
    
    op.create_index(
        'ix_dealer_package_configs_effective_dates',
        'dealer_package_configs',
        ['effective_from', 'effective_to'],
        unique=False,
    )
    
    op.create_index(
        'ix_dealer_package_configs_region',
        'dealer_package_configs',
        ['region'],
        unique=False,
    )
    
    op.create_index(
        'ix_dealer_package_configs_active',
        'dealer_package_configs',
        ['dealer_id', 'is_available', 'effective_from', 'effective_to'],
        unique=False,
    )
    
    # Create recommendation_events table
    op.create_table(
        'recommendation_events',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique event identifier',
        ),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='User who triggered the event',
        ),
        sa.Column(
            'session_id',
            sa.String(length=255),
            nullable=True,
            comment='Session identifier for anonymous tracking',
        ),
        sa.Column(
            'vehicle_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Vehicle being configured',
        ),
        sa.Column(
            'recommended_packages',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment='Recommended packages with scores and metadata',
        ),
        sa.Column(
            'selected_packages',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment='Packages user selected from recommendations',
        ),
        sa.Column(
            'event_type',
            postgresql.ENUM(
                'viewed',
                'clicked',
                'added_to_cart',
                'purchased',
                'dismissed',
                'shared',
                name='recommendation_event_type',
                create_type=False,
            ),
            nullable=False,
            comment='Type of recommendation event',
        ),
        sa.Column(
            'event_metadata',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment='Additional event context and metadata',
        ),
        sa.Column(
            'created_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
            comment='Event timestamp',
        ),
        sa.Column(
            'updated_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
            comment='Last modification timestamp',
        ),
        sa.PrimaryKeyConstraint('id', name='pk_recommendation_events'),
        sa.CheckConstraint(
            "user_id IS NOT NULL OR session_id IS NOT NULL",
            name='ck_recommendation_events_user_or_session',
        ),
        sa.CheckConstraint(
            "length(session_id) >= 1",
            name='ck_recommendation_events_session_id_min_length',
        ),
        comment='Recommendation event tracking for analytics',
    )
    
    # Create indexes for recommendation_events
    op.create_index(
        'ix_recommendation_events_user_id',
        'recommendation_events',
        ['user_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_recommendation_events_session_id',
        'recommendation_events',
        ['session_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_recommendation_events_vehicle_id',
        'recommendation_events',
        ['vehicle_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_recommendation_events_event_type',
        'recommendation_events',
        ['event_type'],
        unique=False,
    )
    
    op.create_index(
        'ix_recommendation_events_created_at',
        'recommendation_events',
        ['created_at'],
        unique=False,
    )
    
    op.create_index(
        'ix_recommendation_events_user_vehicle',
        'recommendation_events',
        ['user_id', 'vehicle_id', 'event_type'],
        unique=False,
    )
    
    op.create_index(
        'ix_recommendation_events_session',
        'recommendation_events',
        ['session_id', 'event_type', 'created_at'],
        unique=False,
    )
    
    op.create_index(
        'ix_recommendation_events_recommended_packages_gin',
        'recommendation_events',
        ['recommended_packages'],
        unique=False,
        postgresql_using='gin',
    )
    
    op.create_index(
        'ix_recommendation_events_selected_packages_gin',
        'recommendation_events',
        ['selected_packages'],
        unique=False,
        postgresql_using='gin',
    )
    
    op.create_index(
        'ix_recommendation_events_metadata_gin',
        'recommendation_events',
        ['event_metadata'],
        unique=False,
        postgresql_using='gin',
    )
    
    # Create popular_configurations table
    op.create_table(
        'popular_configurations',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique configuration identifier',
        ),
        sa.Column(
            'vehicle_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Specific vehicle this configuration applies to',
        ),
        sa.Column(
            'make',
            sa.String(length=100),
            nullable=False,
            comment='Vehicle make for broader matching',
        ),
        sa.Column(
            'model',
            sa.String(length=100),
            nullable=False,
            comment='Vehicle model for broader matching',
        ),
        sa.Column(
            'year',
            sa.Integer(),
            nullable=False,
            comment='Vehicle year for broader matching',
        ),
        sa.Column(
            'body_style',
            sa.String(length=50),
            nullable=False,
            comment='Vehicle body style for broader matching',
        ),
        sa.Column(
            'configuration_data',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment='Selected options and packages configuration',
        ),
        sa.Column(
            'selection_count',
            sa.Integer(),
            nullable=False,
            server_default=sa.text('0'),
            comment='Number of times this configuration was selected',
        ),
        sa.Column(
            'conversion_count',
            sa.Integer(),
            nullable=False,
            server_default=sa.text('0'),
            comment='Number of times this led to purchase',
        ),
        sa.Column(
            'last_selected_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
            comment='Most recent selection timestamp',
        ),
        sa.Column(
            'created_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
            comment='First selection timestamp',
        ),
        sa.Column(
            'updated_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
            comment='Last modification timestamp',
        ),
        sa.PrimaryKeyConstraint('id', name='pk_popular_configurations'),
        sa.CheckConstraint(
            "selection_count >= 0",
            name='ck_popular_configurations_selection_count_non_negative',
        ),
        sa.CheckConstraint(
            "conversion_count >= 0",
            name='ck_popular_configurations_conversion_count_non_negative',
        ),
        sa.CheckConstraint(
            "conversion_count <= selection_count",
            name='ck_popular_configurations_conversion_lte_selection',
        ),
        sa.CheckConstraint(
            "year >= 1900 AND year <= 2100",
            name='ck_popular_configurations_year_range',
        ),
        sa.CheckConstraint(
            "length(make) >= 1",
            name='ck_popular_configurations_make_min_length',
        ),
        sa.CheckConstraint(
            "length(model) >= 1",
            name='ck_popular_configurations_model_min_length',
        ),
        comment='Popular vehicle configurations for recommendations',
    )
    
    # Create indexes for popular_configurations
    op.create_index(
        'ix_popular_configurations_vehicle_id',
        'popular_configurations',
        ['vehicle_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_popular_configurations_make',
        'popular_configurations',
        ['make'],
        unique=False,
    )
    
    op.create_index(
        'ix_popular_configurations_model',
        'popular_configurations',
        ['model'],
        unique=False,
    )
    
    op.create_index(
        'ix_popular_configurations_year',
        'popular_configurations',
        ['year'],
        unique=False,
    )
    
    op.create_index(
        'ix_popular_configurations_body_style',
        'popular_configurations',
        ['body_style'],
        unique=False,
    )
    
    op.create_index(
        'ix_popular_configurations_vehicle_match',
        'popular_configurations',
        ['make', 'model', 'year', 'body_style'],
        unique=False,
    )
    
    op.create_index(
        'ix_popular_configurations_popularity',
        'popular_configurations',
        ['selection_count', 'conversion_count', 'last_selected_at'],
        unique=False,
    )
    
    op.create_index(
        'ix_popular_configurations_data_gin',
        'popular_configurations',
        ['configuration_data'],
        unique=False,
        postgresql_using='gin',
    )


def downgrade() -> None:
    """
    Downgrade database schema by removing recommendation and dealer management tables.
    
    Removes all indexes, constraints, and tables added in the upgrade.
    This operation is safe as it only removes newly added structures.
    """
    # Drop popular_configurations table
    op.drop_index(
        'ix_popular_configurations_data_gin',
        table_name='popular_configurations',
        postgresql_using='gin',
    )
    
    op.drop_index(
        'ix_popular_configurations_popularity',
        table_name='popular_configurations',
    )
    
    op.drop_index(
        'ix_popular_configurations_vehicle_match',
        table_name='popular_configurations',
    )
    
    op.drop_index(
        'ix_popular_configurations_body_style',
        table_name='popular_configurations',
    )
    
    op.drop_index(
        'ix_popular_configurations_year',
        table_name='popular_configurations',
    )
    
    op.drop_index(
        'ix_popular_configurations_model',
        table_name='popular_configurations',
    )
    
    op.drop_index(
        'ix_popular_configurations_make',
        table_name='popular_configurations',
    )
    
    op.drop_index(
        'ix_popular_configurations_vehicle_id',
        table_name='popular_configurations',
    )
    
    op.drop_table('popular_configurations')
    
    # Drop recommendation_events table
    op.drop_index(
        'ix_recommendation_events_metadata_gin',
        table_name='recommendation_events',
        postgresql_using='gin',
    )
    
    op.drop_index(
        'ix_recommendation_events_selected_packages_gin',
        table_name='recommendation_events',
        postgresql_using='gin',
    )
    
    op.drop_index(
        'ix_recommendation_events_recommended_packages_gin',
        table_name='recommendation_events',
        postgresql_using='gin',
    )
    
    op.drop_index(
        'ix_recommendation_events_session',
        table_name='recommendation_events',
    )
    
    op.drop_index(
        'ix_recommendation_events_user_vehicle',
        table_name='recommendation_events',
    )
    
    op.drop_index(
        'ix_recommendation_events_created_at',
        table_name='recommendation_events',
    )
    
    op.drop_index(
        'ix_recommendation_events_event_type',
        table_name='recommendation_events',
    )
    
    op.drop_index(
        'ix_recommendation_events_vehicle_id',
        table_name='recommendation_events',
    )
    
    op.drop_index(
        'ix_recommendation_events_session_id',
        table_name='recommendation_events',
    )
    
    op.drop_index(
        'ix_recommendation_events_user_id',
        table_name='recommendation_events',
    )
    
    op.drop_table('recommendation_events')
    
    # Drop dealer_package_configs table
    op.drop_index(
        'ix_dealer_package_configs_active',
        table_name='dealer_package_configs',
    )
    
    op.drop_index(
        'ix_dealer_package_configs_region',
        table_name='dealer_package_configs',
    )
    
    op.drop_index(
        'ix_dealer_package_configs_effective_dates',
        table_name='dealer_package_configs',
    )
    
    op.drop_index(
        'ix_dealer_package_configs_dealer_available',
        table_name='dealer_package_configs',
    )
    
    op.drop_index(
        'ix_dealer_package_configs_package_id',
        table_name='dealer_package_configs',
    )
    
    op.drop_index(
        'ix_dealer_package_configs_dealer_id',
        table_name='dealer_package_configs',
    )
    
    op.drop_table('dealer_package_configs')
    
    # Drop dealer_option_configs table
    op.drop_index(
        'ix_dealer_option_configs_active',
        table_name='dealer_option_configs',
    )
    
    op.drop_index(
        'ix_dealer_option_configs_region',
        table_name='dealer_option_configs',
    )
    
    op.drop_index(
        'ix_dealer_option_configs_effective_dates',
        table_name='dealer_option_configs',
    )
    
    op.drop_index(
        'ix_dealer_option_configs_dealer_available',
        table_name='dealer_option_configs',
    )
    
    op.drop_index(
        'ix_dealer_option_configs_option_id',
        table_name='dealer_option_configs',
    )
    
    op.drop_index(
        'ix_dealer_option_configs_dealer_id',
        table_name='dealer_option_configs',
    )
    
    op.drop_table('dealer_option_configs')
    
    # Drop enum type
    op.execute('DROP TYPE IF EXISTS recommendation_event_type')