# Security & privacy

- Never commit `.env`, `.local_api_key`, provider tokens, tunnel secrets or adapter weights.
- Audio requests to external TTS/STT providers may send the user-supplied text/audio to that provider; obtain consent before collecting sensitive data.
- The browser demo (`docs/`) has no AI endpoint and does not send text to this repository. Browser speech recognition/TTS, if enabled, follows the browser/platform's own privacy rules.
- Production hosting should add authentication, request limits, logging controls, timeouts and secure secret storage.
- Real inference is **not** hosted on GitHub Pages.
- Do not disclose temporary Colab/Cloudflare API keys in screenshots, issues or commits.
- Keep generated character artwork usage rights separate from code licensing.
