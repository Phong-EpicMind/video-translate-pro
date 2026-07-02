# Release Checklist

TranslateDub AI ships as a Python package on PyPI. No code signing or notarization is
required — installs are via `pip`/`pipx`/`uvx`, so there is no Gatekeeper/SmartScreen
friction and no bundled-binary license obligation.

## Before tagging

* `git status --short` is clean.
* No secret-like files tracked (`config.json`, service-account JSON, API keys). The CI
  hygiene job enforces this.
* Bump the version in both `pyproject.toml` and `translatedub/__init__.py`.
* Add a dated section for the version in `CHANGELOG.md` (move items out of Unreleased).
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

## Tag — publishing is automatic

Publishing to PyPI is handled by `.github/workflows/release.yml` via **trusted
publishing** (OIDC, no tokens). Pushing a version tag builds, checks, and uploads:

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

The workflow refuses to publish if the tag does not match the `pyproject.toml` version.
One-time setup: on pypi.org, add this repo + `release.yml` + environment `pypi` as a
trusted publisher.

Manual fallback (only if the workflow is unavailable):

```bash
python -m pip install --upgrade build twine
python -m build && python -m twine check dist/*
python -m twine upload dist/*
```

## After tagging

* Create a GitHub Release for the tag with the `CHANGELOG.md` section as notes.
* No binaries to attach — the package lives on PyPI.
* Do not advertise the app as endorsed by Google, pyVideoTrans, Apple, or any third party.

---

## Tiếng Việt

TranslateDub AI phát hành dạng gói Python trên PyPI. Không cần ký app hay notarize.

### Trước khi tag

* `git status --short` sạch.
* Không track file giống secret (`config.json`, service-account JSON, API key). CI job
  hygiene sẽ chặn nếu có.
* Tăng version ở cả `pyproject.toml` và `translatedub/__init__.py`.
* Thêm mục phiên bản mới vào `CHANGELOG.md`.
* Cập nhật README nếu đổi flag hoặc hành vi.

### Kiểm tra & phát hành

```bash
pip install -e ".[dev,cloud]" && pytest
python -m bandit -q -r translatedub -ll
git tag vX.Y.Z && git push origin vX.Y.Z   # workflow release.yml tự build + đăng PyPI
```

* Tạo GitHub Release cho tag kèm changelog ngắn. Không cần attach binary.
* Không quảng cáo app như được Google, pyVideoTrans, Apple endorse.
