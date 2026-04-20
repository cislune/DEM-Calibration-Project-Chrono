from pathlib import Path
import sys


def get_mode() -> str:
    while True:
        print("\nChoose a conversion mode:")
        print("1) CSV -> VTK")
        print("2) VTK -> CSV")
        choice = input("Enter 1 or 2: ").strip()

        if choice == "1":
            return "csv_to_vtk"
        if choice == "2":
            return "vtk_to_csv"

        print("Invalid choice. Please enter 1 or 2.")


def get_path_input(expected_ext: str) -> Path:
    while True:
        raw = input(
            f"Enter a file path or folder path for {expected_ext.upper()} files: "
        ).strip().strip('"')

        if not raw:
            print("Path cannot be empty.")
            continue

        path = Path(raw).expanduser().resolve()

        if not path.exists():
            print(f"Path does not exist: {path}")
            continue

        return path


def collect_files(path: Path, ext: str) -> list[Path]:
    ext = ext.lower()

    if path.is_file():
        if path.suffix.lower() != ext:
            raise ValueError(f"Expected a {ext} file, got: {path.name}")
        return [path]

    if path.is_dir():
        files = sorted([p for p in path.iterdir() if p.is_file() and p.suffix.lower() == ext])
        if not files:
            raise ValueError(f"No {ext} files found in folder: {path}")
        return files

    raise ValueError(f"Unsupported path: {path}")


def csv_to_vtk(csv_path: Path, vtk_path: Path) -> None:
    import pandas as pd
    import pyvista as pv

    df = pd.read_csv(csv_path)
    required = ["X", "Y", "Z"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(
            f"{csv_path.name} is missing required columns: {missing}. "
            "CSV must contain X, Y, Z columns."
        )

    points = df[["X", "Y", "Z"]].to_numpy(dtype=float)
    cloud = pv.PolyData(points)

    for col in df.columns:
        if col not in ["X", "Y", "Z"]:
            cloud.point_data[col] = df[col].to_numpy()

    cloud.save(vtk_path)


def vtk_to_csv(vtk_path: Path, csv_path: Path) -> None:
    import pandas as pd
    import pyvista as pv

    mesh = pv.read(vtk_path)
    points = mesh.points

    if points is None or len(points) == 0:
        raise ValueError(f"{vtk_path.name} contains no points.")

    data = {
        "X": points[:, 0],
        "Y": points[:, 1],
        "Z": points[:, 2],
    }

    for name in mesh.point_data.keys():
        arr = mesh.point_data[name]
        if getattr(arr, "ndim", 1) == 1:
            data[name] = arr
        else:
            for i in range(arr.shape[1]):
                data[f"{name}_{i}"] = arr[:, i]

    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False)


def run_csv_to_vtk() -> None:
    path = get_path_input(".csv")
    csv_files = collect_files(path, ".csv")

    for csv_file in csv_files:
        vtk_file = csv_file.with_suffix(".vtk")
        print(f"Converting {csv_file} -> {vtk_file}")
        csv_to_vtk(csv_file, vtk_file)

    print(f"\nDone. Converted {len(csv_files)} file(s) from CSV to VTK.")


def run_vtk_to_csv() -> None:
    path = get_path_input(".vtk")
    vtk_files = collect_files(path, ".vtk")

    for vtk_file in vtk_files:
        csv_file = vtk_file.with_suffix(".csv")
        print(f"Converting {vtk_file} -> {csv_file}")
        vtk_to_csv(vtk_file, csv_file)

    print(f"\nDone. Converted {len(vtk_files)} file(s) from VTK to CSV.")


def main() -> None:
    try:
        mode = get_mode()
        if mode == "csv_to_vtk":
            run_csv_to_vtk()
        else:
            run_vtk_to_csv()
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        sys.exit(1)
    except Exception as exc:
        print(f"\nError: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
