"""Download 100 DiceBear SVG avatars and save locally, pre-classified by gender."""
import urllib.request
import time
import os

# Style per gender — visually distinct, cute cartoon characters
STYLES = {
    "female": "lorelei",           # illustrated feminine portraits
    "male":   "adventurer-neutral", # cartoon masculine characters
    "other":  "notionists-neutral", # fun illustrated neutrals
}

BG = {
    "female": "ffd5dc,f9c0e9,c0aede,fce4ec,ffdfbf",
    "male":   "b6e3f4,bfdbfe,c7f2d0,d1d4f9,a7f3d0",
    "other":  "e2e8f0,fef3c7,e0e7ff,f0fdf4,fff7ed",
}

FEMALE_SEEDS = [
    "Aria","Luna","Stella","Chloe","Emma","Lily","Zoe","Mia","Sofia","Ava",
    "Nora","Isla","Ruby","Violet","Hazel","Aurora","Ellie","Ivy","Jade","Rose",
    "Layla","Freya","Nova","Willow","Scarlett","Penelope","Clara","Grace","Piper","Maya",
    "Elara","Cora","Wren","Skye","Sienna","Nina","Lena","Elsie","Fiona","Alma",
]
MALE_SEEDS = [
    "Liam","Noah","Ethan","Oliver","Lucas","Mason","Logan","Aiden","Jack","Owen",
    "Finn","Leo","Theo","Milo","Hugo","Eli","Zane","Cole","Reid","Beau",
    "Axel","Blake","Caden","Dax","Ezra","Flynn","Gage","Huck","Ivan","Jace",
    "Knox","Lane","Max","Nate","Otto","Penn","Rex","Seth","Tate","Wade",
]
OTHER_SEEDS = [
    "Alex","River","Quinn","Sage","Avery","Casey","Drew","Emery","Finley","Gray",
    "Harley","Jamie","Jordan","Kai","Robin","Morgan","Parker","Reese","Skyler","Taylor",
]

OUT_DIR = os.path.join(os.path.dirname(__file__), "assets", "avatars")
os.makedirs(OUT_DIR, exist_ok=True)

all_seeds = (
    [("female", s) for s in FEMALE_SEEDS] +
    [("male",   s) for s in MALE_SEEDS] +
    [("other",  s) for s in OTHER_SEEDS]
)

print(f"Downloading {len(all_seeds)} avatars from DiceBear...")
ok = fail = skip = 0
for i, (gender, seed) in enumerate(all_seeds):
    filename = f"{gender}_{seed}.svg"
    path = os.path.join(OUT_DIR, filename)
    if os.path.exists(path):
        skip += 1
        continue
    style = STYLES[gender]
    bg    = BG[gender]
    url   = f"https://api.dicebear.com/9.x/{style}/svg?seed={urllib.request.quote(seed)}&backgroundColor={bg}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read()
        with open(path, "wb") as f:
            f.write(data)
        ok += 1
        print(f"  [{i+1:3d}] ok    {filename}")
        time.sleep(0.1)
    except Exception as e:
        fail += 1
        print(f"  [{i+1:3d}] FAIL  {filename}: {e}")

print(f"\nDone. {ok} downloaded, {skip} skipped, {fail} failed.")
