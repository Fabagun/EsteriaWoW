# mod-esteria-skyriding

Server half of Esteria's retail-style Skyriding. The client half and all design docs live in the wowdecomp repo
(`Extensions/Skyriding`, `docs/SKYRIDING_*.md`; status in `docs/SKYRIDING_CHECKPOINT.md`).

- Core patch: opcodes `CMSG_ESTERIA_SKYRIDE` 0x527 / `SMSG_ESTERIA_SKYRIDE` 0x528 (`Opcodes.h/.cpp`), the shared
  headers in `src/server/shared/Skyriding/` (verbatim copies of the client's), and a one-line exemption in
  `mod-anticheat` for active riders.
- Setup: run `data/sql/db-world/esteria_skyriding_mounts.sql` on the world database (the Esteria image starts with
  database updates off) and copy `conf/mod_esteria_skyriding.conf.dist` into the server's module config folder.
- Off switch: `Skyriding.Enable = 0`.
