from __future__ import annotations

from datetime import datetime
from typing import Literal


def tab(n, s):
    return "\n".join([f"{' ' * n}{ln}" for ln in str(s).split("\n")])


class Struct:
    body: Body | None = None
    meta: Meta | None = None

    def __init__(self, kwargs=None, value=None):
        self._stopped = set()
        if kwargs is not None:
            self.add(**kwargs, value=value)

    def add(self, BODY: dict | None = None, META: dict | None = None, value=None, STOP=None):

        if self._stopped is None:
            raise AttributeError("Add failed cuz it's already stopped")
        if BODY is not None:
            if self.body:
                self.body.add(**BODY, value=value)
            else:
                self.body = Body(BODY, value=value)
        if META is not None:
            if self.meta:
                self.meta.add(**META)
            else:
                self.meta = Meta(META)
        if STOP is not None:
            self.stop(STOP)

    def check(self, BODY: dict | Literal["N/A"] | None = None, META: dict | Literal["N/A"] | None = None):
        result = True
        if BODY == "N/A":
            return self.body is None
        elif BODY is not None:
            if self.body is None:
                return False
            result &= self.body.check(**BODY)
        if META == "N/A":
            return self.meta is None
        elif META is not None:
            if self.meta is None:
                return False
            result &= self.meta.check(**META)
        return result

    def stop(self, feat):

        if self._stopped is None:
            raise AttributeError("Cannot stop cuz it's already stopped")
        if isinstance(feat, list):
            self._stopped |= set(feat)
        elif feat == "ALL":
            self._stopped = None
        else:
            self._stopped.add(feat)

    def reset_stop(self):
        self._stopped = set()
        if self.body is not None:
            self.body.reset_stop()
        if self.meta is not None:
            self.meta.reset_stop()

    def __setattr__(self, name, value):

        if name == "_stopped":
            self.__dict__[name] = value
        elif (self._stopped is None) or (name.upper() in self._stopped):
            raise AttributeError(f"Cannot set {name}")
        else:
            self.__dict__[name] = value

    def __repr__(self):
        return f"\nSTRUCT\n{tab(2, repr(self.body))}\n{tab(2, repr(self.meta))}"


class Body(Struct):
    val: int | None = None
    desc: str | None = None
    mod: list[float | str] | None = None

    def add(self, VAL: int | None = None, DESC: str | None = None, MOD: float | str | None = None, value=None, STOP=None):

        if self._stopped is None:
            raise AttributeError("Add failed cuz it's already stopped")
        if VAL is not None:
            self.val = value if VAL == "@" and value is not None else VAL
        if DESC is not None:
            self.desc = DESC
        if MOD is not None:
            if self.mod is None:
                self.mod = []
            self.mod.append(MOD)
        if STOP is not None:
            self.stop(STOP)

    def check(self, VAL: int | list[int] | Literal["N/A"] | None = None, DESC: str | None = None):
        try:
            result = True
            if VAL == "N/A":
                return self.val is None
            elif VAL is not None:
                if self.val is None:
                    return False
                if isinstance(VAL, list):
                    result &= self.val >= VAL[0] and self.val <= VAL[1]
                else:
                    result &= self.val == VAL
            if DESC == "N/A":
                return self.desc is None
            elif DESC is not None:
                if self.desc is None:
                    return False
                result &= self.desc == DESC
            return result
        except TypeError:
            return False

    def reset_stop(self):
        self._stopped = set()

    def __repr__(self):
        return f"BODY\n  VAL: {self.val}\n  DESC: {self.desc}"


class Meta(Struct):
    ID: str | None = None
    step: Step | None = None
    cycl: Cycl | None = None

    def add(self, ID: str | None = None, STEP: dict | None = None, CYCL: dict | None = None, value=None, STOP=None):

        if self._stopped is None:
            raise AttributeError("Add failed cuz it's already stopped")
        if ID is not None:
            self.ID = ID
        if STEP is not None:
            if self.step:
                self.step.add(**STEP)
            else:
                self.step = Step(STEP)
        if CYCL is not None:
            if self.cycl:
                self.cycl.add(**CYCL)
            else:
                self.cycl = Cycl(CYCL)
        if STOP is not None:
            self.stop(STOP)

    def check(self, ID: str | list[str] | None = None, STEP: dict | Literal["N/A"] | None = None, CYCL: dict | Literal["N/A"] | None = None):
        try:
            result = True
            if ID == "N/A":
                return self.ID is None
            elif ID is not None:
                if self.ID is None:
                    return False
                if isinstance(ID, list):
                    result &= self.ID in ID
                else:
                    result &= self.ID == ID
            if STEP == "N/A":
                return self.step is None
            elif STEP is not None:
                if self.step is None:
                    return False
                result &= self.step.check(**STEP)
            if CYCL == "N/A":
                return self.cycl is None
            elif CYCL is not None:
                if self.cycl is None:
                    return False
                result &= self.cycl.check(**CYCL)
            return result
        except TypeError:
            return False

    def reset_stop(self):
        self._stopped = set()
        if self.step is not None:
            self.step.reset_stop()
        if self.cycl is not None:
            self.cycl.reset_stop()

    def __repr__(self):
        return f"META\n  ID: {self.ID}\n{tab(2, repr(self.step))}\n{tab(2, repr(self.cycl))}"


