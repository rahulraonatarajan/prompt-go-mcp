from __future__ import annotations
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Request


async def insert_request(session: AsyncSession, r: Request) -> int:
    session.add(r)
    await session.commit()
    return r.id  # type: ignore[no-any-return]


async def get_usage_between(session: AsyncSession, org: str, since: datetime, until: datetime) -> list[Request]:
    stmt = select(Request).where(Request.org == org, Request.ts >= since, Request.ts < until)
    res = await session.execute(stmt)
    return [row[0] for row in res]

