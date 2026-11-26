"""
setup_environments.py
=====================
Installs the conda environments of the pipeline:
  - guienv          (Python 3.11)   the GUI (GUI.py)
  - spots_analysis  (Python 3.12)   analysis (Newmain.py)
  - segment         (Python 3.10)   Cellpose 2 cell segmentation (the models trained with Cellpose 2)
  - cellpose3       (Python 3.10)   Cellpose 3 cell segmentation
  - cellpose4       (Python 3.10)   Cellpose 4 (Cellpose-SAM) cell segmentation
  - chinmospots     (Python 3.10)   EpySeg object detection
  - spotiflow       (Python 3.10)   Spotiflow object detection

FIRST THING TO DO (any system: Windows, macOS, Linux):
  1. Open the console of Anaconda / Miniconda / Miniforge: "Anaconda Prompt" on Windows, a terminal on macOS / Linux.
  2. Run:    python setup_environments.py
  3. When it has finished, it prints the two lines that start the GUI (open a console, `conda activate guienv`,
     `python GUI.py`). The GUI then checks that the environments needed by an analysis are installed.

Only the standard library of Python 3.7 or later is used, so the base environment of any recent Anaconda is enough.
The functions of this file are also used by the GUI (check of the environments, installation of the missing ones):
keep this file next to the GUI.

Options:
    python setup_environments.py --check              only tells which environments are installed and working
    python setup_environments.py --only segment       only these environments
    python setup_environments.py --device cuda        PyTorch with NVIDIA GPU support (default: auto = GPU if nvidia-smi
                                                      is found, otherwise cpu); also --device cpu
    python setup_environments.py --force              recreate the environments from scratch
    python setup_environments.py --yes                answer yes to the questions (conda terms of service)
    python setup_environments.py --conda /path/to/conda    if conda is not found by itself
"""

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import textwrap

if sys.version_info < (3, 7):
    sys.exit("This script needs Python 3.7 or later (the base environment of a recent Anaconda has it).")

# ─────────────────────────────────────────────────────────────────────────────
# Configuration — pip package lists per environment
# ─────────────────────────────────────────────────────────────────────────────
ENVS = {
    "guienv": {
        "python": "3.11",
        "pip_steps": [
            ["numpy", "scipy", "pandas", "openpyxl"],
            ["matplotlib", "tifffile"],
            ["PyQt6"],
        ],
    },
    "spots_analysis": {
        "python": "3.12",
        "pip_steps": [
            # numpy pinned for ABI compat with czifile / aicspylibczi
            ["numpy==1.26.4"],
            ["scipy"],
            ["pandas", "openpyxl"],
            ["scikit-learn"],
            ["matplotlib"],
            ["tifffile"],
            ["imageio"],
            ["czifile"],
            ["aicspylibczi"],
            ["spyder-kernels==3.1.4"],
        ],
    },
    "segment": {
        "python": "3.10",
        "pip_steps": [
            # numpy 2.x is compatible with cellpose 2.2.3
            ["numpy==2.0.2"],
            ["cellpose==2.2.3"],
            ["tifffile", "matplotlib"],
            ["spyder-kernels==3.1.4"],
        ],
    },
    "cellpose3": {
        "python": "3.10",
        "pip_steps": [
            ["@TORCH@"],                       # replaced by the PyTorch install line of the chosen --device
            ["numpy==2.0.2"],                  # cellpose 3 needs numpy < 2.1
            ["cellpose==3.1.1.3"],
            ["tifffile", "matplotlib"],
            ["spyder-kernels==3.1.4"],
        ],
    },
    "cellpose4": {
        "python": "3.10",
        "pip_steps": [
            ["@TORCH@"],
            ["cellpose>=4,<5"],
            ["tifffile", "matplotlib"],
            ["spyder-kernels==3.1.4"],
        ],
    },
    "chinmospots": {
        "python": "3.10",
        "pip_steps": [
            ["numpy==1.26.3"],
            ["matplotlib", "pandas", "tifffile"],
            ["epyseg"],
            ["batoolset"],
            ["spyder-kernels==3.1.4"],
        ],
    },
    "spotiflow": {
        "python": "3.10",
        "pip_steps": [
            # PyTorch is installed by spotiflow itself (CPU or the default build of the machine);
            # numpy is left free: pip picks the version spotiflow and torch agree on.
            ["@TORCH@"],
            ["tifffile", "pandas"],
            ["spotiflow"],
            ["spyder-kernels==3.1.4"],
        ],
    },
}

