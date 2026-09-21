"""Integration coverage for cooperative cancellation in diffusers backends."""

from threading import Event

import pytest

from app.backends.MediaBackend import GenerationCancelled
from app.backends.flux2klein import flux2klein
from app.backends.hyper_sdxl import hyper_sdxl
from app.backends.qwenimage21 import qwenimage21
from app.backends.sd15 import sd15
from app.backends.sdxs import sdxs
from app.backends.zimageturbo import zimageturbo


class FakeGenerator:
    def manual_seed(self, seed):
        return self


class FakeRandomValue:
    def item(self):
        return 1


class FakeTorch:
    def Generator(self, *args, **kwargs):
        return FakeGenerator()

    def randint(self, *args, **kwargs):
        return FakeRandomValue()


class FakeImage:
    width = 64
    height = 64


class FakePipeline:
    def __init__(self, cancel_during_callback=False, cancellation_event=None):
        self.cancel_during_callback = cancel_during_callback
        self.cancellation_event = cancellation_event
        self.kwargs = None

    def __call__(self, **kwargs):
        self.kwargs = kwargs
        callback = kwargs["callback_on_step_end"]
        callback_kwargs = {"latents": object()}
        if self.cancel_during_callback:
            self.cancellation_event.set()
        assert callback(self, 0, 0, callback_kwargs) is callback_kwargs
        return type("PipelineOutput", (), {"images": [FakeImage()]})()


@pytest.mark.parametrize(
    ("backend_type", "backend_module"),
    [
        (flux2klein, "app.backends.flux2klein"),
        (qwenimage21, "app.backends.qwenimage21"),
        (hyper_sdxl, "app.backends.hyper_sdxl"),
        (sd15, "app.backends.sd15"),
        (sdxs, "app.backends.sdxs"),
        (zimageturbo, "app.backends.zimageturbo"),
    ],
)
def test_diffusers_backends_pass_a_cooperative_cancellation_callback(
    monkeypatch, backend_type, backend_module
):
    module = __import__(backend_module, fromlist=["torch"])
    monkeypatch.setattr(module, "torch", FakeTorch())
    backend = backend_type.__new__(backend_type)
    backend.pipe = FakePipeline()
    backend._save_image_with_metadata = lambda *args, **kwargs: None

    cancellation_event = Event()
    backend.execute("a test image", {"cancellation_event": cancellation_event})

    assert backend.pipe.kwargs["callback_on_step_end"]


def test_pipeline_callback_interrupts_generation_when_cancellation_is_requested(
    monkeypatch,
):
    import app.backends.flux2klein as flux2klein_module

    monkeypatch.setattr(flux2klein_module, "torch", FakeTorch())
    backend = flux2klein.__new__(flux2klein)
    cancellation_event = Event()
    backend.pipe = FakePipeline(
        cancel_during_callback=True,
        cancellation_event=cancellation_event,
    )
    backend._save_image_with_metadata = lambda *args, **kwargs: None

    with pytest.raises(GenerationCancelled):
        backend.execute(
            "a cancellable test image", {"cancellation_event": cancellation_event}
        )
