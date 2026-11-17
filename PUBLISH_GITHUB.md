# Publish a LABEQ update

The existing repository is [LeenAlaslani/Labeq](https://github.com/LeenAlaslani/Labeq). Start your branch from the current `origin/main`. Keep the original team credits and preserve commit history.

1. Run the Python, JavaScript, and browser checks in [the README](README.md#tests-and-deployment).
2. Review `git diff --cached --name-only` and `git diff --cached`. Keep data files, evaluation responses, model weights, and provider credentials in ignored private storage.
3. Push the implementation branch and open a pull request into `main`. Merge once checks pass.
4. Verify GitHub Pages built from `main:/docs`. Open the [public demo](https://leenalaslani.github.io/Labeq/) to check onboarding, the example label, and reply variants. Verify README screenshots from the merged branch.
5. Record the main commit and report which tests used model inference and which used fixtures.

The browser demo requires no GPU or paid voice service. See [deployment and privacy](SECURITY.md) for requirements to host an inference backend.