# Quick smoke-test imports (skipped for heavy ones like cellpose / epyseg)
VERIFY = {
    "guienv":         ["numpy", "scipy", "pandas", "openpyxl", "matplotlib", "tifffile", "PyQt6.QtCore"],
    "spots_analysis": ["numpy", "scipy", "pandas", "sklearn", "tifffile", "matplotlib", "imageio"],
    "segment":        ["numpy", "tifffile", "matplotlib"],
    "cellpose3":      ["numpy", "tifffile", "torch", "from cellpose import models"],
    "cellpose4":      ["numpy", "tifffile", "torch", "from cellpose import models"],
    "chinmospots":    ["numpy", "tifffile", "matplotlib"],
    "spotiflow":      ["numpy", "pandas", "tifffile", "from spotiflow.model import Spotiflow"],
}

# What each analysis step needs (used by the GUI to install only what the chosen parameters require)
ENV_FOR = {"gui": "guienv", "analysis": "spots_analysis", "cells": "segment", "cells2": "segment",
           "cells3": "cellpose3", "cells4": "cellpose4", "epyseg": "chinmospots", "spotiflow": "spotiflow"}
CELLPOSE_ENV = {2: "segment", 3: "cellpose3", 4: "cellpose4"}      # environment of each Cellpose version

GUI_FILE = "GUI.py"
ANACONDA_CHANNELS = ["https://repo.anaconda.com/pkgs/main", "https://repo.anaconda.com/pkgs/r",
                     "https://repo.anaconda.com/pkgs/msys2"]

# ─────────────────────────────────────────────────────────────────────────────
# Console helpers
# ─────────────────────────────────────────────────────────────────────────────
IS_WINDOWS = sys.platform == "win32"
ASSUME_YES = False

for _stream in (sys.stdout, sys.stderr):                 # old Windows consoles: no crash on ✔ ✗ ▸
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if IS_WINDOWS:
    os.system("")                                        # switches on the colours of the Windows 10+ console
_use_colour = bool(getattr(sys.stdout, "isatty", lambda: False)())


def _c(code, text):
    return "\033[{}m{}\033[0m".format(code, text) if _use_colour else text


def ok(msg):   print(_c("32", "  ✔  " + msg))
def err(msg):  print(_c("31", "  ✗  " + msg))
def info(msg): print(_c("36", "  ▸  " + msg))
def warn(msg): print(_c("33", "  ⚠  " + msg))
def head(msg): print(_c("1;34", "\n" + "═" * 60 + "\n  " + msg + "\n" + "═" * 60))


def ask_yes_no(question):
    """True if the user agrees. Without a keyboard (the GUI) the answer is no, unless --yes was given."""
    if ASSUME_YES:
        return True
    try:
        if not sys.stdin or not sys.stdin.isatty():
            return False
        return input("  ?  {} [y/N] ".format(question)).strip().lower() in ("y", "yes", "o", "oui")
    except (EOFError, OSError):
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Locate conda
# ─────────────────────────────────────────────────────────────────────────────
def _conda_in_root(root):
    """The conda executable of an Anaconda / Miniconda / Miniforge installation directory, or None."""
    if IS_WINDOWS:
        names = [("Scripts", "conda.exe"), ("condabin", "conda.bat"), ("Library", "bin", "conda.bat")]
    else:
        names = [("bin", "conda"), ("condabin", "conda")]
    for parts in names:
        candidate = os.path.join(root, *parts)
        if os.path.isfile(candidate):
            return candidate
    return None


