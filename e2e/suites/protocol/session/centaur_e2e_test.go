//go:build e2e

package session_test

import (
	"encoding/binary"
	"fmt"
	"math"
	"strings"
	"testing"
	"time"

	"github.com/azerothcore/AzerothGhost/client"
	"github.com/azerothcore/AzerothGhost/e2e/e2eharness"
	"github.com/azerothcore/azerothcore-wotlk/e2e/internal/meta"
	_ "github.com/go-sql-driver/mysql"
)

// The pinned ScenarioOpts creates males with stock appearance values of one. Centaur's constant
// selectors are zero; create both authored sexes over the actual client opcode before normal login.
func centaurFixture(t *testing.T, race, sex uint8) *e2eharness.ScenarioBot {
	t.Helper()
	authDB, charDB := e2eharness.OpenTestDBs(t)
	id := e2eharness.MakeBotIdentsRaceClass("Cntaur", 1, race, e2eharness.ClassWarrior)[0]
	t.Logf("Centaur fixture account=%s race=%d sex=%d", id.Account, race, sex)
	e2eharness.EnsureBotAccounts(t, authDB, []e2eharness.BotIdent{id})
	auth := client.NewAuthClient(id.Account, e2eharness.DefaultPassword)
	realms, err := auth.Authenticate(e2eharness.AuthAddr)
	if err != nil || len(realms) == 0 {
		e2eharness.Preconditionf(t, "Centaur test account authentication: %v", err)
	}
	w := client.NewWorldClient(strings.ToUpper(id.Account), auth.SessionKey(), t.Logf)
	defer w.Close()
	created := make(chan uint8, 1)
	w.OnCharCreateResult = func(data []byte) {
		if len(data) > 0 {
			select {
			case created <- data[0]:
			default:
			}
		}
	}
	if err := w.Connect(realms[0].Address); err != nil {
		e2eharness.Preconditionf(t, "Centaur world connection: %v", err)
	}
	go func() { _ = w.Run() }()
	if err := w.WaitForSessionPhase(client.PhaseAuthed, 20*time.Second); err != nil {
		e2eharness.Preconditionf(t, "Centaur authenticated session: %v", err)
	}
	head, beard := uint8(8), uint8(7)
	if sex == 1 {
		head, beard = 13, 0
	}
	if err := w.CreateCharacter(id.CharName, race, e2eharness.ClassWarrior, sex, sex*15, 0, head, 0, beard, 0); err != nil {
		e2eharness.HarnessFailf(t, "Centaur create opcode: %v", err)
	}
	select {
	case code := <-created:
		if code != 0x2f {
			e2eharness.Assertf(t, "Centaur race=%d sex=%d creation rejected: 0x%02X", race, sex, code)
		}
	case <-time.After(20 * time.Second):
		e2eharness.HarnessFailf(t, "Centaur creation response timed out")
	}
	w.Close()
	session := e2eharness.LoginBots(t, []e2eharness.BotIdent{id})[0]
	bot := &e2eharness.ScenarioBot{Session: session, AuthDB: authDB, CharDB: charDB, Ident: id}
	if race == 74 {
		bot.World.SetCharRace(e2eharness.RaceOrc) // Harness stock language map does not know custom Horde race 74.
	}
	e2eharness.EnableGM(t, bot.World)
	return bot
}

func waitCentaurDisplay(t *testing.T, bot *e2eharness.ScenarioBot, bird bool, sex uint8) {
	t.Helper()
	ticker := time.NewTicker(25 * time.Millisecond)
	defer ticker.Stop()
	deadline := time.NewTimer(8 * time.Second)
	defer deadline.Stop()
	for {
		if obj := bot.World.GetObject(bot.GUID); obj != nil {
			transformed := obj.Value(client.UnitFieldDisplayID) != obj.Value(client.UnitFieldNativeDisplayID)
			if transformed == bird && (bird || uint8(obj.Value(client.UnitFieldBytes0)>>16) == sex) {
				return
			}
		}
		select {
		case <-ticker.C:
		case <-deadline.C:
			e2eharness.Assertf(t, "Centaur display transition timed out: bird=%v", bird)
		}
	}
}

func waitCentaurLegArmor(t *testing.T, viewer *e2eharness.ScenarioBot, guid uint64, hidden bool) {
	t.Helper()
	// PLAYER_FLAGS is UNIT_END + 2 (0x96), public in the matched server/native field contract.
	const playerFlags, hideLegArmor = 0x96, 0x10000000
	ticker := time.NewTicker(25 * time.Millisecond)
	defer ticker.Stop()
	deadline := time.NewTimer(8 * time.Second)
	defer deadline.Stop()
	for {
		if obj := viewer.World.GetObject(guid); obj != nil && (obj.Value(playerFlags)&hideLegArmor != 0) == hidden {
			return
		}
		select {
		case <-ticker.C:
		case <-deadline.C:
			e2eharness.Assertf(t, "Centaur leg armor not replicated: guid=%d hidden=%v", guid, hidden)
		}
	}
}

