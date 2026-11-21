# Verified LABEQ release

Verification took place on November 20 UTC / November 21 Saudi Arabia time, 2026. This is a noncommercial research demonstration. Generated drafts and coaching still require review.

## Deployment

- Public application: https://leeennn009-labeq.hf.space/
- Hugging Face entry with account sign-in: https://huggingface.co/spaces/leeennn009/LABEQ
- Hardware: free ZeroGPU, reported by the Hub as zero-a10g. No paid hardware or subscription was activated.
- Response model: Qwen/Qwen3.5-4B with the original Saudi pilot PEFT adapter, bfloat16.
- Private pilot adapter revision: db2cf3390e5d163a58309df949aef58acb7bbd9a.
- Faisal adapter revision: 38849bdac4b7850c19587f78f5fe16c38adefac1.

The exact Git source and file hashes are recorded in the Space repository's source-manifest.json. GitHub Pages directs visitors to this app; preview.html retains the separately labeled written examples.

## Real model checks

[Saved public requests and responses](public-inference.json) contain seven newly authored situations across friendship, recurring work boundaries, family, deadlines, apologies, clarification, and customer communication. All seven returned qwen_lora_generated. Six returned faisal; the customer case returned rule_fallback. These are observed sources, not human routing-accuracy scores.

The first three requests completed anonymously. Hugging Face then enforced its anonymous runs limit. The remaining checks used the securely connected account, scoped to this Space's hostname. Visitors may need Hugging Face sign-in after their anonymous allowance. Quota failures display an error and do not substitute example text.

| Scenario | Observed route | Qualitative concern in the actual output |
| --- | --- | --- |
| Friendship misunderstanding | Faisal / diplomatic | Stiff wording, including أضحى. Coaching also misstates the speaker's perspective. |
| Repeated work help | Faisal / firm | Expresses a recurring limit but adds an unrequested scheduled-help commitment. |
| Family study time | Faisal / firm | Relevant boundary, overly formal conversational wording. |
| Report deadline | Faisal / firm | Contradicts the two-day requirement with tomorrow. The app flagged the draft, though its stated reason missed the main contradiction. |
| Forgotten appointment | Faisal / apology | Replaces forgetting with uncertainty about the appointment. The model's review also suggests an unsupported commitment. |
| File clarification | Faisal / clarify | Preserves both questions; address and phrasing could be more natural. |
| Unconfirmed delivery | Explicit rule fallback / polite | Invents a factory/shipping detail. The automatic review missed it. |

The base reviewer is fallible. model_reviewed records a model judgment and does not mean human approval. No production-quality or Saudi dialect accuracy claim follows from these checks.

## Browser and application checks

The actual public HTTPS interface was tested in Chrome with new queued model requests. The desktop test completed onboarding, checked real Faisal and Qwen source metadata, copied the generated text to the clipboard, opened coaching, changed from diplomatic to clarification, and displayed two different generated drafts for the same situation. The final release also checks public mobile inference and layout. Screenshots in ../screenshots are actual captures; release-mobile-demo.png is explicitly the archived written-example preview.

Local regression checks passed: 21 Python tests, the V16 coaching JavaScript suite, the streamed Gradio client suite, and browser tests covering duplicate rewrites, mobile layout, simulated dictation events, and inactive voice controls. Provider fixtures are identified as fixtures. Microphone recognition was not tested with a human recording.

## Training and adapter selection

The preserved v2 run completed two epochs, 479 optimizer updates, and final validation loss 1.804034279825034 on 114 validation examples. Checkpoints at iterations 200, 400, 600, and 800 and the final 256-tensor adapter were verified. The [38-case comparison](../training/EVALUATION.md) covers 114 real outputs across base, pilot, and v2. v2 was not promoted because its intent and dialect failures do not establish an improvement over the incumbent pilot. There are no independent human reviewers yet.

## Maha verification

The original Munsit credentials and configured Najdi female Maha identity were verified against the provider's live voice list. A real synthesis attempt returned HTTP 402, so audio playback and live lip-sync could not be verified. The user chose to leave speech inactive. The provider key remains local. Original TTS requests, audio decoding, playback, lip-sync, artwork, and expressions remain in the source; there is no browser voice substitution.

## Remaining work

Independent Saudi Arabic review, stronger intent preservation and grounded coaching, and a later voice playback check remain open. Shared GPU quotas and cold starts affect access. The noncommercial Faisal license and separate model, dataset, artwork, and voice-provider terms continue to apply.

## Saudi register follow-up

The later [Saudi register repair](SAUDI_REGISTER.md) keeps the original pilot, adds audited wording edits and concrete meaning checks, and records a fresh public customer screenshot. It does not retrain or promote v2.

## Compositional follow-up, November 21

The [generalization report](GENERALIZATION.md) records a completed separate two-epoch experiment, 64 frozen-test generations across base/pilot/v2/candidate, blinded assistant judgments, and new real application screenshots of both user scenarios. Strict local passes are 0/16, 1/16, 3/16 and 5/16 respectively. Neither the new candidate nor an alternative writer qualified; both known user regressions remain unsuccessful. The approved v2 and incumbent pilot weights are preserved. Independent human review remains open.

The final local checks pass 65 Python tests, both JavaScript suites, and Chrome mobile/fixture smoke checks for layout, duplicate rewrites, simulated dictation and inactive Maha controls. Two actual pilot UI requests and two experimental development UI requests used real Qwen generation and Faisal routing. These are serving/source checks, not successful semantic acceptance tests. Incomplete generated output now fails rather than being represented as complete; unavailable model review stays visibly unverified.

The longer grounded-review path reserves 60/90 seconds on free ZeroGPU and pins the official Qwen base/tokenizer revision. Final hosted full-pipeline inference requires available quota; the single successful bfloat16 diagnostic was base-only and does not validate the changed pipeline. Deployment state and any later hosted recheck are recorded separately when observed. No paid resource was enabled and no voice-provider key was copied to hosting.
