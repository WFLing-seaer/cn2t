from __future__ import annotations

from datetime import datetime
from typing import Literal


def tab(n, s):
    return "\n".join([f"{' ' * n}{ln}" for ln in str(s).split("\n")])


class Struct:
    body: Body | None = None
    meta: Meta | None = None
    datum: Datum | None = None

    def __init__(self, kwargs=None, value=None, raw=None):
        self._stopped = set()
        if kwargs is not None:
            self.add(**kwargs, value=value, raw=raw)

    def add(
        self,
        BODY: dict | Literal["N/A"] | None = None,
        META: dict | Literal["N/A"] | None = None,
        DATUM: dict | Literal["N/A"] | None = None,
        value=None,
        raw=None,
        STOP=None,
    ):
        if self._stopped is None:
            raise AttributeError("Add failed cuz it's already stopped")
        if BODY == "N/A":
            self.body = None
        elif BODY is not None:
            if self.body:
                self.body.add(**BODY, value=value, raw=raw)
            else:
                self.body = Body(BODY, value=value, raw=raw)
        if META == "N/A":
            self.meta = None
        elif META is not None:
            if self.meta:
                self.meta.add(**META)
            else:
                self.meta = Meta(META)
        if DATUM == "N/A":
            self.datum = None
        elif DATUM is not None:
            self.datum = Datum({k.lower(): v for k, v in DATUM.items()})
        if STOP is not None:
            self.stop(STOP)

    def check(
        self, BODY: dict | Literal["N/A"] | None = None, META: dict | Literal["N/A"] | None = None, DATUM: dict | Literal["N/A"] | None = None
    ):
        if BODY == "N/A":
            if self.body is not None:
                return False
        elif BODY is not None:
            if self.body is None:
                if set(BODY.values()) != {"N/A"}:
                    return False  # 如果values（一层检测子元素）都是N/A，那么“如果没有body那也一定没有子元素”而返回True。
            elif not (self.body.check(**BODY)):
                return False
        if META == "N/A":
            if self.meta is not None:
                return False
        elif META is not None:
            if self.meta is None:
                if set(META.values()) != {"N/A"}:
                    return False
            elif not (self.meta.check(**META)):
                return False
        if DATUM == "N/A":
            if self.datum is not None:
                return False
        elif DATUM is not None:
            if self.datum is None:
                if set(DATUM.values()) != {"N/A"}:
                    return False
            elif any(getattr(self.datum, k.lower(), object()) != (None if v == "N/A" else v) for k, v in DATUM.items()):
                return False
        return True

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
        return f"\nSTRUCT\n{tab(2, repr(self.body))}\n{tab(2, repr(self.meta))}\n{tab(2, repr(self.datum))}"


class Body(Struct):
    val: int | None = None
    desc: str | None = None
    mod: list[float | str] | None = None
    raw: str | None = None

    def add(
        self, VAL: int | Literal["N/A"] | None = None, DESC: str | None = None, MOD: float | str | None = None, value=None, raw=None, STOP=None
    ):
        if self._stopped is None:
            raise AttributeError("Add failed cuz it's already stopped")
        if VAL == "N/A":
            self.val = None
        elif VAL is not None:
            self.val = value if VAL == "@" and value is not None else VAL
        if DESC == "N/A":
            self.desc = None
        elif DESC is not None:
            self.desc = DESC
        if MOD == "N/A":
            self.mod = None
        elif MOD is not None:
            if self.mod is None:
                self.mod = []
            self.mod.append(MOD)
        if STOP is not None:
            self.stop(STOP)
        if raw is not None:
            self.raw = raw

    def check(self, VAL: int | list[int] | Literal["N/A"] | None = None, DESC: str | None = None, MOD: float | str | None = None, RAW=None):
        try:
            if RAW is not None and not (eval(RAW, {"raw": self.raw})):
                return False
            if VAL == "N/A" and self.val is not None:
                return False
            elif VAL is not None:
                if self.val is None:
                    return False
                elif isinstance(VAL, list):
                    if self.val < VAL[0] or self.val > VAL[1]:
                        return False
                elif self.val != VAL:
                    return False
            if DESC == "N/A":
                if self.desc is not None:
                    return False
            elif DESC is not None:
                if self.desc is None:
                    return False
                if self.desc != DESC:
                    return False
            if MOD == "N/A":
                if self.mod is not None:
                    return False
            elif MOD is not None:
                if self.mod is None:
                    return False
                if MOD not in self.mod:
                    return False
            return True
        except TypeError:
            return False

    def reset_stop(self):
        self._stopped = set()

    def __repr__(self):
        return f"BODY\n  VAL: {self.val}\n  DESC: {self.desc}\n  MOD: {self.mod}\n  RAW: {self.raw}"


