"""A clipped MLX draft may be recorded diagnostically but never served as complete."""
from contextlib import nullcontext
import sys
from types import SimpleNamespace
import pytest
from generation_limits import GenerationBudgetError
from mlx_inference import MlxEngine


def engine_with_clipped_result(monkeypatch):
    sample=SimpleNamespace(text='نص توقف قبل اكتماله',finish_reason='length',generation_tokens=256)
    monkeypatch.setitem(sys.modules,'mlx_vlm',SimpleNamespace(generate=lambda *a,**kw:sample))
    engine=MlxEngine.__new__(MlxEngine)
    engine.model=engine.processor=object();engine.select=lambda name:nullcontext();engine.render=lambda messages:'prompt'
    return engine


def test_actual_serving_path_rejects_incomplete_text(monkeypatch):
    engine=engine_with_clipped_result(monkeypatch)
    with pytest.raises(GenerationBudgetError):engine._one_generation([{'role':'user','content':'موقف'}])
    assert engine.last_generation['finish_reason']=='length'


def test_raw_diagnostic_keeps_text_with_explicit_completion_status(monkeypatch):
    engine=engine_with_clipped_result(monkeypatch)
    assert engine.generate([], 'base',max_tokens=256)=='نص توقف قبل اكتماله'
    assert engine.last_generation['generation_tokens']==256
    assert engine.last_generation['decoded_text']=='نص توقف قبل اكتماله'
    assert engine.last_generation['format_cleanup_applied'] is False
