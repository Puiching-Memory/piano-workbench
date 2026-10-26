# Public examples

All musical notes here come from the project's original eight-bar synthetic composition. These are not transcriptions of the user's recording.

- `original-eight-bars/`: reproducible source MIDI, MusicXML and pedal-compatible MIDI. The source contains 56 notes, two tempo regions (96 then 84 BPM), and 16 CC64 messages.
- `score/`: one-page PDF/SVG engraved from the original MusicXML, plus a 56-event equivalence check. This engraving example does not run a transcription model.
- `listening/`: a real Salamander SF2 comparison of native CC64 versus note-length sustain approximation. Open `index.html` after downloading the repository; switch versions at the same playback position. See its `ATTRIBUTION.md` for the audio's CC BY 3.0 attribution and exact source.

The two listening examples intentionally use the same piano. They demonstrate sustain compatibility and fair loudness matching, not a before/after FL Studio mix. For actual DAW mixing, follow `docs/fl-studio.md` using your own performance and legally available instrument.