class Meta(Struct):
    ID: str | None = None
    step: Step | None = None
    cycl: Cycl | None = None

    def add(
        self,
        ID: str | None = None,
        STEP: dict | Literal["N/A"] | None = None,
        CYCL: dict | Literal["N/A"] | None = None,
        value=None,
        raw=None,
        STOP=None,
    ):
        if self._stopped is None:
            raise AttributeError("Add failed cuz it's already stopped")
        if ID == "N/A":
            self.ID = None
        elif ID is not None:
            self.ID = ID
        if STEP == "N/A":
            self.step = None
        elif STEP is not None:
            if self.step:
                self.step.add(**STEP)
            else:
                self.step = Step(STEP)
        if CYCL == "N/A":
            self.cycl = None
        elif CYCL is not None:
            if self.cycl:
                self.cycl.add(**CYCL)
            else:
                self.cycl = Cycl(CYCL)
        if STOP is not None:
            self.stop(STOP)

    def check(self, ID: str | list[str] | None = None, STEP: dict | Literal["N/A"] | None = None, CYCL: dict | Literal["N/A"] | None = None):
        try:
            if ID == "N/A":
                if self.ID is not None:
                    return False
            elif ID is not None:
                if self.ID is None:
                    return False
                if isinstance(ID, list) and self.ID not in ID or not isinstance(ID, list) and self.ID != ID:
                    return False
            if STEP == "N/A":
                if self.step is not None:
                    return False
            elif STEP is not None:
                if self.step is None:
                    if set(STEP.values()) != {"N/A"}:
                        return False
                elif not (self.step.check(**STEP)):
                    return False
            if CYCL == "N/A":
                if self.cycl is not None:
                    return False
            elif CYCL is not None:
                if self.cycl is None:
                    if set(CYCL.values()) != {"N/A"}:
                        return False
                elif not (self.cycl.check(**CYCL)):
                    return False
            return True
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

    def add(self, PERC: str | None = None, AMP: float | Literal["N/A"] | None = None, value=None, raw=None, STOP=None):
        if self._stopped is None:
            raise AttributeError("Add failed cuz it's already stopped")
        if PERC == "N/A":
            self.perc = None
        elif PERC is not None:
            self.perc = PERC
        if AMP == "N/A":
            self.amp = None
        elif AMP is not None:
            self.amp = AMP
        if STOP is not None:
            self.stop(STOP)

    def check(self, PERC: str | list[str] | None = None, AMP: float | list[float] | Literal["N/A"] | None = None):
        try:
            if PERC == "N/A":
                if self.perc is not None:
                    return False
            elif PERC is not None:
                if self.perc is None:
                    return False
                if isinstance(PERC, list) and self.perc not in PERC or not isinstance(PERC, list) and self.perc != PERC:
                    return False
            if AMP == "N/A":
                if self.amp is not None:
                    return False
            elif AMP is not None:
                if self.amp is None:
                    return False
                if isinstance(AMP, list):
                    if self.amp < AMP[0] or self.amp > AMP[1]:
                        return False
                elif self.amp != AMP:
                    return False
            return True
        except TypeError:
            return False

    def reset_stop(self):
        self._stopped = set()

    def __repr__(self):
        return f"STEP\n  PERC: {self.perc}\n  AMP: {self.amp}"


