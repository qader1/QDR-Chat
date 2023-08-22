import json

from PyQt6.QtWidgets import (QApplication,
                             QPushButton,
                             QVBoxLayout,
                             QWidget,
                             QScrollArea,
                             QHBoxLayout,
                             QListWidget,
                             QTextEdit,
                             QListWidgetItem,
                             QMenu,
                             QSizePolicy,
                             QLineEdit,
                             QLabel,
                             QGridLayout,
                             QDialog,
                             QSpinBox)

from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, pyqtSignal, QObject, QRect, QPropertyAnimation
from PyQt6.QtGui import QColor, QIcon, QFont, QPixmap, QPainter
from python_syntax_highlighting import PythonHighlighter
import pywinstyles
import re
import csv
import os


class ChatWidget(QWidget):
    def __init__(self, message_size, code_size, input_size):
        super().__init__()
        self.chat_container = QVBoxLayout()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.chat_container.setContentsMargins(0, 0, 0, 0)
        self.chat_container.setSpacing(0)
        self.setLayout(self.chat_container)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.robot = QSvgWidget('icons/robot.svg')
        self.setObjectName("robot")
        self.robot.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.robot.renderer().setViewBox(QRect(0, 0, 245, 440))
        self.robot.setHidden(True)

        self.system_message_widget = SystemMessageWidget()
        self.message_display_widget = MessageDisplayWidget(message_size, code_size)
        self.input_widget = InputWidget(input_size)

        self.scroll = ScrollableMessageDisplay(self.message_display_widget)

        self.chat_container.addWidget(self.system_message_widget, 1)
        self.chat_container.addWidget(self.scroll, 13)
        self.chat_container.addWidget(self.robot, Qt.AlignmentFlag.AlignCenter)
        self.chat_container.addWidget(self.input_widget, 1)

    def display_messages(self, messages):
        for i in messages:
            self.message_display_widget.add_message(i['message'], i['role'])
        QTimer.singleShot(5, self.scroll_to_bottom)
        self.input_widget.text_edit.setText('')

    def scroll_to_bottom(self):
        x = self.scroll.verticalScrollBar()
        self.scroll.verticalScrollBar().setValue(x.maximum())

    def clear(self):
        while self.message_display_widget.container.count():
            child = self.message_display_widget.container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def set_system_message(self, text):
        self.system_message_widget.system_message.setText(text)

    def about(self, show):
        self.robot.setHidden(not show)
        self.message_display_widget.setHidden(show)
        self.message_display_widget.container.setAlignment(Qt.AlignmentFlag.AlignBottom)
        self.system_message_widget.setHidden(show)

    def toggle_loading_indicator(self):
        if self.input_widget.loading_indicator.isActive():
            self.input_widget.send_button.setHidden(False)
            self.input_widget.text_edit.setDisabled(False)
            self.input_widget.text_edit.setPlaceholderText("Send a message")
            self.input_widget.loading_indicator.stop()
        else:
            self.input_widget.send_button.setHidden(True)
            self.input_widget.text_edit.setDisabled(True)
            self.input_widget.text_edit.setPlaceholderText("Please wait.")
            self.input_widget.loading_indicator.start()

    def set_font_size(self, message_size, code_size, input_size):
        self.message_display_widget.message_size = message_size
        self.message_display_widget.code_size = code_size
        self.input_widget.change_input_size(input_size)


class Signal(QObject):
    SystemMessageChanged = pyqtSignal(str)
    FontSizesChanged = pyqtSignal(int, int, int)


