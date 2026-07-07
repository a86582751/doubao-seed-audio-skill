---
name: doubao-seed-audio
description: Generate, download, subtitle, and mux audio with Volcano OpenSpeech Seed Audio / seed-audio-1.0. Use when Codex needs to create sound effects, ambience, voiceover, dialogue, audiobooks, dubbing, game audio, image-guided audio, reference-audio-guided audio, speaker-based TTS, subtitle timestamps, or add generated audio to Seedance videos.
---

# Doubao Seed Audio

Use this skill for Volcano OpenSpeech `seed-audio-1.0` non-streaming audio generation. The interface can create speech, voiceover, dialogue, environmental sound, sound effects, and reference-guided audio up to 120 seconds per request. For longer programs, generate natural segments and assemble them with FFmpeg instead of compressing the script into one overstuffed prompt. When segments are independent, launch them in parallel with `batch-generate` to save wall-clock time.

## Model Positioning

Doubao-音频生成-1.0 is a next-generation audio generation engine for sound creators. Treat it as an "audio director" model rather than only a single-sentence TTS tool: one prompt can describe dialogue, sound effects, music-like beds, non-verbal expressions, mood, pacing, and transitions.

Core strengths:

- Film-style mixed audio: generate multi-role dialogue, sound effects, music-like atmosphere, laughter, sighs, pauses, accents, timing, and transitions in one request.
- Long-form voice consistency: connect text generation with reference audio to keep character voices more stable across audiobooks, podcasts, and serial audio.
- Zero-shot multimodal creation: generate target audio from text descriptions, reference audio, or image references without training samples.
- Multimodal voice personality understanding: describe a voice such as "慵懒御姐", upload a reference audio, or provide an image so the model infers a matching vocal temperament.

Use cases include radio drama, audiobooks, podcasts, long-form serials, brand audio, advertising, video dubbing, game audio, and video post-production.

## Audio Director Prompting

This is the canonical prompt guide for Seed Audio. Downstream skills such as `doubao-seedance-video` and `radio-podcast` should link here instead of duplicating the full grammar.

For finished audio scenes, write prompts like an audio-director cue sheet rather than a loose summary. This is the preferred style for radio drama, podcasts, fictional broadcasts, product ads, game scenes, and final Seedance soundtracks.

Use this order:

1. Persistent environment: room tone, crowd, traffic, weather, machinery, phone line, radio bed, tunnel, forest, or other continuous acoustic layer.
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

## Long Audio Segmentation

Seed Audio is excellent at one-prompt finished scenes, but the per-request audio limit is 120 seconds. For multi-minute podcasts, fictional broadcasts, audio dramas, explainers, or long Seedance soundtracks, prefer a segmented workflow:

1. Split the approved script at natural audio breaks: station IDs, EAS tones, phone inserts, field reports, scene changes, music bridges, ambience beats, signal loss/reconnect, or cliffhangers.
2. Write one Audio Director prompt per segment. Keep the same speaker ID/reference and repeat a brief continuity note in each part.
3. End segments with stitch-friendly tails such as static, room tone, channel scan, phone dropout, music bed, or fade. Start the next segment with a matching head.
4. Generate independent parts in parallel with `batch-generate` when possible. Use conservative bounded parallelism such as `--jobs 2` to `--jobs 4` unless the user explicitly wants faster, higher-concurrency generation.
5. Use FFmpeg concat for hard cuts at silence/static, or short `acrossfade` only over ambience/music/static. Avoid crossfading spoken words.
6. Run a final listen or multimodal feedback pass on the assembled output.

Use a single prompt when the target is a short draft, trailer, micro-scene, or a complete piece under roughly two minutes. Use segmentation when the writing would become rushed or thin just to fit one request.

## Tool

Run the bundled CLI:

```powershell
python C:\Users\isund\.codex\skills\doubao-seed-audio\scripts\seed_audio.py --help
```

Prefer the bundled Python runtime when available:

```powershell
C:\Users\isund\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe C:\Users\isund\.codex\skills\doubao-seed-audio\scripts\seed_audio.py --help
```

## Configuration

The CLI reads process environment variables first, then falls back to `C:\Users\isund\.codex\speech.env`, then `C:\Users\isund\.codex\seedance.env` only for audio-specific variable names. Keep the Speech/OpenSpeech key separate from the Ark key whenever possible.

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

Use the Volcano Speech/OpenSpeech key for Seed Audio. Speech key source:

```text
https://console.volcengine.com/speech/new/setting/apikeys?projectName=default
```

Do not use the Ark `SEEDANCE_API_KEY` as the Seed Audio key. Seedance and Seedream use an Ark key from:

```text
https://ark.volcengine.com/region:cn-beijing/apiKey?apikey=%7B%7D
```

Never print full API keys. Use `--show-config --dry-run`, which masks secrets.

## Common Commands

Generate text-described sound effects or ambience:

```powershell
python C:\Users\isund\.codex\skills\doubao-seed-audio\scripts\seed_audio.py generate --prompt "生成一段8秒北京胡同白天环境音：远处人声、自行车铃、脚步声、微风，无音乐无旁白" --format mp3 --sample-rate 24000 --output-dir C:\Users\isund\Documents\Codex\2026-07-05\ban\outputs
```

Generate a one-prompt mixed audio scene:

