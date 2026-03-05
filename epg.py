import requests
import re
from datetime import datetime
import pytz
import sys
import time
import gzip
import html

# =========================================
# CONFIG
# =========================================

BASE_SITE = "https://content.astro.com.my"
tz = pytz.timezone("Asia/Kuala_Lumpur")

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

CHANNEL_SLUGS = [
"KUDADA-599","TV1-HD-395","TV2-HD-396","TV3-106","Astro-Ria-193","Astro-Prima-316",
"Astro-Oasis-315","Astro-Citra-301","Astro-Rania-401","Astro-Aura-400","Al-Hijrah-149",
"Colors-Hindi-HD-365","Z-Cinema-HD-490","TV-Sarawak-429","TV-Okey-HD-467","NTV7-93",
"8TV-115","TV9-48","Astro-Vaanavil-397","Astro-Vinmeen-167","Astro-Vellithirai-HD-399",
"SUN-TV-HD-358","Sun-Music-HD-417","Adithya-67","Sun-News-478","KTV-477","Sun-Life-476",
"Star-Vijay-HD-357","Colors-Tamil-HD-298","Z-Tamil-HD-297","Astro-Thangathirai-177",
"iQIYI-HD-355","TVB-Classic-HD-425","Astro-AEC-182","Astro-QJ-158","Celestial-Movies-HD-134",
"TVB-Jade-203","Astro-AOD-172","CTI-Asia-HD-424","TVB-Entertainment-News-HD-427",
"TVB-Xing-He-HD-383","TVBS-Asia-HD-384","Celestial-Classic-Movies-187",
"Phoenix-Chinese-Channel-HD-382","Phoenix-Info-News-HD-43","Astro-Hua-Hee-Dai-162",
"CCTV4-HD-385","KBS-World-HD-161","ONE-HD-133","tvN-HD-190","K-Plus-HD-266",
"NHK-World-Premium-428","HITS-MOVIES-HD-391","Astro-Boo-251","Astro-Showtime-604",
"Astro-Showcase-454","Rock-Action-601","Rock-X-Stream-605","tvN-Movies-HD-274",
"Astro-Awani-HD-436","Bernama-TV-160","CGTN-HD-426","CNN-HD-336","BBC-News-HD-366",
"Al-Jazeera-English-HD-374","CNA-HD-295","CNBC-Asia-HD-423","Bloomberg-TV-HD-422",
"ABC-Australia-HD-461","DW-English-287",
"France24-289","Love-Nature-4K-472","Love-Nature-483","Discovery-Channel-HD-376",
"Discovery-Asia-HD-136","BBC-Earth-452","History-HD-144","CGTN-Documentary-587",
"Astro-Tutor-TV-411","Astro-Ceria-386","Cartoon-Network-HD-371","Nickelodeon-HD-370",
"Nick-Jr-392","Moonbug-465","Blippi-and-Friends-566","CBeebies-481","AXN-HD-131",
"HITS-NOW-524","Lifetime-HD-447","HITS-HD-179","TLC-HD-338","Asian-Food-Network-HD-91",
"Crime-and-Investigation-HD-369","HGTV-HD-198","BBC-Lifestyle-HD-451","Astro-Arena-235",
"Astro-Arena-2-457","Arena-Bola-486","Arena-Bola-2-487","Astro-Sports-UHD-805-308",
"Astro-Premier-League-4-568","Astro-Premier-League-5-570","Astro-Grandstand-543",
"Astro-Premier-League-536","Astro-Premier-League-2-537","Astro-Premier-League-3-538",
"Astro-Football-539","Astro-Badminton-540","Astro-Badminton-2-541","Astro-Sports-Plus-542",
"beIN-SPORTS-1-236","beIN-SPORTS-2-466","beIN-SPORTS-3-313","W-Sport-503",
"Astro-Golf-189","Astro-Cricket-197","Premier-Sports-Rugby-393","Astro-First-HD-175",
"Astro-First-HD-148","Astro-First-HD-146","Astro-First-HD-152","Astro-First-HD-238",
"Astro-First-HD-173","Astro-First-HD-125","Astro-First-HD-174","Astro-First-HD-242",
"Astro-First-HD-265","Astro-First-HD-142","Astro-First-HD-404","Astro-First-HD-413",
"Astro-First-HD-150","Astro-First-HD-416","Astro-First-HD-240","HITZ-FM-17","MY-FM-15","LITE-FM-19","MIX-FM-18","ERA-FM-14",
"SINAR-FM-26","MELODY-FM-28","THR-RAAGA-30","CLASSIC-ROCK-20","GOLD-21",
"OPUS-16","THR-GEGAR-22","INDIA-BEAT-23","JAZZ-24","OSAI-27","BAYU-31",
"KENYALANG-32","ZAYAN-292","GOXUAN-293","BBC-First-HD-458",
"Smithsonian-Channel-394","BBC-Brit-HD-459"
]

