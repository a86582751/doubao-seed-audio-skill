#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import concurrent.futures
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ENV_FILES = [
    Path.home() / ".codex" / "speech.env",
    Path.home() / ".codex" / "seedance.env",
]
SKILL_DIR = Path(__file__).resolve().parents[1]
VOICE_LIST = SKILL_DIR / "references" / "official-voice-list.md"
DEFAULT_BASE_URL = "https://openspeech.bytedance.com"
DEFAULT_CREATE_PATH = "/api/v3/tts/create"
DEFAULT_MODEL = "seed-audio-1.0"
MAX_TEXT_PROMPT_CHARS = 2048
MAX_REFERENCE_BYTES = 10 * 1024 * 1024
MAX_AUDIO_REFERENCE_SECONDS = 30.0
ALLOWED_AUDIO_SUFFIXES = {".wav", ".mp3", ".pcm", ".ogg", ".opus", ".ogg_opus"}
ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def load_env_files(paths: list[Path] = ENV_FILES) -> dict[str, str]:
    values: dict[str, str] = {}
    for path in paths:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in values:
                values[key] = value
    return values


ENV_FALLBACK = load_env_files()


def env(name: str, default: str = "", *fallbacks: str) -> str:
    for key in (name, *fallbacks):
        value = os.environ.get(key)
        if value:
            return value
    for key in (name, *fallbacks):
        value = ENV_FALLBACK.get(key)
        if value:
            return value
    return default


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * max(4, len(value) - 8) + value[-4:]


def endpoint(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def read_prompt(args: argparse.Namespace) -> str:
    if getattr(args, "prompt_file", None):
        return Path(args.prompt_file).read_text(encoding="utf-8-sig").strip()
    return (args.prompt or "").strip()


def media_b64(path: str) -> str:
    data = Path(path).read_bytes()
    return base64.b64encode(data).decode("ascii")


def winget_ffmpeg_candidates(tool: str) -> list[str]:
    bundled_root = Path.home() / "Documents" / "Codex" / "tools"
    bundled_matches = list(bundled_root.glob(f"ffmpeg-*-full_build/bin/{tool}.exe")) if bundled_root.exists() else []
    roots = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages",
        Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages",
    ]
    matches: list[Path] = bundled_matches[:]
    for root in roots:
        if not root.exists():
            continue
        matches.extend(root.glob(f"Gyan.FFmpeg_*/**/bin/{tool}.exe"))
    unique = {path.resolve(): path for path in matches if path.exists()}
    ordered = sorted(unique.values(), key=lambda path: path.stat().st_mtime, reverse=True)
    return [str(path) for path in ordered]


def find_ffprobe() -> str:
    for bundled in winget_ffmpeg_candidates("ffprobe"):
        return bundled
    direct = shutil.which("ffprobe")
    if direct:
        return direct
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        sibling = Path(ffmpeg).with_name("ffprobe.exe")
        if sibling.exists():
            return str(sibling)
    return ""


def audio_duration_seconds(path: Path) -> float | None:
    ffprobe = find_ffprobe()
    if not ffprobe:
        return None
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=15)
        return float(result.stdout.strip())
    except Exception:
        return None


def validate_local_reference(path_text: str, kind: str) -> None:
    path = Path(path_text)
    if not path.exists():
        raise SystemExit(f"Reference {kind} not found: {path}")
    if not path.is_file():
        raise SystemExit(f"Reference {kind} is not a file: {path}")
    suffix = path.suffix.lower()
    if kind == "audio":
        allowed = ALLOWED_AUDIO_SUFFIXES
        allowed_text = "wav/mp3/pcm/ogg_opus"
    else:
        allowed = ALLOWED_IMAGE_SUFFIXES
        allowed_text = "jpeg/png/webp"
    if suffix not in allowed:
        raise SystemExit(f"Unsupported reference {kind} format: {path.name}. Expected {allowed_text}.")
    size = path.stat().st_size
    if size > MAX_REFERENCE_BYTES:
        raise SystemExit(f"Reference {kind} exceeds 10 MB: {path}")
    if kind == "audio":
        duration = audio_duration_seconds(path)
        if duration is not None and duration > MAX_AUDIO_REFERENCE_SECONDS:
            raise SystemExit(f"Reference audio exceeds 30 seconds ({duration:.2f}s): {path}")


