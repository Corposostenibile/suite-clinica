"""Add Team Tickets system

Revision ID: a1b2c3d4e5f6
Revises: f688901c582d
Create Date: 2026-02-15 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'f688901c582d'
branch_labels = None
depends_on = None


def upgrade():
    # Create ENUM types
    team_ticket_status = postgresql.ENUM(
        'aperto', 'in_lavorazione', 'risolto', 'chiuso',
        name='teamticketstatusenum', schema='public', create_type=False,
    )
    team_ticket_priority = postgresql.ENUM(
        'alta', 'media', 'bassa',
        name='teamticketpriorityenum', schema='public', create_type=False,
    )
    team_ticket_source = postgresql.ENUM(
        'admin', 'teams',
        name='teamticketsourceenum', schema='public', create_type=False,
    )

    team_ticket_status.create(op.get_bind(), checkfirst=True)
    team_ticket_priority.create(op.get_bind(), checkfirst=True)
    team_ticket_source.create(op.get_bind(), checkfirst=True)

    # Add Teams columns to users table
    op.add_column('users', sa.Column('teams_aad_object_id', sa.String(100), nullable=True,
                                      comment='Azure AD Object ID per mappatura Teams<->User'))
    op.add_column('users', sa.Column('teams_conversation_ref', postgresql.JSONB(), nullable=True,
                                      comment='Riferimento conversazione Teams per messaggi proattivi'))
    op.create_index('ix_users_teams_aad_object_id', 'users', ['teams_aad_object_id'], unique=True)

    # Create team_tickets table
    op.create_table(
        'team_tickets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ticket_number', sa.String(20), nullable=False, unique=True, index=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', team_ticket_status, nullable=False, server_default='aperto'),
        sa.Column('priority', team_ticket_priority, nullable=False, server_default='media'),
        sa.Column('source', team_ticket_source, nullable=False, server_default='admin'),
        sa.Column('cliente_id', sa.BigInteger(), sa.ForeignKey('clienti.cliente_id'), nullable=True, index=True),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('teams_conversation_id', sa.String(500), nullable=True),
        sa.Column('teams_activity_id', sa.String(500), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create M2M junction table
    op.create_table(
        'team_ticket_assigned_users',
        sa.Column('ticket_id', sa.Integer(), sa.ForeignKey('team_tickets.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('assigned_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('assigned_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
    )

    # Create team_ticket_messages table
    op.create_table(
        'team_ticket_messages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ticket_id', sa.Integer(), sa.ForeignKey('team_tickets.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('sender_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source', team_ticket_source, nullable=False),
        sa.Column('teams_sender_name', sa.String(255), nullable=True),
        sa.Column('teams_sender_aad_id', sa.String(100), nullable=True),
        sa.Column('read_by', postgresql.JSONB(), server_default='[]',
                  comment='Lista user_id che hanno letto il messaggio'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create team_ticket_attachments table
    op.create_table(
        'team_ticket_attachments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ticket_id', sa.Integer(), sa.ForeignKey('team_tickets.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(512), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('uploaded_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('source', team_ticket_source, nullable=False, server_default='admin'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create team_ticket_status_changes table
    op.create_table(
        'team_ticket_status_changes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ticket_id', sa.Integer(), sa.ForeignKey('team_tickets.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('from_status', team_ticket_status, nullable=True),
        sa.Column('to_status', team_ticket_status, nullable=False),
        sa.Column('changed_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('source', team_ticket_source, nullable=False, server_default='admin'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table('team_ticket_status_changes')
    op.drop_table('team_ticket_attachments')
    op.drop_table('team_ticket_messages')
    op.drop_table('team_ticket_assigned_users')
    op.drop_table('team_tickets')

    op.drop_index('ix_users_teams_aad_object_id', 'users')
    op.drop_column('users', 'teams_conversation_ref')
    op.drop_column('users', 'teams_aad_object_id')

    # Drop ENUM types
    sa.Enum(name='teamticketsourceenum', schema='public').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='teamticketpriorityenum', schema='public').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='teamticketstatusenum', schema='public').drop(op.get_bind(), checkfirst=True)
