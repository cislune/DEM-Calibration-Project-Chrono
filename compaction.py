
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyvista as pv

import config as c


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = PROJECT_ROOT / "DEM-Calibration-Project-Chrono"
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

SETTLED_TERRAIN_CSV = (
    PROJECT_ROOT / c.SPHERE_TERRAIN_GEN_OUT_DIR / f"{c.SPHERE_TERRAIN_GENERATION_SETTLED_DATA_FILE_NAME}.csv"
)
SLIP_ROOT_DIR = PROJECT_ROOT / c.SLIP_SINKAGE_OUT_DIR

WHEEL_LABEL = "TREAD Coupon Wheel"


# ============================================================
# SETTINGS
# ============================================================

DX = 0.05
DY = 0.05

N_TEMPLATES = 12

TERRAIN_GLOB = f"{c.SLIP_SINKAGE_TRIALS_MOTION_TERRAIN_FILE_NAME}_*.csv"
WHEEL_GLOB = f"{c.SLIP_SINKAGE_TRIALS_MOTION_WHEEL_FILE_NAME}_*.vtk"

SMOOTH_WIN_X = 3
SMOOTH_WIN_Y = 3

PLOT_FIELD = "compaction_max"

COMPACTION_THRESHOLD = 1e-4

SUBTRACT_BACKGROUND = True
BACKGROUND_STAT = "median"
THRESHOLD_PERCENTILE = 92.0
MASK_BELOW_THRESHOLD = True

COLOR_VMIN_PERCENTILE = 5.0
COLOR_VMAX_PERCENTILE = 99.5

MASKED_BACKGROUND_COLOR = "#355C9A"


# ============================================================
# HELPERS
# ============================================================

def sphere_volume(r):
    return (4.0 / 3.0) * np.pi * np.asarray(r) ** 3


def load_xyz_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    df = pd.read_csv(path)
    required = ["X", "Y", "Z"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"{path.name} missing columns {missing}. Found: {list(df.columns)}")
    return df


def get_base_radius() -> float:
    if c.USE_DEMO_WHEEL_st:
        return float(c.BASE_TERRAIN_RAD_DEMO_st)
    return float(c.BASE_TERRAIN_RAD_st)


def build_radius_map(radius_start: float, radius_increment: float, n_templates: int):
    mapping = {}
    r = radius_start
    for i in range(n_templates):
        mapping[f"{i}"] = r
        mapping[f"{i:02d}"] = r
        mapping[f"t{i}"] = r
        mapping[f"t{i:02d}"] = r
        r += radius_increment
    return mapping


def infer_radii(df: pd.DataFrame, radius_map, default_radius: float):
    if "r" in df.columns:
        return df["r"].astype(float).to_numpy()

    if "clump_type" in df.columns:
        return (
            df["clump_type"]
            .astype(str)
            .str.strip()
            .map(radius_map)
            .fillna(default_radius)
            .to_numpy(dtype=float)
        )

    return np.full(len(df), default_radius, dtype=float)


def make_grid(x, y, dx, dy):
    x_edges = np.arange(np.min(x) - dx, np.max(x) + 2 * dx, dx)
    y_edges = np.arange(np.min(y) - dy, np.max(y) + 2 * dy, dy)
    return x_edges, y_edges


def digitize_points(x, y, x_edges, y_edges):
    ix = np.clip(np.digitize(x, x_edges) - 1, 0, len(x_edges) - 2)
    iy = np.clip(np.digitize(y, y_edges) - 1, 0, len(y_edges) - 2)
    return ix, iy


def compute_top_surface_grid(df, x_edges, y_edges, radii):
    x = df["X"].to_numpy(float)
    y = df["Y"].to_numpy(float)
    z = df["Z"].to_numpy(float)

    ix, iy = digitize_points(x, y, x_edges, y_edges)

    top = np.full((len(x_edges) - 1, len(y_edges) - 1), np.nan, dtype=float)
    zsurf = z + radii

    for k in range(len(df)):
        i, j = ix[k], iy[k]
        if np.isnan(top[i, j]) or zsurf[k] > top[i, j]:
            top[i, j] = zsurf[k]

    return top


