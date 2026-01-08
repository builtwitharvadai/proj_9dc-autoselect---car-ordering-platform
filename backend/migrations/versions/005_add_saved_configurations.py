"""
Alembic migration: Add saved configurations table for vehicle configurations.

This migration creates the saved_configurations table with proper indexes,
foreign key constraints, and unique constraints for share tokens. Implements
secure token generation, proper relationships, and efficient indexing for
configuration management and sharing capabilities.

Revision ID: 005
Revises: 004
Create Date: 2024-01-07 22:35:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade database schema to add saved configurations table.
    
    Creates saved_configurations table with comprehensive fields for
    configuration management, sharing capabilities, and user associations.
    Implements proper indexes for efficient querying and enforces data
    integrity with constraints.
    """
    # Create saved_configurations table
    op.create_table(
        'saved_configurations',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique saved configuration identifier',
        ),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='User who saved this configuration',
        ),
        sa.Column(
            'configuration_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Associated vehicle configuration',
        ),
        sa.Column(
            'name',
            sa.String(length=255),
            nullable=False,
            comment='Custom name for the saved configuration',
        ),
        sa.Column(
            'share_token',
            sa.String(length=32),
            nullable=False,
            comment='Unique token for sharing configuration',
        ),
        sa.Column(
            'is_public',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
            comment='Whether configuration is publicly accessible',
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
        sa.PrimaryKeyConstraint('id', name='pk_saved_configurations'),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            name='fk_saved_configurations_user_id',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['configuration_id'],
            ['vehicle_configurations.id'],
            name='fk_saved_configurations_configuration_id',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['created_by'],
            ['users.id'],
            name='fk_saved_configurations_created_by',
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['updated_by'],
            ['users.id'],
            name='fk_saved_configurations_updated_by',
            ondelete='SET NULL',
        ),
        sa.CheckConstraint(
            "length(name) >= 1",
            name='ck_saved_configurations_name_min_length',
        ),
        sa.CheckConstraint(
            "length(name) <= 255",
            name='ck_saved_configurations_name_max_length',
        ),
        sa.CheckConstraint(
            "length(share_token) = 32",
            name='ck_saved_configurations_share_token_length',
        ),
        sa.UniqueConstraint(
            'share_token',
            name='uq_saved_configurations_share_token',
        ),
        comment='Saved vehicle configurations with sharing capabilities',
    )
    
    # Create indexes for saved_configurations
    op.create_index(
        'ix_saved_configurations_user_id',
        'saved_configurations',
        ['user_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_saved_configurations_configuration_id',
        'saved_configurations',
        ['configuration_id'],
        unique=False,
    )
    
    op.create_index(
        'ix_saved_configurations_share_token',
        'saved_configurations',
        ['share_token'],
        unique=True,
    )
    
    op.create_index(
        'ix_saved_configurations_is_public',
        'saved_configurations',
        ['is_public'],
        unique=False,
    )
    
    # Composite index for user's configurations ordered by creation date
    op.create_index(
        'ix_saved_configurations_user_created',
        'saved_configurations',
        ['user_id', 'created_at'],
        unique=False,
    )
    
    # Composite index for configuration lookup by user
    op.create_index(
        'ix_saved_configurations_config_user',
        'saved_configurations',
        ['configuration_id', 'user_id'],
        unique=False,
    )
    
    # Composite index for public configurations ordered by creation date
    op.create_index(
        'ix_saved_configurations_public',
        'saved_configurations',
        ['is_public', 'created_at'],
        unique=False,
    )
    
    # Composite index for active configurations (not soft deleted)
    op.create_index(
        'ix_saved_configurations_active',
        'saved_configurations',
        ['user_id', 'deleted_at'],
        unique=False,
    )
    
    # Partial index for active (non-deleted) configurations
    op.create_index(
        'ix_saved_configurations_active_only',
        'saved_configurations',
        ['user_id', 'created_at'],
        unique=False,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )
    
    # Partial index for public active configurations
    op.create_index(
        'ix_saved_configurations_public_active',
        'saved_configurations',
        ['is_public', 'created_at'],
        unique=False,
        postgresql_where=sa.text('is_public = true AND deleted_at IS NULL'),
    )


def downgrade() -> None:
    """
    Downgrade database schema by removing saved configurations table.
    
    Removes all indexes, constraints, and the saved_configurations table
    added in the upgrade. This operation is safe as it only removes newly
    added structures.
    """
    # Drop partial indexes
    op.drop_index(
        'ix_saved_configurations_public_active',
        table_name='saved_configurations',
        postgresql_where=sa.text('is_public = true AND deleted_at IS NULL'),
    )
    
    op.drop_index(
        'ix_saved_configurations_active_only',
        table_name='saved_configurations',
        postgresql_where=sa.text('deleted_at IS NULL'),
    )
    
    # Drop composite indexes
    op.drop_index(
        'ix_saved_configurations_active',
        table_name='saved_configurations',
    )
    
    op.drop_index(
        'ix_saved_configurations_public',
        table_name='saved_configurations',
    )
    
    op.drop_index(
        'ix_saved_configurations_config_user',
        table_name='saved_configurations',
    )
    
    op.drop_index(
        'ix_saved_configurations_user_created',
        table_name='saved_configurations',
    )
    
    # Drop simple indexes
    op.drop_index(
        'ix_saved_configurations_is_public',
        table_name='saved_configurations',
    )
    
    op.drop_index(
        'ix_saved_configurations_share_token',
        table_name='saved_configurations',
    )
    
    op.drop_index(
        'ix_saved_configurations_configuration_id',
        table_name='saved_configurations',
    )
    
    op.drop_index(
        'ix_saved_configurations_user_id',
        table_name='saved_configurations',
    )
    
    # Drop saved_configurations table
    op.drop_table('saved_configurations')