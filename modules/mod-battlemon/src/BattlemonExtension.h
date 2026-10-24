#ifndef BATTLEMON_EXTENSION_H
#define BATTLEMON_EXTENSION_H

#include "ObjectGuid.h"
#include <string>

class Player;

// Optional world-thread integration. Packet callbacks must only enqueue events:
// they can run while the battle manager owns its encounter mutex.
class BattlemonExtension
{
public:
    virtual ~BattlemonExtension() = default;
    virtual bool IsReserved(ObjectGuid guid) const = 0;
    // Return true when the extension takes ownership of eventual packet delivery.
    virtual bool OnPacket(Player* player, std::string const& payload) = 0;
    virtual bool IsPlaybackBusy(ObjectGuid guid) const = 0;
    virtual void OnCatalogReload() = 0;
};

#endif
