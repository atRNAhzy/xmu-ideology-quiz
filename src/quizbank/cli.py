from __future__ import annotations

import argparse
import random
from typing import Optional

from .question_bank import QuestionBank, QuestionSelection
from .utils import answers_match, normalize_answers


def print_question(selection: QuestionSelection) -> None:
    print("")
    if selection.remaining_count is not None:
        print(f"当前剩余题目数量：{selection.remaining_count}")
    print(selection.prompt)
    if selection.options:
        print(selection.options)


def ask_for_answer() -> Optional[str]:
    try:
        return input("请输入答案(输入 q 退出)：")
    except EOFError:
        return None


def run_cli(args: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="交互式题库答题工具")
    parser.add_argument("excel", help="题库 Excel 文件路径")
    parser.add_argument("--max-correct", type=int, default=5, help="达到该次数后不再抽取该题")
    parser.add_argument("--seed", type=int, help="随机种子，方便重现测试")
    ns = parser.parse_args(args)

    rng = random.Random(ns.seed) if ns.seed is not None else random.Random()
    bank = QuestionBank(ns.excel, max_correct=ns.max_correct)

    while True:
        selection = bank.select_question(rng)
        if selection is None:
            print("所有题目都已完成既定次数，恭喜！")
            break

        print_question(selection)
        raw_answer = ask_for_answer()
        if raw_answer is None:
            print("检测到输入结束，终止答题。")
            break
        raw_answer = raw_answer.strip()
        if raw_answer.lower() in {"q", "quit", "exit"}:
            print("用户选择退出，已保存当前进度。")
            break

        user_letters = normalize_answers(raw_answer)
        if not user_letters:
            print("无效输入，请输入合法的选项(如 1、12、AB)。")
            continue

        if answers_match(user_letters, selection.answer):
            bank.record_correct(selection)
            print("回答正确！")
            new_count = bank.data.at[selection.index, bank.correct_column]
            print(f"当前题目正确次数：{new_count}")
            if new_count >= bank.max_correct:
                print("恭喜！该题已达到设定的正确次数阈值。")
        else:
            print(f"回答错误！正确答案是：{selection.answer}")
            current = bank.data.at[selection.index, bank.correct_column]
            print(f"当前题目正确次数：{current}")

        bank.save()


if __name__ == "__main__":
    run_cli()