class Cycl(Struct):
    period: float | None = None
    range: tuple[float, float] | None = None

    def add(
        self,
        PERIOD: float | Literal["N/A"] | None = None,
        RANGE: tuple[float, float] | Literal["N/A"] | None = None,
        value=None,
        raw=None,
        STOP=None,
    ):
        if self._stopped is None:
            raise AttributeError("Add failed cuz it's already stopped")
        if PERIOD == "N/A":
            self.period = None
        elif PERIOD is not None:
            self.period = PERIOD
        if RANGE == "N/A":
            self.range = None
        elif RANGE is not None:
            self.range = RANGE
        if STOP is not None:
            self.stop(STOP)

    def check(
        self,
        PERIOD: float | list[float] | Literal["N/A"] | None = None,
        RANGE: tuple[float, float] | list[float] | Literal["N/A"] | None = None,
    ):
        try:
            if PERIOD == "N/A":
                if self.period is not None:
                    return False
            elif PERIOD is not None:
                if self.period is None:
                    return False
                if isinstance(PERIOD, list):
                    if self.period < PERIOD[0] or self.period > PERIOD[1]:
                        return False
                elif self.period != PERIOD:
                    return False
            if RANGE == "N/A":
                if self.range is not None:
                    return False
            elif RANGE is not None:
                if self.range is None:
                    return False
                if isinstance(RANGE, list):
                    if self.range[0] < RANGE[0] or self.range[0] > RANGE[1] or self.range[1] < RANGE[2] or self.range[1] > RANGE[3]:
                        return False
                elif self.range != RANGE:
                    return False
            return True
        except TypeError:
            return False

    def reset_stop(self):
        self._stopped = set()

    def __repr__(self):
        return f"CYCL\n  PERIOD: {self.period}\n  RANGE: {self.range}"


class Datum:
    def __init__(self, datum: dict | datetime):
        if isinstance(datum, datetime):
            self.year = datum.year
            self.month = datum.month
            self.day = datum.day
            self.hour = datum.hour
            self.minute = datum.minute
            self.second = datum.second
        else:
            self.year: int | None = datum.get("year")
            self.month: int | None = datum.get("month")
            self.day: int | None = datum.get("day")
            self.hour: int | None = datum.get("hour")
            self.minute: int | None = datum.get("minute")
            self.second: int | None = datum.get("second")
            self.lunar: bool | None = datum.get("lunar")

    def get_from_id(self, ID: str, amp: float = 1):
        match ID, amp:
            case "CE", _:
                return self.year and self.year // 100
            case "YR", 10:
                return self.year and self.year // 10 * 10
            case "YR", _:
                return self.year
            case "MO", _:
                return self.month
            case "WK", _:
                return self.day and self.day / 7
            case "DA", _:
                return self.day
            case "HR", _:
                return self.hour
            case "MI", _:
                return self.minute
            case "SC", _:
                return self.second
            case _:
                raise KeyError(f"Unknown ID: {ID}")

    def update(self, other: Datum):
        if other.year is not None:
            self.year = other.year
        if other.month is not None:
            self.month = other.month
        if other.day is not None:
            self.day = other.day
        if other.hour is not None:
            self.hour = other.hour
        if other.minute is not None:
            self.minute = other.minute
        if other.second is not None:
            self.second = other.second
        if other.lunar is not None:
            self.lunar = other.lunar

    def __repr__(self):
        return (
            f"DATUM\n  {self.year or "NA"}-{self.month or "NA":02}-{self.day or "NA":02} "
            f"{"--" if self.hour is None else self.hour:02}:{"--" if self.minute is None else self.minute:02}:"
            f"{"--" if self.second is None else self.second:02}{"（农历）"*bool(self.lunar)}"
        )
