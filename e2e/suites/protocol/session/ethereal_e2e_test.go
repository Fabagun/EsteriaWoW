//go:build e2e

package session_test

import (
	"bytes"
	"database/sql"
	"encoding/binary"
	"fmt"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"github.com/azerothcore/AzerothGhost/client"
	"github.com/azerothcore/AzerothGhost/e2e/e2eharness"
	"github.com/azerothcore/azerothcore-wotlk/e2e/internal/meta"
	_ "github.com/go-sql-driver/mysql"
)

func etherealLook(race, sex, form uint8) []byte {
	look := make([]byte, 132)
	look[0], look[1], look[2] = 2, race, sex|form<<4
	if form == 5 {
		look[3] = 38
		binary.LittleEndian.PutUint16(look[4:], 2)
		binary.LittleEndian.PutUint16(look[6:], 1)
		binary.LittleEndian.PutUint16(look[8:], 5)
	} else {
		look[3] = 8
		binary.LittleEndian.PutUint16(look[4:], 4)
		binary.LittleEndian.PutUint16(look[6:], 5)
		binary.LittleEndian.PutUint16(look[18:], 6)
	}
	return look
}

func waitEtherealSavedPair(t *testing.T, db *sql.DB, guid uint64, active, parked []byte) {
	t.Helper()
	ticker := time.NewTicker(25 * time.Millisecond)
	defer ticker.Stop()
	deadline := time.NewTimer(8 * time.Second)
	defer deadline.Stop()
	for {
		var a, p []byte
		err := db.QueryRow("SELECT a.data,p.data FROM character_retail_look a JOIN character_form_look p ON p.guid=a.guid WHERE a.guid=?", guid).Scan(&a, &p)
		if err == nil && bytes.Equal(a, active) && bytes.Equal(p, parked) {
			return
		}
		if err != nil && err != sql.ErrNoRows {
			e2eharness.HarnessFailf(t, "read saved Ethereal pair: %v", err)
		}
		select {
		case <-ticker.C:
		case <-deadline.C:
			e2eharness.Assertf(t, "Ethereal form commit did not persist both independent looks")
		}
	}
}

func etherealConnect(t *testing.T, authDB *sql.DB, account string) *client.WorldClient {
	t.Helper()
	auth := client.NewAuthClient(account, e2eharness.DefaultPassword)
	realms, err := auth.Authenticate(e2eharness.AuthAddr)
	if err != nil || len(realms) == 0 {
		e2eharness.Preconditionf(t, "Ethereal authentication: %v", err)
	}
	// The pinned harness sends a leading NUL in its OS tag; this Windows test account must retain Win for Warden admission.
	if _, err := authDB.Exec("UPDATE account SET os=? WHERE username=?", "Win", strings.ToUpper(account)); err != nil {
		e2eharness.HarnessFailf(t, "set disposable Windows test account OS: %v", err)
	}
	var closed atomic.Bool
	w := client.NewWorldClient(strings.ToUpper(account), auth.SessionKey(), func(format string, args ...interface{}) {
		if !closed.Load() {
			t.Logf(format, args...)
		}
	})
	t.Cleanup(func() { closed.Store(true); w.Close() })
	if err := w.Connect(realms[0].Address); err != nil {
		e2eharness.Preconditionf(t, "Ethereal world connect: %v", err)
	}
	go func() { _ = w.Run() }()
	if err := w.WaitForSessionPhase(client.PhaseAuthed, 20*time.Second); err != nil {
		e2eharness.Preconditionf(t, "Ethereal session authentication: %v", err)
	}
	return w
}