def validate_reference_args(args: argparse.Namespace) -> None:
    speakers = args.speaker or []
    audio_files = args.audio or []
    audio_urls = args.audio_url or []
    audio_ref_count = len(audio_files) + len(audio_urls) + len(speakers)
    image_ref_count = (1 if args.image else 0) + (1 if args.image_url else 0)
    if audio_ref_count and image_ref_count:
        raise SystemExit("Image references cannot be mixed with speaker/audio references.")
    if audio_ref_count > 3:
        raise SystemExit("At most three audio references are supported, including speaker IDs.")
    if image_ref_count > 1:
        raise SystemExit("At most one reference image is supported.")
    for path in audio_files:
        validate_local_reference(path, "audio")
    if args.image:
        validate_local_reference(args.image, "image")


def build_references(args: argparse.Namespace) -> list[dict[str, Any]]:
    validate_reference_args(args)
    refs: list[dict[str, Any]] = []
    for speaker in args.speaker or []:
        refs.append({"speaker": speaker})
    for url in args.audio_url or []:
        refs.append({"audio_url": url})
    for path in args.audio or []:
        refs.append({"audio_data": media_b64(path)})
    if args.image_url:
        refs.append({"image_url": args.image_url})
    if args.image:
        refs.append({"image_data": media_b64(args.image)})
    audio_like = [r for r in refs if "speaker" in r or "audio_url" in r or "audio_data" in r]
    image_like = [r for r in refs if "image_url" in r or "image_data" in r]
    if audio_like and image_like:
        raise SystemExit("Image references cannot be mixed with speaker/audio references.")
    if len(audio_like) > 3:
        raise SystemExit("At most three audio references are supported, including speaker IDs.")
    if len(image_like) > 1:
        raise SystemExit("At most one reference image is supported.")
    return refs


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    prompt = read_prompt(args)
    if not prompt:
        raise SystemExit("A prompt is required. Use --prompt or --prompt-file.")
    if getattr(args, "strict_tts", False):
        prompt = f"请严格只朗读以下文本，不要续写、不要改写、不要添加任何内容：\n“{prompt}”"
    if len(prompt) > MAX_TEXT_PROMPT_CHARS:
        raise SystemExit(f"text_prompt exceeds {MAX_TEXT_PROMPT_CHARS} characters after wrapping.")
    payload: dict[str, Any] = {
        "model": args.model,
        "text_prompt": prompt,
        "audio_config": {
            "format": args.format,
            "sample_rate": args.sample_rate,
            "speech_rate": args.speech_rate,
            "loudness_rate": args.loudness_rate,
            "pitch_rate": args.pitch_rate,
            "enable_subtitle": args.enable_subtitle,
        },
    }
    refs = build_references(args)
    if refs:
        payload["references"] = refs
    watermark: dict[str, Any] = {}
    if args.aigc_watermark:
        watermark["aigc_watermark"] = True
    if args.metadata:
        watermark["aigc_metadata"] = {"enable": True}
        for key in ("content_producer", "produce_id", "content_propagator", "propagate_id"):
            value = getattr(args, key)
            if value:
                watermark["aigc_metadata"][key] = value
    if watermark:
        payload["watermark"] = watermark
    return payload


