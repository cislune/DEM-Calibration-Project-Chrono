#!/usr/bin/env python3

import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# =============================================================================
# PROJECT PATHS
# =============================================================================

PROJECT_ROOT = Path("/home/cislune/DEM-Cislune-ProjectChrono")
OUTPUT_ROOT = PROJECT_ROOT / "wear degradation output"

BASE_DIRS = {
    0.0: PROJECT_ROOT / "slip sinkage output/Trial 1/Slip 0.0",
    0.3: PROJECT_ROOT / "slip sinkage output/Trial 1/Slip 0.3",
    0.6: PROJECT_ROOT / "slip sinkage output/Trial 1/Slip 0.6",
}

# =============================================================================
# NOTEBOOK CONSTANTS
# =============================================================================

DT = 1e-3
OMEGA = np.pi / 2
R_WHEEL = 0.25

N_PLATES = 25
PLATE_CENTERS = np.linspace(0, 2 * np.pi, N_PLATES, endpoint=False)

WHEEL_Y_MIN = -0.03750000149011612
WHEEL_Y_MAX = 0.042500000447034836
WHEEL_Y_CENTER = 0.5 * (WHEEL_Y_MIN + WHEEL_Y_MAX)
PLATE_WIDTH = WHEEL_Y_MAX - WHEEL_Y_MIN

BINS_U = 25
BINS_V = 15


# =============================================================================
# HELPERS
# =============================================================================

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def slip_label(slip_value: float) -> str:
    return f"{slip_value:.3f}".rstrip("0").rstrip(".")


