import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path):
    db_file = tmp_path / "test.db"
    return Settings(database_url=f"sqlite+aiosqlite:///{db_file}")


@pytest.fixture
async def client(settings):
    app = create_app(settings)
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
