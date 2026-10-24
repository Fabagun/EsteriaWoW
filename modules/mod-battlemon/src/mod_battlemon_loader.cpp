/* Unified AzerothCore module entry point. */

void AddSC_battlemon();
void AddSC_battlemon_sidecar();
void AddSC_battlemon_overworld();
void AddSC_battlemon_battles();
void AddSC_battlemon_center();

void Addmod_battlemonScripts()
{
    AddSC_battlemon();
    AddSC_battlemon_center();
    AddSC_battlemon_sidecar();
    AddSC_battlemon_battles();
    AddSC_battlemon_overworld();
}
