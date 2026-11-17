# LABEQ V16 — Context-first communication coach (experimental)

## Why V15 was inadequate

- Outputs could be grammatically acceptable yet fail to resolve the actual interpersonal problem.
- Selecting "اعتذار" could lead to nearly the same message as "لبق" because the internal style-normalization mapped several choices to one instruction.
- The extra rewriting instruction was appended to the original situation, contaminating the evidence used to understand the user's facts.
- Most explanations and comparisons were scripted for a handful of scenarios rather than grounded in each user's situation.
- A five-goal menu excluded plenty of legitimate use cases.

## Pipeline in V16

1. The user supplies the relationship and goal (or writes a custom goal), then describes the situation.
2. Faisal selects among the existing five communication styles **when automatic mode is used**. This is not a trained interpersonal reasoning specialist and its appropriateness remains unvalidated. In other modes, user choice is reported as `user_selected`.
3. Qwen **base**, without the Saudi LoRA adapter, drafts a short communication brief: core tension, objective, suggested tactic, and potential misunderstanding. This is an AI-generated plan, not a verified account of the social situation.
4. Qwen3.5-4B **with the Saudi LoRA** writes the actual response, conditioning on the original situation, its objective, the selected tone, and the optional rewrite request.
5. Qwen base checks whether the reply appears goal-aligned, socially appropriate, faithful to the situation, and natural. The system can retry once after a concrete problem is found. This self-review is **not independent evidence** that the reply is correct.
6. The interface shows a short contextual coaching note when the planner produced one. For comparison, the user asks the real model to generate another style; it no longer presents canned example messages as if they applied to this specific case.

## Distinctions that must not be lost

- **Goal:** what the user is trying to achieve.
- **Style:** how to express it (e.g. polite, firm, apologetic, diplomatic, clarifying).
- **Formality:** professional or casual wording, a separate axis from style.
- **Facts:** only what the user supplied. Never invent guilt, schedules, commitments, misconduct, agreements, feelings, or intent.
- **Agency:** the assistant proposes a message; the user decides whether to send or modify it.

## Limitations

- No new fine-tuning, data labeling, or training is included.
- Faisal's classification is not proven superior to a rules-based or a single-LLM baseline.
- The base model reviewer can share the same blind spots as the generator; a high-quality reply is not guaranteed.
- Generating a plan and review involves extra inference latency.
- This patch was verified with offline unit tests using mocked model responses; it **has not been measured against the live Colab model**, nor benchmarked on actual Saudi conversations.
- The teaching content is a generated interpretation, not a technical explanation of the internals of Faisal.

## Recommended evaluation before public launch

Run the cases in `V16_EVALUATION_CASES.md` through the live GPU model and score each response on: goal preservation, appropriateness, dialect naturalness, no fabricated details, feasibility of sending it, and meaningful contrast across styles. Record failures; do not publish a claimed quality score without measurements.
