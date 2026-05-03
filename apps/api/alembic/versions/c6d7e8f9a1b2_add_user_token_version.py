"""Add token_version to users for logout-everywhere / per-user revocation.

Permet de revoquer en bloc tous les tokens d'un utilisateur (changement de
mot de passe, suspicion compromise, logout volontaire). Le JWT embarque la
valeur au moment de l'emission ; la dependency `get_current_user` rejette
si le token_version du JWT ne correspond pas a celui en BDD.

Revision ID: c6d7e8f9a1b2
Revises: b5c6d7e8f9a1
Create Date: 2026-05-03 09:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c6d7e8f9a1b2"
down_revision: Union[str, Sequence[str], None] = "b5c6d7e8f9a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
