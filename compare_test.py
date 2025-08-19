import datetime
import time
import timeit

import dateparser
import jionlp

from main import full_parse

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
        "2023年10月1日",
        "2024-05-20",
        "2025年元旦",
        "2022/12/31 18:30",
        "2026年农历正月初一",
        "今天",
        "明天下午3点",
        "大后天晚上",
        "昨天上午9点",
        "上周三",
        "下个月5号",
        "明年春节",
        "3天后",
        "两周前",
        "1小时30分钟后",
    ]

    PERC = (1, "μs")  # 取消注释这行，把下一行注释掉，就是跑1k次，时间能更准点
    # PERC = (1000, "ms")

    trial, ts = PERC

    print("测试时间:", datetime.datetime.now())
    for testing in testings:
        print("=" * 48)
        print(testing)
        cn2t_result = full_parse(testing)
        perf = timeit.timeit(lambda: full_parse(testing), number=1000 // trial)
        if cn2t_result is None:
            print("cn2t:\t\t", f"{perf*1e3:>8.1f}{ts}\t", "<解析错误>")
        elif cn2t_result == -1:
            print("cn2t:\t\t", f"{perf*1e3:>8.1f}{ts}\t", "<无效时间>")
        elif cn2t_result == -2:
            print("cn2t:\t\t", f"{perf*1e3:>8.1f}{ts}\t", "<解析失败>")
        elif cn2t_result == -3:
            print("cn2t:\t\t", f"{perf*1e3:>8.1f}{ts}\t", "<时间溢出>")
        elif cn2t_result == -4:
            print("cn2t:\t\t", f"{perf*1e3:>8.1f}{ts}\t", "<缺农历库>")
        else:
            print(
                "cn2t:\t\t",
                f"{perf*1e3:>8.1f}{ts}\t",
                cn2t_result[0].strftime("%Y-%m-%d %H:%M:%S"),
                "~",
                cn2t_result[1].strftime("%Y-%m-%d %H:%M:%S"),
            )

        def run_jionlp(testing):
            try:
                jionlp_result = jionlp.parse_time(testing, time_base=time.time()).get("time") or ("<解析失败>", "")
                assert isinstance(jionlp_result, list) and isinstance(jionlp_result[0], str)
            except AssertionError:
                jionlp_result = ("<非时间段>", "")
            except Exception:
                jionlp_result = ("<解析失败>", "")
            return jionlp_result

        jionlp_result = run_jionlp(testing)
        perf = timeit.timeit(lambda: run_jionlp(testing), number=1000 // trial)
        print("jionlp:\t\t", f"{perf*1e3:>8.1f}{ts}\t", jionlp_result[0], "~" if jionlp_result[1] else "", jionlp_result[1])

        dateparser_result = dateparser.parse(testing, languages=["zh"]) or "<解析失败>"
        perf = timeit.timeit(lambda: dateparser.parse(testing, languages=["zh"]), number=1000 // trial)
        print("dateparser:\t", f"{perf*1e3:>8.1f}{ts}\t", dateparser_result)
        print()
