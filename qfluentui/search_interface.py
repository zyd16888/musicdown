from typing import List

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QFrame, QHBoxLayout, QHeaderView, QVBoxLayout, QTableWidgetItem
from qfluentwidgets import (
    BodyLabel, CheckBox, ComboBox, FluentIcon as FIF, LineEdit,
    PrimaryPushButton, PushButton, SearchLineEdit, SpinBox, TableWidget,
    ToolButton
)


class SearchInterface(QFrame):
    """ Search interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('SearchInterface')

        self.v_layout = QVBoxLayout(self)
        self.search_bar_layout = QHBoxLayout()

        self.search_type_combo = ComboBox(self)
        self.search_input = SearchLineEdit(self)
        self.limit_spinbox = SpinBox(self)
        self.search_button = PrimaryPushButton('搜索', self)

        self.result_table = TableWidget(self)

        # --- Bottom Controls ---
        self.bottom_layout = QHBoxLayout()
        self.select_all_checkbox = CheckBox("全选", self)
        self.invert_selection_button = PushButton("反选", self)
        self.batch_download_button = PrimaryPushButton("批量下载选中歌曲", self)

        self.prev_page_button = ToolButton(FIF.LEFT_ARROW, self)
        self.page_label = BodyLabel("第 1 页", self)
        self.next_page_button = ToolButton(FIF.RIGHT_ARROW, self)

        self.__init_widgets()
        self.__connect_signals()

    def __init_widgets(self):
        self.v_layout.setContentsMargins(36, 20, 36, 20)
        self.v_layout.setSpacing(10)

        # Search bar
        self.search_type_combo.addItems(["单曲", "专辑", "歌单"])
        self.search_input.setPlaceholderText("输入关键词搜索...")
        self.search_input.setClearButtonEnabled(True)
        self.limit_spinbox.setRange(1, 100)
        self.limit_spinbox.setValue(20)
        self.search_bar_layout.addWidget(self.search_type_combo)
        self.search_bar_layout.addWidget(self.search_input, 1)
        self.search_bar_layout.addWidget(self.limit_spinbox)
        self.search_bar_layout.addWidget(self.search_button)
        self.search_bar_layout.setSpacing(15)

        # Result table
        self.result_table.setWordWrap(False)
        self.result_table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.setup_for_song_results() # Default setup

        # Bottom controls layout
        self.bottom_layout.addWidget(self.select_all_checkbox)
        self.bottom_layout.addWidget(self.invert_selection_button)
        self.bottom_layout.addSpacing(10)
        self.bottom_layout.addWidget(self.batch_download_button)
        self.bottom_layout.addStretch(1)
        self.bottom_layout.addWidget(self.prev_page_button)
        self.bottom_layout.addWidget(self.page_label)
        self.bottom_layout.addWidget(self.next_page_button)

        # Main layout
        self.v_layout.addLayout(self.search_bar_layout)
        self.v_layout.addSpacing(10)
        self.v_layout.addWidget(self.result_table)
        self.v_layout.addLayout(self.bottom_layout)

        self.show_bottom_controls(False)

    def __connect_signals(self):
        self.result_table.cellChanged.connect(self._on_cell_changed)
        self.invert_selection_button.clicked.connect(self._invert_selection)
        self.select_all_checkbox.stateChanged.connect(self._on_select_all_changed)

    def setup_for_song_results(self):
        self.result_table.setColumnCount(6)
        self.result_table.setHorizontalHeaderLabels(['', '标题', '歌手', '专辑', '时长', '操作'])
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.result_table.horizontalHeader().resizeSection(0, 40)
        self.result_table.horizontalHeader().resizeSection(4, 100)
        self.result_table.horizontalHeader().resizeSection(5, 120)

    def setup_for_album_results(self):
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(['专辑名', '歌手', '发行时间', '操作'])
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.result_table.horizontalHeader().resizeSection(3, 120)

    def setup_for_playlist_results(self):
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(['歌单名', '创建者', '歌曲数', '操作'])
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.result_table.horizontalHeader().resizeSection(3, 120)

    def update_page_display(self, page: int, has_next: bool, has_prev: bool):
        self.page_label.setText(f"第 {page} 页")
        self.prev_page_button.setEnabled(has_prev)
        self.next_page_button.setEnabled(has_next)

    def show_bottom_controls(self, show: bool, is_song_search: bool = True):
        self.select_all_checkbox.setVisible(show and is_song_search)
        self.invert_selection_button.setVisible(show and is_song_search)
        self.prev_page_button.setVisible(show)
        self.page_label.setVisible(show)
        self.next_page_button.setVisible(show)
        if not show:
            self.batch_download_button.hide()

    @Slot(int, int)
    def _on_cell_changed(self, row, column):
        if column == 0:
            is_any_checked = len(self.get_checked_rows()) > 0
            self.batch_download_button.setVisible(is_any_checked)
            self.select_all_checkbox.stateChanged.disconnect(self._on_select_all_changed)
            if not is_any_checked:
                self.select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
            elif len(self.get_checked_rows()) == self.result_table.rowCount():
                self.select_all_checkbox.setCheckState(Qt.CheckState.Checked)
            else:
                self.select_all_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
            self.select_all_checkbox.stateChanged.connect(self._on_select_all_changed)

    @Slot(int)
    def _on_select_all_changed(self, state_int: int):
        state = Qt.CheckState(state_int)
        if state == Qt.CheckState.PartiallyChecked:
            return
        self.result_table.cellChanged.disconnect(self._on_cell_changed)
        for i in range(self.result_table.rowCount()):
            item = self.result_table.item(i, 0)
            if item:
                item.setCheckState(state)
        self.result_table.cellChanged.connect(self._on_cell_changed)
        is_any_checked = (state == Qt.CheckState.Checked and self.result_table.rowCount() > 0)
        self.batch_download_button.setVisible(is_any_checked)

    def _invert_selection(self):
        self.result_table.cellChanged.disconnect(self._on_cell_changed)
        for i in range(self.result_table.rowCount()):
            item = self.result_table.item(i, 0)
            if not item:
                continue
            current_state = item.checkState()
            new_state = Qt.CheckState.Unchecked if current_state == Qt.CheckState.Checked else Qt.CheckState.Checked
            item.setCheckState(new_state)
        self.result_table.cellChanged.connect(self._on_cell_changed)
        is_any_checked = len(self.get_checked_rows()) > 0
        self.batch_download_button.setVisible(is_any_checked)
        self._on_cell_changed(0, 0)

    def get_checked_rows(self) -> List[int]:
        checked_rows = []
        for i in range(self.result_table.rowCount()):
            item = self.result_table.item(i, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                checked_rows.append(i)
        return checked_rows
