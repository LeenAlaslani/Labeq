"""Serve V16 unchanged at / with queued Gradio callbacks on ZeroGPU."""
import os
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def gpu_duration(payload):
    if not isinstance(payload, dict):
        return 60
    length = len(str(payload.get("message", ""))) + len(str(payload.get("goal", "")))
    length += len(str(payload.get("history", "")))
    # A grounded JSON review has a larger budget than the old one-line review.
    # Reserve enough time for the plan, routing, two drafts and two reviews;
    # this is a reservation, not a measured latency or a paid resource change.
    return 60 if length <= 800 else 90


def create_app(engine, gpu_decorator, *, gpu_engine=None, max_queue_size=8):
    import gradio as gr

    from app import app
    from labeq_api import ReplyRequest
    from LABEQ_V16_Coaching_Engine import reply_v16

    @gpu_decorator
    def generate(payload):
        request = ReplyRequest.model_validate(payload)
        result = reply_v16(
            engine, request.message, request.relation, request.goal, request.style,
            request.speaker_gender, request.recipient_gender,
            [turn.model_dump() for turn in request.history], request.generation_mode,
        )
        if os.getenv('LABEQ_RETURN_GENERATION_TRACE')=='1':
            result['generation_trace']=getattr(engine,'generation_trace',[])
        return result

    accelerated=None
    if gpu_engine is not None:
        import spaces
        @spaces.GPU(duration=gpu_duration)
        def accelerated(payload):
            request=ReplyRequest.model_validate(payload)
            return reply_v16(gpu_engine,request.message,request.relation,request.goal,request.style,
                request.speaker_gender,request.recipient_gender,[turn.model_dump() for turn in request.history],request.generation_mode)

    with gr.Blocks(title="LABEQ model API") as model_api:
        request = gr.JSON(visible=False)
        response = gr.JSON(visible=False)
        trigger = gr.Button("Generate", visible=False)
        trigger.click(
            generate, inputs=request, outputs=response, api_name="reply",
            concurrency_limit=1,
        )
        if accelerated is not None:
            gr.Button('Accelerated model API',visible=False).click(accelerated,inputs=request,outputs=response,
                api_name='reply_gpu',concurrency_limit=1)
    model_api.queue(max_size=max_queue_size, default_concurrency_limit=1)
    manifest_path=ROOT/'source-manifest.json'
    manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    app.state.gradio_model = {
        "model_loaded": engine.model is not None,
        "faisal_loaded": engine.faisal_ready,
        "generator": engine.generator,
        "adapter_revision": engine.adapter_revision,
        "base_revision": getattr(engine,"base_revision",None),
        "compute_backend":getattr(engine,"compute_backend",None),
        "adapter_sha256":getattr(engine,"adapter_sha256",None),
        "environment_versions":getattr(engine,"environment_versions",None),
        "source_commit":manifest.get('source_commit'),
    }
    # The existing FastAPI HTML is the frontend; Gradio only supplies its queue.
    return gr.mount_gradio_app(app, model_api, path="/model", ssr_mode=False)


def main():
    # Import spaces before torch so ZeroGPU installs its CUDA emulation.
    import spaces
    import uvicorn
    from cloud.torch_engine import SpaceEngine

    os.environ["LABEQ_MODEL_MODE"] = "real"
    print("LABEQ: preparing adapter and queued callback", flush=True)
    engine = SpaceEngine()
    app = create_app(engine, spaces.GPU(duration=gpu_duration))
    print("LABEQ: loading Qwen and both adapters", flush=True)
    engine.load()
    print("LABEQ: model loaded; starting FastAPI", flush=True)
    app.state.gradio_model.update(model_loaded=True, faisal_loaded=engine.faisal_ready)
    # Gradio Spaces reserve their frontend port for the platform's Node proxy.
    # The Python application must use the assigned Gradio backend port.
    port = int(os.getenv("GRADIO_SERVER_PORT", os.getenv("PORT", "7860")))
    print(f"LABEQ: serving Python backend on {port}", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
