from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class Timer:
    start: float = field(default_factory=time.time)

    def elapsed_ms(self) -> int:
        return int((time.time() - self.start) * 1000)
