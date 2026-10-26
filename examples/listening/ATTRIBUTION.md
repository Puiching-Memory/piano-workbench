# Original eight-bar piano audition

This example compares the project's original synthetic performance MIDI under two sustain interpretations:

- `native-cc64`: original MIDI with CC64 forwarded to the SF2 renderer.
- `note-length-approx`: the same note onsets/pitches/velocities, with CC64 approximated by note lengths and same-pitch retrigger clipping.

Both are TinySoundFont renders of **Salamander Grand Piano SF2**, not FL Studio exports. They are matched using constant gain to approximately -23.02 LUFS. This demonstrates the pedal-compatibility path; it is not an example of automatic mixing or an assertion that the approximation is better.

## Instrument attribution

- Original Salamander Grand Piano samples: **Alexander Holm**.
- SF2 adaptation v3+20200602: **Roberto / FreePats**.
- Source: https://freepats.zenvoid.org/Piano/acoustic-grand-piano.html
- License: **Creative Commons Attribution 3.0** — https://creativecommons.org/licenses/by/3.0/
- SoundFont SHA-256: `712d0e681efbe5203a8014e9b3e84168f1908c82f2f6fb13bd2c77d6d72c70b7`.
- The simplified SF2 omits some original SFZ velocity tracking, pedal/hammer noises and key-release string resonance, as described by its author.

The sample audio is offered under CC BY 3.0 with the above credits. The original composition MIDI/MusicXML is separately MIT licensed. No SoundFont samples or source SF2 are distributed in the repository.

Generation: `piano-workbench demo`, then `bake-pedal`, then `render` for the original and compatible MIDI with bank 0/preset 0, followed by `compare`. Rendering records are included; full raw WAVs are not bundled.
