# SonarQube Quality Gate

**Status:** Implemented. Needs a SonarQube project and a token before it does anything (see [Setup](#setup)).
**Stream:** Back-end.

## What it does

Every pull request (and every push to `main`, for a baseline) gets a static
analysis scan and a quality gate covering bugs, vulnerabilities, code smells,
duplication and test coverage. If the gate fails, the `SonarQube Scan` check
fails on the PR.

It runs the same unit-test selection as the main CI job
(`pytest -m "not integration"`) with coverage, then hands the report to the
scanner. Integration tests need the running stack, so they are not part of this
scan.

The default gate ("Sonar way") judges **new code only**. Existing issues and
existing coverage do not block a PR; only what the PR adds or changes does.

## Scope

Only what the Backend stream owns is scanned: `backend/` and
`infrastructure/`. Frontend, AI Modelling and Data Engineering directories are
not scanned at all, so their code quality can never fail a Backend PR.

Some material lives under `backend/` but belongs to another stream, or is not
source, and is excluded (see `sonar-project.properties`):

| Excluded | Why |
|---|---|
| `backend/model-api/src/**` | AI Modelling's forecaster source and trained weights, vendored into model-api |
| `backend/model-api/app/data/**`, `app/models/*.pkl` | Sample data and pickled models |
| `backend/utilities/aggregator-init.sql`, `seed-aggregator.sql`, `v2/**` | Data Engineering's schema and seed data |
| `backend/tests/**` | Analysed as tests, not as source (the two sets must not overlap) |

## Setup

The workflow needs three things you provide. Until `SONAR_TOKEN` exists, the job
**passes with a notice** rather than failing, so merging this does not turn
every PR red.

1. **Create a SonarQube project.** Either:
   - **SonarQube Cloud** (sonarcloud.io): import the repository. Free for public
     repositories. Nothing else to host.
   - **A self-hosted SonarQube Server** that GitHub's runners can reach over the
     internet. A server running only on your own machine cannot be scanned by
     CI, though it is fine for local scans.
2. **Generate a token** for the project and add it as a repository **secret**
   named `SONAR_TOKEN` (Settings, Secrets and variables, Actions).
3. **Add repository variables** (same page, Variables tab):

| Variable | Needed for | Notes |
|---|---|---|
| `SONAR_HOST_URL` | Self-hosted server only | Leave unset for SonarQube Cloud |
| `SONAR_ORGANIZATION` | SonarQube Cloud only | Your organization key |
| `SONAR_PROJECT_KEY` | Optional | Defaults to `InnovAIte-Deakin_InnovAIte_FireFusion_Project`, which is what Cloud generates for this repository |

4. **Make it a required check** (optional, recommended): Settings, Branches,
   branch protection for `main`, require the `SonarQube Scan` status check.
   Do this only after the token is in place, because before that the check passes
   without scanning anything.

PRs from forks never receive secrets, so for them the job is skipped with the
same notice.

## Coverage numbers

- `.coveragerc` produces `coverage.xml` with paths relative to the repo root,
  which is how SonarQube looks files up. (Per-folder source settings produce
  paths relative to each folder instead, so the three different `main.py` files
  become indistinguishable.)
- The unit tests currently import only `firefusion-api` and `shared`.
  `aggregator-api` and `model-api` have no unit tests, so they are absent from
  the report; `sonar.python.coverage.forceZeroCoverage=true` counts them as 0%
  instead of ignoring them. That is honest, and it will look low until those
  services get tests.

## Running a scan locally

Useful for checking a change before pushing, against any SonarQube you can
reach:

```bash
pip install -r backend/tests/requirements-test.txt pytest-cov
pytest backend/tests -m "not integration" --cov --cov-config=.coveragerc --cov-report=xml

sonar-scanner \
  -Dsonar.host.url=http://localhost:9000 \
  -Dsonar.token=<token> \
  -Dsonar.projectKey=firefusion-backend
```

## What has not been verified

The workflow, the scope and the coverage paths were checked locally (the
workflow with `actionlint`, the file selection by emulation, the coverage
report by running it). An actual scan against a SonarQube server has not been
run, because that needs your project and token. The first real run is the first
end-to-end test; expect it to be a baseline, and expect to adjust the
exclusions if the first report shows noise.
