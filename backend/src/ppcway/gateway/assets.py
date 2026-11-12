"""Putting an image into the account's asset library, through the one door.

Google's own campaign screens add an image to the advertiser's asset library
the moment it is uploaded, and the campaign links it when it is published.
PPCWay does the same, for a practical reason as well as a faithful one: a
Performance Max campaign can carry forty images, and forty images inside the
one all-or-nothing launch request would make it many megabytes. Uploaded one
at a time, each is small, and the launch only names them.

An asset on its own spends nothing and shows nowhere until something links
it, so this is not a change to the merchant's advertising. It still goes
through `gateway.create`, so the write switch, the stops and the day's quota
all apply, and Google checks it before keeping it.
"""

from __future__ import annotations

import base64
from datetime import datetime

from sqlalchemy.orm import Session

from ppcway.gateway.create import create_together
from ppcway.gateway.port import Builds, Doing, Operation, Together


def upload_image(
    session: Session,
    *,
    customer_id: str,
    data: bytes,
    name: str,
    door: Builds,
    gate_open: bool,
    now: datetime | None = None,
) -> str:
    """The new asset's resource name. Raises what `create_together` raises."""
    together = Together(
        customer_id=customer_id,
        operations=(
            Operation(
                resource_type="asset",
                doing=Doing.CREATE,
                fields={
                    "name": name[:120],
                    "imageAsset": {"data": base64.b64encode(data).decode("ascii")},
                },
            ),
        ),
    )
    made = create_together(session, together, door=door, gate_open=gate_open, now=now)
    return next((n for n in made.names if "/assets/" in n), "")