class SystemMessageWidget(QWidget):
    def __init__(self):
        super().__init__()
        system_message_layout = QHBoxLayout()
        self.setLayout(system_message_layout)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        label = QLabel("System Prompt")
        label.setObjectName("system_prompt")
        label.setContentsMargins(10, 0, 10, 0)

        label.setFixedHeight(25)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.system_message = QLineEdit()
        self.system_message.setObjectName("system_message")
        self.system_message.setEnabled(False)
        self.system_message.setContentsMargins(0, 0, 10, 0)

        self.system_message.setFont(QFont('serif', 8, 400, True))
        self.system_message.setFixedHeight(25)
        self.system_message.setText("You are a helpful assistant")

        self.edit = ColorableButtonIcon('icons/edit.svg',
                                        "grey",
                                        "silver",
                                        None)
        self.edit.setObjectName("edit")

        self.confirm = QPushButton()
        self.confirm.setObjectName("system_message_confirm")
        self.confirm.setIcon(QIcon("icons/confirm.svg"))

        self.cancel = QPushButton()
        self.cancel.setObjectName("system_message_cancel")
        self.cancel.setIcon(QIcon("icons/cancel.svg"))

        self.confirm.setHidden(True)
        self.cancel.setHidden(True)

        self.edit.clicked.connect(self.edit_slot)
        self.confirm.clicked.connect(self.confirm_slot)
        self.cancel.clicked.connect(self.cancel_slot)

        system_message_layout.addWidget(label, 3)
        system_message_layout.addWidget(self.system_message, 20)
        system_message_layout.addWidget(self.edit)
        system_message_layout.addWidget(self.confirm)
        system_message_layout.addWidget(self.cancel)
        system_message_layout.setSpacing(0)

        self.signal = Signal()
        self.original_system_text = None

    @pyqtSlot()
    def edit_slot(self):
        self.original_system_text = self.system_message.text()
        self.toggle_buttons()
        self.system_message.setFocus()
        self.system_message.setCursorPosition(len(self.system_message.text()))

    @pyqtSlot()
    def confirm_slot(self):
        self.toggle_buttons()
        self.signal.SystemMessageChanged.emit(self.system_message.text())
        self.system_message.setCursorPosition(0)

    @pyqtSlot()
    def cancel_slot(self):
        self.toggle_buttons()
        self.system_message.setText(self.original_system_text)
        self.system_message.setCursorPosition(0)

    def toggle_buttons(self):
        self.system_message.setEnabled(not self.system_message.isEnabled())
        self.edit.setHidden(not self.edit.isHidden())
        self.confirm.setHidden(not self.confirm.isHidden())
        self.cancel.setHidden(not self.cancel.isHidden())
        font = self.system_message.font()
        font.setItalic(not self.system_message.font().italic())
        self.system_message.setFont(font)


class ColorableButtonIcon(QPushButton):
    def __init__(self, icon_path, color, hover_color, pressed_color):
        super().__init__()
        self.color = color
        self.hover_color = hover_color
        self.pressed_color = pressed_color
        self.icon_path = icon_path
        self.setIcon(self.icon_from_svg(color))

    def icon_from_svg(self, color):
        img = QPixmap(self.icon_path)
        qp = QPainter(img)
        qp.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        qp.fillRect(img.rect(), QColor(color))
        qp.end()
        return QIcon(img)

    def enterEvent(self, event):
        if self.hover_color is not None:
            self.setIcon(self.icon_from_svg(self.hover_color))
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self.color is not None:
            self.setIcon(self.icon_from_svg(self.color))
        super().leaveEvent(event)

    def mousePressEvent(self, e) -> None:
        if self.pressed_color is not None:
            self.setIcon(self.icon_from_svg(self.pressed_color))
        return super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        if self.hover_color is not None:
            self.setIcon(self.icon_from_svg(self.hover_color))
        return super().mouseReleaseEvent(e)


