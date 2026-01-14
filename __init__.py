from __future__ import annotations

import contextlib
import datetime
import math
import os
import traceback
from collections import defaultdict
from typing import Any, Literal, cast

import cn2an
import cutword
import dateutil
import dateutil.parser
import yaml
from dateutil.relativedelta import relativedelta

from .classes import Datum, Struct

with open("R:/Python314/Lib/site-packages/cn2t/templates.yaml", encoding="utf-8") as f:
    templates = cast(dict, yaml.safe_load(f))
with open("R:/Python314/Lib/site-packages/cn2t/lexicon.yml", encoding="utf-8") as f:
    lexicon = cast(dict, yaml.safe_load(f))
keywords = lexicon.keys()
path_kwd_temp = "Z:/cn2t_kwd.txt" or os.path.expandvars("%temp%/cn2t_kwd.txt")
with open(path_kwd_temp, "w", encoding="utf-8") as f:
    CUTWORD_EXCLUDE = {"_NUM", ".", " "}
    f.write("\n".join(keyword + "\t1\tN" for keyword in keywords if keyword not in CUTWORD_EXCLUDE))
cutter = cutword.Cutter(dict_name=path_kwd_temp)


def to_num(s: str) -> int | None:
    try:
        return int(s)
    except ValueError:
        try:
            return int(cn2an.cn2an(s, mode="smart"))
        except ValueError:
            return None


def run_merge_num(cut: list[str]) -> list[str]:
    result = []
    last_is_num = False
    for word in cut:
        if to_num(word) is None:
            last_is_num = False
            result.append(word)
        elif last_is_num:
            result[-1] += word
        else:
            last_is_num = True
            result.append(word)
    return result


def add_tag(seq: list[str]) -> list[tuple[dict, int | str, str | None]]:
    result = []
    for word in seq:
        if word in lexicon:
            if lexicon[word] is not None:
                result.append((lexicon[word], word, None))
            continue
        num = to_num(word)
        if num is None:
            raise NameError(f"Unknown word: {word}")
        result.append((lexicon.get("_NUM"), num, word))
    return result


def first_parser(tagged: list[tuple[dict, int | str, str | None]]) -> list[Struct]:
    structs: list[Struct] = []
    this = Struct()
    for tag, value, raw in tagged:
        as_word = tag.get("AS_WORD")
        if not as_word:
            continue
        if isinstance(expand := as_word.get("EXPAND"), list) and len(expand) >= 1:
            expand_structs: list[dict] = [expanding.get("STRUCT", {}) for expanding in expand]
            for expand_struct in expand_structs:
                if this.body is not None or this.meta is not None or this.datum is not None:
                    structs.append(this)
                this = Struct(expand_struct)
            continue
        try:
            this.add(**as_word, value=value, raw=raw)
        except AttributeError:
            if this.body is not None or this.meta is not None or this.datum is not None:
                structs.append(this)
            this = Struct(as_word, value=value, raw=raw)
    if this.body is not None or this.meta is not None:
        structs.append(this)
    return structs


def second_parser(structs: list[Struct | Any]) -> list[Struct]:
    for struct in structs:
        struct.reset_stop()
    for struct in structs:
        if struct.body is not None and struct.body.desc is not None:
            desc = struct.body.desc
            entry = lexicon.get(desc)
            if entry and "AS_STRUCT" in entry:
                as_struct = entry["AS_STRUCT"]
                struct.add(**as_struct)
    stopped_templates = []
    for name, template in templates.items():
        if name in stopped_templates:
            continue
        when_list = template.get("WHEN", [])
        then_list = template.get("THEN", [])
        stop_list = template.get("STOP", [])
        match_len = len(when_list)
        assert len(then_list) == match_len
        idx_offset = 0
        for start_idx in range(len(structs) - match_len + 1):
            for i in range(match_len):
                condition = when_list[i]
                if not structs[start_idx + i + idx_offset].check(**condition.get("STRUCT") or {}):
                    break
            else:
                stopped_templates.extend(stop_list)
                for i in range(match_len):
                    rule = then_list[i]
                    if (struct_expanded := rule.get("EXPAND")) is not None:
                        structs_expanded = [expanding.get("STRUCT", {}) for expanding in struct_expanded]
                        if not structs_expanded:
                            structs[start_idx + i + idx_offset] = None
                            idx_offset -= 1
                        elif len(structs_expanded) == 1:
                            structs[start_idx + i + idx_offset].add(**structs_expanded[0])
                        else:
                            struct_pack = [structs[start_idx + i]] + [Struct()] * (len(structs_expanded) - 1)
                            for pack_item in struct_pack:
                                pack_item.add(**structs_expanded.pop(0))
                            structs[start_idx + i + idx_offset : start_idx + i + idx_offset + 1] = struct_pack
                            idx_offset += len(struct_pack) - 1
                        continue
                    if struct_rule := rule.get("STRUCT"):
                        structs[start_idx + i + idx_offset].add(**struct_rule)
    return structs


