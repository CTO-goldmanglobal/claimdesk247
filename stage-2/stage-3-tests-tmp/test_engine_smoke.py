"""Smoke test: drive every YAML acceptance case through the engine and assert.

This is the builder's first-pass test. It is run before the full test
runner is built so we can iterate on the engine against real expected
bands without going through the full state machine.

Output: a tabular report printed to stdout, with per-case status.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Make `app` importable
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml

from app.engine import classify, EngineResult, EngineBandError

YAML_PATH = Path(__file__).parent.parent / "acceptance-tests.stage2.yaml"


def run_smoke() -> int:
    with YAML_PATH.open() as f:
        data = yaml.safe_load(f)
    cases = data["cases"]
    pass_count = 0
    fail_count = 0
    failures: list[str] = []
    for case in cases:
        cid = case["id"]
        gate = case["gate"]
        inputs = case.get("inputs", {})
        expected = case.get("expect", {})

        # Inject handled at the engine level: skip if not a classification case
        if "inject_band" in inputs:
            # T-2-027: engine must fail-closed on out-of-enum band injection
            try:
                # We don't have a setter for band; the test will be exercised
                # by the full runner via a separate code path.
                classify(inputs)
                failures.append(f"{cid}: expected EngineBandError, got normal result")
                fail_count += 1
                continue
            except EngineBandError:
                pass_count += 1
                continue
            except Exception as e:
                failures.append(f"{cid}: expected EngineBandError, got {type(e).__name__}: {e}")
                fail_count += 1
                continue

        try:
            result: EngineResult = classify(inputs)
        except EngineBandError as e:
            if expected.get("band") is None and expected.get("engine_error"):
                pass_count += 1
                continue
            failures.append(f"{cid}: engine error: {e}")
            fail_count += 1
            continue
        except Exception as e:
            failures.append(f"{cid}: unexpected {type(e).__name__}: {e}")
            fail_count += 1
            continue

        # Compare against expected
        ok = True
        msgs = []
        if "band" in expected:
            if expected["band"] is None:
                if result.band is not None:
                    ok = False
                    msgs.append(f"band: expected null, got {result.band!r}")
            elif result.band != expected["band"]:
                ok = False
                msgs.append(f"band: expected {expected['band']!r}, got {result.band!r}")
        if expected.get("disclaimer_attached") is True:
            if not result.disclaimer_attached:
                ok = False
                msgs.append("disclaimer_attached: expected True, got False")
        if expected.get("disclaimer_attached") is False:
            if result.disclaimer_attached:
                ok = False
                msgs.append("disclaimer_attached: expected False, got True")
        if "escalation" in expected:
            if expected["escalation"] == "none":
                if result.escalation is not None:
                    ok = False
                    msgs.append(f"escalation: expected none, got {result.escalation!r}")
            elif expected["escalation"] == "callback":
                if result.escalation is None:
                    ok = False
                    msgs.append("escalation: expected callback, got None")
            else:
                if result.escalation != expected["escalation"]:
                    ok = False
                    msgs.append(f"escalation: expected {expected['escalation']!r}, got {result.escalation!r}")
        if expected.get("classification_attempted") is False:
            if result.classification_attempted:
                ok = False
                msgs.append("classification_attempted: expected False, got True")

        if ok:
            pass_count += 1
        else:
            fail_count += 1
            failures.append(f"{cid} ({gate}): {'; '.join(msgs)}")

    print(f"\n=== SMOKE TEST RESULTS ===")
    print(f"TOTAL: {len(cases)}  PASS: {pass_count}  FAIL: {fail_count}")
    if failures:
        print("\nFailures:")
        for f in failures:
            print(f"  - {f}")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(run_smoke())
