---
name: doubao-seed-audio
description: Generate, download, subtitle, and mux audio with Volcano OpenSpeech Seed Audio / seed-audio-1.0. Use when Codex needs sound effects, ambience, voiceover, dialogue, audiobooks, dubbing, game audio, image-guided audio, reference-audio-guided audio, speaker-based TTS, subtitle timestamps, or coherent final audio for Seedance videos.
---

# Doubao Seed Audio

Use this skill for Volcano OpenSpeech `seed-audio-1.0` non-streaming audio generation. Treat it as an audio post-production tool for AI video: create ambience, Foley, dialogue, voiceover, dubbing, subtitles/timestamps, and coherent final soundtracks.

## Tool

Run the bundled CLI:

```powershell
python doubao-seed-audio/scripts/seed_audio.py --help
```

## Configuration

The CLI reads process environment variables first, then falls back to `~/.codex/speech.env`, then `~/.codex/seedance.env` only for audio-specific variable names.

Supported variables:

- `SEED_AUDIO_API_KEY`, fallback `SPEECH_API_KEY`
- `SEED_AUDIO_BASE_URL`, default `https://openspeech.bytedance.com`
- `SEED_AUDIO_CREATE_PATH`, default `/api/v3/tts/create`
- `SEED_AUDIO_MODEL`, default `seed-audio-1.0`
- `SEED_AUDIO_FORMAT`, default `mp3`
- `SEED_AUDIO_SAMPLE_RATE`, default `24000`
- `SEED_AUDIO_SPEECH_RATE`, default `0`
- `SEED_AUDIO_LOUDNESS_RATE`, default `0`
- `SEED_AUDIO_PITCH_RATE`, default `0`

Use a Volcano Speech/OpenSpeech API key:

```text
https://console.volcengine.com/speech/new/setting/apikeys?projectName=default
```

Do not use the Ark `SEEDANCE_API_KEY` as the Seed Audio key. Seedance and Seedream use Ark keys.

Never print full API keys. Use `--show-config --dry-run`, which masks secrets.

## Common Commands

Generate ambience:

```powershell
python doubao-seed-audio/scripts/seed_audio.py generate --prompt "Create 10 seconds of quiet winter city ambience: footsteps, distant voices, light wind, no music, no narration" --format mp3 --output-dir ./outputs
```

Generate voiceover with a speaker ID:

```powershell
python doubao-seed-audio/scripts/seed_audio.py generate --prompt "Only read: The city wakes under the first snow." --speaker zh_female_wenrouxiaoya_uranus_bigtts --enable-subtitle --format mp3
```

Search the bundled starter voice list:

```powershell
python doubao-seed-audio/scripts/seed_audio.py voices --query 女声 --limit 20
```

Use reference audio:

```powershell
python doubao-seed-audio/scripts/seed_audio.py generate --prompt "Reference @audio1's voice and say: Welcome to the city." --audio ./voice_ref.mp3
```

Mux generated audio into a video:

```powershell
python doubao-seed-audio/scripts/seed_audio.py mux --video ./silent.mp4 --audio ./audio.mp3 --output ./with_audio.mp4
```

Dry-run:

```powershell
python doubao-seed-audio/scripts/seed_audio.py generate --prompt "test" --dry-run --show-config
```

## Workflow

1. For single Seedance clips, native Seedance audio may be enough.
2. For multi-segment videos, generate one coherent final soundtrack after the visual edit.
3. Use separate prompts or stems when dialogue, ambience, and effects need independent timing.
4. Use `mux` or FFmpeg to attach the final audio to the video.

## Voice List

Use `references/official-voice-list.md` as a compact starter list. For the latest full official list, use `https://www.volcengine.com/docs/6561/1257544?lang=zh`, then pass a selected ID with `--speaker`. Prefer `uranus_bigtts` or `ICL_uranus..._tob` voice IDs with `seed-audio-1.0`.

## References

- Read `references/api-quickref.md` for payload fields, examples, response handling, and prompt guidance.
- Read `references/official-voice-list.md` only when selecting a bundled starter speaker ID.
