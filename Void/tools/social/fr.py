#!/usr/bin/env python3
import sys
from core import set_language, run_tool

STRINGS = {
    "pause": "Entrée pour revenir au menu…",
    "yes": "Oui", "no": "Non", "unknown": "Inconnu", "maybe": "Peut-être",
    "cancelled": "Annulé", "check_manual": "Vérifie manuellement",
    "open_links": "Ouvrir tous les liens",
    "username": "pseudo",
    "uc_title": "Username Check", "uc_desc": "12 plateformes · liens profil",
    "ytc_title": "YouTube Channel", "ytc_desc": "ID ou @handle",
    "channel_id": "channel ID ou @handle",
    "yt_tip": "Ouvre la page pour voir abonnés/stats",
    "yt_api_note": "Stats complètes = clé API YouTube",
    "ytv_title": "YouTube Video", "ytv_desc": "ID ou URL vidéo",
    "video_id": "video ID ou URL",
    "x_title": "Profil X", "x_desc": "Profil public via miroir",
    "tt_title": "TikTok Profile", "tt_desc": "Infos publiques @user",
    "ig_title": "Instagram Profile", "ig_desc": "Profil public (limité)",
    "ig_note": "Instagram limite le scraping",
    "sc_title": "Snapchat Check", "sc_desc": "Lien add / existence",
    "sc_tip": "HTTP 200 = page accessible",
    "tg_title": "Telegram Channel", "tg_desc": "Infos canal public",
    "channel": "nom du canal (@)",
    "tg_channel": "Canal", "tg_members": "Membres", "tg_preview": "Image preview",
    "tg_see_below": "voir lien ci-dessous", "tg_image_link": "Image canal (clic pour ouvrir)",
    "tg_open_link": "Lien Telegram", "tg_not_found": "Canal introuvable",
    "community": "Communauté", "network": "Connexion impossible",
    "gh_title": "GitHub Profile", "gh_desc": "Pseudo → profil, repos, orgs",
    "gh_not_found": "Utilisateur introuvable", "gh_repos": "Repos publics",
    "gh_followers": "Abonnés", "gh_following": "Abonnements", "gh_created": "Création",
    "gh_top_repos": "Top repos", "gh_orgs": "Organisations",
    "kick_title": "Kick Profile", "kick_desc": "Pseudo → abonnés, bio, live",
    "kick_not_found": "Chaîne introuvable", "kick_followers": "Abonnés",
    "kick_live": "En live", "kick_stream": "Titre stream", "kick_viewers": "Viewers",
    "kick_verified": "Vérifié", "kick_profile_link": "Profil Kick",
    "kick_banner_link": "Bannière (clic pour ouvrir)",
    "mc_title": "Minecraft Profile", "mc_desc": "Pseudo → UUID, skin, NameMC",
    "mc_username": "Pseudo Minecraft", "mc_not_found": "Joueur introuvable",
    "mc_textures": "Textures", "mc_custom": "custom", "mc_default": "default",
    "mc_skin_link": "Skin render (clic pour ouvrir)", "mc_namemc_link": "Profil NameMC",
    "unknown": "Outil inconnu:",
}

if __name__ == "__main__":
    set_language(STRINGS)
    run_tool(sys.argv[1] if len(sys.argv) > 1 else "")
