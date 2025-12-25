from __future__ import annotations

import random
import sys
from pathlib import Path

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIntValidator
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .question_bank import QuestionBank, QuestionSelection
from .utils import answers_match, normalize_answers, parse_options_text

DEFAULT_WINDOW_SIZE = QSize(1024, 640)
DEFAULT_FONT_POINT_SIZE = 13
BASE_LOGICAL_DPI = 96.0


class QuizWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("题库练习")
        base_font = QFont(self.font())
        base_font.setPointSize(DEFAULT_FONT_POINT_SIZE)
        self.setFont(base_font)
        self.resize(DEFAULT_WINDOW_SIZE)
        self._base_size = QSize(DEFAULT_WINDOW_SIZE)

        self.app_root = self._resolve_app_root()
        self.quiz_dir = self.app_root / "题库"
        self.bank: QuestionBank | None = None
        self.current_selection: QuestionSelection | None = None
        self.current_recorded = False
        self.awaiting_next = False
        self.rng = random.Random()
        self.current_bank_path: Path | None = None
        self.threshold_value = 5

        self._build_ui()
        self._load_available_banks()

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setSpacing(12)

        # 文件选择
        file_row = QHBoxLayout()
        self.bank_label = QLabel("题库：")
        file_row.addWidget(self.bank_label)
        self.bank_combo = QComboBox()
        self.bank_combo.currentIndexChanged.connect(self.handle_bank_selected)
        file_row.addWidget(self.bank_combo, 1)
        self.file_label = QLabel("未选择文件")
        self.file_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.file_label.setStyleSheet("color: #666666;")
        file_row.addWidget(self.file_label, 1)

        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)
        self.threshold_input = QLineEdit()
        self.threshold_input.setFixedWidth(80)
        self.threshold_input.setPlaceholderText("目标次数")
        self.threshold_input.setValidator(QIntValidator(1, 999))
        self.threshold_input.returnPressed.connect(self.apply_threshold)
        self.threshold_label = QLabel("阈值：")
        controls_row.addWidget(self.threshold_label)
        controls_row.addWidget(self.threshold_input)

        self.reset_button = QPushButton("重置进度")
        self.reset_button.setEnabled(False)
        self.reset_button.clicked.connect(self.reset_progress)
        controls_row.addWidget(self.reset_button)
        controls_row.addStretch(1)

        layout.addLayout(file_row)
        layout.addLayout(controls_row)

        # 题目信息
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setSpacing(10)

        self.question_label = QLabel("")
        self.question_label.setWordWrap(True)
        self.question_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.scroll_layout.addWidget(self.question_label)

        self.options_box = QGroupBox("选项")
        self.options_layout = QVBoxLayout(self.options_box)
        self.options_layout.setSpacing(6)
        self.scroll_layout.addWidget(self.options_box)
        self.scroll_layout.addStretch(1)

        self.scroll_area.setWidget(scroll_content)
        layout.addWidget(self.scroll_area, 1)

        self.correct_answer_label = QLabel("")
        self.correct_answer_label.setWordWrap(True)
        self.correct_answer_label.setStyleSheet("color: #1a73e8; font-weight: bold;")
        layout.addWidget(self.correct_answer_label)

        # 终端风格输入
        self.answer_input = QLineEdit()
        self.answer_input.setPlaceholderText("输入选项数字 (如 13) 后按回车提交")
        self.answer_input.returnPressed.connect(self.handle_input_return)
        layout.addWidget(self.answer_input)

        # 操作按钮
        button_row = QHBoxLayout()
        self.submit_button = QPushButton("提交答案")
        self.submit_button.clicked.connect(self.submit_answer)
        self.submit_button.setEnabled(False)
        self.next_button = QPushButton("下一题")
        self.next_button.clicked.connect(self.load_next_question)
        self.next_button.setEnabled(False)
        button_row.addWidget(self.submit_button)
        button_row.addWidget(self.next_button)
        layout.addLayout(button_row)

        self.feedback_label = QLabel("请先打开题库文件。")
        self.feedback_label.setWordWrap(True)
        layout.addWidget(self.feedback_label)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.setCentralWidget(central)

        self.option_checkboxes: dict[str, QCheckBox] = {}
        self.correct_answer_label.setText("正确答案：")
        self.threshold_input.setText(str(self.threshold_value))
        self._cache_base_fonts()
        self._apply_scaled_fonts()

    def _resolve_app_root(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parents[2]

    def _load_available_banks(self) -> None:
        self.current_bank_path = None
        self.bank_combo.blockSignals(True)
        self.bank_combo.clear()

        excel_files = []
        if self.quiz_dir.exists() and self.quiz_dir.is_dir():
            excel_files = sorted(
                [p for p in self.quiz_dir.glob("*.xls*") if p.is_file()],
                key=lambda p: p.name.lower(),
            )

        if not excel_files:
            self.bank_combo.addItem("未找到题库", None)
            self.bank_combo.setEnabled(False)
            self.feedback_label.setText("未找到题库目录或无可用题库文件。")
            self.answer_input.setPlaceholderText("请先准备题库文件")
            self.file_label.setText("未选择文件")
        else:
            self.bank_combo.addItem("请选择题库", None)
            for path in excel_files:
                self.bank_combo.addItem(path.stem, path)
            self.bank_combo.setEnabled(True)
            self.feedback_label.setText("请选择题库开始练习。")
            self.answer_input.setPlaceholderText("请选择题库开始练习")
            self.file_label.setText("未选择文件")

        self.answer_input.setEnabled(bool(excel_files))
        self.reset_button.setEnabled(False)
        self.threshold_input.setEnabled(bool(excel_files))
        self.next_button.setEnabled(False)
        self.submit_button.setEnabled(False)
        self.awaiting_next = False
        self.current_selection = None
        self.option_checkboxes.clear()
        self._clear_options()
        self.question_label.setText("")
        self.correct_answer_label.setText("正确答案：")
        self.status_label.setText("")

        self.bank_combo.blockSignals(False)
        self._apply_scaled_fonts()

    def handle_bank_selected(self, index: int) -> None:
        data = self.bank_combo.itemData(index)
        if not isinstance(data, Path):
            return
        if self.bank is not None and self.current_bank_path and data == self.current_bank_path:
            return
        self._load_bank(data)

    def _load_bank(self, file_path: Path) -> None:
        if not file_path.exists():
            QMessageBox.warning(self, "提示", f"题库文件不存在：{file_path}")
            self.reset_button.setEnabled(False)
            return
        threshold = self._sync_threshold_from_input()
        try:
            self.bank = QuestionBank(file_path, max_correct=threshold)
        except Exception as exc:  # pylint: disable=broad-except
            QMessageBox.critical(self, "加载失败", f"无法打开题库：{exc}")
            self.bank = None
            self.file_label.setText("未选择文件")
            self.reset_button.setEnabled(False)
            return

        self.current_bank_path = file_path
        self.file_label.setText(str(file_path))
        self.feedback_label.setText("题库加载成功，正在抽取题目……")
        self.status_label.setText("")
        self.current_selection = None
        self.current_recorded = False
        self.option_checkboxes.clear()
        self._clear_options()
        self.question_label.setText("")
        self.correct_answer_label.setText("正确答案：")
        self.next_button.setEnabled(True)
        self.submit_button.setEnabled(False)
        self.answer_input.clear()
        self.answer_input.setEnabled(True)
        self.awaiting_next = False
        self.reset_button.setEnabled(True)
        self.threshold_input.setText(str(self.bank.max_correct))
        self.load_next_question()
        self._apply_scaled_fonts()

    def load_next_question(self) -> None:
        if self.bank is None:
            QMessageBox.information(self, "提示", "请先选择题库。")
            return
        selection = self.bank.select_question(self.rng)
        if selection is None:
            self.current_selection = None
            self._clear_options()
            self.question_label.setText("")
            self.feedback_label.setText("所有题目均已达到设定的正确次数！")
            self.status_label.setText("")
            self.submit_button.setEnabled(False)
            self.answer_input.clear()
            self.answer_input.setPlaceholderText("所有题目已完成。")
            self.correct_answer_label.setText("正确答案：")
            self.awaiting_next = False
            return
        self.current_selection = selection
        self.current_recorded = False
        self._render_question()
        self.submit_button.setEnabled(True)
        self.feedback_label.setText("勾选选项或输入数字后提交。")
        self._refresh_status()
        self.awaiting_next = False
        self.answer_input.clear()
        self.answer_input.setPlaceholderText("输入选项数字 (如 13) 后按回车提交")
        self.answer_input.setFocus()
        self.correct_answer_label.setText("正确答案：")

    def _render_question(self) -> None:
        if not self.current_selection:
            return
        self.question_label.setText(self.current_selection.prompt)
        _, options = parse_options_text(self.current_selection.options)
        self._populate_options(options)
        self._apply_scaled_fonts()

    def _populate_options(self, options: list[tuple[str, str]]) -> None:
        self._clear_options()
        if not options:
            notice = QLabel("此题没有提供选项，请在题干中查看。")
            self.options_layout.addWidget(notice)
            self.option_checkboxes = {}
            self.options_layout.addStretch(1)
            return
        self.option_checkboxes = {}
        for letter, text in options:
            checkbox = QCheckBox(f"{letter}. {text}")
            checkbox.setProperty("letter", letter)
            self.options_layout.addWidget(checkbox)
            self.option_checkboxes[letter] = checkbox
        self.options_layout.addStretch(1)
        self._apply_scaled_fonts()

    def _clear_options(self) -> None:
        while self.options_layout.count():
            item = self.options_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def submit_answer(self) -> None:
        letters = self._collect_checked_letters()
        if letters is not None:
            self._handle_submission(letters)

    def _refresh_status(self) -> None:
        if self.bank is None or self.current_selection is None:
            self.status_label.setText("")
            return
        current_correct = self.bank.data.at[self.current_selection.index, self.bank.correct_column]
        remaining_total = len(self.bank.remaining_questions())
        self.status_label.setText(
            f"当前题目正确次数：{current_correct} | 剩余未完成题目：{remaining_total}"
        )

    def _prepare_for_next_input(self) -> None:
        self.awaiting_next = True
        self.answer_input.clear()
        self.answer_input.setPlaceholderText("按回车进入下一题，或输入重新作答")
        self.answer_input.setFocus()

    def _mark_correct_answers(self, expected_letters: list[str]) -> None:
        if not self.option_checkboxes:
            return
        for letter, checkbox in self.option_checkboxes.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(letter in expected_letters)
            checkbox.blockSignals(False)

    def _collect_checked_letters(self) -> list[str] | None:
        if self.bank is None or self.current_selection is None:
            QMessageBox.information(self, "提示", "请先选择题库。")
            return None
        if not self.option_checkboxes:
            QMessageBox.information(self, "提示", "该题无选项，请在题干中查阅答案。")
            return None
        chosen = [letter for letter, checkbox in self.option_checkboxes.items() if checkbox.isChecked()]
        if not chosen:
            QMessageBox.information(self, "提示", "请至少选择一个选项。")
            return None
        return chosen

    def _handle_submission(self, user_letters: list[str]) -> None:
        if self.bank is None or self.current_selection is None:
            QMessageBox.information(self, "提示", "请先选择题库。")
            return

        is_correct = answers_match(user_letters, self.current_selection.answer)
        expected_letters = normalize_answers(self.current_selection.answer)
        correct_text = "".join(expected_letters) if expected_letters else self.current_selection.answer

        if is_correct:
            if not self.current_recorded:
                self.bank.record_correct(self.current_selection)
                self.bank.save()
                self.current_recorded = True
            updated = self.bank.data.at[self.current_selection.index, self.bank.correct_column]
            self.feedback_label.setText(f"回答正确！当前题目正确次数：{updated}")
            if updated >= self.bank.max_correct:
                self.feedback_label.setText(
                    self.feedback_label.text() + " 已达到阈值，可以切换下一题。"
                )
        else:
            self.feedback_label.setText(f"回答错误，正确答案是：{correct_text}")
        display_letters = " ".join(expected_letters) if expected_letters else correct_text
        self.correct_answer_label.setText(f"正确答案：{display_letters}")
        self._mark_correct_answers(expected_letters)
        self._refresh_status()
        self._prepare_for_next_input()

    def apply_threshold(self) -> None:
        value = self._sync_threshold_from_input()
        if self.bank is not None:
            self.bank.max_correct = value
            if self.current_selection is not None:
                current_count = self.bank.data.at[self.current_selection.index, self.bank.correct_column]
                if current_count >= value:
                    self.feedback_label.setText(
                        f"目标正确次数已更新为 {value} 次，当前题目已达标，已切换下一题。"
                    )
                    self.awaiting_next = False
                    self.load_next_question()
                    return
            self.feedback_label.setText(f"目标正确次数已更新为 {value} 次。")
            self._refresh_status()

    def reset_progress(self) -> None:
        if self.bank is None:
            QMessageBox.information(self, "提示", "请先选择题库。")
            return
        confirm = QMessageBox.question(
            self,
            "确认重置",
            "确定要将当前题库的正确次数全部清零吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        self.bank.data.loc[:, self.bank.correct_column] = 0
        self.bank.save()
        self.bank.reload()
        self.feedback_label.setText("已重置正确次数。")
        self.current_recorded = False
        self.awaiting_next = False
        self.load_next_question()

    def _sync_threshold_from_input(self) -> int:
        text = self.threshold_input.text().strip()
        if text.isdigit():
            value = max(1, int(text))
        else:
            value = self.threshold_value
            self.threshold_input.setText(str(value))
        self.threshold_value = value
        return value

    def handle_input_return(self) -> None:
        if self.bank is None:
            QMessageBox.information(self, "提示", "请先选择题库。")
            return

        text = self.answer_input.text().strip()

        if self.awaiting_next and text == "":
            self.load_next_question()
            return

        if self.current_selection is None:
            QMessageBox.information(self, "提示", "请先选择题库。")
            self.answer_input.clear()
            return

        if not text:
            self.feedback_label.setText("请输入选项数字后按回车提交。")
            return

        letters = normalize_answers(text)
        if not letters:
            self.feedback_label.setText("输入无效，请输入选项数字（如 13）。")
            self.answer_input.selectAll()
            return

        for letter, checkbox in self.option_checkboxes.items():
            checkbox.setChecked(letter in letters)

        self._handle_submission(letters)

    def resizeEvent(self, event) -> None:  # pylint: disable=invalid-name
        super().resizeEvent(event)
        self._apply_scaled_fonts()

    def _cache_base_fonts(self) -> None:
        self._base_fonts = {
            "question": self.question_label.font(),
            "option": self.font(),
            "input": self.answer_input.font(),
            "label": self.feedback_label.font(),
            "button": self.submit_button.font(),
            "combo": self.bank_combo.font(),
            "group": self.options_box.font(),
            "correct_label": self.correct_answer_label.font(),
        }

    def _apply_scaled_fonts(self) -> None:
        if not hasattr(self, "_base_fonts"):
            return

        factor = self._current_scale_factor()

        question_font = self._scaled_font("question", 14.0, factor)
        self.question_label.setFont(question_font)

        option_font = self._scaled_font("option", 12.0, factor)
        for checkbox in self.option_checkboxes.values():
            checkbox.setFont(option_font)
        for index in range(self.options_layout.count()):
            widget = self.options_layout.itemAt(index).widget()
            if isinstance(widget, QLabel):
                widget.setFont(option_font)

        group_font = self._scaled_font("group", 12.0, factor)
        self.options_box.setFont(group_font)

        label_font = self._scaled_font("label", 12.0, factor)
        for widget in (
            self.feedback_label,
            self.status_label,
            self.file_label,
            self.bank_label,
            self.threshold_label,
        ):
            widget.setFont(label_font)

        correct_label_font = self._scaled_font("correct_label", 12.0, factor)
        self.correct_answer_label.setFont(correct_label_font)

        input_font = self._scaled_font("input", 12.0, factor)
        self.answer_input.setFont(input_font)
        self.threshold_input.setFont(input_font)

        combo_font = self._scaled_font("combo", 12.0, factor)
        self.bank_combo.setFont(combo_font)
        combo_view = self.bank_combo.view()
        if combo_view is not None:
            combo_view.setFont(combo_font)

        button_font = self._scaled_font("button", 12.0, factor)
        for button in (self.submit_button, self.next_button, self.reset_button):
            button.setFont(button_font)

    def _scaled_font(self, key: str, minimum: float, factor: float) -> QFont:
        base_font = getattr(self, "_base_fonts", {}).get(key)
        if base_font is None:
            base_font = self.font()
        font = QFont(base_font)
        base_size = font.pointSizeF()
        if base_size <= 0:
            base_size = float(font.pointSize())
        if base_size <= 0:
            base_size = minimum
        font.setPointSizeF(max(minimum, base_size * factor))
        return font

    def _current_scale_factor(self) -> float:
        if self._base_size.width() <= 0 or self._base_size.height() <= 0:
            return 1.0

        width_factor = self.width() / float(self._base_size.width())
        height_factor = self.height() / float(self._base_size.height())
        size_factor = max(1.0, width_factor, height_factor)

        dpi_ratio = self._current_dpi_ratio()
        if dpi_ratio <= 0:
            dpi_ratio = 1.0

        return max(1.0, size_factor / dpi_ratio)

    def _current_dpi_ratio(self) -> float:
        screen = None
        handle = self.windowHandle()
        if handle is not None:
            screen = handle.screen()
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return 1.0
        return screen.logicalDotsPerInch() / BASE_LOGICAL_DPI


def run_gui() -> None:
    app = QApplication(sys.argv)
    window = QuizWindow()
    window.show()
    app.exec_()


if __name__ == "__main__":
    run_gui()
