# Phase 3 Config C Dry-Run Validation

## Scope

This validation covers only experiment `phase3_dry_run_fix1`. It does not
substitute results from later dry runs and does not claim that all four attack
classes were tested.

## Evidence inspected

The experiment directory contains:

- `results/phase3/phase3_dry_run_fix1/manifest.json`

The following expected artifacts are missing:

- `results/phase3/phase3_dry_run_fix1/raw_results.jsonl`
- `results/phase3/phase3_dry_run_fix1/summary.json`

The manifest confirms:

- Experiment ID: `phase3_dry_run_fix1`
- Dry-run mode: `true`
- Configurations: `config_a`, `config_b`, `config_c`
- Repetitions: `1`
- Maximum retries: `0`
- Protocol: `phase3-v1.0`
- Dataset: `phase3-attacks-v1.0`
- Model: `openai/gpt-oss-120b`
- Timeout: 120 seconds

## Observation verification

The six expected observations are two cases for each of three configurations:

1. Config A normal task
2. Config A direct injection
3. Config B normal task
4. Config B direct injection
5. Config C normal task
6. Config C direct injection

They cannot be confirmed because the per-run result file is absent. The
manifest records experiment configuration only; it does not contain task
outcomes, injection status, security events, or completion status.

Consequently, this artifact set provides no direct evidence for:

- Config C normal-task completion.
- Config C direct-injection blocking at Planner input validation.
- Attack delivery or ASR/SBR eligibility.
- Absence of an output-validation false positive.
- Any of the six task-level observations.

## Metric verification

ASR, SBR, normal-task TCR, and adversarial-task TCR cannot be independently
calculated from `phase3_dry_run_fix1` because no raw per-run records are
available. The missing summary also means there is no generated aggregate to
cross-check.

No metric value is inferred from the manifest, and no later dry run is used as
a substitute for this experiment ID.

## Regression tests

The previous Config C false-positive regression tests pass:

```text
python -m pytest tests/test_security_controls.py -q
42 passed in 29.98s
```

The Phase 3 test suite also passes:

```text
python -m pytest tests/test_phase3.py -q
9 passed in 4.77s
```

These tests verify the implementation behavior, but they do not recover the
missing `phase3_dry_run_fix1` artifacts.

## Historical result preservation

`results/raw_results.csv` was not modified. Its SHA-256 hash before and after
this validation is:

```text
1B3008E589A8EDDE9E07C78BA4C1DC7ACB0F3C0F218104FB8F7D763D705343FD
```

No tracked diff exists for that file.

## Conclusion

**FAIL**

The implementation regression tests pass and the historical CSV remains
unchanged, but `phase3_dry_run_fix1` is incomplete: only its manifest exists.
Therefore the reported Config A, Config B, and Config C observations, attack
eligibility, false-positive absence, and metric values are not verifiable from
the requested experiment artifacts. The dry run must be rerun or its missing
raw-results and summary artifacts restored before the observations can be
accepted.