def third_parser(
    structs: list[Struct], base: datetime.datetime | None = None, instant_merge: bool = False
) -> tuple[list[Struct], relativedelta | None]:
    datum = Datum(base or datetime.datetime.now())
    field_map = {"CE": "CE", "YR": "years", "MO": "months", "WK": "WK", "DA": "days", "HR": "hours", "MI": "minutes", "SC": "seconds"}
    mod_fields = defaultdict(int)
    for struct in structs:
        if struct.datum is not None:
            datum.update(struct.datum)
        if struct.body is None or struct.body.mod is None:
            continue
        datum_this = None
        if struct.meta is not None and struct.meta.ID is not None:
            datum_this = datum.get_from_id(struct.meta.ID)
        val = struct.body.val
        if val is None and datum_this is not None:
            val = datum_this
        if val is None:
            continue
        tmp_val = val
        for mod in struct.body.mod:
            if isinstance(mod, str):
                tmp_val = eval(
                    mod,
                    {
                        "val": tmp_val,
                        "datum": datum_this,
                        "Cdatum": datum,
                        "datetime": datetime,
                        "math": math,
                        "struct": struct,
                    },
                )
            else:
                tmp_val += mod
        if not instant_merge and struct.meta is not None and struct.meta.ID is not None:
            key = field_map[struct.meta.ID]
            if key == "WK":
                mod_fields["days"] += int((tmp_val - val) * 7)
            else:
                mod_fields[key] += int(tmp_val - val)
        else:
            val = tmp_val
        struct.body.val = int(val)
    if "CE" in mod_fields:
        mod_fields["years"] = mod_fields.get("years", 0) + mod_fields["CE"] * 100
        del mod_fields["CE"]
    modifier = None if instant_merge else relativedelta(**mod_fields)  # type: ignore
    return structs, modifier


def to_datetime(
    structs: list[Struct], modifier: relativedelta | None = None, now: datetime.datetime | None = None
) -> tuple[datetime.datetime, datetime.datetime]:
    field_map: dict[str, Literal["CE", "years", "months", "WK", "days", "hours", "minutes", "seconds"]] = {
        "CE": "CE",
        "YR": "years",
        "MO": "months",
        "WK": "WK",
        "DA": "days",
        "HR": "hours",
        "MI": "minutes",
        "SC": "seconds",
    }
    perc_level = {"CE": 0, "YR": 1, "MO": 2, "WK": 3, "DA": 4, "HR": 5, "MI": 6, "SC": 7}
    # 别问为什么这有一大坨Literal，问就是不写的话类型检查不给过
    fields: dict[Literal["CE", "years", "months", "WK", "days", "hours", "minutes", "seconds"], int] = {
        field_map[struct.meta.ID]: struct.body.val
        for struct in structs
        if struct.meta is not None
        and struct.meta.ID is not None
        and struct.meta.ID in field_map
        and struct.body is not None
        and struct.body.val is not None
    }
    step = ("CE", 0)
    for struct in structs:
        if struct.meta is None or struct.meta.step is None or struct.meta.step.amp is None or struct.meta.step.perc is None:
            continue
        if perc_level.get(struct.meta.step.perc, 0) > perc_level[step[0]] or (
            perc_level.get(struct.meta.step.perc, 0) == perc_level[step[0]] and struct.meta.step.amp < step[1]
        ):
            step = (struct.meta.step.perc, struct.meta.step.amp)
    now = now or datetime.datetime.now()
    for must in ("YR", "MO", "DA"):
        if field_map[must] not in fields:
            fields[field_map[must]] = getattr(now, field_map[must].removesuffix("s")) if perc_level[must] < perc_level[step[0]] else 1
    step = (field_map[step[0]], step[1])
    if "CE" in fields:
        fields["years"] = fields.get("years", 0) + fields["CE"] * 100
        del fields["CE"]
    if "WK" in fields:
        fields["days"] = fields["WK"] * 7
        del fields["WK"]
    if step[0] == "CE":
        step = ("years", step[1] * 100)
    elif step[0] == "WK":
        step = ("days", step[1])  # 不乘7
    dt = datetime.datetime(1,1,1,0,0,0,0) + relativedelta(**fields) - relativedelta(years=1,months=1,days=1)
    if modifier is not None:
        dt += modifier

    if any(struct.datum and struct.datum.lunar for struct in structs):
        try:
            from lunarcalendar import Converter, DateNotExist, Lunar
        except ImportError:
            raise ImportError("lunarcalendar模块未安装，无法处理农历时间")

        try:
            solar = Converter.Lunar2Solar(Lunar(year=dt.year, month=abs(dt.month), day=dt.day, isleap=dt.month < 0))  # 负数表示闰月
            dt = datetime.datetime(solar.year, solar.month, solar.day, dt.hour, dt.minute, dt.second)
        except DateNotExist as e:
            raise ValueError("无效的农历时间") from e

    try:
        rel_delta = relativedelta(**{step[0]: int(step[1])})  # type: ignore
        edt = dt - relativedelta(seconds=1) + rel_delta
    except OverflowError:
        edt = dt
    return (dt, edt)


def full_parse(text: str, enable_dateutil_trial=False) -> tuple[datetime.datetime, datetime.datetime] | Literal[-1, -2, -3, -4] | None:
    if enable_dateutil_trial:
        with contextlib.suppress(dateutil.parser.ParserError, OverflowError, AssertionError):
            du = dateutil.parser.parse(text, ignoretz=True, fuzzy=True)
            assert isinstance(du, datetime.datetime)
            return (du, du)
    try:
        return to_datetime(*third_parser(second_parser(first_parser(add_tag(run_merge_num(cutter.cutword(text)))))))
    except ValueError:
        return -1
    except NameError:
        return -2
    except OverflowError:
        return -3
    except ImportError:
        return -4
    except Exception:
        traceback.print_exc()
        return None
