# Doubao Seed Audio Skill for Codex

A Codex skill for generating, downloading, subtitling, and muxing audio with Volcano OpenSpeech Seed Audio / `seed-audio-1.0`.

Use it as the audio post-production companion for Seedance videos: create ambience, Foley, voiceover, dialogue, dubbing, subtitles/timestamps, and coherent final soundtracks for multi-segment AI videos.

Keywords: Codex skill, Doubao Seed Audio, Volcano OpenSpeech, AI audio generation, text-to-speech, voiceover, dialogue, ambience, Foley, dubbing, subtitles, Seedance companion.

## What It Does

- Generate speech, voiceover, dialogue, ambience, sound effects, and music-like beds.
- Write finished mixed audio scenes with audio-director prompts: environment, music, chronological sound cues, speaker traits, exact dialogue, interleaved effects, and final constraints.
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

The CLI supports the three official Seed Audio modes:

- Pure text generation: use only `--prompt` / `--prompt-file`.
- Reference audio generation: use `--speaker`, `--audio`, or `--audio-url`; speaker IDs count as audio references.
- Reference image generation: use `--image` or `--image-url`.

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

Generate a mixed audio scene:

```bash
python doubao-seed-audio/scripts/seed_audio.py generate \
  --prompt "背景持续有雨声、手持对讲机底噪和远处警笛，音乐以极弱的低频合成器pad铺底。先是一声频道扫描。男子1（中年男性，标准普通话，嗓音低沉，沉稳但警惕）压低声音说道：'三号巡查组，请报告你们的位置。' 现场记者（青年女性，气息急促，努力保持专业）回答：'我们在西桥下方，路面有大量遗弃车辆。' 对话中夹杂两次短促电台断续和远处金属撞击声。最后通话中断。人声清楚靠前，不要让噪声盖住台词。" \
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
