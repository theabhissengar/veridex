"""Print dataset-tier metrics. Held-out evaluation is the published number."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from veridex.eval.runner import evaluate_tiers


def main() -> None:
    print(json.dumps(evaluate_tiers(), indent=2))


if __name__ == "__main__":
    main()
