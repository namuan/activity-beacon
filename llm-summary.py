#!/usr/bin/env -S uv run --quiet --script
# Copied from https://www.reddit.com/r/LocalLLaMA/comments/1p82u5k/local_videototext_pipeline_on_apple_silicon/
# /// script
# dependencies = [
#   "opencv-python",
#   "pillow",
#   "mlx-vlm",
#   "openai-whisper",
#   "torch"
# ]
# ///
# Video-to-text summary pipeline for local LLM workflows.
# It:
# 1. detects approximate scene boundaries from sampled frames,
# 2. transcribes the video audio with Whisper,
# 3. describes one representative frame per scene with Qwen3-VL,
# 4. writes a timestamped text summary for downstream LLM/RAG use.
#
# Standard usage:
# uv run llm-summary.py video.mp4
#
# Advanced usage:
# uv run llm-summary.py meeting.mp4 --whisper-model large-v3 --prompt "Describe the charts on the slide."
import argparse
import gc
from pathlib import Path
import re
import time

import numpy as np

# --------- QWEN / MLX CONFIG ---------
MODEL_PATH = "mlx-community/Qwen3-VL-2B-Instruct-4bit"
RESIZE_DIM = (384, 384)

PREFIXES_TO_REMOVE = [
    "this image shows",
    "the image shows",
    "in this image",
    "on this image",
    "here is",
    "it's",
    "it is",
    "i see",
    "i can see",
    "there is",
    "we see",
    "a view of",
]


# --------- MODEL LOADING ---------


def load_qwen_model() -> tuple:
    """Load and return the Qwen3-VL model, processor, and config."""
    from mlx_vlm import load
    from mlx_vlm.utils import load_config

    print(f"Loading VLM model: {MODEL_PATH}...")
    model, processor = load(MODEL_PATH, trust_remote_code=True)
    config = load_config(MODEL_PATH)
    print("Qwen3-VL loaded.")
    return model, processor, config


def load_whisper_model(name: str) -> object:
    """Load and return a Whisper model."""
    import whisper

    print(f"Loading Whisper model: {name}...")
    model = whisper.load_model(name)
    print(f"Whisper {name} loaded.")
    return model


# --------- TEXT / TIME UTILITIES ---------


