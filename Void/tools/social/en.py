#!/usr/bin/env python3
import sys
from core import set_language, run_tool

STRINGS = {
    "pause": "Press Enter to return…",
    "yes": "Yes", "no": "No", "unknown": "Unknown", "maybe": "Maybe",
    "cancelled": "Cancelled", "check_manual": "Check manually",
    "open_links": "Open all links",
    "username": "username",
    "uc_title": "Username Check", "uc_desc": "12 platforms · profile links",
    "ytc_title": "YouTube Channel", "ytc_desc": "ID or @handle",
    "channel_id": "channel ID or @handle",
    "yt_tip": "Open page for subscriber stats",
    "yt_api_note": "Full stats need YouTube API key",
    "ytv_title": "YouTube Video", "ytv_desc": "Video ID or URL",
    "video_id": "video ID or URL",
    "x_title": "X Profile", "x_desc": "Public profile via mirror",
    "tt_title": "TikTok Profile", "tt_desc": "Public @user info",
    "ig_title": "Instagram Profile", "ig_desc": "Public profile (limited)",
    "ig_note": "Instagram limits scraping",
    "sc_title": "Snapchat Check", "sc_desc": "Add link / existence",
    "sc_tip": "HTTP 200 = page reachable",
    "tg_title": "Telegram Channel", "tg_desc": "Public channel info",
    "channel": "channel name (@)",
    "tg_channel": "Channel", "tg_members": "Members", "tg_preview": "Preview image",
    "tg_see_below": "see link below", "tg_image_link": "Channel image (click to open)",
    "tg_open_link": "Telegram link", "tg_not_found": "Channel not found",
    "community": "Community", "network": "Network unreachable",
    "gh_title": "GitHub Profile", "gh_desc": "Username → profile, repos, orgs",
    "gh_not_found": "User not found", "gh_repos": "Public repos",
    "gh_followers": "Followers", "gh_following": "Following", "gh_created": "Created",
    "gh_top_repos": "Top repos", "gh_orgs": "Organizations",
    "kick_title": "Kick Profile", "kick_desc": "Username → followers, bio, live status",
    "kick_not_found": "Channel not found", "kick_followers": "Followers",
    "kick_live": "Live", "kick_stream": "Stream title", "kick_viewers": "Viewers",
    "kick_verified": "Verified", "kick_profile_link": "Kick profile",
    "kick_banner_link": "Banner image (click to open)",
    "mc_title": "Minecraft Profile", "mc_desc": "Username → UUID, skin, NameMC",
    "mc_username": "Minecraft username", "mc_not_found": "Player not found",
    "mc_textures": "Textures", "mc_custom": "custom", "mc_default": "default",
    "mc_skin_link": "Skin render (click to open)", "mc_namemc_link": "NameMC profile",
    "unknown": "Unknown tool:",
}

if __name__ == "__main__":
    set_language(STRINGS)
    run_tool(sys.argv[1] if len(sys.argv) > 1 else "")
