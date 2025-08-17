from __future__ import annotations

import datetime
import math
import os
from typing import Literal, cast

import cn2an
import cutword
import dateparser
import yaml
from dateutil.relativedelta import relativedelta

from classes import Datum, Struct

with open("templates.yaml", encoding="utf-8") as f:
    templates = cast(dict, yaml.safe_load(f))
with open("lexicon.yml", encoding="utf-8") as f:
    lexicon = cast(dict, yaml.safe_load(f))
keywords = lexicon.keys()
path_kwd_temp = os.path.expandvars("%temp%/cn2t_kwd.txt")
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


def add_tag(seq: list[str]) -> list[tuple[dict, int | str]]:
    result = []
    for word in seq:
        if word in lexicon:
            if lexicon[word] is not None:
                result.append((lexicon[word], word))
            continue
        num = to_num(word)
        if num is not None:
            result.append((lexicon.get("_NUM"), num))
        else:
            raise ValueError(f"Unknown word: {word}")
    return result


def first_parser(tagged: list[tuple[dict, int | str]]) -> list[Struct]:
    structs: list[Struct] = []
    this = Struct()
    for tag, value in tagged:
        try:
            as_word = tag.get("AS_WORD")

            if not as_word:
                continue
            this.add(**as_word, value=value)
        except AttributeError:

            if this.body is not None:
                structs.append(this)
            this = Struct(as_word, value=value)
    if this.body is not None:
        structs.append(this)

    return structs


def second_parser(structs: list[Struct]) -> list[Struct]:
    for struct in structs:
        struct.reset_stop()

    for struct in structs:
        if struct.body is not None and struct.body.desc is not None:
            desc = struct.body.desc
            entry = lexicon.get(desc)
            if entry and "AS_STRUCT" in entry:
                as_struct = entry["AS_STRUCT"]
                struct.add(**as_struct)

    for template in templates.values():
        when_list = template.get("WHEN", [])
        then_list = template.get("THEN", [])
        match_len = len(when_list)
        assert len(then_list) == match_len

        for start_idx in range(len(structs) - match_len + 1):
            for i in range(match_len):
                condition = when_list[i]
                if not structs[start_idx + i].check(**condition.get("STRUCT") or {}):
                    break
            else:
                for i in range(match_len):
                    rule = then_list[i]
                    if struct_rule := rule.get("STRUCT"):
                        structs[start_idx + i].add(**struct_rule)
    return structs


def third_parser(structs: list[Struct], instant_merge: bool = False) -> tuple[list[Struct], relativedelta | None]:
    datum = Datum(datetime.datetime.now())
    field_map = {"CE": "CE", "YR": "years", "MO": "months", "DA": "days", "HR": "hours", "MI": "minutes", "SC": "seconds"}

    mod_fields = {}

    for struct in structs:
        if struct.datum is not None:
            datum.update(struct.datum)
        if struct.body is not None and struct.body.mod is not None:
            datum_this = None
            if struct.meta is not None and struct.meta.ID is not None:
                datum_this = datum.get_from_id(struct.meta.ID)
            val = struct.body.val
            if val is None:
                if datum_this is None:
                    continue
                val = datum_this

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
                    mod_fields[field_map[struct.meta.ID]] = tmp_val - val
                else:
                    val = tmp_val
            struct.body.val = int(val)

    if "CE" in mod_fields:
        mod_fields["years"] = mod_fields.get("years", 0) + mod_fields["CE"] * 100
        del mod_fields["CE"]

    modifier = None if instant_merge else relativedelta(**mod_fields)

    return structs, modifier


def to_datetime(structs: list[Struct], modifier: relativedelta | None = None) -> tuple[datetime.datetime, datetime.datetime]:
    field_map: dict[str, Literal["CE", "year", "month", "day", "hour", "minute", "second"]] = {
        "CE": "CE",
        "YR": "year",
        "MO": "month",
        "DA": "day",
        "HR": "hour",
        "MI": "minute",
        "SC": "second",
    }
    perc_level = {"CE": -1, "YR": 0, "MO": 1, "DA": 2, "HR": 3, "MI": 4, "SC": 5}
    # 别问为什么这有一大坨Literal，问就是不写的话类型检查不给过
    fields: dict[Literal["CE", "year", "month", "day", "hour", "minute", "second"], int] = {
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
        if perc_level.get(struct.meta.step.perc, 0) > perc_level[step[0]]:
            step = (struct.meta.step.perc, struct.meta.step.amp)

    now = datetime.datetime.now()

    for must in ("YR", "MO", "DA"):
        if field_map[must] not in fields:
            fields[field_map[must]] = getattr(now, field_map[must]) if perc_level[must] < perc_level[step[0]] else 1

    step = (field_map[step[0]], step[1])

    if "CE" in fields:
        fields["year"] = fields.get("year", 0) + fields["CE"] * 100
        del fields["CE"]

    if step[0] == "CE":
        step = ("year", step[1] * 100)

    dt = datetime.datetime(**fields)

    if modifier is not None:
        dt += modifier

    try:
        rel_delta = relativedelta(**{f"{step[0]}s": int(step[1])})
        edt = dt + rel_delta
    except OverflowError:
        edt = dt

    return (dt, edt)


def full_parse(text: str) -> tuple[datetime.datetime, datetime.datetime] | None:
    try:
        return to_datetime(*third_parser(second_parser(first_parser(add_tag(run_merge_num(cutter.cutword(text)))))))
    except Exception:
        return None


if __name__ == "__main__":
    testings = [
        "2025年8月15日",
        "贰零贰伍年捌月拾伍日",
        "二〇二五年八月十五日",
        "2025/08/15",
        "2025年8月16日 14:30:45",
        "2025-08-16 18:15:00",
        "2025/08/16 23:59:59",
        "二〇二五年八月十六日 下午三点半",
        "二零二五年八月十六号 中午12点整",
        "二五年8月16日 午夜12点",
        "2025年8月16日 上午9时15分",
        "2025-08-16 下午11:08",
        "8月16日 凌晨3:20",
        "8月16日 14:00",
        "十二月三十一日 18:00",
        "02月15日 09:30:00",
        "16号晚上8点",
        "01日 15:30",
        "31日下午4点半",
        "下午4点",
        "上午10:15",
        "23:45:30",
        "今天",
        "明天凌晨",
        "昨天中午",
        "三天后",
        "两周前",
        "下个月5号",
        "下周二",
        "上周三上午10点",
        "公历2025年8月16日",
        "2025年8月",
        "8月",
        "2025/8/16 PM 3:45",
        "0001年1月1日",
        "9999年12月31日 23:59:59",
        "2024年2月29日",
        "2025年13月1日",
        "2025年2月30日",
        "昨天25点",
        "2025年农历八月十六",
        "无效时间格式",
        "2025年8月32日",
        "嘉靖十五年",
    ]

    for testing in testings:
        print("=" * 24)
        print(testing)
        if dt := full_parse(testing):
            print("cn2t:\t\t", dt[0].strftime("%Y-%m-%d %H:%M:%S"), "~", dt[1].strftime("%Y-%m-%d %H:%M:%S"))
        else:
            print("cn2t:\t\t", "<解析失败>")
        print("dateparser:\t", dateparser.parse(testing, languages=["zh"]) or "<解析失败>")
