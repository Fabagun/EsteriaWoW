"""Deploy companion addon and the optional packet-routing hook; preserve existing Battlemon."""
import argparse,hashlib,json,shutil
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OLD="    run(handlers[cmd])"
NEW="""    -- Optional alternate battle presentation; classic handlers remain the default.
    local routed = false
    if type(Battlemon.RouteBattlePacket) == "function" then
        local ok, result = pcall(Battlemon.RouteBattlePacket, cmd, a)
        if ok then
            routed = result and true or false
        else
            Battlemon.Print("Pet battle UI error: " .. tostring(result))
        end
    end
    if not routed then
        run(handlers[cmd])
    end"""
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('addons',type=Path)
    args=parser.parse_args();addons=args.addons.resolve()
    net=addons/'Battlemon/Core/Net.lua'
    if not net.is_file():raise SystemExit('Existing Battlemon addon not found')
    original=net.read_text(encoding='utf-8')
    if NEW not in original and original.count(OLD)!=1:raise SystemExit('Unexpected Net.lua; no files changed')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup=addons.parent/'BattlemonBattles-Backups'/stamp;backup.mkdir(parents=True)
    shutil.copy2(net,backup/'Net.lua')
    target=addons/'BattlemonBattles'
    if target.exists():shutil.copytree(target,backup/'BattlemonBattles')
    receipt=dict(net_before=digest(net),backup=str(backup),files={},previous={})
    if (backup/"BattlemonBattles").exists():
        receipt["previous"]={str(p.relative_to(backup/"BattlemonBattles")):digest(p)
            for p in (backup/"BattlemonBattles").rglob("*") if p.is_file()}
    for src in (ROOT/'addon/BattlemonBattles').rglob('*'):
        if not src.is_file():continue
        dst=target/src.relative_to(ROOT/'addon/BattlemonBattles');dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)
        if digest(src)!=digest(dst):raise RuntimeError('Copy hash mismatch')
        receipt['files'][str(dst.relative_to(addons))]=digest(dst)
    if NEW not in original:net.write_text(original.replace(OLD,NEW),encoding='utf-8',newline='\n')
    receipt['net_after']=digest(net)
    (backup/'receipt.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
