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

Generation modes:

- Pure text generation: omit `references`; generate from `text_prompt`.
- Reference audio generation: include up to three audio references. A `speaker` voice ID is also an audio reference. Local/inline audio references correspond to `@音频1`, `@音频2`, etc. by order.
- Reference image generation: include exactly one image reference and synthesize audio according to `text_prompt`.

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
- For finished mixed scenes, write an audio-director cue sheet: persistent environment, music bed, chronological sound cues, speaker labels with age/accent/timbre/emotion, exact quoted dialogue, interleaved effects, closing cue, and final constraints.
- Put sound effects where they should happen rather than collecting them at the end. Example pattern: `背景持续有...，音乐以...铺底。先是...。男子1（中年男性，台湾口音，嗓音低沉）用严肃语气说道："..."。对话中夹杂...。随后...。人声清楚靠前，不要让噪声盖住台词。`
- For multi-character dialogue, keep labels stable (`男子1`, `女子1`, `旁白`, `远端通话者`) and give each role distinct age, accent, timbre, and emotional state.
- For exact voiceover, use short prompts and explicit wording: "只朗读：...。读完立即停止，不要添加其它内容。" Verify returned subtitles/audio because `seed-audio-1.0` can creatively continue medium-length speaker prompts.
- For reference audio, explicitly cite `@音频1`, `@音频2`, or `@音频3`.
- For video post-production, generate one coherent mixed track when the scene is short and the prompt is not dense; generate ambience, dialogue, Foley, and music-like beds as separate stems when timing, edits, or loudness need control.

Director prompt skeleton:

```text
背景持续有[环境底噪]，音乐以[主奏/铺底乐器]为主，加入[辅助乐器/打击乐]，整体情绪[情绪]。先是[开场声效]，随后[动作/转场]。[角色1]（[年龄/性别/口音/音色/气质]）用[情绪]语气说道："[台词]"。对话中夹杂[声效]。[角色2]（[年龄/性别/口音/音色/气质]）用[情绪]语气说道："[台词]"。随后出现[结尾声效/环境变化]。人声清楚靠前，不要让噪声盖住台词，不要添加额外旁白。
```
