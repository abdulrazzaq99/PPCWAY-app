"""what counts as a lead: page views are not

Revision ID: 3e7c5a9b1d48
Revises: 8d3f1a6c2e94
Create Date: 2026-11-06

`not_leads` on each campaign day holds the conversions Google counted that are
not leads, which `forms` used to hold. `leads` on each search-term day holds the
conversions that were. Both start null: null means "read before the split",
and the nightly backfill re-reads the window while any row in it is null.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "3e7c5a9b1d48"
down_revision = "8d3f1a6c2e94"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ads_campaign_day", sa.Column("not_leads", sa.Float(), nullable=True))
    op.add_column("ads_search_term_day", sa.Column("leads", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("ads_search_term_day", "leads")
    op.drop_column("ads_campaign_day", "not_leads")
