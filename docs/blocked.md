# Blocked: Phase 1 vs Phase 5 acceptance conflict

Locked test `service/tests/acceptance/phase_1/test_phase_1.py::test_cli_analyze_with_resume_option`
runs `skillgap analyze <existing posting> --resume <nonexistent file>` and asserts exit code 0
(it was written against the Phase 1 "not yet implemented" stub).

Locked Phase 5 test `tests/acceptance/phase_5/test_phase_5.py::test_ac_3_7_nonexistent_resume_exits_nonzero`
runs the same shape (existing posting, nonexistent resume) and asserts a non-zero exit.

Both cannot pass without special-casing test inputs. The Phase 5 spec ("Missing files -> non-zero exit")
is the current contract; the Phase 1 test is stale. Needs a human decision: update/relax the phase 1
test (and re-lock), then `make check` goes green. Everything else (38 Phase 5 tests, verify-acceptance) passes.
