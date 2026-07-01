# Release Checklist

TranslateDub AI ships as a Python package on PyPI. No code signing or notarization is
required — installs are via `pip`/`pipx`/`uvx`, so there is no Gatekeeper/SmartScreen
friction and no bundled-binary license obligation.

## Before tagging

* `git status --short` is clean.
* No secret-like files tracked (`config.json`, service-account JSON, API keys). The CI
  hygiene job enforces this.
* Bump the version in both `pyproject.toml` and `translatedub/__init__.py`.
* Update any user-facing docs (README) if flags or behavior changed.

## Verify locally

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev,cloud]"
pytest
python -m bandit -q -r translatedub -ll
translatedub --version
translatedub serve --no-browser   # smoke test, then Ctrl+C
```

## Build and publish to PyPI

```bash
python -m pip install --upgrade build twine
python -m build                    # builds sdist + wheel into dist/
python -m twine check dist/*
# Test on TestPyPI first (optional):
# python -m twine upload --repository testpypi dist/*
python -m twine upload dist/*
```

## Tag and release

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

* Create a GitHub Release for the tag with a short changelog.
* Attach `LICENSE` and `THIRD_PARTY_NOTICES.md` is already in the repo; no binaries to attach.
* Do not advertise the app as endorsed by Google, pyVideoTrans, Apple, or any third party.

---

## Tiếng Việt

TranslateDub AI phát hành dạng gói Python trên PyPI. Không cần ký app hay notarize.

### Trước khi tag

* `git status --short` sạch.
* Không track file giống secret (`config.json`, service-account JSON, API key). CI job
  hygiene sẽ chặn nếu có.
* Tăng version ở cả `pyproject.toml` và `translatedub/__init__.py`.
* Cập nhật README nếu đổi flag hoặc hành vi.

### Kiểm tra & phát hành

```bash
pip install -e ".[dev,cloud]" && pytest
python -m bandit -q -r translatedub -ll
python -m build && python -m twine check dist/*
python -m twine upload dist/*        # cần tài khoản PyPI
git tag vX.Y.Z && git push origin vX.Y.Z
```

* Tạo GitHub Release cho tag kèm changelog ngắn. Không cần attach binary.
* Không quảng cáo app như được Google, pyVideoTrans, Apple endorse.