def find_conda(hint=None):
    """Path of the conda executable (any recent Anaconda, Miniconda, Miniforge, on any system)."""
    if hint and os.path.isfile(hint):
        return hint

    exe = os.environ.get("CONDA_EXE")                    # set by every initialised conda console
    if exe and os.path.isfile(exe):
        return exe

    found = shutil.which("conda")
    if found:
        return found

    # the interpreter running this script may be the one of conda (base environment, or an environment of it)
    roots = []
    for prefix in {sys.prefix, getattr(sys, "base_prefix", sys.prefix), os.environ.get("CONDA_PREFIX", "")}:
        if not prefix:
            continue
        roots.append(prefix)
        norm = os.path.normpath(prefix)
        if os.path.basename(os.path.dirname(norm)) == "envs":
            roots.append(os.path.dirname(os.path.dirname(norm)))

    home = os.path.expanduser("~")
    names = ["anaconda3", "miniconda3", "miniforge3", "mambaforge", "anaconda", "miniconda", "Anaconda3",
             "Miniconda3", "Miniforge3"]
    bases = [home, os.path.join(home, "opt"), os.path.join(home, ".conda")]
    if IS_WINDOWS:
        bases += [os.path.join(home, "AppData", "Local"), os.environ.get("ProgramData", r"C:\ProgramData"),
                  "C:\\", os.path.join(home, "AppData", "Local", "Programs")]
    else:
        bases += ["/opt", "/usr/local", "/usr/share", "/Applications", "/root"]
    for base in bases:
        for name in names:
            roots.append(os.path.join(base, name))

    for root in roots:
        candidate = _conda_in_root(root)
        if candidate:
            return candidate

    raise RuntimeError(
        "conda not found.\n"
        "Options:\n"
        "  1. Run this script from the console of Anaconda (Anaconda Prompt on Windows).\n"
        "  2. Run:  python setup_environments.py --conda /full/path/to/conda")


# ─────────────────────────────────────────────────────────────────────────────
# conda helpers
# ─────────────────────────────────────────────────────────────────────────────
def _run(cmd, **kwargs):
    return subprocess.run(cmd, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          **kwargs)