func etherealFixture(t *testing.T, race, sex uint8) *e2eharness.ScenarioBot {
	t.Helper()
	authDB, charDB := e2eharness.OpenTestDBs(t)
	id := e2eharness.MakeBotIdentsRaceClass("Ethrl", 1, race, e2eharness.ClassWarrior)[0]
	e2eharness.EnsureBotAccounts(t, authDB, []e2eharness.BotIdent{id})
	w := etherealConnect(t, authDB, id.Account)
	created, ack := make(chan uint8, 1), make(chan uint8, 1)
	enumerated := make(chan uint64, 1)
	w.OnCharList = func(characters []client.CharEnumEntry) {
		for _, character := range characters {
			if strings.EqualFold(character.Name, id.CharName) {
				select {
				case enumerated <- character.GUID:
				default:
				}
			}
		}
	}
	cancel := w.AddPacketHook(func(op uint16, data []byte) {
		if op == 0x3A && len(data) == 1 {
			select {
			case created <- data[0]:
			default:
			}
		}
		if op == 0x526 && len(data) == 13 {
			select {
			case ack <- data[12]:
			default:
			}
		}
	})
	defer cancel()
	if err := w.CreateCharacter(id.CharName, race, e2eharness.ClassWarrior, sex, 0, 0, 0, 0, 0, 0); err != nil {
		e2eharness.HarnessFailf(t, "Ethereal create: %v", err)
	}
	select {
	case result := <-created:
		if result != 0x2f {
			e2eharness.Assertf(t, "Ethereal creation refused: race=%d sex=%d result=%d", race, sex, result)
		}
	case <-time.After(20 * time.Second):
		e2eharness.HarnessFailf(t, "Ethereal create response timed out")
	}
	var guid uint64
	if err := w.RequestCharList(); err != nil {
		e2eharness.HarnessFailf(t, "request created Ethereal character list: %v", err)
	}
	select {
	case guid = <-enumerated:
	case <-time.After(10 * time.Second):
		e2eharness.HarnessFailf(t, "created Ethereal character was not enumerated")
	}
	// The same post-create commit as the native client, with two independently customized full looks.
	commit := make([]byte, 13, 13+2*132)
	binary.LittleEndian.PutUint64(commit, guid)
	binary.LittleEndian.PutUint32(commit[8:], 1)
	commit[12] = 5
	commit = append(commit, etherealLook(race, sex, 5)...)
	commit = append(commit, etherealLook(race, sex, 6)...)
	if err := w.SendPacketRaw(0x525, commit); err != nil {
		e2eharness.HarnessFailf(t, "send Ethereal saved-form commit: %v", err)
	}
	select {
	case result := <-ack:
		if result != 0 {
			e2eharness.Assertf(t, "Ethereal form commit refused: result=%d", result)
		}
	case <-time.After(10 * time.Second):
		e2eharness.HarnessFailf(t, "Ethereal form commit acknowledgement timed out")
	}
	waitEtherealSavedPair(t, charDB, guid, etherealLook(race, sex, 5), etherealLook(race, sex, 6))
	if err := w.LoginCharacter(guid); err != nil {
		e2eharness.HarnessFailf(t, "enter created Ethereal character: %v", err)
	}
	if err := w.WaitForSessionPhase(client.PhaseInWorld, 20*time.Second); err != nil {
		e2eharness.HarnessFailf(t, "created Ethereal character did not enter world: %v", err)
	}
	session := &e2eharness.Session{World: w, GUID: guid, Name: id.CharName, User: id.Account}
	bot := &e2eharness.ScenarioBot{Session: session, AuthDB: authDB, CharDB: charDB, Ident: id}
	if race == 78 {
		bot.World.SetCharRace(e2eharness.RaceOrc)
	}
	e2eharness.EnableGM(t, bot.World)
	t.Logf("Ethereal fixture guid=%d race=%d sex=%d", guid, race, sex)
	return bot
}

func armEtherealLook(t *testing.T, viewer *e2eharness.ScenarioBot, guid uint64, expected []byte) func() {
	t.Helper()
	updates := make(chan []byte, 4)
	cancel := viewer.World.AddPacketHook(func(op uint16, data []byte) {
		if op == 0x524 && len(data) == 140 && binary.LittleEndian.Uint64(data) == guid {
			select {
			case updates <- append([]byte(nil), data[8:]...):
			default:
			}
		}
	})
	t.Cleanup(cancel)
	return func() {
		defer cancel()
		select {
		case look := <-updates:
			if !bytes.Equal(look, expected) {
				e2eharness.Assertf(t, "active Ethereal form/choices differ: got=%x want=%x", look, expected)
			}
		case <-time.After(10 * time.Second):
			e2eharness.Assertf(t, "Ethereal active appearance not replicated to viewer=%d", viewer.GUID)
		}
	}
}