def compute_phi_grid(df, x_edges, y_edges, top_surface, z_bottom, radii):
    x = df["X"].to_numpy(float)
    y = df["Y"].to_numpy(float)

    ix, iy = digitize_points(x, y, x_edges, y_edges)

    solid = np.zeros((len(x_edges) - 1, len(y_edges) - 1), dtype=float)
    vol = sphere_volume(radii)

    for k in range(len(df)):
        solid[ix[k], iy[k]] += vol[k]

    dx = float(x_edges[1] - x_edges[0])
    dy = float(y_edges[1] - y_edges[0])

    h = np.maximum(top_surface - z_bottom, 1e-8)
    cell_vol = dx * dy * h

    phi = solid / cell_vol
    phi[np.isnan(top_surface)] = np.nan
    return phi


def extract_frame_number(path: Path):
    m = re.search(r"_(\d+)\.(csv|vtk)$", path.name)
    if not m:
        raise ValueError(f"Could not extract frame number from {path.name}")
    return int(m.group(1))


def moving_average_1d(arr, window):
    if window <= 1:
        return arr.copy()

    kernel = np.ones(window, dtype=float)
    valid = np.isfinite(arr).astype(float)
    filled = np.where(np.isfinite(arr), arr, 0.0)

    num = np.convolve(filled, kernel, mode="same")
    den = np.convolve(valid, kernel, mode="same")

    out = np.full_like(arr, np.nan, dtype=float)
    mask = den > 0
    out[mask] = num[mask] / den[mask]
    return out


def smooth_2d(arr, wx, wy):
    out = np.array(arr, dtype=float, copy=True)

    if wx > 1:
        temp = np.full_like(out, np.nan, dtype=float)
        for j in range(out.shape[1]):
            temp[:, j] = moving_average_1d(out[:, j], wx)
        out = temp

    if wy > 1:
        temp = np.full_like(out, np.nan, dtype=float)
        for i in range(out.shape[0]):
            temp[i, :] = moving_average_1d(out[i, :], wy)
        out = temp

    return out


def read_wheel_center_from_vtk(path: Path):
    if not path.exists():
        return None
    try:
        mesh = pv.read(path)
        if mesh.points is None or len(mesh.points) == 0:
            return None
        return np.asarray(mesh.points, dtype=float).mean(axis=0)
    except Exception:
        return None


def save_aggregate_csv(x_edges, y_edges, phi0, comp_mean, comp_max, settle_mean, settle_max, out_csv):
    x_centers = 0.5 * (x_edges[:-1] + x_edges[1:])
    y_centers = 0.5 * (y_edges[:-1] + y_edges[1:])

    rows = []
    for i, xc in enumerate(x_centers):
        for j, yc in enumerate(y_centers):
            rows.append(
                {
                    "x": xc,
                    "y": yc,
                    "phi_initial": phi0[i, j],
                    "compaction_mean_over_frames": comp_mean[i, j],
                    "compaction_max_over_frames": comp_max[i, j],
                    "settlement_mean_over_frames": settle_mean[i, j],
                    "settlement_max_over_frames": settle_max[i, j],
                }
            )

    pd.DataFrame(rows).to_csv(out_csv, index=False)


def prepare_display_grid(grid):
    g = np.array(grid, dtype=float, copy=True)

    finite = np.isfinite(g)
    if not np.any(finite):
        return g, None, None

    if SUBTRACT_BACKGROUND:
        if BACKGROUND_STAT == "mean":
            bg = np.nanmean(g)
        else:
            bg = np.nanmedian(g)
        g = g - bg
        g[g < 0.0] = 0.0

    positive = np.isfinite(g) & (g > 0.0)
    if MASK_BELOW_THRESHOLD and np.any(positive):
        thresh = np.nanpercentile(g[positive], THRESHOLD_PERCENTILE)
        g = np.where(g >= thresh, g, np.nan)

    vals = g[np.isfinite(g)]
    if vals.size == 0:
        return g, None, None

    vmin = np.nanpercentile(vals, COLOR_VMIN_PERCENTILE)
    vmax = np.nanpercentile(vals, COLOR_VMAX_PERCENTILE)

    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax <= vmin:
        vmin = np.nanmin(vals)
        vmax = np.nanmax(vals)

    return g, vmin, vmax