def read_vtk_points_ascii(vtk_file: Path) -> np.ndarray:
    with open(vtk_file, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    n_points = None
    start_idx = None

    for i, line in enumerate(lines):
        parts = line.strip().split()
        if parts and parts[0].upper() == "POINTS":
            n_points = int(parts[1])
            start_idx = i + 1
            break

    if n_points is None or start_idx is None:
        raise ValueError(f"Could not find POINTS section in {vtk_file}")

    vals = []
    for line in lines[start_idx:]:
        if not line.strip():
            continue
        first = line.strip().split()[0].upper()
        if first in [
            "VERTICES",
            "LINES",
            "POLYGONS",
            "CELLS",
            "CELL_TYPES",
            "POINT_DATA",
            "CELL_DATA",
            "SCALARS",
            "VECTORS",
            "FIELD",
            "LOOKUP_TABLE",
        ]:
            break
        vals.extend([float(x) for x in line.split()])

    vals = np.array(vals, dtype=float)

    if vals.size < 3 * n_points:
        raise ValueError(f"Not enough point data in {vtk_file}")

    return vals[: 3 * n_points].reshape((n_points, 3))


def fit_circle_xz(x: np.ndarray, z: np.ndarray):
    A = np.column_stack([x, z, np.ones_like(x)])
    b = -(x**2 + z**2)
    coeff, *_ = np.linalg.lstsq(A, b, rcond=None)
    a, bcoef, c = coeff
    xc = -a / 2.0
    zc = -bcoef / 2.0
    r_fit = np.sqrt(max(xc**2 + zc**2 - c, 0.0))
    return xc, zc, r_fit


def circular_diff(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    d = np.abs(a - b)
    return np.minimum(d, 2 * np.pi - d)


def assign_plate_ids(theta: np.ndarray, centers: np.ndarray) -> np.ndarray:
    d = circular_diff(theta[:, None], centers[None, :])
    return np.argmin(d, axis=1)


def signed_angle_from_center(theta: np.ndarray, center: np.ndarray) -> np.ndarray:
    return np.arctan2(np.sin(theta - center), np.cos(theta - center))


def contact_file(base_dir: Path, frame: int) -> Path:
    return base_dir / "contact forces" / f"slip_sinkage_contact_data_{frame:04d}.csv"


def wheel_vtk_file(base_dir: Path, frame: int) -> Path:
    return base_dir / "wheel motion" / f"slip_sinkage_wheel_motion_{frame:04d}.vtk"


def available_frames(base_dir: Path):
    frames = []
    contact_dir = base_dir / "contact forces"
    for p in sorted(contact_dir.glob("slip_sinkage_contact_data_*.csv")):
        m = re.search(r"_(\d+)\.csv$", p.name)
        if not m:
            continue
        frame = int(m.group(1))
        if wheel_vtk_file(base_dir, frame).exists():
            frames.append(frame)
    return frames


def normalize_contact_type(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.upper()


def extract_wheel_contacts(df: pd.DataFrame):
    """
    Primary notebook logic:
      1) filter to contact_type == 'SM'
      2) choose wheel_id from most frequent B
      3) keep rows with B == wheel_id

    Robust fallback:
      if no SM exists, use all contacts and still choose dominant B.
    """
    if "B" not in df.columns:
        raise RuntimeError("B column missing; cannot identify wheel owner.")

    if "contact_type" in df.columns:
        ctype = normalize_contact_type(df["contact_type"])
        sm = df[ctype == "SM"].copy()
        pool = sm if not sm.empty else df.copy()
    else:
        pool = df.copy()

    if pool.empty:
        raise RuntimeError("No usable contacts in this frame.")

    wheel_id = pool["B"].value_counts().idxmax()
    wheel = pool[pool["B"] == wheel_id].copy()

    if wheel.empty:
        raise RuntimeError("Wheel-contact subset is empty after B-owner filtering.")

    return wheel, wheel_id


def load_frame_data(base_dir: Path, slip_value: float, frame: int):
    cf = contact_file(base_dir, frame)
    wf = wheel_vtk_file(base_dir, frame)

    if not cf.exists():
        raise FileNotFoundError(f"Missing contact file: {cf}")
    if not wf.exists():
        raise FileNotFoundError(f"Missing wheel VTK: {wf}")

    df = pd.read_csv(cf).drop_duplicates().copy()
    wheel, wheel_id = extract_wheel_contacts(df)

    pts = read_vtk_points_ascii(wf)
    xc, zc, r_fit = fit_circle_xz(pts[:, 0], pts[:, 2])

    U = (1 - slip_value) * OMEGA * R_WHEEL

    wheel["rx"] = wheel["X"] - xc
    wheel["rz"] = wheel["Z"] - zc
    wheel["rmag"] = np.sqrt(wheel["rx"]**2 + wheel["rz"]**2).replace(0, 1e-12)
    wheel["nx"] = wheel["rx"] / wheel["rmag"]
    wheel["nz"] = wheel["rz"] / wheel["rmag"]

    wheel["vx"] = U + OMEGA * wheel["rz"]
    wheel["vz"] = -OMEGA * wheel["rx"]

    wheel["vdotn"] = wheel["vx"] * wheel["nx"] + wheel["vz"] * wheel["nz"]
    wheel["vtx"] = wheel["vx"] - wheel["vdotn"] * wheel["nx"]
    wheel["vtz"] = wheel["vz"] - wheel["vdotn"] * wheel["nz"]
    wheel["vt_mag"] = np.sqrt(wheel["vtx"]**2 + wheel["vtz"]**2)

    wheel["Fn"] = np.abs(wheel["f_z"])
    wheel["dI"] = wheel["Fn"] * wheel["vt_mag"] * DT

    wheel["theta"] = np.mod(np.arctan2(wheel["rz"], wheel["rx"]), 2 * np.pi)
    wheel["plate_id"] = assign_plate_ids(wheel["theta"].values, PLATE_CENTERS)

    plate_pitch_angle = 2 * np.pi / N_PLATES
    plate_half_length = r_fit * (plate_pitch_angle / 2)

    wheel["plate_center_theta"] = PLATE_CENTERS[wheel["plate_id"].values]
    wheel["theta_rel"] = signed_angle_from_center(
        wheel["theta"].values,
        wheel["plate_center_theta"].values,
    )
    wheel["u_local"] = r_fit * wheel["theta_rel"]
    wheel["v_local"] = wheel["Y"] - WHEEL_Y_CENTER

    wheel["inside_plate_rect"] = (
        (np.abs(wheel["u_local"]) <= plate_half_length) &
        (np.abs(wheel["v_local"]) <= PLATE_WIDTH / 2)
    )

    wheel_rect = wheel[wheel["inside_plate_rect"]].copy()

    return {
        "wheel": wheel,
        "wheel_rect": wheel_rect,
        "wheel_id": wheel_id,
        "xc": xc,
        "zc": zc,
        "r_fit": r_fit,
        "plate_half_length": plate_half_length,
    }


def first_usable_frame(base_dir: Path, slip_value: float) -> int:
    frames = available_frames(base_dir)
    if not frames:
        raise RuntimeError(f"No matching contact/VTK frame pairs found in {base_dir}")

    for frame in frames:
        try:
            result = load_frame_data(base_dir, slip_value, frame)
            if len(result["wheel_rect"]) > 0:
                return frame
        except Exception:
            continue

    raise RuntimeError(f"No usable frames found in {base_dir}")


def frame_range_slug(frames):
    if not frames:
        return "empty"
    if len(frames) == 1:
        return f"{frames[0]:04d}"
    diffs = np.diff(frames)
    if len(set(diffs.tolist())) == 1:
        return f"{frames[0]:04d}_to_{frames[-1]:04d}_step_{diffs[0]}"
    return f"{frames[0]:04d}_to_{frames[-1]:04d}_n_{len(frames)}"


# =============================================================================
# INPUT PARSING
# =============================================================================

def parse_slip_selection(text: str):
    text = text.strip().lower()
    if text in ("", "all"):
        return [0.0, 0.3, 0.6]

    out = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        val = float(part)
        if val not in BASE_DIRS:
            raise ValueError(f"Unsupported slip value: {val}")
        out.append(val)

    return sorted(set(out))


def parse_frame_list(text: str):
    """
    Examples:
      5
      5,10,25
      5-25
      5-25:5
      5,10-30:5,45
    """
    text = text.strip()
    if text == "":
        return []

    frames = set()

    for token in text.split(","):
        token = token.strip()
        if not token:
            continue

        m = re.fullmatch(r"(\d+)-(\d+)(?::(\d+))?", token)
        if m:
            start = int(m.group(1))
            stop = int(m.group(2))
            step = int(m.group(3)) if m.group(3) else 1
            if step <= 0:
                raise ValueError(f"Invalid step in token: {token}")
            if stop < start:
                raise ValueError(f"Invalid range in token: {token}")
            frames.update(range(start, stop + 1, step))
            continue

        if re.fullmatch(r"\d+", token):
            frames.add(int(token))
            continue

        raise ValueError(f"Could not parse frame token: {token}")

    return sorted(frames)


def parse_range_list(text: str):
    """
    Examples:
      5-50
      5-50:5
      5-50:5,60-120:10
    Returns list of frame lists.
    """
    text = text.strip()
    if text == "":
        return []

    ranges = []

    for token in text.split(","):
        token = token.strip()
        if not token:
            continue

        m = re.fullmatch(r"(\d+)-(\d+)(?::(\d+))?", token)
        if not m:
            raise ValueError(f"Cumulative range must look like start-end or start-end:step, got: {token}")

        start = int(m.group(1))
        stop = int(m.group(2))
        step = int(m.group(3)) if m.group(3) else 1

        if step <= 0:
            raise ValueError(f"Invalid step in token: {token}")
        if stop < start:
            raise ValueError(f"Invalid range in token: {token}")

        ranges.append(list(range(start, stop + 1, step)))

    return ranges


# =============================================================================
# PLOTTING
# =============================================================================

def save_summary_text(result: dict, out_dir: Path, slip_value: float, label: str) -> None:
    wheel = result["wheel"]
    wheel_rect = result["wheel_rect"]

    plate_summary = wheel_rect.groupby("plate_id").agg(
        n_contacts=("plate_id", "size"),
        plate_wear=("dI", "sum"),
    ).reset_index()

    lines = []
    lines.append(f"Slip: {slip_value}, Label: {label}")
    lines.append(f"wheel_id: {result['wheel_id']}")
    lines.append(f"xc = {result['xc']} zc = {result['zc']} r_fit = {result['r_fit']}")
    lines.append(f"total wheel contacts: {len(wheel)}")
    lines.append(f"contacts inside plate rectangles: {len(wheel_rect)}")
    lines.append(plate_summary.to_string(index=False))

    text = "\n".join(lines)
    print(text)

    with open(out_dir / "summary.txt", "w", encoding="utf-8") as f:
        f.write(text + "\n")

    plate_summary.to_csv(out_dir / "plate_summary.csv", index=False)


def save_contact_assignment_plot(result: dict, out_dir: Path, title: str) -> None:
    wheel_rect = result["wheel_rect"]
    xc = result["xc"]
    zc = result["zc"]
    r_fit = result["r_fit"]

    theta_plot = np.linspace(0, 2 * np.pi, 400)
    x_circle = xc + r_fit * np.cos(theta_plot)
    z_circle = zc + r_fit * np.sin(theta_plot)

    plt.figure(figsize=(7, 7))
    sc = plt.scatter(
        wheel_rect["X"],
        wheel_rect["Z"],
        c=wheel_rect["plate_id"],
        s=12,
        cmap="tab20",
    )
    plt.plot(x_circle, z_circle, color="black", linewidth=1.2)
    plt.scatter(xc, zc, color="red", marker="x", s=60)
    plt.xlabel("X (m)")
    plt.ylabel("Z (m)")
    plt.title(title)
    plt.axis("equal")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.colorbar(sc, label="plate_id")
    plt.tight_layout()
    plt.savefig(out_dir / "contacts_assigned_to_tread_coupons.png", dpi=220)
    plt.close()


def save_coupon_heatmaps_from_maps(maps: dict, plate_half_length: float, out_dir: Path, title: str) -> None:
    ncols = 5
    nrows = int(np.ceil(N_PLATES / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(18, 14))
    axes = axes.flatten()

    for pid in range(N_PLATES):
        ax = axes[pid]
        H = maps[pid]

        ax.imshow(
            H,
            extent=[-plate_half_length, plate_half_length, -PLATE_WIDTH / 2, PLATE_WIDTH / 2],
            origin="lower",
            aspect="auto",
            cmap="plasma",
        )

        rect_u = [
            -plate_half_length,
            plate_half_length,
            plate_half_length,
            -plate_half_length,
            -plate_half_length,
        ]
        rect_v = [
            -PLATE_WIDTH / 2,
            -PLATE_WIDTH / 2,
            PLATE_WIDTH / 2,
            PLATE_WIDTH / 2,
            -PLATE_WIDTH / 2,
        ]
        ax.plot(rect_u, rect_v, color="black", linewidth=1.2)
        ax.set_title(f"Coupon {pid}")
        ax.set_xlabel("u_local (m)")
        ax.set_ylabel("v_local (m)")
        ax.grid(True, linestyle="--", alpha=0.25)

    for j in range(N_PLATES, len(axes)):
        fig.delaxes(axes[j])

    fig.suptitle(title, fontsize=14)
    plt.tight_layout()
    plt.savefig(out_dir / "per coupon heatmaps.png", dpi=220)
    plt.close(fig)


def save_active_coupon_heatmaps(result: dict, out_dir: Path, title: str) -> None:
    wheel_rect = result["wheel_rect"]
    plate_half_length = result["plate_half_length"]

    active = (
        wheel_rect.groupby("plate_id")["dI"]
        .sum()
        .loc[lambda s: s > 0]
        .index.tolist()
    )

    if not active:
        with open(out_dir / "active_coupon_heatmaps.txt", "w", encoding="utf-8") as f:
            f.write("No coupons with wear.\n")
        return

    ncols = min(4, len(active))
    nrows = int(np.ceil(len(active) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.5 * ncols, 4 * nrows))
    axes = np.atleast_1d(axes).flatten()

    u_edges = np.linspace(-plate_half_length, plate_half_length, BINS_U + 1)
    v_edges = np.linspace(-PLATE_WIDTH / 2, PLATE_WIDTH / 2, BINS_V + 1)

    for ax, pid in zip(axes, active):
        d = wheel_rect[wheel_rect["plate_id"] == pid]
        H, _, _ = np.histogram2d(
            d["v_local"],
            d["u_local"],
            bins=[v_edges, u_edges],
            weights=d["dI"],
        )
        ax.imshow(
            H,
            extent=[-plate_half_length, plate_half_length, -PLATE_WIDTH / 2, PLATE_WIDTH / 2],
            origin="lower",
            aspect="auto",
            cmap="plasma",
        )
        ax.set_title(f"Coupon {pid}")
        ax.set_xlabel("u_local")
        ax.set_ylabel("v_local")

    for j in range(len(active), len(axes)):
        fig.delaxes(axes[j])

    fig.suptitle(title, fontsize=14)
    plt.tight_layout()
    plt.savefig(out_dir / "active_coupon_heatmaps.png", dpi=220)
    plt.close(fig)


def save_coupon_totals_from_maps(maps: dict, out_dir: Path, title: str) -> None:
    totals_dir = out_dir / "total coupon wear"
    ensure_dir(totals_dir)

    rows = []
    for pid in range(N_PLATES):
        rows.append({
            "plate_id": pid,
            "wear_sum": float(np.sum(maps[pid])),
            "max_local_wear": float(np.max(maps[pid])) if maps[pid].size else 0.0,
        })
    df = pd.DataFrame(rows)
    df.to_csv(totals_dir / "coupon total wear.csv", index=False)

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(11, 5.5))

    wear_values = df["wear_sum"].to_numpy(dtype=float)
    if np.allclose(wear_values.max(), wear_values.min()):
        norm_vals = np.full_like(wear_values, 0.6, dtype=float)
    else:
        norm_vals = (wear_values - wear_values.min()) / (wear_values.max() - wear_values.min())

    colors = plt.cm.viridis(0.15 + 0.75 * norm_vals)
    bars = ax.bar(
        df["plate_id"],
        wear_values,
        color=colors,
        edgecolor="white",
        linewidth=0.8,
        width=0.82,
        zorder=3,
    )

    ax.set_title(title, fontsize=16, weight="bold", pad=14)
    ax.set_xlabel("Coupon ID", fontsize=12, labelpad=8)
    ax.set_ylabel("Wear sum", fontsize=12, labelpad=8)
    ax.set_xticks(df["plate_id"])
    ax.tick_params(axis="x", labelsize=9)
    ax.tick_params(axis="y", labelsize=10)

    ax.grid(True, axis="y", linestyle="--", alpha=0.28, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#bbbbbb")
    ax.spines["bottom"].set_color("#bbbbbb")

    if len(wear_values) > 0:
        top_idx = int(np.argmax(wear_values))
        bars[top_idx].set_linewidth(1.4)

    plt.tight_layout()
    plt.savefig(totals_dir / "coupon total wear.png", dpi=240, bbox_inches="tight")
    plt.close(fig)
    plt.style.use("default")


# =============================================================================
# ANALYSIS
# =============================================================================

def build_maps_from_result(result: dict):
    wheel_rect = result["wheel_rect"]
    plate_half_length = result["plate_half_length"]

    u_edges = np.linspace(-plate_half_length, plate_half_length, BINS_U + 1)
    v_edges = np.linspace(-PLATE_WIDTH / 2, PLATE_WIDTH / 2, BINS_V + 1)

    maps = {}
    for pid in range(N_PLATES):
        d = wheel_rect[wheel_rect["plate_id"] == pid]
        H, _, _ = np.histogram2d(
            d["v_local"],
            d["u_local"],
            bins=[v_edges, u_edges],
            weights=d["dI"],
        )
        maps[pid] = H

    return maps, plate_half_length


def analyze_single_frame(base_dir: Path, slip_value: float, frame: int, out_dir: Path):
    result = load_frame_data(base_dir, slip_value, frame)
    maps, plate_half_length = build_maps_from_result(result)

    save_summary_text(result, out_dir, slip_value, f"single frame {frame}")
    save_contact_assignment_plot(
        result,
        out_dir,
        f"Frame {frame}: contacts assigned to tread coupons, slip {slip_value}",
    )
    save_coupon_heatmaps_from_maps(
        maps,
        plate_half_length,
        out_dir,
        f"Per-coupon wear heatmaps, frame {frame}, slip {slip_value}",
    )
    save_active_coupon_heatmaps(
        result,
        out_dir,
        f"Active coupons, frame {frame}, slip {slip_value}",
    )
    save_coupon_totals_from_maps(
        maps,
        out_dir,
        f"Per-coupon wear totals, frame {frame}, slip {slip_value}",
    )


def analyze_cumulative_range(base_dir: Path, slip_value: float, requested_frames, out_dir: Path):
    valid_frames = []
    cumulative_maps = None
    plate_half_length_ref = None
    last_result = None

    for frame in requested_frames:
        cf = contact_file(base_dir, frame)
        wf = wheel_vtk_file(base_dir, frame)
        if not (cf.exists() and wf.exists()):
            continue

        try:
            result = load_frame_data(base_dir, slip_value, frame)
        except Exception:
            continue

        maps, plate_half_length = build_maps_from_result(result)

        if cumulative_maps is None:
            cumulative_maps = {pid: np.zeros((BINS_V, BINS_U)) for pid in range(N_PLATES)}
            plate_half_length_ref = plate_half_length

        for pid in range(N_PLATES):
            cumulative_maps[pid] += maps[pid]

        valid_frames.append(frame)
        last_result = result

    if cumulative_maps is None:
        raise RuntimeError("No usable frames found in the requested cumulative range.")

    save_coupon_heatmaps_from_maps(
        cumulative_maps,
        plate_half_length_ref,
        out_dir,
        f"Cumulative per-coupon wear heatmaps, slip {slip_value}, frames {requested_frames[0]} to {requested_frames[-1]}",
    )
    save_coupon_totals_from_maps(
        cumulative_maps,
        out_dir,
        f"Cumulative wear totals per coupon, slip {slip_value}, frames {requested_frames[0]} to {requested_frames[-1]}",
    )

    return cumulative_maps, plate_half_length_ref, valid_frames, last_result


# =============================================================================
# MAIN
# =============================================================================

def main():
    ensure_dir(OUTPUT_ROOT)

    print("\nAvailable slip cases: 0.0, 0.3, 0.6")
    slip_text = input("Enter slip cases to process (all or comma list, e.g. 0.0,0.6): ").strip()
    selected_slips = parse_slip_selection(slip_text)

    print("\nSingle-frame input examples:")
    print("  5")
    print("  5,10,25")
    print("  5-25")
    print("  5-25:5")
    single_text = input("Enter single frames to analyze (blank for none): ").strip()
    single_frames = parse_frame_list(single_text)

    print("\nCumulative-range input examples:")
    print("  5-50")
    print("  5-50:5")
    print("  5-50:5,60-120:10")
    cumulative_text = input("Enter cumulative frame ranges to analyze (blank for none): ").strip()
    cumulative_ranges = parse_range_list(cumulative_text)

    if not single_frames and not cumulative_ranges:
        print("Nothing requested. Exiting.")
        return

    for slip_value in selected_slips:
        base_dir = BASE_DIRS[slip_value]

        frames_available = available_frames(base_dir)
        if not frames_available:
            print(f"\nSlip {slip_value}: no matching contact/VTK frame pairs found.")
            continue

        print(f"\nSlip {slip_value}: available frames from {frames_available[0]} to {frames_available[-1]}")

        # Single frames
        for frame in single_frames:
            out_dir = OUTPUT_ROOT / f"slip {slip_label(slip_value)} (frame {frame})"
            ensure_dir(out_dir)

            try:
                analyze_single_frame(base_dir, slip_value, frame, out_dir)
                print(f"Saved single-frame outputs for slip {slip_value}, frame {frame}")
            except Exception as exc:
                print(f"Skipping single frame {frame} for slip {slip_value}: {exc}")

        # Cumulative ranges
        for requested_frames in cumulative_ranges:
            out_dir = OUTPUT_ROOT / f"slip {slip_label(slip_value)} (frame {requested_frames[0]} to frame {requested_frames[-1]})"
            ensure_dir(out_dir)

            try:
                maps, plate_half_length, used_frames, last_result = analyze_cumulative_range(
                    base_dir,
                    slip_value,
                    requested_frames,
                    out_dir,
                )
                print(
                    f"Saved cumulative outputs for slip {slip_value}, "
                    f"requested {requested_frames[0]}-{requested_frames[-1]}, "
                    f"used {len(used_frames)} frame(s)"
                )
            except Exception as exc:
                print(
                    f"Skipping cumulative range {requested_frames[0]}-{requested_frames[-1]} "
                    f"for slip {slip_value}: {exc}"
                )

    print(f"\nDone. Outputs written to: {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