def env_prefix(conda, name):
    """Directory of the environment, or None if it does not exist."""
    try:
        r = subprocess.run([conda, "env", "list", "--json"], universal_newlines=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for path in json.loads(r.stdout).get("envs", []):
            if os.path.basename(os.path.normpath(path)) == name:
                return path
    except Exception:
        pass
    return None


def python_of(prefix):
    exe = os.path.join(prefix, "python.exe") if IS_WINDOWS else os.path.join(prefix, "bin", "python")
    return exe if os.path.isfile(exe) else None


def find_env_python(name, conda=None):
    """Python interpreter of the environment <name>, or None. Asks conda, then looks in the usual places."""
    try:
        conda = conda or find_conda(None)
    except RuntimeError:
        conda = None
    if conda:
        prefix = env_prefix(conda, name)
        if prefix and python_of(prefix):
            return python_of(prefix)
        # envs directory of the installation the executable belongs to
        root = os.path.dirname(os.path.dirname(os.path.realpath(conda)))
        for guess in (os.path.join(root, "envs", name), os.path.join(os.path.dirname(root), "envs", name)):
            if python_of(guess):
                return python_of(guess)
    home = os.path.expanduser("~")
    for base in (home, os.path.join(home, "opt"), os.path.join(home, "AppData", "Local"), "/opt", "/usr/local",
                 os.environ.get("ProgramData", "C:\\ProgramData")):
        for inst in ("anaconda3", "miniconda3", "miniforge3", "mambaforge"):
            guess = os.path.join(base, inst, "envs", name)
            if python_of(guess):
                return python_of(guess)
    return None


def env_exists(conda, name):
    return env_prefix(conda, name) is not None


def remove_env(conda, name):
    info("Removing existing environment '{}'…".format(name))
    r = _run([conda, "env", "remove", "-n", name, "-y"])
    if r.returncode != 0:
        warn("Could not cleanly remove '{}' — continuing anyway.".format(name))


def accept_terms(conda):
    """Recent conda versions refuse to use the Anaconda channels until their terms of service are accepted."""
    info("Anaconda asks to accept its terms of service (https://www.anaconda.com/legal) before installing packages.")
    if not ask_yes_no("Accept the terms of service of the Anaconda channels now?"):
        warn("Not accepted. Accept them yourself with:  conda tos accept --override-channels --channel "
             + ANACONDA_CHANNELS[0] + "   (same for the .../r and .../msys2 channels), or run this script "
             "with --yes.")
        return False
    done = False
    for channel in ANACONDA_CHANNELS:
        r = _run([conda, "tos", "accept", "--override-channels", "--channel", channel])
        done = done or r.returncode == 0
    return done


def create_env(conda, name, python_ver, force=False):
    if env_exists(conda, name):
        if force:
            remove_env(conda, name)
        else:
            warn("'{}' already exists — skipping creation (use --force to recreate).".format(name))
            return True

    info("Creating '{}' with Python {}…".format(name, python_ver))
    base_cmd = [conda, "create", "-n", name, "python=" + python_ver, "-y", "-q"]
    r = _run(base_cmd)
    if r.returncode != 0 and ("Terms of Service" in r.stdout or "CondaToS" in r.stdout):
        if accept_terms(conda):
            r = _run(base_cmd)
    if r.returncode != 0:                                  # last resort: the conda-forge channel only
        warn("Default channels failed — trying conda-forge.")
        r = _run(base_cmd + ["--override-channels", "-c", "conda-forge"])
    if r.returncode == 0:
        ok("Created '{}'.".format(name))
        return True
    err("Failed to create '{}'.".format(name))
    print(r.stdout[-2000:])
    return False


def pip_install(conda, name, packages, retries=2):
    """
    Runs `<python of the environment> -m pip install <packages>` (does not depend on `conda run`, which differs between
    conda versions). Prints the progress lines. Returns True on success, False after all retries.
    """
    py = find_env_python(name, conda)
    if not py:
        err("Python of '{}' not found.".format(name))
        return False
    cmd = [py, "-m", "pip", "install", "--no-warn-script-location", "--disable-pip-version-check"] + packages
    label = " ".join(packages[:4]) + ("…" if len(packages) > 4 else "")
    for attempt in range(1, retries + 2):
        info("pip install {}  [attempt {}]".format(label, attempt))
        proc = subprocess.Popen(cmd, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        tail = []
        for line in proc.stdout:
            line = line.rstrip()
            tail = (tail + [line])[-25:]
            if re.match(r"(Collecting|Downloading|Installing collected|Successfully)", line):
                print("      " + line[:110])
        proc.wait()
        if proc.returncode == 0:
            ok("Installed: " + label)
            return True
        print("\n".join(tail))
        if attempt <= retries:
            warn("Retrying ({}/{})…".format(attempt, retries))
    err("Failed permanently: pip install " + label)
    return False


DEVICE = "auto"


def resolve_device(device=None):
    """'cpu' or 'cuda'. auto = cuda when an NVIDIA driver is found (nvidia-smi), cpu otherwise."""
    device = (device or DEVICE or "auto").lower()
    if device == "auto":
        return "cuda" if shutil.which("nvidia-smi") else "cpu"
    return device


def torch_step(device=None):
    """pip arguments installing PyTorch for the device. Windows: the default wheel is CPU only, the CUDA one
    comes from the PyTorch index. Linux: the default wheel has CUDA, the CPU one comes from the PyTorch index.
    macOS: one build (Apple GPU is used automatically when present)."""
    device = resolve_device(device)
    base = ["torch", "torchvision"]
    if sys.platform == "darwin":
        return base
    if device == "cuda":
        return base + ["--index-url", "https://download.pytorch.org/whl/cu124"] if IS_WINDOWS else base
    return base if IS_WINDOWS else base + ["--index-url", "https://download.pytorch.org/whl/cpu"]


def install_env(conda, name, pip_steps):
    failures = []
    pip_steps = [torch_step() if step == ["@TORCH@"] else step for step in pip_steps]
    for step in pip_steps:
        if not pip_install(conda, name, step):
            failures.append(step)
    if failures:
        err("Package failures in '{}':".format(name))
        for f in failures:
            print("    pip install " + " ".join(f))
        return False
    return True


def verify_env(conda, name, imports, quiet=False):
    if not imports:
        return True
    py = find_env_python(name, conda)
    if not py:
        if not quiet:
            warn("Python of '{}' not found.".format(name))
        return False
    code = "; ".join(m if m.startswith("from ") else "import " + m for m in imports)
    r = _run([py, "-c", code])
    if r.returncode == 0:
        if not quiet:
            ok("Verification passed for '{}'.".format(name))
        return True
    if not quiet:
        warn("Verification failed for '{}':".format(name))
        print(r.stdout[-800:])
    return False


def environment_status(conda, names=None):
    """{name: 'ok' | 'broken' | 'missing'} for the environments (used by --check and by the GUI)."""
    status = {}
    for name in (names or list(ENVS.keys())):
        if not env_exists(conda, name):
            status[name] = "missing"
        else:
            status[name] = "ok" if verify_env(conda, name, VERIFY.get(name, []), quiet=True) else "broken"
    return status


def launch_instructions():
    here = os.path.dirname(os.path.abspath(__file__))
    gui = os.path.join(here, GUI_FILE)
    lines = ["To start the GUI, open the console of Anaconda (Anaconda Prompt on Windows, a terminal elsewhere):",
             "      conda activate guienv",
             '      cd "{}"'.format(here),
             "      python " + GUI_FILE]
    py = find_env_python("guienv")
    if py:
        lines += ["or, in one line, from any console:", '      "{}" "{}"'.format(py, gui)]
    return lines


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
def main():
    global ASSUME_YES
    parser = argparse.ArgumentParser(
        description="Install the conda environments of the pipeline (GUI included).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python setup_environments.py
              python setup_environments.py --check
              python setup_environments.py --force --only segment chinmospots
              python setup_environments.py --conda C:/Users/Me/anaconda3/Scripts/conda.exe
        """))
    parser.add_argument("--conda",       metavar="PATH", help="Path to conda executable.")
    parser.add_argument("--force",       action="store_true", help="Recreate environments from scratch.")
    parser.add_argument("--skip-verify", action="store_true", help="Skip import verification.")
    parser.add_argument("--check",       action="store_true", help="Only report the state of the environments.")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto",
                        help="PyTorch build for Cellpose 3/4 and Spotiflow: auto (GPU if an NVIDIA driver is found), "
                             "cpu or cuda.")
    parser.add_argument("--yes", "-y",   action="store_true", help="Answer yes to the questions.")
    parser.add_argument("--only", nargs="+", metavar="ENV", choices=list(ENVS.keys()),
                        help="Only process these environments ({}).".format(", ".join(ENVS)))
    args = parser.parse_args()
    ASSUME_YES = args.yes
    global DEVICE
    DEVICE = args.device

    # ── find conda ──────────────────────────────────────────────────────────
    try:
        conda = find_conda(args.conda)
    except RuntimeError as e:
        err(str(e))
        sys.exit(1)

    ok("conda: " + conda)
    info("Platform   : {} {}".format(platform.system(), platform.machine()))
    info("Host Python: " + sys.version.split()[0])
    info("Conda      : " + _run([conda, "--version"]).stdout.strip())

    targets = args.only or list(ENVS.keys())
    dev = resolve_device()
    info("PyTorch device: {}{}".format(dev, " (detected)" if args.device == "auto" else ""))
    if dev == "cuda" and IS_WINDOWS:
        info("Note: EpySeg (TensorFlow) cannot use the GPU natively on Windows (TensorFlow > 2.10); "
             "it runs on CPU unless installed under WSL2. Cellpose and Spotiflow use the GPU.")

    if args.check:
        head("State of the environments")
        bad = False
        for name, state in environment_status(conda, targets).items():
            (ok if state == "ok" else err)("{:16s}  {}".format(name, state))
            bad = bad or state != "ok"
        sys.exit(1 if bad else 0)

    results = {}
    for name in targets:
        cfg = ENVS[name]
        head("{}  (Python {})".format(name, cfg["python"]))

        if not create_env(conda, name, cfg["python"], force=args.force):
            results[name] = "FAILED — creation"
            continue

        if not install_env(conda, name, cfg["pip_steps"]):
            results[name] = "FAILED — install"
            continue

        if args.skip_verify:
            results[name] = "OK (verify skipped)"
        else:
            ok_v = verify_env(conda, name, VERIFY.get(name, []))
            results[name] = "OK" if ok_v else "OK (verify warnings)"

    # ── summary ─────────────────────────────────────────────────────────────
    head("Summary")
    any_fail = False
    for name in targets:
        status = results.get(name, "SKIPPED")
        if "FAILED" in status:
            err("{:20s}  {}".format(name, status))
            any_fail = True
        elif "warn" in status.lower():
            warn("{:20s}  {}".format(name, status))
        else:
            ok("{:20s}  {}".format(name, status))

    if any_fail:
        print()
        warn("Some environments failed. Tips:")
        warn("  • Re-run with --force to start from scratch.")
        warn("  • Re-run with --only <env_name> to retry just one environment.")
        warn("  • Install a failed package manually:")
        warn("      <python of the environment> -m pip install <package>")
        sys.exit(1)
    else:
        print()
        ok("All environments are ready.")
        if "guienv" in targets:
            print()
            for line in launch_instructions():
                info(line)


if __name__ == "__main__":
    main()
