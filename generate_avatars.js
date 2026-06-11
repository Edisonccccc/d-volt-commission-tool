const multiavatar = require('@multiavatar/multiavatar');
const fs = require('fs');
const path = require('path');

const OUT_DIR = path.join(__dirname, 'assets', 'avatars');
fs.mkdirSync(OUT_DIR, { recursive: true });

const FEMALE = [
  "Aria","Luna","Stella","Chloe","Emma","Lily","Zoe","Mia","Sofia","Ava",
  "Nora","Isla","Ruby","Violet","Hazel","Aurora","Ellie","Ivy","Jade","Rose",
  "Layla","Freya","Nova","Willow","Scarlett","Penelope","Clara","Grace","Piper","Maya",
  "Elara","Cora","Wren","Skye","Sienna","Nina","Lena","Elsie","Fiona","Alma",
];
const MALE = [
  "Liam","Noah","Ethan","Oliver","Lucas","Mason","Logan","Aiden","Jack","Owen",
  "Finn","Leo","Theo","Milo","Hugo","Eli","Zane","Cole","Reid","Beau",
  "Axel","Blake","Caden","Dax","Ezra","Flynn","Gage","Huck","Ivan","Jace",
  "Knox","Lane","Max","Nate","Otto","Penn","Rex","Seth","Tate","Wade",
];
const OTHER = [
  "Alex","River","Quinn","Sage","Avery","Casey","Drew","Emery","Finley","Gray",
  "Harley","Jamie","Jordan","Kai","Robin","Morgan","Parker","Reese","Skyler","Taylor",
];

const all = [
  ...FEMALE.map(s => ['female', s]),
  ...MALE.map(s => ['male', s]),
  ...OTHER.map(s => ['other', s]),
];

let ok = 0;
for (const [gender, seed] of all) {
  const filename = `${gender}_${seed}.svg`;
  const outPath = path.join(OUT_DIR, filename);
  try {
    const svgCode = multiavatar(seed);
    fs.writeFileSync(outPath, svgCode, 'utf8');
    ok++;
    process.stdout.write(`  ok  ${filename}\n`);
  } catch (e) {
    process.stdout.write(`  FAIL ${filename}: ${e.message}\n`);
  }
}
console.log(`\nDone. ${ok}/${all.length} generated.`);
