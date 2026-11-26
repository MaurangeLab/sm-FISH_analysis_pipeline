"""
fiji_tools.py
=============
Helpers to run the Trainable Weka Segmentation of Fiji without its interface (headless).
Standard library only: used by the GUI (check of the Fiji location) and by segmentation_weka.py.
Fiji brings its own Java: nothing else has to be installed.
"""
import glob
import os
import subprocess
import sys

EXE_NAMES = {
    "win32": ["ImageJ-win64.exe", "fiji-windows-x64.exe", "ImageJ-win32.exe"],
    "darwin": ["Contents/MacOS/fiji-macos", "Contents/MacOS/ImageJ-macosx", "Contents/MacOS/fiji-macos-arm64",
               "Contents/MacOS/ImageJ-macosx-arm64"],
    "linux": ["ImageJ-linux64", "fiji-linux-x64", "fiji-linux-arm64", "ImageJ-linux32"],
}


def find_executable(location):
    """Launcher of Fiji from what the user gave: the Fiji.app folder (or the one that holds it) or the launcher itself.
    None when nothing usable is found."""
    if not location:
        return None
    location = os.path.normpath(os.path.expanduser(str(location)))
    if os.path.isfile(location):
        return location if os.access(location, os.X_OK) or sys.platform == "win32" else None
    if not os.path.isdir(location):
        return None
    key = "win32" if sys.platform == "win32" else ("darwin" if sys.platform == "darwin" else "linux")
    roots = [location, os.path.join(location, "Fiji.app"), os.path.join(location, "Fiji")]
    if location.endswith(".app"):
        roots.insert(0, location)
    for root in roots:
        for name in EXE_NAMES[key]:
            exe = os.path.join(root, name)
            if os.path.isfile(exe):
                return exe
    return None


def fiji_root(executable):
    """Folder that holds plugins/ and jars/ for a launcher."""
    here = os.path.dirname(os.path.abspath(executable))
    for cand in (here, os.path.dirname(here), os.path.dirname(os.path.dirname(here))):
        if os.path.isdir(os.path.join(cand, "plugins")) or os.path.isdir(os.path.join(cand, "jars")):
            return cand
    return here


def has_weka(executable):
    """True when the Trainable Weka Segmentation plugin is installed in this Fiji."""
    root = fiji_root(executable)
    patterns = [os.path.join(root, sub, "*rainable_?egmentation*.jar") for sub in ("plugins", "jars")]
    return any(glob.glob(p) for p in patterns)


def check(location):
    """(ok, message) for the Fiji location given by the user."""
    exe = find_executable(location)
    if exe is None:
        return False, "Fiji launcher not found here (select the Fiji.app folder or its launcher)."
    if not has_weka(exe):
        return False, ("Fiji found, but the Trainable Weka Segmentation plugin is missing "
                       "(Fiji: Help > Update… and tick the 'Trainable Segmentation' update site).")
    return True, f"Fiji found: {exe}"


GROOVY = '''#@ String inPath
#@ String outPath
#@ String modelPath
#@ String mode
// Applies a Trainable Weka Segmentation classifier and saves the probability maps:
// output stack = for each input plane z, one slice per class (index z * nClasses + class).
import ij.IJ
import ij.ImagePlus
import ij.ImageStack
import trainableSegmentation.WekaSegmentation

def imp = IJ.openImage(inPath)
def out = null
if (mode == "2d") {
    // plane by plane: the classifier never sees the neighbouring planes
    for (int i = 1; i <= imp.getStackSize(); i++) {
        def plane = new ImagePlus("plane", imp.getStack().getProcessor(i).duplicate())
        def seg = new WekaSegmentation(plane)
        if (!seg.loadClassifier(modelPath)) { throw new RuntimeException("Cannot load classifier " + modelPath) }
        def res = seg.applyClassifier(plane, 0, true)
        if (out == null) { out = new ImageStack(res.getWidth(), res.getHeight()) }
        for (int k = 1; k <= res.getStackSize(); k++) { out.addSlice(res.getStack().getProcessor(k)) }
    }
} else {
    def seg = new WekaSegmentation(true)
    seg.setTrainingImage(imp)
    if (!seg.loadClassifier(modelPath)) { throw new RuntimeException("Cannot load classifier " + modelPath) }
    def res = seg.applyClassifier(imp, 0, true)
    out = res.getStack()
}
IJ.saveAs(new ImagePlus("probabilities", out), "Tiff", outPath)
println("WEKA_DONE")
'''


def run_weka(executable, workdir, in_path, out_path, model_path, mode, log=print):
    """Runs the classifier in Fiji (headless). Raises RuntimeError with the end of Fiji's output on failure."""
    script = os.path.join(workdir, "weka_apply.groovy")
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(GROOVY)
    args = 'inPath="{}",outPath="{}",modelPath="{}",mode="{}"'.format(
        in_path.replace("\\", "/"), out_path.replace("\\", "/"), model_path.replace("\\", "/"), mode)
    cmd = [executable, "--headless", "--console", "--run", script, args]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                          encoding="utf-8", errors="replace")
    tail = "\n".join(proc.stdout.strip().splitlines()[-25:])
    if proc.returncode != 0 or not os.path.isfile(out_path):
        raise RuntimeError("Fiji (Weka) failed (exit code {}):\n{}".format(proc.returncode, tail))
    log(tail.splitlines()[-1] if tail else "")
