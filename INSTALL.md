# Install & fix pip

## Execution policy (PowerShell script won’t run)

If you see **“running scripts is disabled”** or an execution policy error when running `.\install.ps1`:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

That allows local scripts (like `install.ps1`) to run. To allow **any** script for your user (most permissive):

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser
```

You only need to do this once. Then run `.\install.ps1` again.

---

## “Scripts are installed in '...\Scripts' which is not on PATH”

If pip warns that **pip.exe** (and similar) are in a folder not on PATH, add that folder for your user:

**PowerShell (run once, permanent for your user):**
```powershell
$scripts = "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\Scripts"
if (Test-Path $scripts) {
  [Environment]::SetEnvironmentVariable("Path", $env:Path + ";$scripts", "User")
  $env:Path = $env:Path + ";$scripts"
  Write-Host "Added to PATH: $scripts"
} else {
  Write-Host "Not found: $scripts — check your Python install path and add its Scripts folder to PATH in System Properties."
}
```

If you use a different Python version, replace `3.14` with your version (e.g. `3.12`). Then **close and reopen** the terminal so `pip` is found.

---

## Errors you might see (and fixes)

| Error | Fix |
|-------|-----|
| **`pip : The term 'pip' is not recognized`** | Don’t run `pip` by itself. Use **`python -m pip`** (see “Install this project” below). Or run **`.\install.ps1`** from the repo root. |
| **`Python was not found; run without arguments to install from the Microsoft Store`** | See **“I already installed Python”** below. |
| **`then` or command chaining doesn’t work** | In PowerShell you can’t use `then` like in bash. Run **one command per line**, or use **`.\install.ps1`** to do both steps. |

---

## I already installed Python but the terminal says “Python was not found”

Try these in order:

1. **Close and reopen PowerShell** (or Cursor’s terminal) so it picks up the updated PATH.
2. **Use the Python launcher** (often works when `python` doesn’t):
   ```powershell
   py -3 -m pip install -e unr_setup
   py -3 -m pip install -e backend
   ```
   Then run the scan with: `py -3 -m scanner.cli --yahoo --as-of 2025-03-07 -o watchlist.json` (from the `backend` folder).
3. **Turn off the Windows Store “python” alias** so your real Python is used:
   - Open **Settings** → **Apps** → **Advanced app settings** → **App execution aliases**.
   - Turn **Off** the toggles for **python.exe** and **python3.exe** (so they don’t open the Store).
4. **Confirm Python is on PATH**: in PowerShell run:
   ```powershell
   Get-Command python -ErrorAction SilentlyContinue
   where.exe python
   ```
   If nothing is found, reinstall Python from [python.org](https://www.python.org/downloads/) and **check “Add python.exe to PATH”** at the first screen of the installer.

If **`py -3`** works, you can always use that instead of `python` (e.g. `py -3 -m pip`, `py -3 .\install.ps1`).

---

## One-command install (recommended)

From the repo root in PowerShell:

```powershell
cd c:\Users\iotra\OneDrive\Documents\dev
.\install.ps1
```

The script finds Python (`python` or `py -3`), installs **unr_setup** then **backend** in the right order, and prints how to run the Friday scan.

---

## If you get "pip not found" or "pip error"

1. **Use Python’s module instead of the `pip` command**
   - Run:
     ```powershell
     python -m pip install --upgrade pip
     ```
   - Then install the project with `python -m pip` (see below).

2. **If `python` opens the Microsoft Store**
   - You don’t have a real Python yet. Install from [python.org](https://www.python.org/downloads/) (e.g. 3.11 or 3.12).
   - In the installer, check **“Add python.exe to PATH”**.
   - Close and reopen your terminal, then use `python -m pip` as above.

3. **If you use a virtual environment (recommended)**
   ```powershell
   cd c:\Users\iotra\OneDrive\Documents\dev
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   # Then install packages (see below).
   ```

---

## Install this project (correct order)

From the repo root `dev`:

```powershell
cd c:\Users\iotra\OneDrive\Documents\dev

# 1. Install unr_setup first (backend depends on it)
python -m pip install -e unr_setup

# 2. Install backend (scanner + yfinance)
python -m pip install -e backend
```

If you’re in a venv, run the same two lines after activating it.

---

## Run the Friday scan

```powershell
cd backend
python -m scanner.cli --yahoo --as-of 2025-03-07 -o watchlist_2025-03-07.json
```

---

## Only third-party libs (no editable packages)

```powershell
python -m pip install -r requirements.txt
```

Then you still need to run from the repo so `unr_setup` and `scanner` are on `PYTHONPATH`, or install them in editable form as above.

If you see a different pip error (e.g. SSL, permission, or a specific package), paste the full message and we can fix it.
