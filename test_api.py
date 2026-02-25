"""Quick API smoke test for SmartV2X-CP server."""
import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(base_url="http://localhost:3000", timeout=10) as c:
        # 1. Health check
        r = await c.get("/api/health")
        print(f"HEALTH: {r.status_code} -> {r.text[:200]}")

        # 2. Register a new user
        r2 = await c.post("/api/auth/register", json={
            "username": "testuser2",
            "password": "Test1234!",
            "name": "Test User"
        })
        print(f"REGISTER: {r2.status_code} -> {r2.text[:200]}")

        # 3. Login with the new user
        r3 = await c.post("/api/auth/login", json={
            "username": "testuser2",
            "password": "Test1234!"
        })
        print(f"LOGIN: {r3.status_code} -> {r3.text[:200]}")

        # 4. Demo user login (fallback)
        r4 = await c.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        print(f"DEMO LOGIN: {r4.status_code} -> {r4.text[:200]}")

asyncio.run(test())
