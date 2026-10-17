import json
import sys
from pathlib import Path
from time import perf_counter

from ocr_core import build_ocr

input_path = sys.argv[1]
output_dir = Path(__file__).resolve().parent / "output"
output_dir.mkdir(parents=True, exist_ok=True)

ocr = build_ocr()

# Repeat in the same process to separate startup from warm inference.
for run in range(2):
    start = perf_counter()

    for result in ocr.predict(input_path):
        if run == 1:
            result.print()
            # Keep only the recognized texts and their scores in the JSON output.
            res = result.json["res"]
            stem = Path(res["input_path"]).stem
            filtered = {
                "rec_texts": res["rec_texts"],
                "rec_scores": res["rec_scores"],
            }
            with open(output_dir / f"{stem}_res.json", "w", encoding="utf-8") as f:
                json.dump(filtered, f, ensure_ascii=False, indent=4)
            result.save_to_img(str(output_dir))

    print(f"Run {run + 1}: {perf_counter() - start:.3f}s")