```powershell
python C:\Users\isund\.codex\skills\doubao-seed-audio\scripts\seed_audio.py generate --prompt "背景持续有低频发电机声和轻微电台底噪，音乐以极弱的合成器pad铺底，整体情绪紧张克制。先是一声短促电台静电。播音员（中老年男性，标准普通话，低沉厚实，字正腔圆，像资深电台主持）用沉稳严肃的语气说道：'这里是第七应急频段。请所有仍在收听的居民，立即远离地下停车区。' 对话中夹杂一次信号干扰和纸张翻动声。最后远处传来沉闷撞击声，播音员压低声音说道：'不要开门。' 随后信号突然切断。人声清楚靠前，不要让噪声盖住台词。" --speaker ICL_uranus_zh_male_cixingnansang_tob --format mp3 --sample-rate 24000 --output-dir C:\Users\isund\Documents\Codex\2026-07-05\ban\outputs
```

Generate multiple long-audio segments in parallel:

```powershell
python C:\Users\isund\.codex\skills\doubao-seed-audio\scripts\seed_audio.py batch-generate --prompt-dir C:\path\episode_prompts --prompt-glob "part*.txt" --speaker ICL_uranus_zh_male_cixingnansang_tob --format mp3 --sample-rate 24000 --speech-rate -8 --jobs 3 --output-dir C:\path\episode_audio --show-config
```

Use repeated `--prompt-files` or `--prompt-list` when exact segment order matters and filenames do not sort naturally. The command returns a batch JSON with ordered `audio_paths` for later FFmpeg assembly.

Generate voiceover with a speaker ID:

```powershell
python C:\Users\isund\.codex\skills\doubao-seed-audio\scripts\seed_audio.py generate --prompt "只朗读：今天的故事，从北京一条安静的胡同开始。读完立即停止，不要添加其它内容。" --speaker zh_female_wenrouxiaoya_uranus_bigtts --enable-subtitle --format mp3
```

Use reference audio. Mention `@音频1`, `@音频2`, etc. in the prompt when you want the model to imitate or transform references:

```powershell
python C:\Users\isund\.codex\skills\doubao-seed-audio\scripts\seed_audio.py generate --prompt "参考@音频1的音色和语气，说：欢迎来到这条老北京胡同。" --audio C:\path\voice_ref.mp3
```

Use a reference image to generate audio from visual context:

```powershell
python C:\Users\isund\.codex\skills\doubao-seed-audio\scripts\seed_audio.py generate --prompt "根据图片氛围生成10秒自然环境声，无音乐无旁白" --image C:\path\scene.png
```

Search the bundled official voice list:

```powershell
python C:\Users\isund\.codex\skills\doubao-seed-audio\scripts\seed_audio.py voices --query 女友 --limit 20
python C:\Users\isund\.codex\skills\doubao-seed-audio\scripts\seed_audio.py voices --scene 视频配音 --limit 30
```

Mux generated audio into a video:

```powershell
python C:\Users\isund\.codex\skills\doubao-seed-audio\scripts\seed_audio.py mux --video C:\path\silent.mp4 --audio C:\path\audio.mp3 --output C:\path\with_audio.mp4
```

Dry-run a payload without spending quota:

```powershell
python C:\Users\isund\.codex\skills\doubao-seed-audio\scripts\seed_audio.py generate --prompt "测试" --speaker zh_female_wenrouxiaoya_moon_bigtts --dry-run --show-config
```

## Workflow

1. Choose the mode:
   - Pure text generation: pass only `--prompt` / `--prompt-file`; the payload omits `references`.
   - Reference audio generation: pass `--speaker`, `--audio`, or `--audio-url`. Speaker IDs count as audio references. Use `@音频1`, `@音频2`, etc. in prompt text for audio files/URLs according to reference order.
   - Reference image generation: pass `--image` or `--image-url`; the prompt describes the audio to synthesize from the image.
2. Search `references/official-voice-list.md` with `voices` when the user asks for a role, accent, gender, scene, or emotion. Prefer `uranus_bigtts` or `ICL_uranus..._tob` voice IDs for this new API; older `moon_bigtts` / `mars_bigtts` IDs may appear in the official list but can be rejected by `seed-audio-1.0`.
3. For one-prompt mixed scenes, use the Audio Director Prompting structure above and keep the full prompt within the provider limit. For longer works, create a segment map and one prompt per segment, run `batch-generate` with bounded parallelism, then assemble with FFmpeg.
4. Use `--enable-subtitle` when timing is needed for subtitles or lip-sync planning.
5. For exact dialogue, keep each request short, use explicit "只朗读...读完立即停止" wording or `--strict-tts`, and verify the returned subtitle/audio. `seed-audio-1.0` can creatively continue medium-length speaker prompts even with strict wording.
6. Keep generated outputs under the active thread `outputs` directory when possible.
7. Use `mux` to attach audio to Seedance videos; use Seedance `--no-generate-audio` for predictable post-production audio.

## Constraints

- Model: `seed-audio-1.0`.
- Max `text_prompt`: 2048 characters.
- Max generated audio: 120 seconds.
- Reference audio: up to 3 items total, including speaker IDs; local files are checked for 30 seconds and 10 MB; formats `wav`, `mp3`, `pcm`, `ogg_opus`.
- Reference image: exactly one at most, up to 10 MB; formats `jpeg`, `png`, `webp`.
- Do not mix image references with speaker/audio references.
- For each reference entry, use only one of `speaker`, `audio_data`, or `audio_url`; for image use one of `image_data` or `image_url`.
- Output format: `wav`, `mp3`, `pcm`, `ogg_opus`.
- Output sample rate: `8000`, `16000`, `24000`, `32000`, `44100`, `48000`.
- `speech_rate`: `-50` to `100`; `100` is 2.0x, `-50` is 0.5x.
- `loudness_rate`: `-50` to `100`; `100` is 2.0x, `-50` is 0.5x.
- `pitch_rate`: `-12` to `12`.
- Subtitle output is best-effort; very short clips may omit `subtitle` even when requested.

## References

- Read `references/api-quickref.md` for payload fields, examples, and response handling.
- Search `references/official-voice-list.md` for the full pasted official voice table.
