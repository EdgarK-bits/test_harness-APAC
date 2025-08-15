#!/usr/bin/env python3
import os
import zipfile

def scaffold(task_id: str, count: int = 10):
    folder_name = f"{task_id}_TestCases"
    os.makedirs(folder_name, exist_ok=True)
    for i in range(1, count + 1):
        in_file = os.path.join(folder_name, f"{task_id}_Input_TestCase_{i}.txt")
        out_file = os.path.join(folder_name, f"{task_id}_Output_TestCase_{i}.txt")
        with open(in_file, "w", encoding="utf-8") as f:
            f.write("")  # empty placeholder
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("")  # empty placeholder
    print(f"[+] Created {count} input and {count} output files in '{folder_name}'")

def make_zip(task_id: str):
    folder_name = f"{task_id}_TestCases"
    zip_name = f"{folder_name}.zip"
    if not os.path.exists(folder_name):
        print(f"[!] Folder '{folder_name}' does not exist.")
        return
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(folder_name):
            for file in sorted(files):
                file_path = os.path.join(root, file)
                zf.write(file_path, os.path.basename(file_path))
    print(f"[+] Created ZIP: {zip_name}")

if __name__ == "__main__":
    print("=== Test Case Scaffolder ===")
    task_id = input("Enter task ID (e.g., 1942G): ").strip()
    print("Choose an action:")
    print("  1. Create placeholder input/output files")
    print("  2. Zip existing test cases folder")
    choice = input("Enter choice (1 or 2): ").strip()
    if choice == "1":
        scaffold(task_id)
    elif choice == "2":
        make_zip(task_id)
    else:
        print("[!] Invalid choice")
