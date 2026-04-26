import asyncio
from sqlalchemy import select
from app.db.session import create_engine, create_session_factory
from app.core.config import get_settings
from app.db.models import Project

async def main():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    
    async with session_factory() as session:
        query1 = select(Project).where(Project.archived_at.is_(None))
        res1 = await session.execute(query1)
        print("Unarchived count:", len(res1.scalars().all()))
        
        query2 = select(Project)
        res2 = await session.execute(query2)
        print("Total count:", len(res2.scalars().all()))
        
        query3 = select(Project).where(Project.archived_at.is_not(None))
        res3 = await session.execute(query3)
        print("Archived count:", len(res3.scalars().all()))

asyncio.run(main())
