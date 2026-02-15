"""Add SOPDocument model for SOP Chatbot RAG

Revision ID: f688901c582d
Revises: fa6222fc1fb3
Create Date: 2026-02-15 17:50:21.804835

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f688901c582d'
down_revision = 'fa6222fc1fb3'
branch_labels = None
depends_on = None


def upgrade():
    # Create ENUM type
    sopdocumentstatus = postgresql.ENUM('processing', 'ready', 'error',
                                        name='sopdocumentstatus', create_type=False)
    sopdocumentstatus.create(op.get_bind(), checkfirst=True)

    op.create_table('sop_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('status', postgresql.ENUM('processing', 'ready', 'error',
                  name='sopdocumentstatus', create_type=False), nullable=True),
        sa.Column('chunks_count', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('uploaded_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_path')
    )


def downgrade():
    op.drop_table('sop_documents')
    sa.Enum(name='sopdocumentstatus').drop(op.get_bind(), checkfirst=True)