// Centaur travel must use racial self-running/bird forms, never ordinary mounts, across both factions and sexes.
func TestSession_CentaurCreationAndTravel(t *testing.T) {
	meta.Begin(t, meta.TestMeta{Tags: []string{"protocol", "centaur", "serial"}, Runtime: "med", Category: "protocol/session"})
	for _, race := range []uint8{73, 74} {
		for _, sex := range []uint8{0, 1} {
			t.Run(fmt.Sprintf("race%d-sex%d", race, sex), func(t *testing.T) {
				bot := centaurFixture(t, race, sex)
				bot.TeleportPad(t, e2eharness.PackagePad(t))
				e2eharness.SetLevel(t, bot.World, 80)
				bot.SetSkill(t, 762, 300, 300)
				bot.FlushWorld(t)
				bot.Relog(t) // Login must teach the racials without donor skill-line grants.
				if race == 74 {
					bot.World.SetCharRace(e2eharness.RaceOrc)
				}
				bot.GM(t, ".gm on")
				bot.FlushWorld(t)
				wantDisplay := uint32(60074) + uint32(race-73)*2 + uint32(sex)
				obj := bot.World.GetObject(bot.GUID)
				if obj == nil || obj.Value(client.UnitFieldNativeDisplayID) != wantDisplay {
					e2eharness.Assertf(t, "Centaur native display does not match sex/faction: want=%d", wantDisplay)
				}
				bot.Learn(t, 750) // Plate proficiency; equipment must use the ordinary player item path.
				bot.EquipEntry(t, 16730, 1)
				bot.WaitEquippedSlot(t, 16730, 4, 10*time.Second)
				observer := centaurFixture(t, race, sex^1)
				observer.TeleportPad(t, e2eharness.PackagePad(t))
				observer.GM(t, ".gm off")
				bot.EquipEntry(t, 16732, 1)
				bot.WaitEquippedSlot(t, 16732, 6, 10*time.Second)
				bot.GM(t, ".gm off")
				if _, err := bot.AuthDB.Exec(
					"UPDATE account_access SET gmlevel=0 WHERE id=(SELECT id FROM account WHERE username=?)",
					bot.Ident.Account,
				); err != nil {
					e2eharness.HarnessFailf(t, "set ordinary-player access for native toggle: %v", err)
				}
				bot.Relog(t)
				if race == 74 {
					bot.World.SetCharRace(e2eharness.RaceOrc)
				}
				bot.GM(t, ".centaurlegs off")
				waitCentaurLegArmor(t, bot, bot.GUID, true)
				waitCentaurLegArmor(t, observer, bot.GUID, true)
				bot.Save(t)
				bot.Relog(t)
				if race == 74 {
					bot.World.SetCharRace(e2eharness.RaceOrc)
				}
				waitCentaurLegArmor(t, bot, bot.GUID, true)
				waitCentaurLegArmor(t, observer, bot.GUID, true)
				bot.WaitEquippedSlot(t, 16732, 6, 10*time.Second)
				bot.GM(t, ".centaurlegs on")
				waitCentaurLegArmor(t, bot, bot.GUID, false)
				waitCentaurLegArmor(t, observer, bot.GUID, false)
				if _, err := bot.AuthDB.Exec(
					"UPDATE account_access SET gmlevel=3 WHERE id=(SELECT id FROM account WHERE username=?)",
					bot.Ident.Account,
				); err != nil {
					e2eharness.HarnessFailf(t, "restore fixture setup access: %v", err)
				}
				bot.Relog(t)
				if race == 74 {
					bot.World.SetCharRace(e2eharness.RaceOrc)
				}
				bot.GM(t, ".gm on")
				bot.FlushWorld(t) // Relog reaches LOGIN_VERIFY_WORLD before INITIAL_SPELLS is guaranteed processed.
				for _, spell := range []uint32{111000, 111001, 111002, 111003} {
					if !bot.World.KnowsSpell(spell) {
						e2eharness.Assertf(t, "Centaur racial %d missing after login", spell)
					}
				}
				bot.Learn(t, 458)
				bot.SetSkill(t, 762, 1, 300)
				bot.GM(t, ".gm off")
				bot.FlushWorld(t)
				skillResult, skillErr := bot.TryCast(t, 111000, bot.GUID, 8*time.Second)
				if skillErr != nil || skillResult.Success || skillResult.FailReason != 150 {
					e2eharness.Assertf(t, "Gallop bypassed riding training: result=%+v err=%v", skillResult, skillErr)
				}
				bot.GM(t, ".gm on")
				bot.SetSkill(t, 762, 300, 300)
				bot.GM(t, ".gm off")
				bot.FlushWorld(t)
				res, err := bot.TryCast(t, 458, bot.GUID, 8*time.Second)
				if err != nil || res.Success || res.FailReason != 107 {
					// SPELL_FAILED_SPELL_UNAVAILABLE is the shared cast hook's explicit mount rejection.
					e2eharness.Assertf(t, "ordinary mount result=%+v err=%v", res, err)
				}
				for _, spell := range []uint32{111000, 111001} {
					speeds := make(chan float32, 4)
					cancelSpeed := bot.World.AddPacketHook(func(op uint16, payload []byte) {
						if op == client.SmsgForceRunSpeedChange && len(payload) >= 10 {
							select {
							case speeds <- math.Float32frombits(binary.LittleEndian.Uint32(payload[len(payload)-4:])):
							default:
							}
						}
					})
					bot.CastMust(t, spell, bot.GUID, 8*time.Second)
					e2eharness.WaitUnitAura(t, bot.World, bot.GUID, spell, 8*time.Second)
					wantSpeed := float32(11.2)
					if spell == 111001 {
						wantSpeed = 14
					}
					select {
					case speed := <-speeds:
						if math.Abs(float64(speed-wantSpeed)) > .01 {
							e2eharness.Assertf(t, "Gallop %d speed=%.2f want=%.2f", spell, speed, wantSpeed)
						}
					case <-time.After(8 * time.Second):
						e2eharness.HarnessFailf(t, "Gallop speed update timed out")
					}
					cancelSpeed()
					if obj := bot.World.GetObject(bot.GUID); obj == nil || obj.Value(0x45) != 0 {
						e2eharness.Assertf(t, "Gallop created an ordinary mount display")
					}
					if err := bot.World.CancelAura(spell); err != nil {
						e2eharness.HarnessFailf(t, "cancel Gallop: %v", err)
					}
					bot.AssertAuraConsumed(t, spell, 8*time.Second, 0)
				}
				bot.GM(t, ".gm on")
				bot.Teleport(t, -1800, 5300, -12, e2eharness.MapOutland)
				bot.GM(t, ".gm off")
				bot.FlushWorld(t)
				for _, spell := range []uint32{111002, 111003, 111002, 111003} {
					if result, ok := bot.CastRetries(t, spell, bot.GUID, 10, 3*time.Second); !ok {
						e2eharness.Assertf(t, "bird form failed after cooldown wait: %+v", result)
					}
					e2eharness.WaitUnitAura(t, bot.World, bot.GUID, spell, 8*time.Second)
					waitCentaurDisplay(t, bot, true, sex)
					if err := bot.World.CancelAura(spell); err != nil {
						e2eharness.HarnessFailf(t, "cancel bird form: %v", err)
					}
					bot.AssertAuraConsumed(t, spell, 8*time.Second, 0)
					waitCentaurDisplay(t, bot, false, sex)
				}
				bot.Save(t)
				bot.Relog(t)
				if race == 74 {
					bot.World.SetCharRace(e2eharness.RaceOrc)
				}
				var gotRace, gotSex, gotSkin, gotHead, gotBeard uint8
				if err := bot.CharDB.QueryRow("SELECT race,gender,skin,hairStyle,facialStyle FROM characters WHERE guid=?", bot.GUID).Scan(&gotRace, &gotSex, &gotSkin, &gotHead, &gotBeard); err != nil {
					e2eharness.HarnessFailf(t, "saved Centaur identity: %v", err)
				}
				if gotRace != race || gotSex != sex || gotSkin != sex*15 {
					e2eharness.Assertf(t, "saved identity changed to race=%d sex=%d skin=%d", gotRace, gotSex, gotSkin)
				}
				wantHead, wantBeard := uint8(8), uint8(7)
				if sex == 1 {
					wantHead, wantBeard = 13, 0
				}
				if gotHead != wantHead || gotBeard != wantBeard {
					e2eharness.Assertf(t, "Centaur facial choices changed: head=%d beard=%d", gotHead, gotBeard)
				}
				bot.WaitEquippedSlot(t, 16730, 4, 10*time.Second)
				bot.AssertWorldAlive(t)
				t.Logf("PASS Centaur race=%d sex=%d creation, mount rejection, Gallop, bird forms and relog", race, sex)
			})
		}
	}
}