def save_overlay_png(grid, x_edges, y_edges, wheel_xy, title, cbar_label, out_png):
    g, vmin, vmax = prepare_display_grid(grid)

    finite_vals = g[np.isfinite(g)]
    if finite_vals.size == 0:
        raise RuntimeError("Grid has no finite values to plot after masking.")

    cmap = plt.cm.viridis.copy()
    cmap.set_bad(MASKED_BACKGROUND_COLOR)

    plt.figure(figsize=(10, 7))
    plt.imshow(
        g.T,
        origin="lower",
        extent=[x_edges[0], x_edges[-1], y_edges[0], y_edges[-1]],
        aspect="auto",
        vmin=vmin,
        vmax=vmax,
        cmap=cmap,
    )
    plt.colorbar(label=cbar_label)

    if wheel_xy is not None and len(wheel_xy) > 1:
        plt.plot(
            wheel_xy[:, 0],
            wheel_xy[:, 1],
            color="red",
            linewidth=3.0,
            label="wheel center path",
            zorder=5,
        )
        plt.scatter(
            wheel_xy[0, 0],
            wheel_xy[0, 1],
            s=70,
            marker="o",
            facecolors="white",
            edgecolors="black",
            linewidths=1.2,
            label="start",
            zorder=6,
        )
        plt.scatter(
            wheel_xy[-1, 0],
            wheel_xy[-1, 1],
            s=70,
            marker="x",
            color="white",
            linewidths=2.0,
            label="end",
            zorder=6,
        )
        plt.legend(loc="upper right", framealpha=0.9)

    plt.xlabel("X [m]")
    plt.ylabel("Y [m]")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_png, dpi=240)
    plt.close()


def summarize_compaction_metrics(compaction_mean_s, compaction_max_s, settlement_max_s, dx, dy, threshold):
    cell_area = dx * dy

    positive_max = np.where(np.isfinite(compaction_max_s) & (compaction_max_s > 0.0), compaction_max_s, 0.0)
    positive_mean = np.where(np.isfinite(compaction_mean_s) & (compaction_mean_s > 0.0), compaction_mean_s, 0.0)
    positive_settlement = np.where(np.isfinite(settlement_max_s) & (settlement_max_s > 0.0), settlement_max_s, 0.0)

    impacted_mask = positive_max > threshold

    return {
        "peak_compaction_max": float(np.nanmax(compaction_max_s)),
        "peak_compaction_mean": float(np.nanmax(compaction_mean_s)),
        "mean_compaction_all_cells": float(np.nanmean(compaction_mean_s)),
        "mean_compaction_impacted_cells": float(np.nanmean(compaction_mean_s[impacted_mask])) if np.any(impacted_mask) else np.nan,
        "compaction_area_above_threshold_m2": float(np.sum(impacted_mask) * cell_area),
        "integrated_compaction_max_map_m2": float(np.sum(positive_max) * cell_area),
        "integrated_compaction_mean_map_m2": float(np.sum(positive_mean) * cell_area),
        "max_settlement_m": float(np.nanmax(settlement_max_s)),
        "integrated_settlement_max_map_m3_per_m": float(np.sum(positive_settlement) * cell_area),
    }


def build_summary_figure(results, out_path):
    n = len(results)
    fig, axes = plt.subplots(1, n, figsize=(5.5 * n, 5.2), constrained_layout=True)

    if n == 1:
        axes = [axes]

    for ax, result in zip(axes, results):
        g, vmin, vmax = prepare_display_grid(result["plot_grid"])
        vals = g[np.isfinite(g)]
        if vals.size == 0:
            continue

        cmap = plt.cm.viridis.copy()
        cmap.set_bad(MASKED_BACKGROUND_COLOR)

        im = ax.imshow(
            g.T,
            origin="lower",
            extent=[result["x_edges"][0], result["x_edges"][-1], result["y_edges"][0], result["y_edges"][-1]],
            aspect="auto",
            vmin=vmin,
            vmax=vmax,
            cmap=cmap,
        )

        wheel_xy = result["wheel_xy"]
        if wheel_xy is not None and len(wheel_xy) > 1:
            ax.plot(wheel_xy[:, 0], wheel_xy[:, 1], "r-", linewidth=2.2, label="wheel center path")
            ax.scatter(wheel_xy[0, 0], wheel_xy[0, 1], s=30, marker="o", facecolors="white", edgecolors="black", label="start")
            ax.scatter(wheel_xy[-1, 0], wheel_xy[-1, 1], s=30, marker="x", color="white", label="end")

        ax.set_title(f"{WHEEL_LABEL}\nSlip {result['slip_display']}")
        ax.set_xlabel("X [m]")
        ax.set_ylabel("Y [m]")
        ax.legend(loc="upper right", fontsize=7, framealpha=0.9)

        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label(result["cbar_label"])

    fig.suptitle(f"{WHEEL_LABEL}: {PLOT_FIELD.replace('_', ' ').title()} Across Slip Conditions", fontsize=14)
    fig.savefig(out_path, dpi=240)
    plt.close(fig)


