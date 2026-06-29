import os
import shutil
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed


def list_directory(path: str) -> set:
    """Return a set of filenames found directly inside `path`."""
    return {f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))}


def get_base_name(filename: str) -> str:
    """Enlève le suffixe _inpainted si présent."""
    if filename.lower().endswith("_inpainted.png"):
        return filename[:-len("_inpainted.png")] + ".png"
    return filename


def copy_file(src: str, dst_dir: str, filename: str) -> str:
    """Copy a single file to dst_dir and return the destination path."""
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, filename)
    shutil.copy2(src, dst)
    return dst


def process_subdirectory(subdir_name: str, subdir_set: set, source_files: dict, subdir_path: str, output_dir: str) -> int:
    """
    Match intelligent + copie en gardant le nom _inpainted.png
    """
    if not subdir_set:
        return 0

    matches = []
    for split_file in subdir_set:
        base_name = get_base_name(split_file)          # ex: image_001.png
        source_path = source_files.get(base_name)
        if source_path:
            # Récupérer le vrai nom du fichier source (avec _inpainted)
            source_filename = os.path.basename(source_path)
            matches.append((source_path, source_filename))

    if not matches:
        return 0

    out_path = os.path.join(output_dir, subdir_name)
    copied = 0

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(
                copy_file,
                src_path,           # chemin source
                out_path,
                dest_filename,      # nom avec _inpainted
            ): dest_filename
            for src_path, dest_filename in matches
        }

        for future in as_completed(futures):
            try:
                future.result()
                copied += 1
            except Exception as exc:
                print(f"  [ERROR] {futures[future]}: {exc}")

    del futures
    gc.collect()

    return copied

def main():
    # ── 1. Source directory ──────────────────────────────────────
    source_dir = input("Enter source directory path: ").strip()
    if not os.path.isdir(source_dir):
        print(f"[ERROR] '{source_dir}' is not a valid directory.")
        return

    source_filenames = list_directory(source_dir)
    print(f"  Found {len(source_filenames)} file(s) in source directory.")

    # Création d'un mapping : base_name -> chemin complet du fichier _inpainted
    source_files = {}
    for fname in source_filenames:
        base = get_base_name(fname)
        source_files[base] = os.path.join(source_dir, fname)

    # ── 2. Split directory ──────────────────────────────────────
    split_dir = input("Enter split directory path (must contain test/, train/, val/): ").strip()
    if not os.path.isdir(split_dir):
        print(f"[ERROR] '{split_dir}' is not a valid directory.")
        return

    subdirs = ["test", "train", "val"]
    subdir_sets: dict[str, set] = {}

    for name in subdirs:
        path = os.path.join(split_dir, name)
        if not os.path.isdir(path):
            print(f"[WARNING] Subdirectory '{name}' not found, skipping.")
            continue
        subdir_sets[name] = list_directory(path)
        print(f"  '{name}': {len(subdir_sets[name])} file(s)")

    if not subdir_sets:
        print("[ERROR] No valid subdirectories found.")
        return

    # ── 3. Output directory ──────────────────────────────────────
    output_dir = input("Enter output directory path: ").strip()

    # ── 4. Processing ────────────────────────────────────────────
    print("\nProcessing matches…")
    total_copied = 0

    for name, subdir_set in subdir_sets.items():
        subdir_path = os.path.join(split_dir, name)
        count = process_subdirectory(name, subdir_set, source_files, subdir_path, output_dir)
        print(f"  [{name}] {count} file(s) copied → {os.path.join(output_dir, name)}/")
        total_copied += count

        del subdir_set
        gc.collect()

    print(f"\nDone. Total files copied: {total_copied}")


if __name__ == "__main__":
    main()
