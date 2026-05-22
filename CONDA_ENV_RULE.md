# Conda Environment Rule

## Mandatory Rule

All development, testing, and execution work for this project must use the conda environment named **`text2audiobook`** (as declared in `environment.yml`).

## Required Commands

### One-time create / update environment

Create:

```sh
conda env create --file environment.yml
```

Update (re-run after any change to `environment.yml`):

```sh
conda env update --name text2audiobook --file environment.yml --prune
```

### Activate the environment for a session

```sh
conda activate text2audiobook
```

After activation, run python directly:

```sh
python main.py
python -m pytest tests
```

### One-shot equivalents (no activation)

If a single command is needed without an active session, use `conda run --name`:

```sh
conda run --name text2audiobook python main.py
conda run --name text2audiobook python -m pytest tests
```

## Enforcement

- Do not use the base interpreter for this repository.
- Do not install project dependencies into the global Python environment.
- All future commands for this project assume `conda activate text2audiobook` has been run, OR use `conda run --name text2audiobook ...` for single-shot invocations.
- Never use the legacy `--prefix .conda` pattern — the named env is the source of truth.

## Reactivating after shell restart

```sh
conda activate text2audiobook
```

Each new terminal session requires re-activation.
