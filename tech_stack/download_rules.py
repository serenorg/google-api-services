# ABOUTME: Installs one immutable upstream fingerprint bundle during image builds.
# ABOUTME: Keeps GPL rules and their license inside the image and outside git.

import io
from pathlib import Path
import re
import sys
import tarfile
from urllib.request import urlopen


def download(commit: str, destination: Path):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Rules commit must be a full immutable commit ID")
    url = f"https://codeload.github.com/enthec/webappanalyzer/tar.gz/{commit}"
    with urlopen(url, timeout=60) as response:
        archive = response.read(30_000_001)
    if len(archive) > 30_000_000:
        raise ValueError("Rules archive exceeds the download limit")
    prefix = f"webappanalyzer-{commit}/"
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
        for member in bundle:
            relative = member.name.removeprefix(prefix)
            if not member.isfile() or not (
                relative in ("src/categories.json", "src/groups.json", "LICENSE")
                or re.fullmatch(r"src/technologies/[\w-]+\.json", relative)
            ):
                continue
            target = destination / relative.removeprefix("src/")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bundle.extractfile(member).read())
    (destination / "COMMIT").write_text(commit + "\n")


if __name__ == "__main__":
    download(sys.argv[1], Path(sys.argv[2]))
