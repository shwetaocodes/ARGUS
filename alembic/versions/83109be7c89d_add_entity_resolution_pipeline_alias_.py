"""add entity resolution pipeline: alias dictionary, merge candidates, embeddings, resolution log

Revision ID: 83109be7c89d
Revises: c3f77a42675e
Create Date: 2026-08-18 21:43:55.052376

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '83109be7c89d'
down_revision: Union[str, Sequence[str], None] = 'c3f77a42675e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # --- Create every enum type explicitly, checkfirst=True so it's safe
    # regardless of whether an earlier failed migration already created it ---
    mergecandidatestatus = postgresql.ENUM('pending', 'confirmed', 'rejected', name='mergecandidatestatus')
    mergecandidatestatus.create(bind, checkfirst=True)

    notificationtype = postgresql.ENUM('entity_watch', 'location_watch', 'threshold_alert', 'daily_digest', name='notificationtype')
    notificationtype.create(bind, checkfirst=True)

    detectiontype = postgresql.ENUM('temporal', 'sequence', 'anomaly', 'cross_source', name='detectiontype')
    detectiontype.create(bind, checkfirst=True)

    detectionstatus = postgresql.ENUM('new', 'reviewed', 'dismissed', name='detectionstatus')
    detectionstatus.create(bind, checkfirst=True)

    eventcategory = postgresql.ENUM(
        'infiltration_attempt', 'ied', 'protest', 'troop_movement', 'propaganda_broadcast',
        'ceasefire_violation', 'supply_convoy', 'aerial_activity', 'other', name='eventcategory'
    )
    eventcategory.create(bind, checkfirst=True)

    confidencelevel = postgresql.ENUM('high', 'medium', 'low', name='confidencelevel')
    confidencelevel.create(bind, checkfirst=True)

    reviewstatus = postgresql.ENUM('pending', 'accepted', 'corrected', 'rejected', name='reviewstatus')
    reviewstatus.create(bind, checkfirst=True)

    incidenttype = postgresql.ENUM(
        'border_clash', 'ceasefire_violation', 'troop_movement', 'civilian_incident',
        'influence_operation', 'other', name='incidenttype'
    )
    incidenttype.create(bind, checkfirst=True)

    reportstatus = postgresql.ENUM('draft', 'published', name='reportstatus')
    reportstatus.create(bind, checkfirst=True)

    # --- Tables with no enum columns, unchanged ---
    op.create_table('entity_alias_dictionary',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('canonical_name', sa.String(), nullable=False),
    sa.Column('alias_normalized', sa.String(), nullable=False),
    sa.Column('language', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('alias_normalized', name='uq_alias_normalized')
    )
    op.create_index(op.f('ix_entity_alias_dictionary_canonical_name'), 'entity_alias_dictionary', ['canonical_name'], unique=False)

    op.create_table('entity_annotations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('entity_id', sa.Integer(), nullable=False),
    sa.Column('analyst_id', sa.Integer(), nullable=False),
    sa.Column('note', sa.Text(), nullable=False),
    sa.Column('tag', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['analyst_id'], ['analysts.id'], ),
    sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # --- entity_merge_candidates: uses mergecandidatestatus ---
    op.create_table('entity_merge_candidates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('new_entity_id', sa.Integer(), nullable=False),
    sa.Column('matched_entity_id', sa.Integer(), nullable=False),
    sa.Column('method', sa.String(), nullable=False),
    sa.Column('score', sa.Float(), nullable=False),
    sa.Column('status', postgresql.ENUM('pending', 'confirmed', 'rejected', name='mergecandidatestatus', create_type=False), nullable=False),
    sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['matched_entity_id'], ['entities.id'], ),
    sa.ForeignKeyConstraint(['new_entity_id'], ['entities.id'], ),
    sa.ForeignKeyConstraint(['reviewed_by_id'], ['analysts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('entity_relationships',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('entity_a_id', sa.Integer(), nullable=False),
    sa.Column('entity_b_id', sa.Integer(), nullable=False),
    sa.Column('co_occurrence_count', sa.Integer(), nullable=False),
    sa.Column('first_co_occurred_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_co_occurred_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('entity_a_id < entity_b_id', name='ck_entity_order'),
    sa.ForeignKeyConstraint(['entity_a_id'], ['entities.id'], ),
    sa.ForeignKeyConstraint(['entity_b_id'], ['entities.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('entity_a_id', 'entity_b_id', name='uq_entity_pair')
    )

    op.create_table('entity_resolution_log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('input_name', sa.String(), nullable=False),
    sa.Column('normalized_name', sa.String(), nullable=False),
    sa.Column('resolved_entity_id', sa.Integer(), nullable=True),
    sa.Column('method', sa.String(), nullable=False),
    sa.Column('score', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['resolved_entity_id'], ['entities.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('entity_watches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('analyst_id', sa.Integer(), nullable=False),
    sa.Column('entity_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['analyst_id'], ['analysts.id'], ),
    sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # --- notifications: uses notificationtype ---
    op.create_table('notifications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('analyst_id', sa.Integer(), nullable=False),
    sa.Column('type', postgresql.ENUM('entity_watch', 'location_watch', 'threshold_alert', 'daily_digest', name='notificationtype', create_type=False), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('evidence', sa.Text(), nullable=True),
    sa.Column('is_read', sa.Boolean(), nullable=True),
    sa.Column('email_sent', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['analyst_id'], ['analysts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('pattern_templates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['analysts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('sectors',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('analyst_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('polygon_geojson', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['analyst_id'], ['analysts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # --- detections: uses detectiontype, detectionstatus ---
    op.create_table('detections',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('type', postgresql.ENUM('temporal', 'sequence', 'anomaly', 'cross_source', name='detectiontype', create_type=False), nullable=False),
    sa.Column('sector_id', sa.Integer(), nullable=True),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('evidence', sa.Text(), nullable=False),
    sa.Column('status', postgresql.ENUM('new', 'reviewed', 'dismissed', name='detectionstatus', create_type=False), nullable=False),
    sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['reviewed_by_id'], ['analysts.id'], ),
    sa.ForeignKeyConstraint(['sector_id'], ['sectors.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # --- event_classifications: uses eventcategory (twice), confidencelevel, reviewstatus ---
    op.create_table('event_classifications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('event_id', sa.Integer(), nullable=False),
    sa.Column('category', postgresql.ENUM(
        'infiltration_attempt', 'ied', 'protest', 'troop_movement', 'propaganda_broadcast',
        'ceasefire_violation', 'supply_convoy', 'aerial_activity', 'other', name='eventcategory', create_type=False
    ), nullable=False),
    sa.Column('confidence', postgresql.ENUM('high', 'medium', 'low', name='confidencelevel', create_type=False), nullable=False),
    sa.Column('review_status', postgresql.ENUM('pending', 'accepted', 'corrected', 'rejected', name='reviewstatus', create_type=False), nullable=False),
    sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('original_category', postgresql.ENUM(
        'infiltration_attempt', 'ied', 'protest', 'troop_movement', 'propaganda_broadcast',
        'ceasefire_violation', 'supply_convoy', 'aerial_activity', 'other', name='eventcategory', create_type=False
    ), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
    sa.ForeignKeyConstraint(['reviewed_by_id'], ['analysts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('extraction_corrections',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('event_id', sa.Integer(), nullable=False),
    sa.Column('analyst_id', sa.Integer(), nullable=False),
    sa.Column('extraction_type', sa.String(), nullable=False),
    sa.Column('original_value', sa.Text(), nullable=False),
    sa.Column('corrected_value', sa.Text(), nullable=True),
    sa.Column('action', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['analyst_id'], ['analysts.id'], ),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # --- incidents: uses incidenttype ---
    op.create_table('incidents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('analyst_id', sa.Integer(), nullable=False),
    sa.Column('event_id', sa.Integer(), nullable=True),
    sa.Column('incident_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('location', sa.String(), nullable=False),
    sa.Column('type', postgresql.ENUM(
        'border_clash', 'ceasefire_violation', 'troop_movement', 'civilian_incident',
        'influence_operation', 'other', name='incidenttype', create_type=False
    ), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('reliability_rating', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['analyst_id'], ['analysts.id'], ),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('location_watches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('analyst_id', sa.Integer(), nullable=False),
    sa.Column('sector_id', sa.Integer(), nullable=True),
    sa.Column('polygon_geojson', sa.Text(), nullable=True),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['analyst_id'], ['analysts.id'], ),
    sa.ForeignKeyConstraint(['sector_id'], ['sectors.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('pattern_template_steps',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('template_id', sa.Integer(), nullable=False),
    sa.Column('step_order', sa.Integer(), nullable=False),
    sa.Column('category', sa.String(), nullable=False),
    sa.Column('max_days_after_previous', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['template_id'], ['pattern_templates.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # --- reports: uses reportstatus ---
    op.create_table('reports',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('sector_id', sa.Integer(), nullable=True),
    sa.Column('polygon_geojson', sa.Text(), nullable=True),
    sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('end_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('event_types', sa.String(), nullable=True),
    sa.Column('situation', sa.Text(), nullable=False),
    sa.Column('analysis', sa.Text(), nullable=False),
    sa.Column('implications', sa.Text(), nullable=False),
    sa.Column('recommendation', sa.Text(), nullable=False),
    sa.Column('status', postgresql.ENUM('draft', 'published', name='reportstatus', create_type=False), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.Column('published_by_id', sa.Integer(), nullable=True),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['analysts.id'], ),
    sa.ForeignKeyConstraint(['published_by_id'], ['analysts.id'], ),
    sa.ForeignKeyConstraint(['sector_id'], ['sectors.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('sector_baselines',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('sector_id', sa.Integer(), nullable=False),
    sa.Column('category', sa.String(), nullable=False),
    sa.Column('month', sa.Integer(), nullable=False),
    sa.Column('mean_count', sa.Float(), nullable=False),
    sa.Column('std_count', sa.Float(), nullable=False),
    sa.Column('sample_years', sa.Integer(), nullable=False),
    sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['sector_id'], ['sectors.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('sector_id', 'category', 'month', name='uq_sector_category_month')
    )

    op.create_table('threshold_alerts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('analyst_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('sector_id', sa.Integer(), nullable=False),
    sa.Column('event_category', sa.String(), nullable=False),
    sa.Column('threshold_count', sa.Integer(), nullable=False),
    sa.Column('window_days', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['analyst_id'], ['analysts.id'], ),
    sa.ForeignKeyConstraint(['sector_id'], ['sectors.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('report_versions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('report_id', sa.Integer(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('situation', sa.Text(), nullable=False),
    sa.Column('analysis', sa.Text(), nullable=False),
    sa.Column('implications', sa.Text(), nullable=False),
    sa.Column('recommendation', sa.Text(), nullable=False),
    sa.Column('edited_by_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['edited_by_id'], ['analysts.id'], ),
    sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('report_versions')
    op.drop_table('threshold_alerts')
    op.drop_table('sector_baselines')
    op.drop_table('reports')
    op.drop_table('pattern_template_steps')
    op.drop_table('location_watches')
    op.drop_table('incidents')
    op.drop_table('extraction_corrections')
    op.drop_table('event_classifications')
    op.drop_table('detections')
    op.drop_table('sectors')
    op.drop_table('pattern_templates')
    op.drop_table('notifications')
    op.drop_table('entity_watches')
    op.drop_table('entity_resolution_log')
    op.drop_table('entity_relationships')
    op.drop_table('entity_merge_candidates')
    op.drop_table('entity_annotations')
    op.drop_index(op.f('ix_entity_alias_dictionary_canonical_name'), table_name='entity_alias_dictionary')
    op.drop_table('entity_alias_dictionary')

    bind = op.get_bind()
    postgresql.ENUM(name='reportstatus').drop(bind, checkfirst=True)
    postgresql.ENUM(name='incidenttype').drop(bind, checkfirst=True)
    postgresql.ENUM(name='reviewstatus').drop(bind, checkfirst=True)
    postgresql.ENUM(name='confidencelevel').drop(bind, checkfirst=True)
    postgresql.ENUM(name='eventcategory').drop(bind, checkfirst=True)
    postgresql.ENUM(name='detectionstatus').drop(bind, checkfirst=True)
    postgresql.ENUM(name='detectiontype').drop(bind, checkfirst=True)
    postgresql.ENUM(name='notificationtype').drop(bind, checkfirst=True)
    postgresql.ENUM(name='mergecandidatestatus').drop(bind, checkfirst=True)