# Deploying LABEQ on ZeroGPU

The Space serves the existing V16 HTML, JavaScript, CSS, and Maha artwork at its root. The model callback is mounted at /model through Gradio. The browser sends a queued request, receives a completion event, and displays the returned source metadata.

At startup, the original Saudi pilot adapter and Faisal adapter load onto the same Qwen3.5-4B base, pinned with its tokenizer to revision `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`. PEFT reads adapter tensors on CPU before ZeroGPU packs the CUDA transfer. A GPU callback performs Faisal option scoring, Qwen base planning, Saudi LoRA response generation, and grounded JSON review. One callback runs at a time. The Space uses the free zero-a10g hardware, with a 60-second GPU reservation for ordinary requests and 90 seconds for longer contexts and a bounded queue. These are reservations for the larger bounded review budgets, not measured latency guarantees. Account quota can prevent a request from starting.

## Account and model setup

Authenticate locally with Hugging Face's CLI. Keep the token in its secure local cache and Space secrets. Use a token scoped to the LABEQ Space and the private adapter repository.

Create a private model repository containing the original PEFT adapter_config.json and adapter_model.safetensors. Set LABEQ_ADAPTER_REPO and LABEQ_ADAPTER_REVISION on the Space to the private repository and its exact commit. Give the Space read access through an HF_TOKEN secret. The deployment uses Omer Nacar's original noncommercial Faisal adapter at revision 38849bdac4b7850c19587f78f5fe16c38adefac1.

Create a Gradio Space with ZeroGPU hardware. Eligible free personal accounts can host ZeroGPU Spaces. An ineligible account must stop at that access limitation. Paid hardware is a separate deployment decision. [Hugging Face ZeroGPU documentation](https://huggingface.co/docs/hub/spaces-zerogpu)

## Source packaging

Run the publisher from the LABEQ repository with the Space ID returned by Hugging Face.

    python cloud/publish_space.py --space YOUR_ACCOUNT/LABEQ --commit YOUR_TESTED_COMMIT

The publisher takes files from that exact Git commit, flattens the web and model dependency lists, copies the existing interface assets, and records their hashes in source-manifest.json. It verifies that the requested Space hardware is zero-a10g before uploading.

The build uses cloud/space_app.py as its entrypoint and cloud/SPACE_README.md as the Space card. The private adapter and provider credentials are excluded from the uploaded source.

## Voice and secrets

The preserved Munsit integration identifies the approved Maha Najdi female voice before synthesis. Configure MUNSIT_API_KEY, MUNSIT_VOICE_ID, and the provider region using Space secrets and variables. LABEQ_VOICE_ENABLED controls activation. With that value set to 0, the UI keeps voice controls inactive and the API declines synthesis requests. Playback and character timing remain in the application for activation.

## Verification

Check the build and runtime logs through Hugging Face. Once the app is running, exercise the public HTTPS interface and the queued callback with new situations. Inspect per-request router_source and reply_source, generated text, style switching, scenario-based coaching, and mobile layout. The /api/model-health endpoint reports loaded components. Actual generation is checked separately.
