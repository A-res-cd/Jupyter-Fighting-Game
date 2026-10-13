"""Presentation interpolation without changing authoritative simulation state."""
from collections import deque
import copy


class Interpolator:
    """Only presentation positions interpolate; fighter state remains authoritative."""
    def __init__(self, delay=.05):
        self.samples = deque(maxlen=12)
        self.delay = delay

    def add(self, snapshot, received):
        if self.samples and snapshot['round'] != self.samples[-1][1]['round']:
            self.samples.clear()
        self.samples.append((received, copy.deepcopy(snapshot)))

    def positions(self, now):
        if not self.samples:
            return None
        target = now - self.delay
        while len(self.samples) > 2 and self.samples[1][0] < target:
            self.samples.popleft()
        a = self.samples[0]
        b = self.samples[-1]
        for sample in list(self.samples)[1:]:
            if sample[0] >= target:
                b = sample
                break
            a = sample
        amount = max(0, min(1, (target - a[0]) / max(.000001, b[0] - a[0])))
        return [(round(a[1][key]['x'] + (b[1][key]['x'] - a[1][key]['x']) * amount),
                 round(a[1][key]['y'] + (b[1][key]['y'] - a[1][key]['y']) * amount)) for key in ('p1', 'p2')]


