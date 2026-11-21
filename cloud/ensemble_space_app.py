"""Original LABEQ interface with explicitly configured candidate inference."""
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def main():
    import spaces
    import uvicorn
    from cloud.cpu_engine import ConfiguredTorchEngine
    from cloud.ensemble_engine import EnsembleEngine
    from cloud.space_app import create_app
    os.environ['LABEQ_MODEL_MODE']='real'
    cpu=EnsembleEngine(ConfiguredTorchEngine('cpu'));gpu=ConfiguredTorchEngine('cuda')
    app=create_app(cpu,lambda function:function,gpu_engine=gpu,max_queue_size=1)
    cpu.load();gpu.load()
    app.state.gradio_model.update(model_loaded=True,faisal_loaded=cpu.faisal_ready,**cpu.deployment_metadata())
    uvicorn.run(app,host='0.0.0.0',port=int(os.getenv('GRADIO_SERVER_PORT',os.getenv('PORT','7860'))))


if __name__=='__main__':main()
