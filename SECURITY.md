# Security, privacy, and deployment

The [GitHub Pages demo](https://leenalaslani.github.io/Labeq/) serves `main:/docs` over HTTPS. Example selection and coaching run in the browser. Browser speech depends on the user's browser and device, which may send audio to their speech provider.

The local setup binds both servers to `127.0.0.1`. The web server keeps the model and voice service credentials in an ignored `.env`. The model API authenticates inference with `X-API-Key`. Validate model endpoints before sending credentials. Local HTTP is allowed only for loopback. The web API bounds model and speech requests to 30 per minute per client address by default, configurable through `LABEQ_REQUESTS_PER_MINUTE`. For multi-worker deployments, enforce shared limits at the gateway.

For persistent model hosting, use a public HTTPS web service and a private authenticated inference service. Put provider secrets in the host's secret manager. Use a reverse proxy or platform gateway with authentication, bounded per-user rate limits, request-size limits, and concurrency limits. Keep the inference API inaccessible from the browser, configure the proxy to trust only its own forwarded client headers, and exclude scenarios, raw audio, and secrets from logs. Voice and model calls may transmit user-provided content to external providers. Inform users before enabling those providers.

Before publishing live inference, verify capacity and provider terms for the specific usage. Faisal weights are licensed CC BY-NC 4.0. Consult the author for commercial use. Obtain redistribution terms for the approved data and an operator authorized to use the selected voice endpoint. Keep model weights, data and raw evaluation output in private storage. The static public release has no application inference endpoint or service credentials.

For existing demo deployments, configure GitHub Pages with `main` as the branch and `/docs` as the directory. Serve the same folder locally to test the release before pushing.
