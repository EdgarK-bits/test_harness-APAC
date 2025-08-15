# https://drive.google.com/file/d/1yCfbs1A7BpMDjF2ZXqkUFgDF_YKzO-Y_/view?usp=sharing

#!/usr/bin/env python3
# run_zip_harness.py
#
# Examples:
#   python3 run_zip_harness.py --gdrive "https://drive.google.com/file/d/1AbC.../view?usp=sharing"
#   python3 run_zip_harness.py --gdrive 1AbCDefGhIjKlMnOpQRsTuvWxYz-12345
#   python3 run_zip_harness.py --zip 1942G_TestCases.zip
#   python3 run_zip_harness.py --zip /path/to/ZIP --cpp solution.cpp --compiler g++-14 --compare tokens
#
# ZIP must contain:
#   <ID>_Input_TestCase_<N>.txt
#   <ID>_Output_TestCase_<N>.txt
#
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time, zipfile, hashlib
from pathlib import Path
from difflib import unified_diff
from urllib.parse import urlparse, parse_qs
from urllib.request import urlretrieve

ID_RE   = r"(?P<id>[A-Za-z0-9]+)"
KIND_RE = r"(?P<kind>Input|Output)"
NUM_RE  = r"(?P<num>\d+)"
NAME_RE = re.compile(rf"^{ID_RE}_{KIND_RE}_TestCase_{NUM_RE}\.txt$")

def sha256_path(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

# ---------------- Google Drive helpers ----------------
def extract_drive_id(s: str) -> str | None:
    """Accepts a Drive URL or raw ID, returns file ID or None."""
    s = s.strip()
    # raw ID (no slashes/spaces, typical 25+ chars)
    if "/" not in s and " " not in s and len(s) >= 20:
        return s
    try:
        u = urlparse(s)
        if "drive.google.com" not in u.netloc:
            return None
        # /file/d/<id>/view
        parts = u.path.strip("/").split("/")
        if "file" in parts and "d" in parts:
            i = parts.index("d")
            if i + 1 < len(parts):
                return parts[i + 1]
        # uc?id=<id>
        q = parse_qs(u.query)
        if "id" in q:
            return q["id"][0]
    except Exception:
        return None
    return None

def download_from_drive(file_id: str, out_path: Path):
    """
    Try gdown first (best handling). If unavailable, fallback to a simple direct URL.
    For typical small/medium zips this works fine.
    """
    used = None
    try:
        import gdown   # type: ignore
        url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url, str(out_path), quiet=False)
        used = "gdown"
    except Exception:
        # Fallback: simple URL retrieve (may fail on very large files with virus check)
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        urlretrieve(url, str(out_path))
        used = "urllib"
    if not out_path.exists() or out_path.stat().st_size == 0:
        print("[!] Failed to download ZIP from Drive.")
        sys.exit(1)
    print(f"[+] Downloaded ZIP via {used} -> {out_path.name} ({out_path.stat().st_size} bytes)")

# ---------------- ZIP + case discovery ----------------
def extract_zip(zip_path: Path, dest: Path):
    if not zipfile.is_zipfile(zip_path):
        print(f"[!] Not a valid ZIP: {zip_path}")
        sys.exit(1)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(dest)

def discover_cases(root: Path):
    """Return: id_str, {num: input_path}, {num: output_path}, issues[]"""
    inputs, outputs, issues = {}, {}, []
    ids_seen = set()
    for p in sorted(root.glob("**/*.txt")):
        m = NAME_RE.match(p.name)
        if not m:
            issues.append(f"IGNORING unexpected file name: {p.name}")
            continue
        pid, kind, num = m["id"], m["kind"], int(m["num"])
        ids_seen.add(pid)
        (inputs if kind == "Input" else outputs)[num] = p

    if not ids_seen:
        return None, inputs, outputs, ["No properly named test files found."]
    if len(ids_seen) > 1:
        issues.append(f"Multiple IDs detected in ZIP: {sorted(ids_seen)}")
    id_str = sorted(ids_seen)[0]
    return id_str, inputs, outputs, issues

# ---------------- Build + run ----------------
def compile_cpp(cpp: Path, exe: Path, compiler: str):
    cmds = [
        [compiler, "-std=gnu++17", "-O2", "-pipe", str(cpp), "-o", str(exe)],
        [compiler, "-std=c++17",   "-O2", "-pipe", str(cpp), "-o", str(exe)],  # fallback
    ]
    last_err = None
    for cmd in cmds:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            return
        last_err = r.stderr
    print("Compilation failed:\n", last_err or "")
    sys.exit(1)

def run_case(exe: Path, input_text: str, timeout_s: int) -> tuple[str, str, int, float]:
    t0 = time.perf_counter()
    proc = subprocess.run([str(exe)],
                          input=input_text, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=timeout_s)
    dt_ms = (time.perf_counter() - t0) * 1000.0
    return proc.stdout, proc.stderr, proc.returncode, dt_ms

