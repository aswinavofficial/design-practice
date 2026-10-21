#!/usr/bin/env python3
"""Extract the OpenAPI YAML block from each project/solution markdown file.

Each project brief and solution contains exactly one fenced ```yaml block whose
body starts with `openapi:`. That block is written to openapi/<slug>.yaml so it
can be imported into Swagger Editor via its ?url= parameter.

The Pages workflow runs this before deploying, so the deployed files can never
drift from the markdown. Re-run locally after editing the markdown.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "openapi"
FENCE = re.compile(r"^```yaml[ \t]*$(.*?)^```[ \t]*$", re.M | re.S)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    count = 0
    for md in sorted(ROOT.glob("*.md")):
        if md.name == "README.md":
            continue
        for block in FENCE.findall(md.read_text(encoding="utf-8")):
            if re.search(r"^openapi:", block, re.M):
                (OUT / f"{md.stem}.yaml").write_text(block.strip() + "\n", encoding="utf-8")
                count += 1
                break
        else:
            print(f"WARNING: no OpenAPI block found in {md.name}")
    print(f"extracted {count} OpenAPI specs into {OUT}")


if __name__ == "__main__":
    main()
