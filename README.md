# Test Harness – User Guide

This harness compiles a C++ solution, runs it against a bundle of test cases packaged in a single ZIP, and reports **PASS/FAIL** per case with a one-line summary.



## 1) What you need

* **Python 3.8+**
* A C++ compiler:

  * Prefer **GNU g++** (e.g., `g++-14` via Homebrew on macOS), else `g++`, else `clang++`.
* Optional (for Google Drive):



## 2) Test ZIP format (required)

One ZIP per task (problem). Inside the ZIP, files must be **flat** (no nested folders) and named exactly:

```
<ID>_Input_TestCase_<N>.txt
<ID>_Output_TestCase_<N>.txt
```

Example (task ID = `1942G`):

```
1942G_Input_TestCase_1.txt
1942G_Output_TestCase_1.txt
...
1942G_Input_TestCase_10.txt
1942G_Output_TestCase_10.txt
```

> ✱ Inputs and outputs must have the **same set of N indices** (1..N).
> ✱ Each input file’s content is exactly what the program reads from `stdin`.
> ✱ Each output file’s content is the expected `stdout` for that input.

### Avoid macOS “.\_” files in ZIP

If you zip on macOS, **don’t** use Finder’s “Compress”. Use:

```bash
zip -r -X 720D_TestCases.zip 720D_TestCases/
```

Or clean first:

```bash
dot_clean 720D_TestCases/
```

This prevents “resource fork” files like `._720D_Input_TestCase_1.txt`.



## 3) Files in this repo

```
solution.cpp            # your C++ code that passes all tests in codeforces 
run_zip_harness.py      # the harness
results/                # created automatically with summary, reports, diffs
```



## 4) Quick start

### A) Run with a **local ZIP**

```bash
python3 run_zip_harness.py --zip 720D_TestCases.zip
```

### B) Run with a **Google Drive link or file ID**

```bash
# Example:
python3 run_zip_harness.py --gdrive "https://drive.google.com/file/d/1yCfbs1A7BpMDjF2ZXqkUFgDF_YKzO-Y_/view?usp=sharing"

# Raw file ID:
python3 run_zip_harness.py --gdrive 1yCfbs1A7BpMDjF2ZXqkUFgDF_YKzO-Y_/
```

The harness downloads the ZIP to a temp folder, validates files, compiles `solution.cpp`, runs all tests, and writes reports to `results/`.



## 5) Common options

```bash
# Choose compiler (prefers g++-14 if present)
python3 run_zip_harness.py --zip 720D_TestCases.zip --compiler g++-14

# Use token comparison (ignores whitespace/layout differences)
python3 run_zip_harness.py --zip 720D_TestCases.zip --compare tokens

# Increase per-test timeout (seconds)
python3 run_zip_harness.py --zip 720D_TestCases.zip --timeout 60

# Use a different C++ file name
python3 run_zip_harness.py --zip 720D_TestCases.zip --cpp my_solution.cpp

# Change output directory for reports
python3 run_zip_harness.py --zip 720D_TestCases.zip --outdir results_720D
```

**Defaults**

* Compiler: `g++-14` if found, else `g++`, else `clang++`
* Flags: `-std=gnu++17 -O2 -pipe` (falls back to `-std=c++17` if needed)
* Comparison: `exact`
* Timeout: 30s per test
* Reports: `./results/`



## 6) What you get after running

`results/` contains:

* **summary.txt** – one line: `All passed` or `K out of N failed`
* **report.csv** – per case: index, status, runtime (ms), return code
* **report.json** – detailed info (stdin/expected file paths, sample stdout, environment)
* **diffs/** – unified diffs for failed cases (one `.patch` per failing test)

Example console output:

```
[*] Running 10 test case(s)...

Test 1: PASS
Test 2: FAIL
 expected_2.txt
+++ got_2.txt
@@
-42
+41

===== SUMMARY =====
1 out of 10 failed
```



## 7) Interpreting failures

* **Compilation failed** – fix compiler errors in `solution.cpp`.
* **Mismatch (FAIL)** – your program’s `stdout` differs from the expected file:

  * Check `results/diffs/diff_<N>.patch`
  * If it’s only spacing/newlines, retry with `--compare tokens`
* **Timeout** – program didn’t finish in the allotted time. Increase `--timeout` or optimize code.
* **ZIP issues detected** – naming mismatches, missing pairs, or extra files:

  * Ensure every input `<N>` has a matching output `<N>`
  * File names must **exactly** match the pattern (case-sensitive)
  * Remove `._` files (see macOS note above)



## 8) Tips for matching Codeforces behavior

* Prefer **GNU g++** and `-std=gnu++17 -O2 -pipe`
* Avoid OS-specific headers/behavior
* Don’t print debug info to `stdout` (use `stderr` if you must)
* Make sure your program reads until EOF or exactly the format required by the input file

On macOS:

```bash
brew install gcc
python3 run_zip_harness.py --zip 720D_TestCases.zip --compiler g++-14
```



## 9) Creating a skeleton ZIP (optional helper)

Use this helper script to scaffold 10 blank I/O files:

```python
# create_testcases.py
import os, sys
def create(task_id, n=10):
    base = os.path.join(os.getcwd(), task_id)
    os.makedirs(base, exist_ok=True)
    folder = os.path.join(base, f"{task_id}_TestCases")
    os.makedirs(folder, exist_ok=True)
    for i in range(1, n+1):
        open(os.path.join(folder, f"{task_id}_Input_TestCase_{i}.txt"), "w").close()
        open(os.path.join(folder, f"{task_id}_Output_TestCase_{i}.txt"), "w").close()
    print(f"Created {n} pairs in {folder}")
if __name__ == "__main__":
    create(sys.argv[1] if len(sys.argv)>1 else "720D")
```

Zip it (cross-platform-friendly):

```bash
cd 720D
zip -r -X 720D_TestCases.zip 720D_TestCases/
```



## 10) Exit codes (for CI)

* `0` – all tests passed
* `1` – any failure (compile/run/compare/zip validation)

Use this in CI to gate merges.



## 11) FAQ

**Q: I see “IGNORING unexpected file name: .\_…txt”**
A: Those are macOS resource files. Zip with `zip -r -X …` or run `dot_clean` before zipping. The harness ignores them but warns you.

**Q: The first test seems mismatched**
A: Ensure input/output filenames share the same `<N>` index. The harness pairs by number, not by file order.