class LeftWidget(QWidget):
    def __init__(self, message_size, code_size, input_size):
        super().__init__()
        self.history_container = QGridLayout()
        self.history_container.setContentsMargins(0, 0, 0, 0)
        self.history_container.setSpacing(0)
        self.setLayout(self.history_container)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.history_list = CustomQListWidget()
        self.new_chat_btn = QPushButton('New chat')
        self.new_chat_btn.setObjectName("new_chat_btn")

        self.burger = QPushButton(icon=QIcon("icons/burger.svg"))
        self.burger.setObjectName("burger")

        self.menu = QMenu(self.burger)
        self.menu.setObjectName("burger_menu")

        self.burger.setMenu(self.menu)

        menu_options = [
            "API Key",
            "Font size",
            "About",
            "Close"
        ]

        self.create_menu(menu_options, self.menu)
        self.menu.setWindowFlags(Qt.WindowType.Popup |
                                 Qt.WindowType.FramelessWindowHint |
                                 Qt.WindowType.NoDropShadowWindowHint)
        self.menu.triggered.connect(self.triggered)

        self.menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.message_size, self.code_size, self.input_size = message_size, code_size, input_size
        self.size_dialog = SizeDialog()

        self.history_container.addWidget(self.burger, 1, 1, 1, 1)
        self.history_container.addWidget(self.new_chat_btn, 1, 2, 1, 3)
        self.history_container.addWidget(self.history_list, 2, 1, 10, 4)

    def add(self, title):
        new_item = QListWidgetItem(title)
        new_item.setIcon(QIcon('icons/message.svg'))
        self.history_list.insertItem(0, new_item)
        self.history_list.setCurrentItem(new_item)

    def create_menu(self, data, menu):
        if isinstance(data, dict):
            for k, v in data.items():
                sub_menu = QMenu(k, menu)
                sub_menu.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                                        Qt.WindowType.NoDropShadowWindowHint |
                                        Qt.WindowType.Popup)
                sub_menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                menu.addMenu(sub_menu)
                self.create_menu(v, sub_menu)
        elif isinstance(data, list):
            for i in data:
                self.create_menu(i, menu)
        else:
            action = menu.addAction(data)
            if isinstance(data, str):
                action.setIconVisibleInMenu(False)

    def triggered(self, item):
        if item.text() == 'Close':
            self.window().close()
        elif item.text() == 'API Key':
            ApiDialog().exec()
        elif item.text() == 'Font size':
            self.size_dialog.get_currents_exec(self.message_size, self.code_size, self.input_size)
        else:
            AboutDialog().exec()

    def set_current_font_size(self, message_size, code_size, input_size):
        self.message_size = message_size
        self.code_size = code_size
        self.input_size = input_size


class Dialog(QDialog):
    def __init__(self):
        super().__init__()
        self.container = QGridLayout()
        self.setLayout(self.container)
        self.container.setSpacing(25)
        self.container.setContentsMargins(20, 20, 20, 20)
        self.setWindowIcon(QIcon("icons/main_window.svg"))

    def exec(self) -> int:
        pywinstyles.change_header_color(self, color="#202123")
        pywinstyles.change_border_color(self, color="#515473")
        return super().exec()


