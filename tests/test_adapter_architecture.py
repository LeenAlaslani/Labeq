"""Guard the newly supported linear-attention conversion against silent mis-mapping."""
import json
import numpy as np
import pytest
from safetensors.numpy import load_file, save_file
from convert_mlx_to_peft import convert


def source(tmp_path, path, input_size, output_size):
    src=tmp_path/"source";src.mkdir()
    prefix="language_model.model."+path
    rng=np.random.default_rng(13)
    a=rng.normal(size=(input_size,2)).astype(np.float32)
    b=rng.normal(size=(2,output_size)).astype(np.float32)
    save_file({prefix+".lora_a":a,prefix+".lora_b":b},str(src/"adapters.safetensors"))
    (src/"adapter_config.json").write_text(json.dumps({"lora_parameters":{"rank":2,"scale":1.5,"keys":[prefix]}}))
    return src,a,b


def test_linear_attention_delta_survives_peft_layout(tmp_path):
    src,a,b=source(tmp_path,"layers.0.linear_attn.in_proj_qkv",2560,8192)
    dst=tmp_path/"peft"
    manifest=convert(src,dst)
    saved=load_file(str(dst/"adapter_model.safetensors"))
    prefix="base_model.model.model.language_model.layers.0.linear_attn.in_proj_qkv"
    np.testing.assert_array_equal(saved[prefix+".lora_A.weight"],a.T)
    np.testing.assert_array_equal(saved[prefix+".lora_B.weight"],b.T)
    x=np.arange(2560,dtype=np.float64)[None,:]/2560
    actual=x@saved[prefix+".lora_A.weight"].T@saved[prefix+".lora_B.weight"].T*1.5
    np.testing.assert_allclose(actual,x@a@b*1.5,rtol=1e-10,atol=1e-10)
    assert manifest["tensor_count"]==2


@pytest.mark.parametrize("path,inputs,outputs",[
    ("layers.3.linear_attn.out_proj",4096,2560),
    ("layers.0.linear_attn.in_proj_qkv",2560,4096),
    ("layers.32.mlp.up_proj",2560,9216),
])
def test_wrong_attention_type_layer_or_shape_is_rejected(tmp_path,path,inputs,outputs):
    src,_,_=source(tmp_path,path,inputs,outputs)
    with pytest.raises(ValueError):convert(src,tmp_path/"peft")
    assert not (tmp_path/"peft").exists()
