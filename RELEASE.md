# PicoRouter Release Checklist

## Pre-Release

- [ ] Run tests locally
  ```bash
  make test
  ```

- [ ] Run coverage check
  ```bash
  make coverage
  ```
  Target: >80% coverage

- [ ] Check syntax
  ```bash
  python -m py_compile picorouter.py
  ```

- [ ] Update version in `picorouter.py`
  ```python
  __version__ = "0.x.0"
  ```

- [ ] Update CHANGELOG.md with:
  - New features
  - Bug fixes
  - Breaking changes (if any)

## CI/CD Verification

- [ ] All CI checks pass on GitHub
  - Tests pass
  - Coverage report generated
  - No lint errors

- [ ] GitHub Actions workflow runs successfully

## Release

- [ ] Create git tag
  ```bash
  git tag -a v0.x.0 -m "Release v0.x.0"
  git push origin v0.x.0
  ```

- [ ] Verify tag on GitHub

- [ ] Create GitHub Release with:
  - Release notes from CHANGELOG
  - Download link (if applicable)

## Post-Release

- [ ] Update version to next dev version
  ```python
  __version__ = "0.x.1-dev"
  ```

- [ ] Announce (if applicable)

---

## Quick Commands

```bash
# Full pre-release check
make test && make coverage && python -m py_compile picorouter.py

# Release tag
git tag -a v$(grep '__version__' picorouter.py | cut -d'"' -f2) -m "Release"
```
