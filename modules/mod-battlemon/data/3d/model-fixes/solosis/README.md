# Solosis body/shell correction

Normal and shiny Solosis retain all 455 vertices, 678 faces, animation tracks, UVs and compressed textures.
The opaque body (486 faces) and translucent shell (192 faces) now have separate draw sections.
The body uses alpha-key with depth writes; the shell uses source alpha blending without depth writes.
Both independent layers use material layer 0, so they cannot be interpreted as combined texture stages.

`before/` contains exact prior M2/SKIN backups; `receipt.json` records every before/after hash.
`tools/fix_solosis_materials.py` reproduces the correction from those exact files and rejects other inputs.
Twelve decoded-pose renders were reviewed. This does not certify a live WoW rendering test.
Fully exit and restart WoW after copying the corrected client files. Do not substitute old raw textures.

The material interpretation follows the WotLK renderer implementation:
https://github.com/wowdev/noggit3 (Model render passes and render flags).
