"""Void Tools — structured help pages (.p1 – .p15)."""
from __future__ import annotations

# page_num -> {title, subtitle, vip, sections: [(name, [(cmd, desc), ...])]}
PAGES: dict[int, dict] = {
    1: {
        "title": "MULTI TOKEN",
        "subtitle": "Multi-account power tools",
        "vip": False,
        "sections": [
            ("Multi token", [
                (".multilast", "Multi-token outlast"),
                (".stopmultilast", "Stop multilast"),
                (".tok", "List tokens"),
                (".multivc", "All tokens → VC"),
                (".arm / .armend", "Multi-token reply"),
            ]),
            ("Spam & control", [
                (".mping / .mpingoff", "Mass ping"),
                (".gcfill / .gc", "GC token tools"),
                (".invis / .invisoff", "Invisible spam"),
                (".say", "Send with tokens"),
                (".rpcall / .stoprpc", "Custom status all"),
            ]),
            ("Utility", [
                (".bold / .unbold", "Bold messages"),
                (".translate", "Auto-translate"),
                (".mimic / .mimic off", "Copy user messages"),
                (".serverinfo", "Server info"),
                (".reload", "Restart bot"),
            ]),
        ],
    },
    2: {
        "title": "MISC & SERVER",
        "subtitle": "Server tools & utilities",
        "vip": False,
        "sections": [
            ("Interaction", [
                (".ghostping", "Ghost ping user"),
                (".triggertyping", "Force typing"),
                (".avatar", "Get avatar"),
                (".roblox", "Roblox lookup"),
            ]),
            ("Server", [
                (".tempchannel / .tempvc", "Temp channels"),
                (".pin", "Pin last message"),
                (".servername", "Rename server"),
                (".inviteinfo", "Invite details"),
            ]),
            ("VIP server", [
                (".pfpscrape", "Scrape member pfps"),
                (".forcedc", "Force disconnect VC"),
                (".mspam", "Multi-token spam"),
                (".webhookcopy", "Send as webhook"),
                (".backupserver", "Backup server JSON"),
                (".pasteserver", "Restore backup"),
                (".clearchannels", "Delete all channels"),
            ]),
        ],
    },
    3: {
        "title": "FUN",
        "subtitle": "Social & anime actions",
        "vip": False,
        "sections": [
            ("Friendly", [
                (".kiss / .hug / .pat", "Affection actions"),
                (".wave / .cuddle", "Wave & cuddle"),
                (".handhold / .highfive", "Hand hold & high-five"),
                (".poke", "Poke user"),
            ]),
            ("Playful", [
                (".nom / .wink / .dance", "Fun reactions"),
                (".smug / .cry", "Expressions"),
            ]),
            ("Aggressive", [
                (".slap / .bite / .bonk", "Combat actions"),
                (".yeet / .bully / .hurt", "Chaos actions"),
            ]),
        ],
    },
    4: {
        "title": "MORE MISC",
        "subtitle": "Emoji, pings & info",
        "vip": False,
        "sections": [
            ("Emoji", [
                (".emojiexport", "Export emojis VIP"),
                (".pastemojis", "Import emojis"),
                (".wipemojis", "Clear exports VIP"),
            ]),
            ("Activity", [
                (".leavegroups", "Leave all groups"),
                (".firstmessage", "First msg in channel"),
                (".fakeactive", "Fake server activity VIP"),
                (".info", "Bot stats in chat"),
            ]),
            ("Ping systems", [
                (".pingresponse", "Custom ping replies"),
                (".pinginsult", "Insult on ping"),
                (".pingreact", "React on ping"),
            ]),
        ],
    },
    5: {
        "title": "AUTO & AFK",
        "subtitle": "Automation & moderation",
        "vip": False,
        "sections": [
            ("AFK check", [
                (".countdown", "AFK check user"),
                (".countdownoff", "Stop countdown"),
                (".mcountdown", "Multi AFK check VIP"),
            ]),
            ("User control", [
                (".autotrap", "Block GC leave"),
                (".autonick", "Force nickname"),
                (".forcepurge", "Auto-delete msgs VIP"),
                (".autokick", "Auto kick user"),
                (".autovclock", "Lock VC on join"),
            ]),
        ],
    },
    6: {
        "title": "SERVER NUKE",
        "subtitle": "Destructive server tools",
        "vip": False,
        "sections": [
            ("Nuke config", [
                (".destroy", "Run nuke sequence"),
                (".nukehook / .nukename", "Webhook & name"),
                (".nukedelay / .nukechannel", "Timing & channel"),
                (".nukeconfig", "Show nuke config"),
                (".nukeconfigwipe", "Reset nuke config"),
            ]),
            ("Mass actions", [
                (".massrole / .massroledel", "Mass roles"),
                (".masschannel", "Mass channels"),
                (".massban / .masskick", "Ban/kick all"),
                (".massdelemoji", "Delete all emojis"),
            ]),
        ],
    },
    7: {
        "title": "SPOTIFY",
        "subtitle": "Playback control",
        "vip": False,
        "sections": [
            ("Playback", [
                (".spotify pause", "Pause track"),
                (".spotify unpause", "Resume track"),
                (".spotify next / prev", "Skip tracks"),
                (".spotify current", "Now playing"),
            ]),
            ("Queue & settings", [
                (".spotify play <song>", "Play song"),
                (".spotify addqueue", "Add to queue"),
                (".spotify volume <0-100>", "Set volume"),
                (".spotify shuffle", "Toggle shuffle"),
                (".spotify repeat", "Repeat mode"),
            ]),
        ],
    },
    8: {
        "title": "ACCOUNT",
        "subtitle": "Profile & identity",
        "vip": False,
        "sections": [
            ("Profile", [
                (".setpfp / .setbanner", "Set avatar & banner"),
                (".rotatepfp", "Rotate profile pics"),
                (".setbio / .rotatebio", "Bio tools"),
                (".rstatus", "Rotate status"),
            ]),
            ("Steal VIP", [
                (".stealpfp / .stealbanner", "Steal avatar/banner"),
                (".stealbio / .stealname", "Steal bio/name"),
                (".stealpronoun", "Steal pronouns"),
            ]),
            ("Info & VC", [
                (".channelinfo / .channels", "Channel list"),
                (".roles / .mutualinfo", "Roles & mutuals"),
                (".spamregion", "Spam VC region VIP"),
            ]),
        ],
    },
    9: {
        "title": "NOTIFICATIONS",
        "subtitle": "Auto react & alerts",
        "vip": False,
        "sections": [
            ("Message hooks", [
                (".ronmessage", "Auto-react to text"),
                (".sonmessage", "Auto-reply to text"),
                (".eonmessage", "Auto-edit messages"),
            ]),
            ("Desktop alerts", [
                (".nonping", "Notify on ping"),
                (".nondm", "Notify on DM"),
                (".nonreaction", "Notify on reaction"),
            ]),
        ],
    },
    10: {
        "title": "PC TOOLS",
        "subtitle": "Screenshots & desktop",
        "vip": False,
        "sections": [
            ("Screenshots", [
                (".wscreenshot", "Full screen capture"),
                (".pscreenshot", "Active window"),
                (".sendss / .openss", "Send or open last"),
            ]),
            ("Windows", [
                (".bsearch", "Browser search"),
                (".opencalc / .openpad", "Open apps"),
                (".dfolder", "Desktop folder"),
                (".cleartemp", "Clear %temp%"),
            ]),
            ("Social search", [
                (".byoutube / .btwitter", "YT & Twitter"),
                (".btiktok / .broblox", "TikTok & Roblox"),
            ]),
        ],
    },
    11: {
        "title": "SETTINGS",
        "subtitle": "Core bot & social",
        "vip": False,
        "sections": [
            ("Core", [
                (".menu / .help / .info", "Navigation"),
                (".theme", "Color themes"),
                (".reload / .shutdown", "Restart & stop"),
                (".cls / .clear", "Clear console"),
            ]),
            ("Friends", [
                (".friend / .unfriend", "Manage friends"),
                (".block / .unblock", "Block list"),
                (".fnote / .fnick", "Friend notes"),
            ]),
            ("VIP tools", [
                (".mdm", "Mass DM friends"),
                (".autobump", "Auto server bump"),
                (".tjoin / .tleave", "Token join/leave"),
                (".addtoken", "Add alt token"),
            ]),
        ],
    },
    12: {
        "title": "AUTO BEEF",
        "subtitle": "Auto press & kill",
        "vip": False,
        "sections": [
            ("Auto press", [
                (".autopress", "Auto press user"),
                (".autopress stop", "Stop autopress"),
                (".autopress add", "Add press message"),
            ]),
            ("Auto kill", [
                (".autokill", "Auto kill user"),
                (".autokill stop / list", "Manage autokill"),
                (".manual", "Manual beef mode"),
            ]),
            ("Multi & VC", [
                (".testimony", "Multi testimony"),
                (".gcleave / .gcleaveall", "Leave GCs"),
                (".vcjoin", "Multi VC join"),
                (".dripcheck", "Drip check roast"),
            ]),
        ],
    },
    13: {
        "title": "AUTO MULTI",
        "subtitle": "Token automation",
        "vip": False,
        "sections": [
            ("Group chat", [
                (".autogc", "Auto add tokens to GC"),
                (".autogcleave", "Mirror GC leaves"),
                (".autoserverleave", "Mirror server leaves"),
            ]),
            ("Repeat & ladder", [
                (".repeat start / stop", "Auto repeat msg"),
                (".ladder", "Auto ladder spam"),
                (".ladder add / clear", "Manage ladder msgs"),
            ]),
        ],
    },
    14: {
        "title": "OTHER",
        "subtitle": "Protection & snipe",
        "vip": False,
        "sections": [
            ("Anti GC spam", [
                (".antigcspam", "GC spam protection"),
                (".antigcspam whitelist", "Whitelist user"),
                (".antigcspam webhook", "Log webhook"),
            ]),
            ("Protection", [
                (".protection start", "GC protection spam"),
                (".rotateguild", "Rotate guild badge"),
            ]),
            ("Snipe", [
                (".dmsnipe", "Deleted msg sniper"),
                (".dmsnipe toggle", "Enable/disable"),
            ]),
        ],
    },
    15: {
        "title": "ADVANCED",
        "subtitle": "Power user toolkit",
        "vip": False,
        "sections": [
            ("Anti last", [
                (".antilast toggle", "Anti last word"),
                (".antilast webhook", "Log webhook"),
                (".laz / .endlaz", "Laz spam mode"),
            ]),
            ("Server profile", [
                (".setspfp / .setsbanner", "Server avatar"),
                (".rotateguild", "Rotate guild tag"),
                (".hypesquad", "Change HypeSquad"),
            ]),
            ("Dumps & tokens", [
                (".imgdump / .gifdump", "Media dumps"),
                (".mp4dump / .movdump", "Video dumps"),
                (".addtoken / .listtokens", "Token manager"),
                (".tokengrab", "Grab token info"),
            ]),
        ],
    },
}

PAGE_COUNT = len(PAGES)

NAV_LABELS = {
    1: "Multi",
    2: "Misc",
    3: "Fun",
    4: "More",
    5: "Auto",
    6: "Nuke",
    7: "Spotify",
    8: "Account",
    9: "Notif",
    10: "PC",
    11: "Settings",
    12: "Beef",
    13: "Multi+",
    14: "Other",
    15: "Advanced",
}


def get_page(num: int) -> dict | None:
    return PAGES.get(int(num))
