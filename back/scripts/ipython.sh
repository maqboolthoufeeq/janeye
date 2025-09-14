#!/usr/bin/env python
"""
Interactive IPython shell for the application.
This script imports common modules and sets up the application context.

Usage:
    python scripts/ipython_shell.py

From inside the shell, you can access models, services, and database sessions.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Initialize IPython
import IPython
from traitlets.config import Config

# Import SQLAlchemy modules
from sqlalchemy import select, update, delete, insert, and_, or_, not_, func, desc, asc
from sqlalchemy.orm import joinedload, selectinload, contains_eager, aliased
from sqlalchemy.sql import text
from sqlalchemy.ext.asyncio import AsyncSession, AsyncResult

# Import common modules from the application
from app.models import *
from app.services import *
from app.db_selectors import *
from app.core.db import AsyncSessionLocal, engine
from app.settings import settings


async def get_session():
    """Get a database session that can be used in the shell."""
    async with AsyncSessionLocal() as session:
        return session


if __name__ == "__main__":
    # Configure IPython
    c = Config()
    c.InteractiveShellApp.exec_lines = [
        "import asyncio",
        "import uuid",
        # SQLAlchemy imports
        "from sqlalchemy import select, update, delete, insert, and_, or_, not_, func, desc, asc",
        "from sqlalchemy.orm import joinedload, selectinload, contains_eager, aliased",
        "from sqlalchemy.sql import text",
        # Application imports
        "from app.models import *",
        "from app.services import *",
        "from app.db_selectors import *",
        "from app.core.db import AsyncSessionLocal, engine",
        "from app.settings import settings",
        # Common models people will use
        "from app.models.auth.user import User",
        "from app.models.organizations.organization import Organization",
        "from app.models.organizations.organization_user import OrganizationUser, RoleEnum",
        # Welcome message
        "print('\\nWelcome to the JanEye IPython shell\\n')",
        "print('Available modules: app.models, app.services, app.db_selectors')",
        "print('SQLAlchemy: select, update, delete, insert, and_, or_, func, etc.')",
        "print('Settings available as: settings')",
        "print('\\nTo get a DB session use: session = await get_session()')",
        "print('Example query: result = await session.execute(select(User))')",
        "print('For async operations, use: await asyncio.gather(...)')",
    ]

    # Start IPython
    IPython.start_ipython(argv=[], config=c, user_ns={"get_session": get_session})