class SizeDialog(Dialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("set font sizes")
        label_code = QLabel("Code font size")
        label_message = QLabel("Message font size")
        label_input = QLabel("Input font size")

        (self.original_message_size,
         self.original_code_size,
         self.original_input_size) = None, None, None

        self.code_spin = QSpinBox()
        self.message_spin = QSpinBox()
        self.input_spin = QSpinBox()

        self.cancel_btn = QPushButton("Cancel")
        self.confirm_btn = QPushButton("Confirm")

        self.container.addWidget(label_message, 1, 1, 1, 3)
        self.container.addWidget(self.message_spin, 1, 4, 1, 2)
        self.container.addWidget(label_code, 2, 1, 1, 3)
        self.container.addWidget(self.code_spin, 2, 4, 1, 2)
        self.container.addWidget(label_input, 3, 1, 1, 3)
        self.container.addWidget(self.input_spin, 3, 4, 1, 2)

        self.container.addWidget(self.cancel_btn, 4, 2, 1, 1)
        self.container.addWidget(self.confirm_btn, 4, 4, 1, 1)

        self.setFixedSize(self.sizeHint())

        self.cancel_btn.clicked.connect(self.cancel)
        self.confirm_btn.clicked.connect(self.confirm)

        self.signal = Signal()

    def cancel(self):
        self.close()
        
    def confirm(self):
        message = self.message_spin.value()
        code = self.code_spin.value()
        input_ = self.input_spin.value()

        if (message == self.original_message_size
                and code == self.original_code_size
                and input_ == self.original_input_size):
            self.cancel()
            return
        self.signal.FontSizesChanged.emit(message, code, input_)
        self.close()

    def get_currents_exec(self, message_size, code_size, input_size):
        self.original_message_size = message_size
        self.original_code_size = code_size
        self.original_input_size = input_size
        self.message_spin.setValue(message_size)
        self.code_spin.setValue(code_size)
        self.input_spin.setValue(input_size)
        return super().exec()
        
        
class AboutDialog(Dialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("by QDR")
        label = QLabel("<p>If you liked the App, "
                       "<a href=\"https://github.com/qader1/GPT-GUI\">I'd appreciate a star on the Repo.</a> "
                       "Enjoy!</p>"
                       "\nby Qdr")
        label.setOpenExternalLinks(True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        button = QPushButton("Ok")
        button.clicked.connect(self.close)
        self.container.addWidget(label, 1, 1, 1, 5)
        self.container.addWidget(button, 2, 3, 1, 1)
        self.setFixedSize(self.sizeHint())


class ErrorDialog(Dialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("API Error")
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.button = QPushButton("Ok")
        self.button.clicked.connect(self.close)
        self.container.addWidget(self.label, 1, 1, 3, 3)
        self.container.addWidget(self.button, 4, 2, 1, 1)

    def message(self, message):
        if message == "Incorrect API key":
            self.label.setText(
                "<b>Either no or incorrect API key provided</b></br>"
                "<p>Set the key in the options menu in the top right corner.</p>"
            )
        else:
            self.label.setText("<b>Unspecified API Error</b>"
                               f"<p>{message}</p>")
        self.setFixedSize(self.sizeHint())
        return self.exec()


class ApiDialog(Dialog):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setWindowTitle("API Key")
        self.label = QLabel("<b>Enter API key</b>")
        self.field = QLineEdit()
        with open("key.json") as f:
            api_key = json.load(f)['api_key']
        self.field.setText(api_key)

        self.cancel_btn = QPushButton("Cancel")
        self.confirm_btn = QPushButton("Confirm")

        self.cancel_btn.clicked.connect(self.close)
        self.confirm_btn.clicked.connect(self.confirm)

        self.container.addWidget(self.label, 1, 3, 1, 1, Qt.AlignmentFlag.AlignCenter)
        self.container.addWidget(self.field, 2, 1, 1, 5)
        self.container.addWidget(self.cancel_btn, 3, 2)
        self.container.addWidget(self.confirm_btn, 3, 4)
        self.setFixedSize(self.sizeHint())

    def confirm(self):
        with open('key.json', 'r') as f:
            file = json.load(f)
        file['api_key'] = self.field.text()
        with open('key.json', 'w') as f:
            json.dump(file, f)
        self.close()


class InputWidget(QWidget):
    def __init__(self, input_size):
        super().__init__()
        input_widget_box = QHBoxLayout()
        self.setLayout(input_widget_box)
        self.text_edit = InputText(input_size)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.send_button = ColorableButtonIcon('icons/send.svg',
                                               'grey',
                                               'silver',
                                               None)

        self.send_button.setObjectName("send_btn")
        input_widget_box.addWidget(self.text_edit, 50)
        input_widget_box.addWidget(self.send_button,
                                   1,
                                   Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignRight)

        self.loading_indicator = QTimer()
        self.loading_indicator.setInterval(200)
        self.loading_indicator.timeout.connect(self.loading_indicator_callback)

    def loading_indicator_callback(self):
        place_holder = self.text_edit.placeholderText()
        if len(place_holder) > 15:
            place_holder = place_holder.strip(".")
        self.text_edit.setPlaceholderText(
             place_holder + '.'
        )

    def change_input_size(self, size):
        font = QFont()
        font.setPointSize(size)
        self.text_edit.setFont(font)
        self.text_edit.auto_resize()


class CustomQListWidget(QListWidget):
    def __init__(self):
        super().__init__()

        self.menu = QMenu(self)
        self.menu.setObjectName("delete_menu")
        self.menu.setWindowFlags(Qt.WindowType.Popup |
                                 Qt.WindowType.FramelessWindowHint |
                                 Qt.WindowType.NoDropShadowWindowHint)
        self.menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        delete_action = self.menu.addAction(QIcon('icons/delete.svg'), "Delete")
        delete_action.triggered.connect(self.delete_action)

    def contextMenuEvent(self, event) -> None:
        item = self.itemAt(event.pos())
        if item is not None:
            self.menu.exec(event.globalPos())

    def delete_action(self):
        idx = self.selectedIndexes()[0].row()
        self.takeItem(idx)
        with open('history/history.csv', 'r') as f:
            rows = list(csv.reader(f))
            id_ = rows.pop(idx)[0]
        os.remove(f'history/{id_}.chs')
        with open('history/history.csv', 'w') as f:
            f.write(''.join([','.join(x)+'\n' for x in rows]))
        self.menu.close()
        self.window().new_session()


class ScrollableMessageDisplay(QScrollArea):
    def __init__(self, widget):
        super().__init__()
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setWidget(widget)
        self.setWidgetResizable(True)


class MessageDisplayWidget(QWidget):
    def __init__(self, message_size, code_size):
        super().__init__()
        self.container = QVBoxLayout()
        self.container.setSpacing(0)
        self.container.addStretch(0)
        self.container.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.container)

        self.message_size = message_size
        self.code_size = code_size

    def add_message(self, message, role):
        if role == 'assistant':
            pattern = re.compile(r"(^```python.*?```$)", flags=re.DOTALL | re.MULTILINE)
            for match in pattern.split(message):
                match = match.strip()
                if not match:
                    continue
                if match.startswith("```python") and match.endswith("```"):
                    self.container.addWidget(Code(match[10:-3], self.code_size))
                else:
                    self.container.addWidget(Message(match.strip(), role, self.message_size))
        else:
            self.container.addWidget(Message(message, role, self.message_size))
        self.container.setAlignment(Qt.AlignmentFlag.AlignBottom)


class ResizableQText(QTextEdit):
    def __init__(self):
        super().__init__()

    def auto_resize(self):
        self.document().setTextWidth(self.viewport().width())
        margins = self.contentsMargins()
        height = int(self.document().size().height() + margins.top() + margins.bottom())
        self.setFixedHeight(height)

    def resizeEvent(self, event):
        self.auto_resize()


class InputText(ResizableQText):
    def __init__(self, size):
        super().__init__()
        font = QFont()
        font.setPointSize(size)
        self.setFont(font)
        self.setPlaceholderText('Send a message')
        self.textChanged.connect(self.auto_resize)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setObjectName("input_text")
        self.setAcceptRichText(False)

    def keyPressEvent(self, e):
        key = e.key()
        modifier = QApplication.keyboardModifiers()
        if modifier != Qt.KeyboardModifier.ShiftModifier:
            if key == Qt.Key.Key_Enter or key == Qt.Key.Key_Return:
                if self.toPlainText().strip() != '':
                    self.window().send()
                QTimer.singleShot(5, lambda: self.setText(''))

        return super().keyPressEvent(e)

    def auto_resize(self):
        self.document().setTextWidth(self.viewport().width())
        margins = self.contentsMargins()
        height = int(self.document().size().height() + margins.top() + margins.bottom())
        if height > self.window().height()//3:
            return
        self.setFixedHeight(height)


class Code(ResizableQText):
    def __init__(self, code, size):
        super().__init__()
        self.setObjectName("code")
        with open("style/style.qss") as f:
            self.setStyleSheet(f.read())
        self.setTextColor(QColor('lightgrey'))
        self.setReadOnly(True)
        self.highlighter = PythonHighlighter(self.document(), size)
        self.setText(code)


class Message(ResizableQText):
    def __init__(self, text, role, size):
        super().__init__()
        self.role = role
        self.setReadOnly(True)
        self.setObjectName(role)
        self.setFontPointSize(size)
        self.setText(text)