def parse_slip_value_from_dirname(dirname: str):
    m = re.search(r"_slip_([0-9.]+)$", dirname)
    if not m:
        return None
    raw = m.group(1)
    try:
        return float(raw)
    except ValueError:
        return None


def discover_slip_dirs(root: Path):
    dirs = []
    if not root.exists():
        raise FileNotFoundError(f"Slip root directory not found: {root}")

    for path in sorted(root.iterdir()):
        if not path.is_dir():
            continue
        if "_slip_" not in path.name:
            continue
        slip = parse_slip_value_from_dirname(path.name)
        if slip is None:
            continue
        dirs.append((slip, path))

    return sorted(dirs, key=lambda x: x[0])


# ============================================================
# MAIN
# ============================================================

def main():
    print("Loading settled terrain:", SETTLED_TERRAIN_CSV)
    df0 = load_xyz_csv(SETTLED_TERRAIN_CSV)

    base_radius = get_base_radius()
    radius_map = build_radius_map(base_radius, base_radius / 100.0, N_TEMPLATES)
    r0 = infer_radii(df0, radius_map, base_radius)

    slip_runs = discover_slip_dirs(SLIP_ROOT_DIR)
    if not slip_runs:
        raise RuntimeError(f"No slip trial directories found in {SLIP_ROOT_DIR}")

    all_cases_out_dir = OUTPUT_ROOT / "compaction_overlay_maps"
    all_cases_out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    summary_rows = []

    for slip, run_dir in slip_runs:
        slip_display = f"{slip:.3f}".rstrip("0").rstrip(".")
        print("=" * 80)
        print(f"Processing slip {slip_display} in {run_dir}")
        print("=" * 80)

        terrain_files = sorted(run_dir.glob(TERRAIN_GLOB), key=extract_frame_number)
        wheel_files = sorted(run_dir.glob(WHEEL_GLOB), key=extract_frame_number)

        if not terrain_files:
            print(f"Skipping {slip_display}: no terrain files found")
            continue

        x_edges, y_edges = make_grid(df0["X"].to_numpy(float), df0["Y"].to_numpy(float), DX, DY)

        z_bottom = float(np.min(df0["Z"].to_numpy(float) - r0))
        top0 = compute_top_surface_grid(df0, x_edges, y_edges, r0)
        phi0 = compute_phi_grid(df0, x_edges, y_edges, top0, z_bottom, r0)

        comp_stack = []
        settle_stack = []

        for frame_file in terrain_files:
            print("Processing:", frame_file.name)
            df = load_xyz_csv(frame_file)
            r = infer_radii(df, radius_map, base_radius)

            top = compute_top_surface_grid(df, x_edges, y_edges, r)

            fill_mask = np.isnan(top) & np.isfinite(top0)
            top[fill_mask] = top0[fill_mask]

            phi = compute_phi_grid(df, x_edges, y_edges, top, z_bottom, r)

            fill_phi = np.isnan(phi) & np.isfinite(phi0)
            phi[fill_phi] = phi0[fill_phi]

            comp_stack.append(phi - phi0)
            settle_stack.append(top0 - top)

        comp_stack = np.stack(comp_stack, axis=0)
        settle_stack = np.stack(settle_stack, axis=0)

        with np.errstate(all="ignore"):
            comp_mean = np.nanmean(comp_stack, axis=0)
            comp_max = np.nanmax(comp_stack, axis=0)
            settle_mean = np.nanmean(settle_stack, axis=0)
            settle_max = np.nanmax(settle_stack, axis=0)

        comp_mean[np.isnan(comp_mean)] = 0.0
        comp_max[np.isnan(comp_max)] = 0.0
        settle_mean[np.isnan(settle_mean)] = 0.0
        settle_max[np.isnan(settle_max)] = 0.0

        comp_mean_s = smooth_2d(comp_mean, SMOOTH_WIN_X, SMOOTH_WIN_Y)
        comp_max_s = smooth_2d(comp_max, SMOOTH_WIN_X, SMOOTH_WIN_Y)
        settle_mean_s = smooth_2d(settle_mean, SMOOTH_WIN_X, SMOOTH_WIN_Y)
        settle_max_s = smooth_2d(settle_max, SMOOTH_WIN_X, SMOOTH_WIN_Y)

        wheel_centers = []
        for wheel_file in wheel_files:
            center = read_wheel_center_from_vtk(wheel_file)
            if center is not None and np.all(np.isfinite(center)):
                wheel_centers.append(center)

        wheel_xy = None
        if wheel_centers:
            wheel_xy = np.array(wheel_centers, dtype=float)[:, :2]

        case_out_dir = all_cases_out_dir / f"slip_{slip_display}"
        case_out_dir.mkdir(parents=True, exist_ok=True)

        out_csv = case_out_dir / f"compaction_all_frames_slip_{slip_display}.csv"
        out_png = case_out_dir / f"compaction_all_frames_overlay_slip_{slip_display}.png"

        save_aggregate_csv(
            x_edges,
            y_edges,
            phi0,
            comp_mean_s,
            comp_max_s,
            settle_mean_s,
            settle_max_s,
            out_csv,
        )

        if PLOT_FIELD == "settlement_mean":
            plot_grid = settle_mean_s
            title = f"Slip {slip_display} Terrain Settlement Map - Mean Over All Frames"
            cbar_label = "Settlement [m]"
        elif PLOT_FIELD == "settlement_max":
            plot_grid = settle_max_s
            title = f"Slip {slip_display} Terrain Settlement Map - Maximum Over All Frames"
            cbar_label = "Settlement [m]"
        elif PLOT_FIELD == "compaction_mean":
            plot_grid = comp_mean_s
            title = f"{WHEEL_LABEL}: Compaction Mean Over All Frames (Slip {slip_display})"
            cbar_label = "Compaction above background"
        elif PLOT_FIELD == "compaction_max":
            plot_grid = comp_max_s
            title = f"{WHEEL_LABEL}: Compaction Max Over All Frames (Slip {slip_display})"
            cbar_label = "Compaction above background"
        else:
            raise ValueError(f"Unknown PLOT_FIELD: {PLOT_FIELD}")

        save_overlay_png(
            plot_grid,
            x_edges,
            y_edges,
            wheel_xy,
            title,
            cbar_label,
            out_png,
        )

        metrics = summarize_compaction_metrics(
            comp_mean_s,
            comp_max_s,
            settle_max_s,
            DX,
            DY,
            COMPACTION_THRESHOLD,
        )
        metrics["wheel_label"] = WHEEL_LABEL
        metrics["slip"] = slip
        metrics["terrain_frames"] = len(terrain_files)
        metrics["wheel_frames"] = len(wheel_files)
        metrics["run_directory"] = str(run_dir)

        print(f"\nSaved CSV : {out_csv}")
        print(f"Saved PNG : {out_png}")
        print(f"Peak compaction max : {metrics['peak_compaction_max']:.6e}")
        print(f"Integrated compaction max map : {metrics['integrated_compaction_max_map_m2']:.6e}")
        print(f"Compaction area above threshold : {metrics['compaction_area_above_threshold_m2']:.6e}")

        results.append(
            {
                "metrics": metrics,
                "plot_grid": plot_grid,
                "wheel_xy": wheel_xy,
                "x_edges": x_edges,
                "y_edges": y_edges,
                "cbar_label": cbar_label,
                "slip": slip,
                "slip_display": slip_display,
            }
        )
        summary_rows.append(metrics)

    if not results:
        raise RuntimeError("No valid slip runs were processed.")

    summary_df = pd.DataFrame(summary_rows).sort_values(by="slip")
    summary_csv = all_cases_out_dir / f"{WHEEL_LABEL.lower().replace(' ', '_')}_comparison_summary.csv"
    summary_df.to_csv(summary_csv, index=False)
    print(f"Saved summary CSV : {summary_csv}")

    summary_png = all_cases_out_dir / f"{WHEEL_LABEL.lower().replace(' ', '_')}_comparison_summary.png"
    build_summary_figure(results, summary_png)
    print(f"Saved summary figure : {summary_png}")


if __name__ == "__main__":
    main()
