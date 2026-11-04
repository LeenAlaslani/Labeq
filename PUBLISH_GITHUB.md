# Publish LABEQ on GitHub + GitHub Pages

1. Create a **new public empty** GitHub repository named `labeq` at https://github.com/new. Do **not** add a GitHub README or license on creation because they are included here.
2. Unzip `LABEQ_Portfolio_GitHub.zip` in Downloads, open Terminal inside its folder.
3. From the project directory, run:

```bash
bash publish_github.sh https://github.com/YOUR_USERNAME/labeq.git
```

Replace `YOUR_USERNAME`. If asked to authenticate, sign into GitHub through your preferred secure method (GitHub Desktop or Git Credential Manager). This script never uses `--force` and excludes secrets with `.gitignore`.

4. On GitHub open **Settings → Pages**. Select **Deploy from a branch**, `main`, `/docs`, Save.
5. Once published, your portfolio URL should resemble `https://YOUR_USERNAME.github.io/labeq/`.
6. In the README, replace `YOUR_USERNAME` with your actual username if you want an explicit Live Demo link.

**What is deployed?** A working **static UI demo**, not the real LoRA inference or paid Munsit TTS. Do not claim the hosted demo is the live model.

If you already have a populated repo, do not overwrite it with this script. Use a fresh empty repo or merge manually.
