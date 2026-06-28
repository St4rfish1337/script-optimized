import os
import shutil
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed


def list_directory(path: str) -> set:
    """Return a set of filenames found directly inside `path`."""
    return {f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))}


def copy_file(src: str, dst_dir: str, filename: str) -> str:
    """Copy a single file to dst_dir and return the destination path."""
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, filename)
    shutil.copy2(src, dst)
    return dst


def process_subdirectory(subdir_name: str, subdir_set: set, target_set: set, subdir_path: str, output_dir: str) -> int:
    """
    Match every file in target_set against subdir_set.
    Copy matches to output/<subdir_name>/ using a thread pool.
    Returns the number of files copied.
    """
    matches = target_set & subdir_set          # intersection – O(min(|A|,|B|))
    if not matches:
        return 0

    out_path = os.path.join(output_dir, subdir_name)
    copied = 0

    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(
                copy_file,
                os.path.join(subdir_path, filename),
                out_path,
                filename,
            ): filename
            for filename in matches
        }
        for future in as_completed(futures):
            try:
                future.result()
                copied += 1
            except Exception as exc:
                print(f"  [ERROR] {futures[future]}: {exc}")

    # Release the futures dict and trigger GC for this batch
    del futures
    gc.collect()

    return copied


def main():
    # ── 1. Source directory (target_set) ──────────────────────────────────────
    source_dir = input("Enter source directory path: ").strip()
    if not os.path.isdir(source_dir):
        print(f"[ERROR] '{source_dir}' is not a valid directory.")
        return

    target_set = list_directory(source_dir)
    print(f"  Found {len(target_set)} file(s) in source directory.")

    # ── 2. Split directory (must contain test / train / val) ──────────────────
    split_dir = input("Enter split directory path (must contain test/, train/, val/): ").strip()
    if not os.path.isdir(split_dir):
        print(f"[ERROR] '{split_dir}' is not a valid directory.")
        return

    subdirs = ["test", "train", "val"]
    subdir_sets: dict[str, set] = {}

    for name in subdirs:
        path = os.path.join(split_dir, name)
        if not os.path.isdir(path):
            print(f"[WARNING] Subdirectory '{name}' not found in '{split_dir}', skipping.")
            continue
        subdir_sets[name] = list_directory(path)
        print(f"  '{name}': {len(subdir_sets[name])} file(s)")

    if not subdir_sets:
        print("[ERROR] No valid subdirectories found.")
        return

    # ── 3. Output directory ───────────────────────────────────────────────────
    output_dir = input("Enter output directory path: ").strip()

    # ── 4. Match & copy – one thread pool per subdirectory ────────────────────
    print("\nProcessing matches…")
    total_copied = 0

    for name, subdir_set in subdir_sets.items():
        subdir_path = os.path.join(split_dir, name)
        count = process_subdirectory(name, subdir_set, target_set, subdir_path, output_dir)
        print(f"  [{name}] {count} file(s) copied → {os.path.join(output_dir, name)}/")
        total_copied += count

        # Explicit GC after each subdirectory batch
        del subdir_set
        gc.collect()

    print(f"\nDone. Total files copied: {total_copied}")


if __name__ == "__main__":
    main()
