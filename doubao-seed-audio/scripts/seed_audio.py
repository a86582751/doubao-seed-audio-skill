#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
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


def build_references(args: argparse.Namespace) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    if args.speaker:
        refs.append({"speaker": args.speaker})
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
    if len([r for r in refs if "audio_url" in r or "audio_data" in r]) > 3:
        raise SystemExit("At most three reference audio files/URLs are supported.")
    if len(image_like) > 1:
        raise SystemExit("At most one reference image is supported.")
    return refs


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    prompt = read_prompt(args)
    if not prompt:
        raise SystemExit("A prompt is required. Use --prompt or --prompt-file.")
    if getattr(args, "strict_tts", False):
        prompt = f"请严格只朗读以下文本，不要续写、不要改写、不要添加任何内容：\n“{prompt}”"
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


def command_generate(args: argparse.Namespace) -> None:
    api_key = env("SEED_AUDIO_API_KEY", "", "SPEECH_API_KEY", "X_API_KEY")
    base_url = env("SEED_AUDIO_BASE_URL", DEFAULT_BASE_URL, "SPEECH_BASE_URL")
    path = env("SEED_AUDIO_CREATE_PATH", DEFAULT_CREATE_PATH, "SPEECH_CREATE_PATH")
    payload = build_payload(args)
    if args.show_config:
        print(json.dumps({
            "api_key": mask_secret(api_key),
            "base_url": base_url,
            "path": path,
            "model": args.model,
        }, ensure_ascii=False, indent=2))
    if args.dry_run:
        print(json.dumps(scrub_payload(payload), ensure_ascii=False, indent=2))
        return
    if not api_key:
        raise SystemExit("Missing SEED_AUDIO_API_KEY or SPEECH_API_KEY.")
    result, meta = call_create(payload, api_key, base_url, path, args.timeout)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", args.name or "seed_audio").strip("_") or "seed_audio"
    name = f"{stamp}_{safe}"
    output_dir = Path(args.output_dir)
    audio_path = save_audio(result, output_dir, name, args.format, args.timeout)
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
    }
    summary_path = output_dir / f"{name}.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


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
        raise SystemExit(
            "Voice list not bundled in this public package. "
            "Consult the current Volcano OpenSpeech console/docs for voice IDs, "
            "or add references/official-voice-list.md locally."
        )
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
    parser.add_argument("--speaker", help="Voice type ID from the official voice list.")
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
