import requests
import re
import sys
import time
import gzip
import shutil
import os
import html
import pytz
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# =========================================
# CONFIG
# =========================================

BASE_SITE = "https://content.astro.com.my"
HEADERS = {"User-Agent": "Mozilla/5.0"}
tz = pytz.timezone("Asia/Kuala_Lumpur")

TEMP_FILE = "astro_new.xml"
FINAL_FILE = "astro.xml"
OLD_FILE = "astro_old.xml"

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
# LOGGING SETUP
# =========================================

logging.basicConfig(
    filename="epg.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# =========================================
# SAFE REQUEST (Retry)
# =========================================

def safe_request(url, retries=3):
    for _ in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r
        except Exception as e:
            logging.warning(f"Retrying request: {url}")
            time.sleep(1)
    logging.error(f"Failed request: {url}")
    return None


def get_build_id():
    r = safe_request(f"{BASE_SITE}/channels")
    if not r:
        sys.exit("Failed to get build ID")
    match = re.search(r'"buildId":"(.*?)"', r.text)
    if not match:
        sys.exit("Build ID not found")
    logging.info(f"Build ID: {match.group(1)}")
    return match.group(1)


def fetch_channel(build_id, slug):
    url = f"{BASE_SITE}/_next/data/{build_id}/channels/{slug}.json?channelId={slug}"
    r = safe_request(url)
    if not r:
        logging.warning(f"Skipped channel: {slug}")
        return None
    return r.json()


def format_time(dt_str):
    dt = datetime.fromisoformat(dt_str)
    dt = dt.astimezone(tz)
    return dt.strftime("%Y%m%d%H%M%S %z")

# =========================================
# PROCESS ONE CHANNEL (THREAD WORKER)
# =========================================

def process_slug(build_id, slug):
    try:
        data = fetch_channel(build_id, slug)
        if not data:
            return None

        details = data.get("pageProps", {}).get("channelDetails", {})
        schedule = details.get("schedule", {})

        if not schedule:
            logging.info(f"No schedule: {slug}")
            return None

        channel_number = details.get("stbNumber")
        fallback_id = details.get("id")
        channel_id = f"{channel_number or fallback_id}.astro"

        channel_name = html.escape(details.get("title", slug))
        logo_url = details.get("imageUrl")

        channel_block = [
            f'  <channel id="{channel_id}">',
            f'    <display-name lang="en">{channel_name}</display-name>'
        ]

        if channel_number:
            channel_block.append(f'    <display-name lang="en">{channel_number}</display-name>')

        if logo_url:
            channel_block.append(f'    <icon src="{logo_url}" />')

        channel_block.append("  </channel>")

        programme_blocks = []

        for day, programmes in schedule.items():
            for prog in programmes:

                start = format_time(prog["eventStartMyt"])
                end = format_time(prog["eventEndMyt"])

                title = html.escape(prog.get("title", "No Title"))
                desc = html.escape(prog.get("description", ""))

                prog_block = [
                    f'  <programme start="{start}" stop="{end}" channel="{channel_id}">',
                    f'    <title lang="en">{title}</title>'
                ]

                if desc:
                    prog_block.append(f'    <desc lang="en">{desc}</desc>')

                prog_block.append("  </programme>")

                programme_blocks.append("\n".join(prog_block))

        logging.info(f"OK: {slug}")
        return ("\n".join(channel_block), programme_blocks)

    except Exception as e:
        logging.error(f"Error processing {slug}: {e}")
        return None

# =========================================
# GENERATE EPG (PARALLEL)
# =========================================

def generate_epg():

    build_id = get_build_id()

    channel_blocks = []
    programme_blocks = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_slug, build_id, slug) for slug in CHANNEL_SLUGS]

        for future in as_completed(futures):
            result = future.result()
            if result:
                channel_block, progs = result
                channel_blocks.append(channel_block)
                programme_blocks.extend(progs)

    with open(TEMP_FILE, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<tv generator-info-name="AstroEPG">\n\n')

        for block in channel_blocks:
            f.write(block + "\n")

        f.write("\n")

        for block in programme_blocks:
            f.write(block + "\n")

        f.write("</tv>\n")

    logging.info("Temp XML generated")

# =========================================
# MAIN
# =========================================

if __name__ == "__main__":

    if os.path.exists(FINAL_FILE):
        os.replace(FINAL_FILE, OLD_FILE)

    generate_epg()

    try:
        ET.parse(TEMP_FILE)
    except:
        logging.error("XML corrupted. Abort.")
        sys.exit(1)

    os.replace(TEMP_FILE, FINAL_FILE)

    with open(FINAL_FILE, "rb") as f_in:
        with gzip.open(FINAL_FILE + ".gz", "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

    logging.info("EPG Updated Successfully")