# =========================================

def get_build_id():
    r = requests.get(f"{BASE_SITE}/channels", headers=HEADERS)
    r.raise_for_status()
    match = re.search(r'"buildId":"(.*?)"', r.text)
    if not match:
        print("Build ID not found")
        sys.exit(1)
    return match.group(1)

def fetch_channel(build_id, slug):
    url = f"{BASE_SITE}/_next/data/{build_id}/channels/{slug}.json?channelId={slug}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()

def format_time(dt_str):
    dt = datetime.fromisoformat(dt_str.replace("+08:00", ""))
    dt = tz.localize(dt)
    return dt.strftime("%Y%m%d%H%M%S +0800")

# =========================================

def generate_epg():

    build_id = get_build_id()
    print("Build ID:", build_id)

    total_programmes = 0
    processed_channels = 0

    channel_blocks = []
    programme_blocks = []

    for slug in CHANNEL_SLUGS:

        print("Processing:", slug)

        try:
            data = fetch_channel(build_id, slug)
            if not data:
                print("  -> 404 Skipped")
                continue

            details = data.get("pageProps", {}).get("channelDetails", {})
            schedule = details.get("schedule", {})

            if not schedule:
                print("  -> No schedule (Skipped)")
                continue

            channel_number = details.get("stbNumber")
            fallback_id = details.get("id")

            if channel_number:
                channel_id = f"{channel_number}.astro"
            else:
                channel_id = f"{fallback_id}.astro"

            channel_name = details.get("title", slug)
            logo_url = details.get("imageUrl")

            block = []
            block.append(f'  <channel id="{channel_id}">')
            block.append(f'    <display-name lang="en">{channel_name}</display-name>')
            block.append(f'    <display-name lang="en">{channel_number}</display-name>')
            if logo_url:
                block.append(f'    <icon src="{logo_url}" />')
            block.append('  </channel>')

            channel_blocks.append("\n".join(block))

            channel_programmes = 0

            for day, programmes in schedule.items():
                for prog in programmes:

                    start = format_time(prog["eventStartMyt"])
                    end = format_time(prog["eventEndMyt"])

                    title =  html.escape(prog.get("title", "No Title"))
                    desc = html.escape(prog.get("description", ""))

                    land = prog.get("landscapeImage")
                    img = prog.get("imageUrl")
                    image = land if land else img

                    prog_block = []
                    prog_block.append(
                        f'  <programme start="{start}" stop="{end}" channel="{channel_id}">'
                    )

                    prog_block.append(f'    <title lang="en">{title}</title>')

                    if desc:
                        prog_block.append(f'    <desc lang="en">{desc}</desc>')

                    if image:
                        prog_block.append(f'    <icon src="{image}"/>')

                    prog_block.append('  </programme>')

                    programme_blocks.append("\n".join(prog_block))

                    total_programmes += 1
                    channel_programmes += 1

            processed_channels += 1
            print(f"  -> OK ({channel_programmes} programmes)")

            time.sleep(0.03)

        except Exception as e:
            print("  -> ERROR:", e)

    # WRITE XML
    with open("astro.xml", "w", encoding="utf-8") as f:

        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<tv generator-info-name="AstroEPG" generator-info-url="https://content.astro.com.my">\n\n')

        for block in channel_blocks:
            f.write(block + "\n")

        f.write("\n")

        for block in programme_blocks:
            f.write(block + "\n")

        f.write('</tv>\n')

    print("XML generated")

    # CREATE GZIP
    with open("astro.xml", "rb") as f_in:
        with gzip.open("astro.xml.gz", "wb") as f_out:
            f_out.writelines(f_in)

    print("GZIP generated")

    print("\n=================================")
    print("Channels processed:", processed_channels)
    print("Total programmes:", total_programmes)
    print("Files: astro.xml , astro.xml.gz")

# =========================================

if __name__ == "__main__":
    generate_epg()
