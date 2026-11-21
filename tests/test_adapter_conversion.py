import json
from pathlib import Path

import numpy as np
import pytest
from safetensors.numpy import load_file, save_file

from convert_mlx_to_peft import convert


def source_adapter(root):
    source = root / "source"
    source.mkdir()
    prefix = "language_model.model.layers.0.mlp.down_proj"
    (source / "adapter_config.json").write_text(json.dumps({
        "lora_parameters": {"rank": 2, "scale": 0.5, "keys": [prefix]},
    }))
    a=np.zeros((9216,2),dtype=np.float32);a[:3]=[[1.,2.],[3.,4.],[5.,6.]]
    b=np.zeros((2,2560),dtype=np.float32);b[:,:2]=[[1.,2.],[3.,4.]]
    save_file({prefix+".lora_a":a,prefix+".lora_b":b},str(source/"adapters.safetensors"))
    return source


def test_conversion_preserves_the_delta_and_does_not_modify_source(tmp_path):
    source = source_adapter(tmp_path)
    before = (source / "adapters.safetensors").read_bytes()
    output = tmp_path / "output"
    manifest = convert(source, output)
    config = json.loads((output / "adapter_config.json").read_text())
    assert config["r"] == 2 and config["lora_alpha"] == 1
    weights = load_file(str(output / "adapter_model.safetensors"))
    a, b = (weights["base_model.model.model.language_model.layers.0.mlp.down_proj.lora_" + side + ".weight"] for side in ("A", "B"))
    x=np.zeros((1,9216));x[0,0]=1
    delta=x@a.T@b.T*.5
    np.testing.assert_allclose(delta[:,:2],[[3.5,5.]])
    assert not delta[:,2:].any()
    assert (source / "adapters.safetensors").read_bytes() == before
    assert manifest["exact_transpose_roundtrip"]


def test_existing_destination_cannot_be_overwritten(tmp_path):
    source = source_adapter(tmp_path)
    output = tmp_path / "output"
    output.mkdir()
    (output / "keep.txt").write_text("preserve")
    with pytest.raises(FileExistsError):
        convert(source, output)
    assert (output / "keep.txt").read_text() == "preserve"


def test_unknown_tensor_is_rejected(tmp_path):
    source = source_adapter(tmp_path)
    save_file({"unknown.weight": np.ones((2, 2), dtype=np.float32)}, str(source / "adapters.safetensors"))
    with pytest.raises(ValueError, match="Unexpected"):
        convert(source, tmp_path / "output")
