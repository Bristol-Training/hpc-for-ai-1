"""Repair the truncated JPEGs in the FracAtlas dataset.

87 of the non-fractured images in the FracAtlas download are truncated: the
end of the file is missing. Some image readers (including the one Ultralytics
uses for prediction) can't open them, and the readers that can open them fill
the missing part with a flat mid-grey band (pixel value 128) at the bottom of
the image. Because all 87 are non-fractured, that grey band could act as a
shortcut for the model, so this script:

1. backs up the original files (to BACKUP_DIR),
2. crops off any grey band at the bottom of each image,
3. saves each one again as a complete JPEG, keeping the file's original date,
4. writes a record of what it changed to FracAtlas/truncated-images.txt.

Run it once, on an Isambard-AI login node, with the course environment:

    $PROJECTDIR/hpc-ai-1/venv/bin/python setup/repair-truncated-images.py \
        $PROJECTDIR/hpc-ai-1/FracAtlas $SCRATCHDIR/fracatlas-truncated-originals

Running it again is safe: images that have already been repaired end
properly, so they aren't picked up a second time.
"""

import os
import shutil
import sys
from pathlib import Path

import cv2

dataset = Path(sys.argv[1])
backup_dir = Path(sys.argv[2])
backup_dir.mkdir(parents=True, exist_ok=True)

images = sorted((dataset / "images").glob("*/*.jpg"))
truncated = [f for f in images if f.read_bytes()[-2:] != b"\xff\xd9"]  # every complete JPEG ends FF D9

log = []
for f in truncated:
    backup = backup_dir / f.name
    if not backup.exists():
        shutil.copy2(f, backup)

    im = cv2.imread(str(backup))
    rows = 0
    while rows < im.shape[0] - 1 and (im[-(rows + 1)] == 128).all():  # flat grey rows at the bottom
        rows += 1
    if rows:
        im = im[:-rows]

    stat = f.stat()
    tmp = f.with_name(f.stem + ".tmp.jpg")
    cv2.imwrite(str(tmp), im, [cv2.IMWRITE_JPEG_QUALITY, 100])
    os.replace(tmp, f)  # swap in the repaired file in one step
    os.utime(f, (stat.st_atime, stat.st_mtime))
    f.chmod(stat.st_mode)
    log.append(f"{f.relative_to(dataset / 'images')},{rows}")

if log:
    (dataset / "truncated-images.txt").write_text("image,grey_rows_removed\n" + "\n".join(log) + "\n")

cropped = [int(line.split(",")[1]) for line in log if not line.endswith(",0")]
print(f"{len(images)} images checked | {len(truncated)} truncated and repaired | "
      f"{len(cropped)} had a grey band (largest {max(cropped, default=0)} rows)")
print(f"Originals backed up to {backup_dir}")