def clean_caption(raw_text: str) -> str:
    """Clean caption text by removing common boilerplate prefixes and trailing punctuation."""
    cleaned = raw_text.strip()
    if not cleaned:
        return ""

    lower_clean = cleaned.lower()

    # avoid apology responses
    if "sorry" in lower_clean:
        return ""

    for prefix in PREFIXES_TO_REMOVE:
        if lower_clean.startswith(prefix):
            cleaned = cleaned[len(prefix) :]
            lower_clean = cleaned.lower()

    cleaned = re.sub(
        r"^(que\s|qu'|:|,|\.|je vois)\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()

    # cut at the first strong punctuation from the end
    m = re.search(r"[\.!?]", cleaned[::-1])
    if m:
        end_pos = len(cleaned) - m.start()
        cleaned = cleaned[:end_pos]

    cleaned = cleaned.strip()
    if not cleaned:
        return ""

    return cleaned[0].upper() + cleaned[1:]


def format_time_str(t_sec: float) -> str:
    minutes = int(t_sec // 60)
    seconds = int(t_sec % 60)
    return f"{minutes:02d}:{seconds:02d}"


# --------- FEATURES FOR SCENES ---------


def compute_frame_feature(frame_bgr: object) -> np.ndarray:
    """
    Create a simple image fingerprint for scene detection.
    -> grayscale, resize 64x64, vector 0-1.
    """
    import cv2

    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (64, 64))
    vec = small.astype("float32") / 255.0
    return vec.flatten()


# --------- PASS 1: SCENE DETECTION (WITHOUT QWEN) ---------


def detect_scenes(
    video_path: str, sample_fps: float = 1.0, scene_threshold: float = 0.20
) -> tuple:
    """
    Pass 1: iterate the video at sample_fps (e.g., 1 frame/sec),
    compute a feature per frame, and detect scene changes based on
    an average-difference threshold.

    Returns:
    - scenes_raw: list of dicts { "start_sec", "end_sec" }
    - duration_sec: approximate video duration
    """
    import cv2

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video: {video_path}")

    base_fps = cap.get(cv2.CAP_PROP_FPS)
    if base_fps <= 0:
        base_fps = 25.0

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / base_fps if total_frames > 0 else 0

    frame_interval = max(1, round(base_fps / sample_fps))

    print(f"[SCENES] Video FPS ≈ {base_fps:.2f}")
    print(f"[SCENES] Total frames: {total_frames}")
    print(f"[SCENES] Approx duration: {duration_sec:.1f} s")
    print(f"[SCENES] Sampling at {sample_fps} fps => interval {frame_interval} frames")
    print(f"[SCENES] Scene threshold: {scene_threshold}")

    scenes_raw = []
    last_feat = None
    current_start_sec = None
    prev_t_sec = None

    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval != 0:
            frame_idx += 1
            continue

        t_sec = frame_idx / base_fps
        feat = compute_frame_feature(frame)

        if last_feat is None:
            # first frame
            current_start_sec = t_sec
            prev_t_sec = t_sec
            last_feat = feat
        else:
            diff = float(np.mean(np.abs(feat - last_feat)))
            if diff > scene_threshold:
                # close previous scene
                scenes_raw.append({
                    "start_sec": current_start_sec,
                    "end_sec": prev_t_sec,
                })
                # new scene
                current_start_sec = t_sec

            prev_t_sec = t_sec
            last_feat = feat

        frame_idx += 1

    # close the last scene
    if current_start_sec is not None:
        end_sec = duration_sec if duration_sec > 0 else prev_t_sec
        scenes_raw.append({
            "start_sec": current_start_sec,
            "end_sec": end_sec,
        })

    cap.release()

    print(f"[SCENES] Number of scenes detected: {len(scenes_raw)}")
    for i, sc in enumerate(scenes_raw, start=1):
        print(
            f"  SCENE {i}: {format_time_str(sc["start_sec"])} - {format_time_str(sc["end_sec"])}"
        )

    return scenes_raw, duration_sec


# --------- PASS 2: QWEN ON A REPRESENTATIVE FRAME PER SCENE ---------


def grab_frame_at_time(video_path: str, t_sec: float) -> object | None:
    """
    Retrieve a frame at t_sec (in seconds).
    """
    import cv2

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video: {video_path}")

    cap.set(cv2.CAP_PROP_POS_MSEC, t_sec * 1000.0)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return None
    return frame


def describe_scene_qwen(
    model: object,
    processor: object,
    config: object,
    video_path: str,
    start_sec: float,
    end_sec: float,
    max_tokens: int,
    prompt: str,
) -> str | None:
    """
    Choose a representative time (middle of the scene),
    retrieve the corresponding frame and send it to Qwen-VL.
    """
    rep_sec = (start_sec + end_sec) / 2.0
    frame = grab_frame_at_time(video_path, rep_sec)
    if frame is None:
        return None

    import cv2
    from mlx_vlm import generate
    from mlx_vlm.prompt_utils import apply_chat_template
    from PIL import Image

    small_frame = cv2.resize(frame, RESIZE_DIM)
    frame_rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(frame_rgb)

    formatted_prompt = apply_chat_template(processor, config, prompt, num_images=1)

    output = generate(
        model,
        processor,
        formatted_prompt,
        pil_image,
        max_tokens=max_tokens,
        verbose=False,
        repetition_penalty=1.05,
        temp=0.0,
    )

    raw_text = output.text if hasattr(output, "text") else str(output)

    cleaned = clean_caption(raw_text)
    if not cleaned:
        return None

    return cleaned


def describe_all_scenes(
    model: object,
    processor: object,
    config: object,
    video_path: str,
    scenes_raw: list,
    max_tokens: int,
    prompt: str,
) -> list:
    """
    For each raw scene (start_sec, end_sec),
    call Qwen-VL ONCE,
    and return a list of enriched scenes:
    {
      "start_sec": ...,
      "end_sec": ...,
      "start_str": "MM:SS",
      "end_str": "MM:SS",
      "caption": "..."
    }
    """
    scenes = []
    t0 = time.time()

    for idx, sc in enumerate(scenes_raw, start=1):
        start_sec = sc["start_sec"]
        end_sec = sc["end_sec"]
        print(
            f"[VLM-SCENE] SCENE {idx} => {format_time_str(start_sec)} - {format_time_str(end_sec)}"
        )
        caption = describe_scene_qwen(
            model,
            processor,
            config,
            video_path,
            start_sec,
            end_sec,
            max_tokens=max_tokens,
            prompt=prompt,
        )
        if caption is None:
            caption = "(Description unavailable)"

        scene_entry = {
            "start_sec": start_sec,
            "end_sec": end_sec,
            "start_str": format_time_str(start_sec),
            "end_str": format_time_str(end_sec),
            "caption": caption,
        }
        print("    ->", caption)
        scenes.append(scene_entry)

    print(f"[VLM-SCENE] Total VLM time for scenes: {time.time() - t0:.1f} s")
    return scenes


# --------- WHISPER ---------


def transcribe_audio_whisper(
    whisper_model: object, video_path: str, language: str | None = None
) -> dict:
    """
    Transcribe the video directly (Whisper uses ffmpeg internally).
    Returns the full object (with segments).
    """
    print("[WHISPER] Transcription in progress...")
    t0 = time.time()
    result = whisper_model.transcribe(video_path, language=language)
    print(f"[WHISPER] Transcription completed in {time.time() - t0:.1f} s")
    return result


# --------- BUILD FINAL TEXT ---------


def build_output_text(
    transcription: dict, scenes: list, video_path: str, duration_sec: float
) -> str:
    lines = []

    lines.append("### VIDEO CONTEXT FOR LLM (UTF-8)\n")
    lines.append(f"Original video file: {video_path}")
    lines.append(f"Approximate duration: {duration_sec:.1f} seconds\n")

    # --- SECTION 0: approximate global description ---
    lines.append("SECTION 0: GLOBAL DESCRIPTION (from scenes)\n")
    if scenes:
        first = scenes[0]
        mid = scenes[len(scenes) // 2]
        last = scenes[-1]

        lines.append(
            f"- Start [{first["start_str"]} - {first["end_str"]}]: {first["caption"]}"
        )
        if mid is not first and mid is not last:
            lines.append(
                f"- Middle [{mid["start_str"]} - {mid["end_str"]}]: {mid["caption"]}"
            )
        lines.append(
            f"- End [{last["start_str"]} - {last["end_str"]}]: {last["caption"]}"
        )
    else:
        lines.append("(No scenes detected.)")
    lines.append("")

    # --- SECTION 1: audio transcription ---
    lines.append("SECTION 1: AUDIO TRANSCRIPTION (Whisper)\n")
    full_text = transcription.get("text", "").strip()
    lines.append("FULL TEXT:")
    lines.append(full_text if full_text else "(Empty or unavailable transcription.)")
    lines.append("")

    if "segments" in transcription:
        lines.append("TIMESTAMPED SEGMENTS:")
        for seg in transcription["segments"]:
            start = seg.get("start", 0.0)
            end = seg.get("end", 0.0)
            txt = seg.get("text", "").strip()
            m1, s1 = divmod(int(start), 60)
            m2, s2 = divmod(int(end), 60)
            lines.append(f"[{m1:02d}:{s1:02d} - {m2:02d}:{s2:02d}] {txt}")
        lines.append("")

    # --- SECTION 2: described visual scenes ---
    lines.append("SECTION 2: VISUAL SCENES (Qwen3-VL, 1 description per scene)\n")
    if not scenes:
        lines.append("(No scenes available.)")
    else:
        for idx, sc in enumerate(scenes, start=1):
            lines.append(f"SCENE {idx} [{sc["start_str"]} - {sc["end_str"]}]")
            lines.append(f"- Description: {sc["caption"]}")
            lines.append("")

    lines.append("\nEND OF CONTEXT.\n")
    return "\n".join(lines)


# --------- MAIN ---------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze a video for LLM consumption by combining scene detection, "
            "audio transcription, and one visual description per detected scene."
        ),
        epilog=(
            "Pipeline:\n"
            "  1. Sample frames to detect approximate scene changes.\n"
            "  2. Run Whisper on the full video audio track.\n"
            "  3. Pick the midpoint frame of each scene and describe it with Qwen3-VL.\n"
            "  4. Write a text file containing the global summary, full transcript, "
            "timestamped segments, and scene descriptions.\n\n"
            "Examples:\n"
            "  uv run llm-summary.py video.mp4\n"
            "  uv run llm-summary.py meeting.mov --whisper-model large-v3 "
            '--prompt "Describe the slide content factually."\n'
            "  uv run llm-summary.py demo.mp4 --sample-fps 2 --scene-threshold 0.15 "
            "--out demo-context.txt"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "video",
        help="Path to the input video file, such as .mp4 or .mov.",
    )
    parser.add_argument(
        "--sample-fps",
        type=float,
        default=1.0,
        help="Frame sampling rate used for scene detection. Higher values detect changes more precisely.",
    )
    parser.add_argument(
        "--scene-threshold",
        type=float,
        default=0.20,
        help="Average frame-difference threshold for opening a new scene, in the 0-1 range.",
    )
    parser.add_argument(
        "--whisper-model",
        type=str,
        default="small",
        help="Whisper model to load, for example small, medium, or large-v3.",
    )
    parser.add_argument(
        "--whisper-lang",
        type=str,
        default=None,
        help="Optional Whisper language code, such as en. Defaults to auto-detection.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=60,
        help="Maximum Qwen3-VL output tokens generated for each scene description.",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=(
            "Describe factually what is present in the image in English. "
            "Be direct and precise, without unnecessary interpretation."
        ),
        help="Prompt sent to Qwen3-VL for each representative scene frame.",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="video_context_v3_1.txt",
        help="UTF-8 output path for the generated summary text file.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    video_path = str(Path(args.video).resolve())
    if not Path(video_path).exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    # 1) Scene detection (fast, without models)
    scenes_raw, duration_sec = detect_scenes(
        video_path,
        sample_fps=args.sample_fps,
        scene_threshold=args.scene_threshold,
    )

    # 2) Whisper first (audio)
    model_whisper = load_whisper_model(args.whisper_model)
    transcription = transcribe_audio_whisper(
        model_whisper, video_path, language=args.whisper_lang
    )

    # 🔥 Free Whisper from RAM
    del model_whisper
    gc.collect()

    # 3) Then Qwen-VL (vision)
    model_vlm, processor_vlm, config_vlm = load_qwen_model()

    # 4) Description of each scene (1 representative frame)
    scenes = describe_all_scenes(
        model_vlm,
        processor_vlm,
        config_vlm,
        video_path,
        scenes_raw,
        max_tokens=args.max_tokens,
        prompt=args.prompt,
    )

    # 5) Build the final text
    output_text = build_output_text(
        transcription,
        scenes,
        video_path,
        duration_sec,
    )

    out_path = Path(args.out)
    out_path.write_text(output_text, encoding="utf-8")
    print(f"\n✅ Context file V3.1 generated: {out_path}")
    print("   You can now copy/paste this file into Open WebUI or LM Studio (RAG).")


if __name__ == "__main__":
    main()
