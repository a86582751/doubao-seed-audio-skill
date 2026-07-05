# Doubao Seed Audio Skill for Codex

A Codex skill for generating, downloading, subtitling, and muxing audio with Volcano OpenSpeech Seed Audio / `seed-audio-1.0`.

Use it as the audio post-production companion for Seedance videos: create ambience, Foley, voiceover, dialogue, dubbing, subtitles/timestamps, and coherent final soundtracks for multi-segment AI videos.

Keywords: Codex skill, Doubao Seed Audio, Volcano OpenSpeech, AI audio generation, text-to-speech, voiceover, dialogue, ambience, Foley, dubbing, subtitles, Seedance companion.

## What It Does

- Generate speech, voiceover, dialogue, ambience, sound effects, and music-like beds.
- Use speaker IDs, reference audio, or a reference image when supported.
- Generate subtitles/timestamps when requested.
- Mux generated audio into a video with FFmpeg.
- Run dry-run configuration checks with masked API keys.

## Repository Layout

```text
doubao-seed-audio/
  SKILL.md
  agents/openai.yaml
  references/api-quickref.md
  references/official-voice-list.md
  scripts/seed_audio.py
```

## Install In Codex

```bash
mkdir -p ~/.codex/skills
cp -R doubao-seed-audio ~/.codex/skills/
```

Restart Codex after installing a new skill.

## Configuration

The CLI reads process environment variables first, then falls back to:

```text
~/.codex/speech.env
~/.codex/seedance.env
```

Use a Volcano Speech/OpenSpeech API key:

```text
https://console.volcengine.com/speech/new/setting/apikeys?projectName=default
```

Supported variables:

```text
SEED_AUDIO_API_KEY=your_volcano_speech_api_key
SPEECH_API_KEY=your_volcano_speech_api_key
SEED_AUDIO_BASE_URL=https://openspeech.bytedance.com
SEED_AUDIO_MODEL=seed-audio-1.0
```

Do not use the Volcano Ark `SEEDANCE_API_KEY` as the Seed Audio key. Ark keys are for Seedance and Seedream.

## Quick Start

Generate ambience:

```bash
python doubao-seed-audio/scripts/seed_audio.py generate \
  --prompt "Create 10 seconds of a quiet winter city street: footsteps, distant voices, light wind, no music, no narration." \
  --format mp3 \
  --output-dir outputs
```

Generate voiceover:

```bash
python doubao-seed-audio/scripts/seed_audio.py generate \
  --prompt "Only read this sentence: The city wakes under the first snow." \
  --speaker zh_female_wenrouxiaoya_uranus_bigtts \
  --enable-subtitle \
  --format mp3 \
  --output-dir outputs
```

Mux audio into video:

```bash
python doubao-seed-audio/scripts/seed_audio.py mux \
  --video outputs/silent.mp4 \
  --audio outputs/audio.mp3 \
  --output outputs/with_audio.mp4
```

Dry-run configuration:

```bash
python doubao-seed-audio/scripts/seed_audio.py generate \
  --prompt "test" --dry-run --show-config
```

## Voice List

This public package includes a compact starter voice list at:

```text
doubao-seed-audio/references/official-voice-list.md
```

Search it with:

```bash
python doubao-seed-audio/scripts/seed_audio.py voices --query 女声 --limit 20
```

For the latest full official voice list, see:

```text
https://www.volcengine.com/docs/6561/1257544?lang=zh
```

Pass the selected ID with `--speaker`. Prefer `uranus_bigtts` or `ICL_uranus..._tob` voice IDs with `seed-audio-1.0`.

## Privacy And Safety

This public package does not include API keys, private env files, generated audio, local output folders, or machine-specific configuration.

## License

MIT. See [LICENSE](LICENSE).
