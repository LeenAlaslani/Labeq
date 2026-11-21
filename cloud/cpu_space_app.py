"""Original LABEQ UI with actual CPU inference and a separate real GPU API."""
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    # The optional real GPU engine needs ZeroGPU emulation before torch imports.
    import spaces
    import uvicorn
    from cloud.cpu_engine import ConfiguredTorchEngine
    from cloud.space_app import create_app
    os.environ['LABEQ_MODEL_MODE']='real'
    cpu=ConfiguredTorchEngine('cpu');gpu=ConfiguredTorchEngine('cuda')
    app=create_app(cpu,lambda function:function,gpu_engine=gpu,max_queue_size=1)
    print('LABEQ: loading actual CPU Qwen, Saudi adapter and Faisal',flush=True)
    cpu.load();gpu.load()
    app.state.gradio_model.update(model_loaded=True,faisal_loaded=cpu.faisal_ready)
    print('LABEQ: CPU reply API ready; optional real GPU endpoint available',flush=True)
    uvicorn.run(app,host='0.0.0.0',port=int(os.getenv('GRADIO_SERVER_PORT',os.getenv('PORT','7860'))))


if __name__=='__main__':main()
