# Seed Audio API Quick Reference

Endpoint:

```text
POST https://openspeech.bytedance.com/api/v3/tts/create
```

Headers:

```text
X-Api-Key: <speech api key>
X-Api-Request-Id: <uuid optional but recommended>
Content-Type: application/json
```

Core request:

```json
{
  "model": "seed-audio-1.0",
  "text_prompt": "生成一段8秒北京胡同环境音，无音乐无旁白",
  "audio_config": {
    "format": "mp3",
    "sample_rate": 24000,
    "speech_rate": 0,
    "loudness_rate": 0,
    "pitch_rate": 0,
    "enable_subtitle": false
  }
}
```

Speaker TTS:

```json
{
  "model": "seed-audio-1.0",
  "text_prompt": "今天的故事，从一条北京胡同开始。",
  "references": [
    {"speaker": "zh_female_wenrouxiaoya_moon_bigtts"}
  ],
  "audio_config": {"format": "mp3", "sample_rate": 24000, "enable_subtitle": true}
}
```

Reference audio:

```json
{
  "model": "seed-audio-1.0",
  "text_prompt": "参考@音频1的音色，说：欢迎来到这条老北京胡同。",
  "references": [
    {"audio_data": "<base64 wav/mp3/pcm/ogg_opus>"}
  ]
}
```

Reference image:

```json
{
  "model": "seed-audio-1.0",
  "text_prompt": "根据图片氛围生成10秒自然环境声，无音乐无旁白。",
  "references": [
    {"image_data": "<base64 jpeg/png/webp>"}
  ]
}
```

Response fields:

- `code`, `message`: status values. Some successful responses may omit or null them.
- `audio`: base64 audio bytes.
- `url`: expiring audio URL, usually valid for about 2 hours.
- `duration`: processed duration in seconds.
- `original_duration`: model output duration; billing uses this field.
- `subtitle`: present only when `audio_config.enable_subtitle=true`; includes sentence and word timestamps in milliseconds.

Prompt guidance:

- For ambience/effects, specify duration, acoustic sources, distance, density, and exclusions: "no music, no narration, no melody".
- For exact voiceover, use short prompts and explicit wording: "只朗读：...。读完立即停止，不要添加其它内容。" Verify returned subtitles/audio because `seed-audio-1.0` can creatively continue medium-length speaker prompts.
- For reference audio, explicitly cite `@音频1`, `@音频2`, or `@音频3`.
- For video post-production, generate ambience and dialogue as separate files when possible, then mix/mux outside the generation API.
