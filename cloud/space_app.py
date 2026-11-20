"""Serve V16 unchanged at / with queued Gradio callbacks on ZeroGPU."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def create_app(engine, gpu_decorator):
    import gradio as gr

    from app import app
    from labeq_api import ReplyRequest
    from LABEQ_V16_Coaching_Engine import reply_v16

    @gpu_decorator
    def generate(payload):
        request = ReplyRequest.model_validate(payload)
        return reply_v16(
            engine, request.message, request.relation, request.goal, request.style,
            request.speaker_gender, request.recipient_gender,
            [turn.model_dump() for turn in request.history], request.generation_mode,
        )

    with gr.Blocks(title="LABEQ model API") as model_api:
        request = gr.JSON(visible=False)
        response = gr.JSON(visible=False)
        trigger = gr.Button("Generate", visible=False)
        trigger.click(
            generate, inputs=request, outputs=response, api_name="reply",
            concurrency_limit=1,
        )
    model_api.queue(max_size=8, default_concurrency_limit=1)
    app.state.gradio_model = {
        "model_loaded": engine.model is not None,
        "faisal_loaded": engine.faisal_ready,
        "generator": engine.generator,
        "adapter_revision": engine.adapter_revision,
    }
    return gr.mount_gradio_app(app, model_api, path="/model")


def main():
    # Import spaces before torch so ZeroGPU installs its CUDA emulation.
    import spaces
    import uvicorn
    from cloud.torch_engine import SpaceEngine

    os.environ["LABEQ_MODEL_MODE"] = "real"
    engine = SpaceEngine()
    app = create_app(engine, spaces.GPU(duration=60))
    engine.load()
    app.state.gradio_model.update(model_loaded=True, faisal_loaded=engine.faisal_ready)
    # Gradio Spaces reserve their frontend port for the platform's Node proxy.
    # The Python application must use the assigned Gradio backend port.
    port = int(os.getenv("GRADIO_SERVER_PORT", os.getenv("PORT", "7860")))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
