#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#     "pyobjc-framework-Vision",
#     "pyobjc-framework-Quartz",
#     "pyobjc-framework-Cocoa",
#     "opencv-python-headless",
#     "tqdm",
# ]
# ///

"""
Apple Vision OCR - Images + Videos (smart dynamic mode)
Now with corrected grayscale change detection (no more OpenCV size error).

Usage:
  ./vision-ocr.py screen_recording.mp4 --dynamic --json -vv
  ./vision-ocr.py slides.mov --dynamic --change-threshold 0.02
    ./vision-ocr.py timelapse-20251021.mp4 --dynamic --json --skip-existing
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
from datetime import date, datetime
import json
import logging
from pathlib import Path
import platform
import sys

from Cocoa import NSURL, NSData
import cv2
import Quartz
from tqdm import tqdm
import Vision

VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm"}


def setup_logging(verbosity):
    logging_level = logging.WARNING
    if verbosity == 1:
        logging_level = logging.INFO
    elif verbosity >= 2:
        logging_level = logging.DEBUG
    logging.basicConfig(
        handlers=[logging.StreamHandler()],
        format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging_level,
    )


def parse_args():
    parser = ArgumentParser(
        description=__doc__, formatter_class=RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help=(
            "Optional files or directories to process. Directories are scanned "
            "recursively for video files."
        ),
    )
    parser.add_argument(
        "--base-dir",
        default=str(Path.home() / "Documents" / "Screenshots"),
        help="Base screenshots directory used when no positional inputs are provided",
    )
    parser.add_argument(
        "--date",
        help=(
            "Process a single date under --base-dir (YYYY-MM-DD or YYYYMMDD). "
            "Only used when no positional inputs are provided."
        ),
    )
    parser.add_argument(
        "--languages",
        nargs="*",
        default=["en"],
        help="Recognition languages (default: en)",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.35,
        help="Minimum confidence threshold (default: 0.35)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Fixed interval (seconds) when --dynamic is NOT used",
    )
    parser.add_argument(
        "--dynamic",
        action="store_true",
        help="Smart mode: only process frames when screen content changes",
    )
    parser.add_argument(
        "--change-threshold",
        type=float,
        default=0.03,
        help="Change sensitivity (0.01 = very sensitive, 0.1 = less sensitive)",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        help="Limit number of frames processed per video",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Export detailed results as .ocr.json",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip files that already have a matching .ocr.json output",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="Increase verbosity (-v = INFO, -vv = DEBUG)",
    )
    return parser.parse_args()


def parse_date(date_str: str) -> date:
    try:
        if "-" in date_str:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        return datetime.strptime(date_str, "%Y%m%d").date()
    except ValueError:
        print("Date must be in YYYY-MM-DD or YYYYMMDD format", file=sys.stderr)
        sys.exit(2)


def build_date_dir(base_dir: Path, target_date: date) -> Path:
    return (
        base_dir
        / f"{target_date.year:04d}"
        / f"{target_date.month:02d}"
        / f"{target_date.day:02d}"
    )


def collect_videos_recursively(root_dir: Path) -> list[Path]:
    files = [
        path
        for path in root_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in VIDEO_EXTS
    ]
    return sorted(files)


def resolve_targets(args) -> list[Path]:
    targets: list[Path] = []

    if args.inputs:
        for raw in args.inputs:
            path = Path(raw).expanduser()
            if not path.exists():
                logging.error(f"File or directory not found: {path}")
                continue
            if path.is_dir():
                targets.extend(collect_videos_recursively(path))
            else:
                targets.append(path)
    else:
        base_dir = Path(args.base_dir).expanduser()
        if args.date:
            target_date = parse_date(args.date)
            date_dir = build_date_dir(base_dir, target_date)
            if not date_dir.exists():
                logging.error(f"Date directory not found: {date_dir}")
                return []
            targets = collect_videos_recursively(date_dir)
        else:
            if not base_dir.exists():
                logging.error(f"Base directory not found: {base_dir}")
                return []
            targets = collect_videos_recursively(base_dir)

    unique_targets: list[Path] = []
    seen: set[str] = set()
    for target in targets:
        key = str(target.resolve())
        if key in seen:
            continue
        seen.add(key)
        unique_targets.append(target)
    return sorted(unique_targets)


def numpy_to_ciimage(frame):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    success, buffer = cv2.imencode(".png", rgb)
    if not success:
        return None
    nsdata = NSData.dataWithBytes_length_(buffer.tobytes(), len(buffer))
    return Quartz.CIImage.imageWithData_(nsdata)


def perform_ocr(ci_image, languages, min_confidence):
    if ci_image is None:
        return []

    extent = ci_image.extent()
    width = extent.size.width
    height = extent.size.height

    handler = Vision.VNImageRequestHandler.alloc().initWithCIImage_options_(
        ci_image, None
    )

    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLanguages_(languages)
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)

    success, error = handler.performRequests_error_([request], None)
    if not success:
        logging.error(f"Vision request failed: {error}")
        return []

    results = []
    for observation in request.results():
        candidate = observation.topCandidates_(1)[0]
        confidence = float(candidate.confidence())
        if confidence < min_confidence:
            continue

        box = observation.boundingBox()
        x = box.origin.x * width
        y = (1.0 - box.origin.y - box.size.height) * height
        w = box.size.width * width
        h = box.size.height * height

        results.append({
            "text": candidate.string(),
            "confidence": round(confidence, 4),
            "bbox": [round(x), round(y), round(w), round(h)],
        })

    return results


def is_significant_change(current_frame, last_gray, threshold):
    """Fast change detection – now correctly handles grayscale only."""
    if last_gray is None:
        return True

    gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (640, 360), interpolation=cv2.INTER_AREA)
    last_small = cv2.resize(last_gray, (640, 360), interpolation=cv2.INTER_AREA)

    diff = cv2.absdiff(small, last_small)
    mean_change = cv2.mean(diff)[0] / 255.0
    return mean_change > threshold


def process_file(path: Path, args):
    print(f"\n{"=" * 80}")
    print(f"📂 {path.name}")
    print("=" * 80)

    is_video = path.suffix.lower() in VIDEO_EXTS

    all_results = []

    if is_video:
        cap = cv2.VideoCapture(str(path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        processed = 0
        last_gray = None  # ← now always grayscale
        last_timestamp = -1.0

        with tqdm(total=total_frames, desc="Scanning frames", unit="frame") as pbar:
            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                timestamp = frame_idx / fps

                if args.dynamic:
                    should_process = is_significant_change(
                        frame, last_gray, args.change_threshold
                    )
                    if should_process and (timestamp - last_timestamp < 0.2):
                        should_process = False
                else:
                    should_process = (frame_idx % max(1, int(fps * args.interval))) == 0

                if should_process:
                    ci_image = numpy_to_ciimage(frame)
                    detections = perform_ocr(
                        ci_image, args.languages, args.min_confidence
                    )

                    print(f"  ⏱️  {timestamp:6.2f}s → {len(detections):2d} text regions")
                    for item in detections:
                        print(f"     • {item["text"]}")

                    all_results.append({
                        "timestamp": round(timestamp, 3),
                        "frame": frame_idx,
                        "detections": detections,
                    })

                    # FIXED: store grayscale version
                    last_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    last_timestamp = timestamp
                    processed += 1

                pbar.update(1)
                frame_idx += 1

                if args.max_frames and processed >= args.max_frames:
                    break

        cap.release()
        print(
            f"   Processed {processed} unique frames (skipped {frame_idx - processed} duplicates)"
        )

    else:
        # Image handling unchanged
        url = NSURL.fileURLWithPath_(str(path))
        ci_image = Quartz.CIImage.imageWithContentsOfURL_(url)
        detections = perform_ocr(ci_image, args.languages, args.min_confidence)

        for i, item in enumerate(detections, 1):
            print(f"{i:2d}. {item["text"]}")

        all_results = [{"detections": detections}]

    if args.json:
        json_path = path.with_suffix(".ocr.json")
        with Path(json_path).open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "filename": path.name,
                    "type": "video" if is_video else "image",
                    "languages": args.languages,
                    "results": all_results,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        print(f"   → Saved detailed JSON: {json_path.name}")


def main(args):
    if platform.system() != "Darwin":
        print("❌ Error: This script requires macOS.")
        sys.exit(1)

    paths = resolve_targets(args)
    if not paths:
        print("No matching files found.")
        return

    print(f"Found {len(paths)} file(s) to process")
    for path in paths:
        if args.skip_existing:
            json_path = path.with_suffix(".ocr.json")
            if json_path.exists():
                print(f"Skipping {path.name}: {json_path.name} already exists")
                continue
        process_file(path, args)


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