class Step(Struct):
    perc: str | None = None
    amp: float | None = None

    def add(self, PERC: str | None = None, AMP: float | None = None, value=None, STOP=None):

        if self._stopped is None:
            raise AttributeError("Add failed cuz it's already stopped")
        if PERC is not None:
            self.perc = PERC
        if AMP is not None:
            self.amp = AMP
        if STOP is not None:
            self.stop(STOP)

    def check(self, PERC: str | list[str] | None = None, AMP: float | list[float] | Literal["N/A"] | None = None):
        try:
            result = True
            if PERC == "N/A":
                return self.perc is None
            elif PERC is not None:
                if self.perc is None:
                    return False
                if isinstance(PERC, list):
                    result &= self.perc in PERC
                else:
                    result &= self.perc == PERC
            if AMP == "N/A":
                return self.amp is None
            elif AMP is not None:
                if self.amp is None:
                    return False
                if isinstance(AMP, list):
                    result &= self.amp >= AMP[0] and self.amp <= AMP[1]
                else:
                    result &= self.amp == AMP
            return result
        except TypeError:
            return False

    def reset_stop(self):
        self._stopped = set()

    def __repr__(self):
        return f"STEP\n  PERC: {self.perc}\n  AMP: {self.amp}"


class Cycl(Struct):
    period: float | None = None
    range: tuple[float, float] | None = None

    def add(self, PERIOD: float | None = None, RANGE: tuple[float, float] | None = None, value=None, STOP=None):

        if self._stopped is None:
            raise AttributeError("Add failed cuz it's already stopped")
        if PERIOD is not None:
            self.period = PERIOD
        if RANGE is not None:
            self.range = RANGE
        if STOP is not None:
            self.stop(STOP)

    def check(
        self,
        PERIOD: float | list[float] | Literal["N/A"] | None = None,
        RANGE: tuple[float, float] | list[float] | Literal["N/A"] | None = None,
    ):
        try:
            result = True
            if PERIOD == "N/A":
                return self.period is None
            elif PERIOD is not None:
                if self.period is None:
                    return False
                if isinstance(PERIOD, list):
                    result &= self.period >= PERIOD[0] and self.period <= PERIOD[1]
                else:
                    result &= self.period == PERIOD
            if RANGE == "N/A":
                return self.range is None
            elif RANGE is not None:
                if self.range is None:
                    return False
                if isinstance(RANGE, list):
                    result &= (
                        self.range[0] >= RANGE[0] and self.range[0] <= RANGE[1] and self.range[1] >= RANGE[2] and self.range[1] <= RANGE[3]
                    )
                else:
                    result &= self.range == RANGE
            return result
        except TypeError:
            return False

    def reset_stop(self):
        self._stopped = set()

    def __repr__(self):
        return f"CYCL\n  PERIOD: {self.period}\n  RANGE: {self.range}"


class Datum:
    def __init__(self, datum: datetime):
        self.datum = datum

    def get_from_id(self, ID: str, amp: float = 1):
        match ID, amp:
            case "CE", _:
                return self.datum.year // 100
            case "YR", 10:
                return self.datum.year // 10 * 10
            case "YR", _:
                return self.datum.year
            case "MO", _:
                return self.datum.month
            case "DA", _:
                return self.datum.day
            case "HR", _:
                return self.datum.hour
            case "MI", _:
                return self.datum.minute
            case "SC", _:
                return self.datum.second
            case _:
                raise ValueError(f"Unknown ID: {ID}")

    def __repr__(self):
        return f"DATUM\n  {self.datum.year}-{self.datum.month:02d}-{self.datum.day:02d} {self.datum.hour:02d}:{self.datum.minute:02d}:{self.datum.second:02d}"
