# Contributing to OwnDash

Thanks for helping improve OwnDash.

## Bug reports

Please use GitHub Issues and include:
- OwnDash version
- Linux distribution and desktop environment
- display model and connection type
- steps to reproduce the problem
- expected and actual behavior

Do not include passwords, account details, serial numbers, personal files, or other private information.

## Code contributions

Keep changes focused, preserve existing profile compatibility where practical, and add regression tests for bug fixes and new behavior.

Before submitting a change, run:

```bash
python3 -m compileall -q src tests
PYTHONPATH=src pytest -q
bash -n run-owndash.sh
```

By contributing code, you agree that your contribution may be distributed under OwnDash's MIT License.