func etherealRelog(t *testing.T, bot *e2eharness.ScenarioBot) {
	t.Helper()
	if err := bot.World.SendLogout(); err != nil {
		e2eharness.HarnessFailf(t, "Ethereal logout request: %v", err)
	}
	if err := bot.World.WaitForLogout(30 * time.Second); err != nil {
		e2eharness.HarnessFailf(t, "Ethereal logout: %v", err)
	}
	bot.World.Close()
	w := etherealConnect(t, bot.AuthDB, bot.Ident.Account)
	enumerated := make(chan struct{}, 1)
	w.OnCharList = func(characters []client.CharEnumEntry) {
		for _, character := range characters {
			if character.GUID == bot.GUID {
				select {
				case enumerated <- struct{}{}:
				default:
				}
			}
		}
	}
	if err := w.RequestCharList(); err != nil {
		e2eharness.HarnessFailf(t, "Ethereal relog character list: %v", err)
	}
	select {
	case <-enumerated:
	case <-time.After(10 * time.Second):
		e2eharness.HarnessFailf(t, "Ethereal relog character not enumerated")
	}
	if err := w.LoginCharacter(bot.GUID); err != nil {
		e2eharness.HarnessFailf(t, "Ethereal relog login: %v", err)
	}
	if err := w.WaitForSessionPhase(client.PhaseInWorld, 20*time.Second); err != nil {
		e2eharness.HarnessFailf(t, "Ethereal relog did not load the character: %v", err)
	}
	bot.Session = &e2eharness.Session{World: w, GUID: bot.GUID, Name: bot.Name, User: bot.Ident.Account}
}

// Creating, committing, casting the racial, nearby replication and relog must preserve both independent looks.
func TestSession_EtherealSavedForms(t *testing.T) {
	meta.Begin(t, meta.TestMeta{Tags: []string{"protocol", "ethereal", "serial"}, Runtime: "med", Category: "protocol/session"})
	for _, race := range []uint8{77, 78} {
		for _, sex := range []uint8{0, 1} {
			t.Run(fmt.Sprintf("race%d-sex%d", race, sex), func(t *testing.T) {
				bot, observer := etherealFixture(t, race, sex), etherealFixture(t, race, sex^1)
				pad := e2eharness.PackagePad(t)
				bot.TeleportPad(t, pad)
				observer.TeleportPad(t, pad)
				bot.EquipEntry(t, 25, 1)
				bot.WaitEquippedSlot(t, 25, 15, 10*time.Second)
				bot.GM(t, ".gm off")
				observer.GM(t, ".gm off")
				bot.FlushWorld(t)
				observer.FlushWorld(t)
				if !bot.World.KnowsSpell(111004) {
					e2eharness.Assertf(t, "Ethereal racial not learned")
				}
				for _, form := range []uint8{6, 5} {
					look := etherealLook(race, sex, form)
					ownerWait := armEtherealLook(t, bot, bot.GUID, look)
					observerWait := armEtherealLook(t, observer, bot.GUID, look)
					if result, ok := bot.CastRetries(t, 111004, bot.GUID, 10, 2*time.Second); !ok || !result.Success {
						e2eharness.Assertf(t, "Ethereal racial failed after waiting for the global cooldown: %+v", result)
					}
					ownerWait()
					observerWait()
					bot.WaitEquippedSlot(t, 25, 15, 10*time.Second)
					obj := bot.World.GetObject(bot.GUID)
					if obj == nil || uint8(obj.Value(client.UnitFieldBytes0)) != race || uint8(obj.Value(client.UnitFieldBytes0)>>16) != sex {
						e2eharness.Assertf(t, "Ethereal transformation changed race or gender")
					}
				}
				bot.Save(t)
				etherealRelog(t, bot)
				if race == 78 {
					bot.World.SetCharRace(e2eharness.RaceOrc)
				}
				bot.FlushWorld(t)
				ownerWait := armEtherealLook(t, bot, bot.GUID, etherealLook(race, sex, 6))
				bot.CastMust(t, 111004, bot.GUID, 8*time.Second)
				ownerWait()
				bot.Save(t)
				waitEtherealSavedPair(t, bot.CharDB, bot.GUID, etherealLook(race, sex, 6), etherealLook(race, sex, 5))
				t.Logf("PASS Ethereal race=%d sex=%d saved forms, normal racial, equipped weapon, observer and relog", race, sex)
			})
		}
	}
}
