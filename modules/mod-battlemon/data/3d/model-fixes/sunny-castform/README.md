# Sunny Castform material correction

The original draw batch mixed 654 opaque faces and 728 source-alpha faces with depth writes enabled.
The corrected model draws the opaque faces first and the translucent faces without depth writes.
Normal and shiny retain their exact textures, vertices, UVs, weights, bones and animation tracks.
All 1382 oriented triangles are preserved, reordered only by material pass.

`before/` and `receipt.json` contain exact original hashes and the reviewed per-face classification.
`tools/fix_sunny_castform_materials.py` reproduces the repair and rejects unknown inputs/classifications.
The material selection uses conservative alpha sampling over every face's UV rectangle including a one-pixel margin.
Offline decoded views cover both palettes, idle/walk and front/back. Live WoW confirmation remains pending.
