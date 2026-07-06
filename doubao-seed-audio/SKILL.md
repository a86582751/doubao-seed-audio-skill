---
name: doubao-seed-audio
description: Generate, download, subtitle, and mux audio with Volcano OpenSpeech Seed Audio / seed-audio-1.0. Use when Codex needs sound effects, ambience, voiceover, dialogue, audiobooks, dubbing, game audio, image-guided audio, reference-audio-guided audio, speaker-based TTS, subtitle timestamps, or coherent final audio for Seedance videos.
---

# Doubao Seed Audio

Use this skill for Volcano OpenSpeech `seed-audio-1.0` non-streaming audio generation. Treat it as an audio director and post-production tool for AI video: create ambience, Foley, dialogue, voiceover, dubbing, subtitles/timestamps, mixed audio scenes, and coherent final soundtracks.

## Audio Director Prompting

For finished audio scenes, write prompts like an audio-director cue sheet rather than a loose summary. This is the preferred style for radio drama, podcasts, fictional broadcasts, product ads, game scenes, and final Seedance soundtracks.

Use this order:

1. Persistent environment: room tone, crowd, traffic, weather, machinery, phone line, radio bed, tunnel, forest, or another continuous acoustic layer.
2. Music bed: main instrument, supporting instruments, mood, intensity, and whether it should stay weak under speech.
3. Chronological cues: opening effects and action sounds in the order they should occur.
4. Speaker labels: role, age, gender, accent, timbre, vocal texture, and emotional performance.
5. Exact dialogue: quote the lines to speak.
6. Interleaved effects: place sound effects between dialogue lines where timing matters.
7. Closing cue and constraints: signal cut, footsteps, impact, fade, "voice forward", "no noise over words", "no extra narration".

Example:

```text
背景持续有雨声、手持对讲机底噪和远处警笛，音乐以极弱的低频合成器pad铺底，整体情绪紧张悬疑。先是一声频道扫描，随后接入远端通话。男子1（中年男性，标准普通话，嗓音低沉，沉稳但警惕）压低声音说道："三号巡查组，请报告你们的位置。" 现场记者（青年女性，普通话，气息急促，努力保持专业）回答："我们在西桥下方，路面有大量遗弃车辆。" 对话中夹杂两次短促电台断续和远处金属撞击声。男子1停顿半拍后说道："不要继续向桥面移动。重复，不要继续向桥面移动。" 随后出现一声尖锐电流干扰，通话中断。人声清楚靠前，不要让噪声盖住台词。
```

For exact narration or TTS tests, do not use the full director grammar. Use `--strict-tts` or explicit wording such as `只朗读：...读完立即停止，不要添加其它内容。`

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

Generate a one-prompt mixed audio scene:

```powershell
python doubao-seed-audio/scripts/seed_audio.py generate --prompt "背景持续有低频发电机声和轻微电台底噪，音乐以极弱的合成器pad铺底，整体情绪紧张克制。先是一声短促电台静电。播音员（中老年男性，标准普通话，低沉厚实，字正腔圆，像资深电台主持）用沉稳严肃的语气说道：'这里是第七应急频段。请所有仍在收听的居民，立即远离地下停车区。' 对话中夹杂一次信号干扰和纸张翻动声。最后远处传来沉闷撞击声，播音员压低声音说道：'不要开门。' 随后信号突然切断。人声清楚靠前，不要让噪声盖住台词。" --speaker ICL_uranus_zh_male_cixingnansang_tob --format mp3 --sample-rate 24000 --output-dir ./outputs
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
3. For one-prompt mixed scenes, use the Audio Director Prompting structure above and keep the prompt within the provider limit.
4. Use separate prompts or stems when dialogue, ambience, and effects need independent timing.
5. For exact dialogue or narration, keep each request short, use explicit "只朗读...读完立即停止" wording or `--strict-tts`, and verify the returned subtitle/audio.
6. Use `mux` or FFmpeg to attach the final audio to the video.

## Voice List

Use `references/official-voice-list.md` as a compact starter list. For the latest full official list, use `https://www.volcengine.com/docs/6561/1257544?lang=zh`, then pass a selected ID with `--speaker`. Prefer `uranus_bigtts` or `ICL_uranus..._tob` voice IDs with `seed-audio-1.0`.

## References

- Read `references/api-quickref.md` for payload fields, examples, response handling, and prompt guidance.
- Read `references/official-voice-list.md` only when selecting a bundled starter speaker ID.
