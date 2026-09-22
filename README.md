# ci-pipeline-kit

[![CI](https://github.com/Orhevba/ci-pipeline-kit/actions/workflows/self-test.yml/badge.svg)](https://github.com/Orhevba/ci-pipeline-kit/actions/workflows/self-test.yml)
[![Example: Go](https://github.com/Orhevba/ci-pipeline-kit/actions/workflows/example-go-ci.yml/badge.svg)](https://github.com/Orhevba/ci-pipeline-kit/actions/workflows/example-go-ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A library of **reusable GitHub Actions workflows** — lint, test, security
scan, build, and deploy as separate, composable stages instead of one
monolithic pipeline copy-pasted into every repo. Point a project's own CI
at these, and it gets a consistent, maintained pipeline instead of a
one-off written from scratch — fix a bug or add a check here once, and
every repo using it benefits next run, no copy-paste required.

## Why stages, not one big workflow

A typical repo's CI is a single `.github/workflows/ci.yml` with everything
inlined — lint, test, build, all hand-written per project. That's fine
once. It stops being fine the second you have five repos and want to add
a security scan to all of them, or fix a caching bug that's now
duplicated five times.

This repo instead publishes each stage as its own [reusable
workflow](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
(`on: workflow_call`), parameterized with inputs. A project's own workflow
becomes a short list of `uses:` lines chaining the stages it wants,
instead of the stages' actual implementation:

```yaml
# a caller repo's own .github/workflows/ci.yml
jobs:
  lint:
    uses: Orhevba/ci-pipeline-kit/.github/workflows/go-lint.yml@master
  test:
    uses: Orhevba/ci-pipeline-kit/.github/workflows/go-test.yml@master
  security-scan:
    uses: Orhevba/ci-pipeline-kit/.github/workflows/go-security-scan.yml@master
  build:
    needs: [lint, test, security-scan]
    uses: Orhevba/ci-pipeline-kit/.github/workflows/go-build.yml@master
```

## What's here

| Workflow | Stage | Stack |
|---|---|---|
| `go-lint.yml` | `gofmt` + `go vet` | Go |
| `go-test.yml` | `go build` + `go test -cover` | Go |
| `go-security-scan.yml` | `gosec` (insecure code patterns) + `govulncheck` (known CVEs in dependencies) | Go |
| `go-build.yml` | `go build`, optional artifact upload | Go |
| `node-ci.yml` | install, lint, test — combined, lighter | Node |
| `python-ci.yml` | install, `ruff` lint, `pytest` — combined, lighter | Python |
| `python-security-scan.yml` | `pip-audit` (known-vulnerable dependencies) + `bandit` (insecure code patterns), two separate jobs | Python |
| `docker-build-push.yml` | build (and optionally push to GHCR) an image | any — stack-agnostic |
| `deploy-k8s.yml` | `kubectl apply` against a target cluster | any — stack-agnostic |

**Go is the fully-built reference implementation** (all four stages,
separately, matching real production pipeline shape). **Node and Python
are deliberately lighter** — one combined workflow each, to prove the
reusable-workflow pattern generalizes across stacks without needing full
stage-by-stage parity on day one. Extending either to match Go's depth
means adding `node-security-scan.yml`/`node-build.yml` (and the Python
equivalents) the same way the Go ones are built.

The Go workflows default `go-version` to `"stable"` (an
`actions/setup-go` keyword resolving to the current latest release)
rather than a hardcoded number like `"1.23"` — learned the hard way
while building this: `govulncheck` failed the very first real run of
`go-security-scan.yml` against a pinned old version, and a dozen more
stdlib CVEs surfaced the moment it was bumped to a version that was
*merely* patched rather than genuinely current. Go only backports
security fixes to its two most recent major releases, so any hardcoded
version number here will eventually age out of support entirely — using
`"stable"` sidesteps that whole class of problem rather than kicking it
down the road to the next time someone has to notice and re-bump it.

## Examples (run for real, not just documentation)

`examples/go-project`, `examples/node-project`, and
`examples/python-project` are tiny real apps, each with a workflow at the
repo root (`example-go-ci.yml`, etc.) that actually chains the relevant
reusable workflows against them on every push — so the badges above are
proof these pipelines genuinely work, not just YAML that looks right.

Note the example workflows live at the **repo root** (`.github/workflows/`),
not nested under `examples/*/`. GitHub Actions only ever discovers
workflow files in a repo's top-level `.github/workflows/` directory — a
`.github/workflows/` folder nested inside a subdirectory is never
triggered, however tempting a "real-looking" per-example repo structure
might seem. The examples' own workflows call the reusable workflows with
`working-directory:` pointed at the example's subfolder instead.

## Using this from another repo

1. Add a workflow to that repo calling whichever stages you want:
   ```yaml
   name: CI
   on: [push, pull_request]
   jobs:
     lint:
       uses: Orhevba/ci-pipeline-kit/.github/workflows/go-lint.yml@master
     test:
       uses: Orhevba/ci-pipeline-kit/.github/workflows/go-test.yml@master
   ```
2. Pass `with:` inputs to override defaults (see each workflow file for
   its full input list — `go-version`, `working-directory`, etc.).
3. For `docker-build-push.yml`, the calling job needs
   `permissions: packages: write` itself — a reusable workflow's own
   `permissions:` block can only narrow what the caller already granted,
   never widen it:
   ```yaml
   jobs:
     build-image:
       permissions:
         contents: read
         packages: write
       uses: Orhevba/ci-pipeline-kit/.github/workflows/docker-build-push.yml@master
       with:
         image-name: my-app
         push: true
   ```
   Every push tags the image both `:<commit-sha>` (immutable, for
   rollback/audit) and `:latest` (moving — so a Deployment referencing
   `:latest` plus `kubectl rollout restart` always picks up whatever was
   pushed most recently).
4. For `deploy-k8s.yml`, pass the kubeconfig as a secret explicitly —
   reusable workflows don't inherit custom secrets automatically, only
   `GITHUB_TOKEN` is automatic:
   ```yaml
   jobs:
     deploy:
       uses: Orhevba/ci-pipeline-kit/.github/workflows/deploy-k8s.yml@master
       with:
         manifests-path: ./k8s
         namespace: default
       secrets:
         kubeconfig: ${{ secrets.KUBECONFIG_B64 }}
   ```
   Store that secret as the *whole kubeconfig file*, base64-encoded:
   ```sh
   cat ~/.kube/config | base64 -w0 | gh secret set KUBECONFIG_B64 --repo <owner>/<repo>
   ```

## Python security scan (`python-security-scan.yml`)

Two independent jobs, each with its own readable table on the run's **Summary** page and annotations on the offending lines:

| Job | Tool | Question it answers |
|---|---|---|
| `dependencies` | [pip-audit](https://github.com/pypa/pip-audit) | Is any package in `requirements.txt` - **or any package those pull in** - a version with a known vulnerability? |
| `code` | [bandit](https://github.com/PyCQA/bandit) | Does *your* code contain insecure patterns: `shell=True`, unverified TLS/SSH host keys, weak hashes, `eval`, hard-coded passwords...? |

```yaml
jobs:
  security-scan:
    uses: Orhevba/ci-pipeline-kit/.github/workflows/python-security-scan.yml@master
    # with:                          # every input is optional; these are the defaults
    #   python-version: "3.12"
    #   working-directory: "."
    #   requirements-file: requirements.txt
    #   audit-fail: true             # fail on a vulnerable dependency (false = report only)
    #   audit-ignore: ""             # advisory IDs you accept for now, space-separated
    #   bandit-fail-level: high      # none | low | medium | high  (none = report only)
    #   bandit-exclude: "./tests,./test,./venv,./.venv,*/node_modules/*,./build,./dist"
```

**Adopting it on an existing project - report first, then enforce.** Switching a scan on usually finds old problems on day one, and a check
that is red from the start gets ignored. So begin with `audit-fail: false` and `bandit-fail-level: none` (the jobs still run and still
write the tables), fix what they show, then remove those two lines so the strict defaults apply. That is a *ratchet*: it can only tighten.

**New advisories are published every week**, so a project with no code changes can turn red. Call the scan on a schedule too, so that
happens on your terms:
```yaml
on:
  push: { branches: [main] }
  pull_request:
  schedule:
    - cron: "17 5 * * 1"     # Mondays 05:17
```

**Silencing a finding you have judged safe** (always say why):
- bandit: put `# nosec B603` on that line, e.g. `subprocess.run(["ffmpeg", *args])  # nosec B603 - fixed argv, no user input`. A `[tool.bandit]`
  section in `pyproject.toml` is picked up automatically (e.g. `skips = ["B101"]`).
- pip-audit: add the advisory ID to `audit-ignore` and note *when you will revisit it*.

A tool that cannot run at all (e.g. the requirements cannot be resolved) is reported as a failure of the check, never as a pass - even in
report-only mode it leaves an annotation.

## Versioning

Every example above pins `@master` for simplicity while this is a personal
project under active development. For anything you'd actually depend on
long-term, pin a tag instead (`@v1`, or a specific commit SHA) once this
repo starts cutting releases — pinning `@master` means a caller gets
whatever this repo's default branch looks like *right now*, which is
fine for learning/portfolio use but not for a pipeline you don't want to
break out from under you.

## Dogfooding

[`gitops-drift-detector`](https://github.com/Orhevba/gitops-drift-detector)'s
own CI (`.github/workflows/ci.yml`) uses this kit's `go-lint`, `go-test`,
and `go-security-scan` reusable workflows — proof this is actually used
for something real, not just an example repo talking to itself, and it
picked up dependency vulnerability scanning it didn't have before in the
process.