def scrub_payload(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned = json.loads(json.dumps(payload, ensure_ascii=False))
    for ref in cleaned.get("references", []):
        for key in ("audio_data", "image_data"):
            if key in ref:
                ref[key] = f"<base64:{len(ref[key])} chars>"
    return cleaned


def call_create(payload: dict[str, Any], api_key: str, base_url: str, path: str, timeout: int) -> tuple[dict[str, Any], dict[str, str]]:
    request_id = str(uuid.uuid4())
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "X-Api-Key": api_key,
        "X-Api-Request-Id": request_id,
        "Content-Type": "application/json",
    }
    request = Request(endpoint(base_url, path), data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8")
            meta = {"http_status": str(response.status), "request_id": request_id}
            logid = response.headers.get("X-Tt-Logid")
            if logid:
                meta["logid"] = logid
            return json.loads(text), meta
    except HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {exc.reason}: {body_text}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error: {exc.reason}") from exc


def save_audio(result: dict[str, Any], output_dir: Path, name: str, fmt: str, timeout: int) -> Path | None:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{name}.{fmt}"
    audio = result.get("audio")
    if audio:
        path.write_bytes(base64.b64decode(audio))
        return path
    url = result.get("url")
    if url:
        with urlopen(url, timeout=timeout) as response:
            path.write_bytes(response.read())
        return path
    return None


def generate_once(args: argparse.Namespace, prompt_file: str = "", prompt_text: str = "", name_suffix: str = "") -> dict[str, Any]:
    api_key = env("SEED_AUDIO_API_KEY", "", "SPEECH_API_KEY", "X_API_KEY")
    base_url = env("SEED_AUDIO_BASE_URL", DEFAULT_BASE_URL, "SPEECH_BASE_URL")
    path = env("SEED_AUDIO_CREATE_PATH", DEFAULT_CREATE_PATH, "SPEECH_CREATE_PATH")
    task_args = argparse.Namespace(**vars(args))
    if prompt_file:
        task_args.prompt_file = prompt_file
        task_args.prompt = None
    if prompt_text:
        task_args.prompt = prompt_text
        task_args.prompt_file = None
    payload = build_payload(task_args)
    if args.show_config:
        print(json.dumps({
            "api_key": mask_secret(api_key),
            "base_url": base_url,
            "path": path,
            "model": args.model,
        }, ensure_ascii=False, indent=2))
    if args.dry_run:
        return {"payload": scrub_payload(payload), "prompt_file": prompt_file or None}
    if not api_key:
        raise SystemExit("Missing SEED_AUDIO_API_KEY or SPEECH_API_KEY.")
    result, meta = call_create(payload, api_key, base_url, path, args.timeout)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = args.name or (Path(prompt_file).stem if prompt_file else "seed_audio")
    if name_suffix:
        base_name = f"{base_name}_{name_suffix}"
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", base_name).strip("_") or "seed_audio"
    name = f"{stamp}_{safe}"
    output_dir = Path(args.output_dir)
    audio_path = save_audio(result, output_dir, name, task_args.format, args.timeout)
    summary = {
        "meta": meta,
        "code": result.get("code"),
        "message": result.get("message"),
        "duration": result.get("duration"),
        "original_duration": result.get("original_duration"),
        "has_audio": bool(result.get("audio")),
        "has_url": bool(result.get("url")),
        "audio_path": str(audio_path) if audio_path else None,
        "subtitle": result.get("subtitle"),
        "payload": scrub_payload(payload),
        "prompt_file": prompt_file or None,
    }
    summary_path = output_dir / f"{name}.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def command_generate(args: argparse.Namespace) -> None:
    summary = generate_once(args)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def collect_batch_prompt_files(args: argparse.Namespace) -> list[Path]:
    files: list[Path] = []
    if args.prompt_list:
        for raw_line in Path(args.prompt_list).read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.strip()
            if line and not line.startswith("#"):
                files.append(Path(line))
    for item in args.prompt_files or []:
        files.append(Path(item))
    if args.prompt_file:
        files.append(Path(args.prompt_file))
    if args.prompt_dir:
        files.extend(sorted(Path(args.prompt_dir).glob(args.prompt_glob)))
    unique: list[Path] = []
    seen: set[Path] = set()
    for file in files:
        path = file.expanduser().resolve()
        if path in seen:
            continue
        if not path.exists():
            raise SystemExit(f"Prompt file not found: {path}")
        if not path.is_file():
            raise SystemExit(f"Prompt path is not a file: {path}")
        seen.add(path)
        unique.append(path)
    if not unique and args.prompt:
        return []
    if not unique:
        raise SystemExit("Provide --prompt-files, --prompt-list, --prompt-dir, --prompt-file, or --prompt.")
    return unique


def command_batch_generate(args: argparse.Namespace) -> None:
    prompt_files = collect_batch_prompt_files(args)
    if args.show_config:
        print(json.dumps({
            "api_key": mask_secret(env("SEED_AUDIO_API_KEY", "", "SPEECH_API_KEY", "X_API_KEY")),
            "base_url": env("SEED_AUDIO_BASE_URL", DEFAULT_BASE_URL, "SPEECH_BASE_URL"),
            "path": env("SEED_AUDIO_CREATE_PATH", DEFAULT_CREATE_PATH, "SPEECH_CREATE_PATH"),
            "model": args.model,
            "jobs": args.jobs,
        }, ensure_ascii=False, indent=2))
        args.show_config = False
    if not prompt_files:
        summary = generate_once(args, prompt_text=args.prompt, name_suffix="part01")
        print(json.dumps({"jobs": 1, "results": [summary]}, ensure_ascii=False, indent=2))
        return
    jobs = max(1, min(args.jobs, len(prompt_files)))
    results: list[dict[str, Any] | None] = [None] * len(prompt_files)

    def run(index_and_path: tuple[int, Path]) -> dict[str, Any]:
        index, path = index_and_path
        suffix = f"part{index + 1:02d}_{path.stem}"
        return generate_once(args, prompt_file=str(path), name_suffix=suffix)

    if args.dry_run:
        for index, path in enumerate(prompt_files):
            results[index] = run((index, path))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
            future_map = {executor.submit(run, item): item[0] for item in enumerate(prompt_files)}
            for future in concurrent.futures.as_completed(future_map):
                index = future_map[future]
                results[index] = future.result()
    completed = [item for item in results if item is not None]
    batch_summary = {
        "jobs": jobs,
        "count": len(completed),
        "audio_paths": [item.get("audio_path") for item in completed if item.get("audio_path")],
        "results": completed,
    }
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{args.name or 'seed_audio_batch'}.batch.json"
    summary_path.write_text(json.dumps(batch_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    batch_summary["summary_path"] = str(summary_path)
    print(json.dumps(batch_summary, ensure_ascii=False, indent=2))


def parse_voice_rows(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    current_scene = ""
    for line in text.splitlines():
        if "|" not in line or "voice_type" in line or "---" in line:
            continue
        cleaned = re.sub(r"<[^>]+>", "", line).replace("\\", "")
        cells = [c.strip() for c in cleaned.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        voice_type = next((c for c in cells if re.search(r"(bigtts|_tob)\b", c)), "")
        if not voice_type:
            continue
        scene = cells[0] if cells[0] and cells[0] != "^^" else current_scene
        if scene:
            current_scene = scene
        name = cells[1] if len(cells) > 1 else ""
        language = cells[3] if len(cells) > 3 else ""
        ability = cells[4] if len(cells) > 4 else ""
        tags = cells[5] if len(cells) > 5 else ""
        rows.append({
            "scene": scene,
            "name": name,
            "voice_type": voice_type,
            "language": language,
            "ability": ability,
            "tags": tags,
        })
    return rows


def command_voices(args: argparse.Namespace) -> None:
    if not VOICE_LIST.exists():
        raise SystemExit(f"Voice list not found: {VOICE_LIST}")
    rows = parse_voice_rows(VOICE_LIST.read_text(encoding="utf-8-sig"))
    query = (args.query or "").lower()
    if query:
        rows = [r for r in rows if query in json.dumps(r, ensure_ascii=False).lower()]
    if args.scene:
        rows = [r for r in rows if args.scene in r["scene"]]
    if args.json:
        print(json.dumps(rows[: args.limit], ensure_ascii=False, indent=2))
        return
    for row in rows[: args.limit]:
        print(f"{row['name']}\t{row['voice_type']}\t{row['scene']}\t{row['language']}\t{row['tags']}")


def find_ffmpeg(explicit: str = "") -> str:
    candidates = [
        explicit,
        *winget_ffmpeg_candidates("ffmpeg"),
        shutil.which("ffmpeg") or "",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise SystemExit("ffmpeg not found. Pass --ffmpeg.")


def command_mux(args: argparse.Namespace) -> None:
    ffmpeg = find_ffmpeg(args.ffmpeg)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        args.video,
        "-i",
        args.audio,
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
    ]
    if args.audio_volume != 1.0:
        cmd.extend(["-filter:a", f"volume={args.audio_volume}"])
    cmd.append(str(output))
    subprocess.run(cmd, check=True)
    print(str(output))


def common_generate_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--prompt", help="Text prompt or text to synthesize.")
    parser.add_argument("--prompt-file", help="UTF-8 text file containing the prompt.")
    parser.add_argument("--speaker", action="append", help="Voice type ID from the official voice list. Repeat when multiple speaker references are needed.")
    parser.add_argument("--strict-tts", action="store_true", help="Wrap prompt to force exact read-aloud without creative continuation.")
    parser.add_argument("--audio", action="append", help="Reference audio file path. Repeat up to three times.")
    parser.add_argument("--audio-url", action="append", help="Reference audio URL. Repeat up to three times.")
    parser.add_argument("--image", help="Reference image file path. Cannot mix with audio/speaker references.")
    parser.add_argument("--image-url", help="Reference image URL. Cannot mix with audio/speaker references.")
    parser.add_argument("--model", default=env("SEED_AUDIO_MODEL", DEFAULT_MODEL, "SPEECH_MODEL"))
    parser.add_argument("--format", choices=["wav", "mp3", "pcm", "ogg_opus"], default=env("SEED_AUDIO_FORMAT", "mp3"))
    parser.add_argument("--sample-rate", type=int, choices=[8000, 16000, 24000, 32000, 44100, 48000], default=int(env("SEED_AUDIO_SAMPLE_RATE", "24000")))
    parser.add_argument("--speech-rate", type=int, default=int(env("SEED_AUDIO_SPEECH_RATE", "0")))
    parser.add_argument("--loudness-rate", type=int, default=int(env("SEED_AUDIO_LOUDNESS_RATE", "0")))
    parser.add_argument("--pitch-rate", type=int, default=int(env("SEED_AUDIO_PITCH_RATE", "0")))
    parser.add_argument("--enable-subtitle", action="store_true")
    parser.add_argument("--aigc-watermark", action="store_true")
    parser.add_argument("--metadata", action="store_true", help="Enable implicit AIGC metadata watermark.")
    parser.add_argument("--content-producer", default="")
    parser.add_argument("--produce-id", default="")
    parser.add_argument("--content-propagator", default="")
    parser.add_argument("--propagate-id", default="")
    parser.add_argument("--name", default="")
    parser.add_argument("--output-dir", default=str(Path.cwd() / "outputs"))
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--show-config", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate audio with Volcano Seed Audio.")
    sub = parser.add_subparsers(dest="command", required=True)

    generate = sub.add_parser("generate", help="Create speech, sound effects, ambience, or audio from references.")
    common_generate_options(generate)
    generate.set_defaults(func=command_generate)

    batch_generate = sub.add_parser("batch-generate", help="Create multiple Seed Audio segments in parallel from prompt files.")
    common_generate_options(batch_generate)
    batch_generate.add_argument("--prompt-files", action="append", help="Prompt file path. Repeat in desired output order.")
    batch_generate.add_argument("--prompt-list", help="Text file containing one prompt-file path per line.")
    batch_generate.add_argument("--prompt-dir", help="Directory of prompt files to generate.")
    batch_generate.add_argument("--prompt-glob", default="*.txt", help="Glob used with --prompt-dir.")
    batch_generate.add_argument("--jobs", type=int, default=int(env("SEED_AUDIO_BATCH_JOBS", "3")), help="Parallel generation jobs.")
    batch_generate.set_defaults(func=command_batch_generate)

    voices = sub.add_parser("voices", help="Search the bundled official voice list.")
    voices.add_argument("--query", default="", help="Search text across name, voice_type, language, scene, and tags.")
    voices.add_argument("--scene", default="", help="Filter by scene text, e.g. 视频配音 or 角色扮演.")
    voices.add_argument("--limit", type=int, default=40)
    voices.add_argument("--json", action="store_true")
    voices.set_defaults(func=command_voices)

    mux = sub.add_parser("mux", help="Mux generated audio into a video.")
    mux.add_argument("--video", required=True)
    mux.add_argument("--audio", required=True)
    mux.add_argument("--output", required=True)
    mux.add_argument("--audio-volume", type=float, default=1.0)
    mux.add_argument("--ffmpeg", default="")
    mux.set_defaults(func=command_mux)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
