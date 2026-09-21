"""Integration coverage for cooperative image-generation cancellation."""

import asyncio
from threading import Event

import httpx

import app.main as main_module


class WaitingBackend:
    """Fake backend that models a diffusion step waiting for cancellation."""

    def __init__(self):
        self.started = Event()

    def execute(self, *, prompt, config, media):
        self.started.set()
        if not config["cancellation_event"].wait(timeout=1):
            raise AssertionError("backend did not receive a cancellation signal")
        raise main_module.GenerationCancelled()


def test_cancelling_an_active_generation_interrupts_backend_and_cleans_up(monkeypatch):
    async def exercise_cancellation():
        backend = WaitingBackend()
        monkeypatch.setattr(main_module, "get_backend", lambda _: backend)
        transport = httpx.ASGITransport(app=main_module.app)

        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            generation = asyncio.create_task(
                client.post(
                    "/images/generations",
                    json={
                        "prompt": "a cancellable test image",
                        "request_id": "request-123",
                    },
                )
            )

            for _ in range(100):
                if backend.started.is_set():
                    break
                await asyncio.sleep(0.01)
            assert backend.started.is_set()

            cancellation = await client.post("/images/cancellations/request-123")
            assert cancellation.status_code == 202
            assert cancellation.json() == {
                "request_id": "request-123",
                "status": "cancelling",
            }

            response = await generation
            assert response.status_code == 409
            assert response.json() == {"detail": "Generation cancelled"}

            cleanup = await client.post("/images/cancellations/request-123")
            assert cleanup.status_code == 404

    asyncio.run(exercise_cancellation())
