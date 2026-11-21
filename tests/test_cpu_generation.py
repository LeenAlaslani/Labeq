"""A CPU time stop must not certify an unfinished response as complete."""
from contextlib import nullcontext
from threading import RLock
from types import SimpleNamespace
import time

import pytest

from cloud.cpu_engine import ConfiguredTorchEngine
from generation_limits import GenerationBudgetError


def fixture_engine(tokens):
    options = {}
    class Output:
        def __getitem__(self, key):
            assert key == (0, slice(3, None))
            return tokens
    def generate(**kwargs):
        options.update(kwargs)
        return Output()
    engine = ConfiguredTorchEngine.__new__(ConfiguredTorchEngine)
    engine.device_name = 'cpu'; engine.compute_backend = 'torch-cpu'
    engine.lock = RLock(); engine.deadline = time.monotonic() + 120
    engine.generation_trace = []
    engine.repetition_penalty=1.08
    engine.model = SimpleNamespace(set_adapter=lambda name: None, generate=generate,
                                   disable_adapter=nullcontext)
    engine.processor = SimpleNamespace(eos_token_id=9, decode=lambda *a, **k: 'رد فعلي')
    engine.torch = SimpleNamespace(inference_mode=nullcontext)
    engine._inputs = lambda messages: {'input_ids': SimpleNamespace(shape=(1, 3))}
    return engine, options


def test_cpu_time_stop_rejects_partial_text_before_token_cap():
    engine, options = fixture_engine([3, 4])
    with pytest.raises(GenerationBudgetError):
        engine._one_generation([], max_tokens=256)
    assert engine.last_generation['finish_reason'] == 'budget'
    assert options['max_time'] == 45
    assert options['forced_eos_token_id'] is None


def test_cpu_complete_review_has_bounded_time_and_actual_stop():
    engine, options = fixture_engine([3, 9])
    assert engine._one_generation([], use_adapter=False, max_tokens=640) == 'رد فعلي'
    assert options['max_time'] == 40
    assert engine.last_generation['finish_reason'] == 'stop'


def test_cpu_expired_request_does_not_start_another_generation():
    engine, options = fixture_engine([3, 9])
    engine.deadline = time.monotonic() - 1
    with pytest.raises(TimeoutError):
        engine._one_generation([])
    assert options == {}


def test_optional_gpu_backend_respects_the_same_configured_penalty():
    engine, options = fixture_engine([3, 9])
    engine.device_name='cuda';engine.repetition_penalty=1.0
    assert engine._one_generation([])=='رد فعلي'
    assert options['repetition_penalty']==1.0
