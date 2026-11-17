# LABEQ V15 — Intent preservation and contextual learning

This release builds on V14. Avatar artwork, voice setup, page flow, Faisal adapter and the trained Saudi LoRA weights are unchanged.

## What changed

1. **Preserve the user's goal:** A request to stop helping *every day* cannot be rewritten as a polite refusal *just for today*. The inference guard sends an additional, situation-derived instruction to Qwen.
2. **Groundedness / quality check:** A lightweight Arabic heuristic catches responses that erase clear recurrence or promise a replacement time that the user did not request. The existing inference flow retries once with targeted feedback. This is not a semantic guarantee, and residual problems are labeled for user review.
3. **Relevant educational comparisons:** The teaching cards adapt to supported scenarios (recurring requests for help, recurring loans, interpersonal conflicts). Other situations show the style effects **without fabricating a tailored example**. Comparisons are **editorial learning templates**, not extra generations or Faisal explanations.
4. **Quality alert in result UI:** Only shown when the model marks its response as needing review. The main UI layout and voice assets are otherwise untouched.

## Apply to your running V14 + Colab without reloading models

You can use the updated website (V15) and existing Colab session; no need to re-download Qwen or create a new tunnel.

**In Colab**, after Qwen/Faisal have loaded, add a Code cell:

```python
from google.colab import files
uploaded = files.upload()
exec(uploaded["LABEQ_V15_Goal_Fix.py"].decode("utf-8"))
```

Upload the Python file from the V15 folder. Confirm it prints the patch confirmation plus the actual loaded statuses. This modifies the in-memory Qwen prompt/quality hooks, not the model weights. Keep the existing API and Cloudflare cells running.

**On Mac**, stop just the website server (Ctrl+C), then:

```bash
cd ~/Downloads
# V15 ZIP should be unzipped already
cp LABEQ_Communication_Coach_V14/.env LABEQ_Communication_Coach_V15/.env
cd LABEQ_Communication_Coach_V15
LABEQ_PORT=8030 bash run_mac.sh
```

Use the exact port printed by Terminal. Check `/api/model-health` for connectivity; a health check cannot guarantee an individual decision used Faisal.

## Fresh Colab session later

Use `notebooks/LABEQ_Colab_API_Connect.ipynb` bundled in V15, which includes the V15 guard installation immediately after `engine.load()`. It still requires the existing trained adapter ZIP and a compatible GPU.

## Regression check (no GPU needed)

```bash
python3 -m unittest discover -s tests -v
node tests/test_v15_coach.js
node --check app.js
```

The code tests intent preservation and that no model output is silently replaced with a hard-coded answer. The live Qwen dialect and semantic quality still require real user testing.
