"""MangoBrain — Decay manager."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

from server.config import DECAY_LAMBDAS
from server.database import Database


class DecayManager:
    """Applies temporal decay to memories."""

    @staticmethod
    async def apply_decay(
        db: Database,
        dry_run: bool = False,
    ) -> dict:
        """Apply exponential decay to all non-deprecated memories.

        Formula: new_score = decay_score * e^(-λ * days_since_last_access)
        λ depends on memory type.

        Returns:
            {decayed: int, deprecated: int}
        """
        memories = await db.get_all_memories(deprecated=False)
        now = datetime.utcnow()
        decayed = 0
        deprecated = 0

        for m in memories:
            ref_date = m.last_accessed or m.created_at
            if isinstance(ref_date, str):
                ref_date = datetime.fromisoformat(ref_date)
            days = (now - ref_date).total_seconds() / 86400.0
            if days <= 0:
                continue

            lam = DECAY_LAMBDAS.get(m.type.value if hasattr(m.type, 'value') else m.type, 0.01)
            new_score = m.decay_score * math.exp(-lam * days)

            if abs(new_score - m.decay_score) < 0.001:
                continue

            is_now_deprecated = new_score < 0.1

            if not dry_run:
                fields: dict = {"decay_score": new_score}
                if is_now_deprecated:
                    fields["is_deprecated"] = True
                await db.update_memory(m.id, fields)

            decayed += 1
            if is_now_deprecated:
                deprecated += 1

        return {"decayed": decayed, "deprecated": deprecated}
