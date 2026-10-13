"""Fixed simulation rate, independent of drawing frequency."""
from collections import deque
import time


class FixedClock:
    def __init__(self, hz=60, max_steps=8):
        self.hz = hz
        self.max_steps = max_steps
        self.accumulator = 0.0
        self.dropped_seconds = 0.0

    def steps(self, elapsed):
        # Long stalls discard excess time rather than freezing UI with catch-up.
        limit = self.max_steps / self.hz
        accepted = min(max(0.0, elapsed), limit)
        self.dropped_seconds += max(0.0, elapsed - accepted)
        self.accumulator += accepted * self.hz
        count = min(self.max_steps, int(self.accumulator + 1e-9))
        self.accumulator -= count
        return count

    def reset(self):
        self.accumulator = 0.0


class FrameMetrics:
    def __init__(self):
        self.samples = deque(maxlen=240)
        self.updates = deque(maxlen=240)
        self.renders = deque(maxlen=240)
        self.start = time.perf_counter()

    def begin(self):
        self.start = time.perf_counter()
        self.render_start = None

    def begin_render(self):
        self.render_start = time.perf_counter()
        self.updates.append((self.render_start - self.start) * 1000)

    def end(self):
        now = time.perf_counter()
        self.samples.append((now - self.start) * 1000)
        if self.render_start is not None:
            self.renders.append((now - self.render_start) * 1000)

    def label(self):
        values = sorted(self.samples)
        if not values:
            return 'Frame work: measuring'
        update = sum(self.updates) / max(1, len(self.updates))
        render = sum(self.renders) / max(1, len(self.renders))
        return f'Update {update:.1f} ms | Draw {render:.1f} ms | Work p95 {values[int((len(values)-1)*.95)]:.1f} ms'