def tokens(s: str):
    return s.replace("\r\n","\n").replace("\r","\n").strip().split()

# ---------------- Main ----------------
def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--gdrive", help="Google Drive link or file ID of the ZIP")
    src.add_argument("--zip",    help="Path to a local ZIP")
    ap.add_argument("--cpp", default="solution.cpp", help="C++ source file")
    ap.add_argument("--compiler", default=os.getenv("CF_CXX", "g++-14"),
                    help="Compiler (e.g., g++-14, g++, clang++)")
    ap.add_argument("--compare", choices=["exact","tokens"], default="exact",
                    help="Comparison mode")
    ap.add_argument("--timeout", type=int, default=30, help="Per-test timeout (s)")
    ap.add_argument("--outdir", default="results", help="Directory for reports")
    args = ap.parse_args()

    base = Path.cwd()
    outdir = base / args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    diffs_dir = outdir / "diffs"
    diffs_dir.mkdir(exist_ok=True)

    # Acquire ZIP
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        if args.gdrive:
            file_id = extract_drive_id(args.gdrive)
            if not file_id:
                print("[!] Could not extract file ID from provided --gdrive value.")
                sys.exit(1)
            zip_path = td_path / "testcases.zip"
            download_from_drive(file_id, zip_path)
        else:
            zip_path = Path(args.zip).resolve()
            if not zip_path.exists():
                print(f"[!] ZIP not found: {zip_path}")
                sys.exit(1)

        # Extract & discover
        stage = td_path / "unzipped"
        stage.mkdir(parents=True, exist_ok=True)
        extract_zip(zip_path, stage)
        pid, inputs, outputs, issues = discover_cases(stage)
        if pid is None:
            print("\n".join(issues))
            sys.exit(1)

        missing_in  = sorted(set(outputs) - set(inputs))
        missing_out = sorted(set(inputs)  - set(outputs))
        if missing_in:
            issues.append(f"Missing input files for cases: {missing_in}")
        if missing_out:
            issues.append(f"Missing output files for cases: {missing_out}")

        if issues:
            print("== ZIP issues detected ==")
            for msg in issues:
                print("-", msg)
            if missing_in or missing_out:
                sys.exit(1)

        pairs = [(n, inputs[n], outputs[n]) for n in sorted(inputs.keys())]

        # Compile once (prefer requested compiler if present)
        compiler = args.compiler if shutil.which(args.compiler) else ("g++" if shutil.which("g++") else "clang++")
        exe_path = base / (pid + "_exec")
        compile_cpp(Path(args.cpp), exe_path, compiler)

        # Run cases
        results = []
        failed = 0
        for n, in_path, out_path in pairs:
            in_txt  = in_path.read_text(encoding="utf-8")
            exp_txt = out_path.read_text(encoding="utf-8")

            got_out, got_err, rc, dt_ms = run_case(exe_path, in_txt, args.timeout)

            if args.compare == "tokens":
                ok = tokens(got_out) == tokens(exp_txt)
            else:
                ok = got_out.replace("\r\n","\n").strip() == exp_txt.replace("\r\n","\n").strip()

            if not ok:
                failed += 1
                diff = "\n".join(unified_diff(
                    exp_txt.replace("\r\n","\n").splitlines(),
                    got_out.replace("\r\n","\n").splitlines(),
                    fromfile=f"expected_{n}.txt",
                    tofile=f"got_{n}.txt",
                    lineterm=""
                ))
                (diffs_dir / f"diff_{n}.patch").write_text(diff, encoding="utf-8")

            results.append({
                "case": n,
                "status": "PASS" if ok else "FAIL",
                "runtime_ms": round(dt_ms, 3),
                "return_code": rc,
                "stdin_file": str(in_path),
                "expected_file": str(out_path),
                "stdout_len": len(got_out),
                "stderr_len": len(got_err),
                "stdout_sample": got_out[:2000],
            })

    # Write reports (outside tempdir so they persist)
    summary_line = ("All passed" if failed == 0 else f"{failed} out of {len(results)} failed")
    (outdir / "summary.txt").write_text(summary_line + "\n", encoding="utf-8")

    lines = ["case,status,runtime_ms,return_code"]
    for r in results:
        lines.append(f'{r["case"]},{r["status"]},{r["runtime_ms"]},{r["return_code"]}')
    (outdir / "report.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "source": ("gdrive" if args.gdrive else "zip"),
        "zip": str(zip_path),
        "zip_sha256": sha256_path(zip_path) if Path(zip_path).exists() else None,
        "cpp": str(Path(args.cpp).resolve()),
        "compiler": compiler,
        "compare_mode": args.compare,
        "results": results,
    }
    (outdir / "report.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(summary_line)

if __name__ == "__main__":
    main()
