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
                             )
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, pyqtSignal, QObject, QRect
from PyQt6.QtGui import QColor, QPalette, QIcon, QFont, QPixmap, QPainter
from python_syntax_highlighting import PythonHighlighter
import re
import csv
import os


class ChatWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.chat_container = QVBoxLayout()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.chat_container.setContentsMargins(0, 0, 0, 0)
        self.chat_container.setSpacing(0)
        self.setLayout(self.chat_container)
        self.setStyleSheet("border: none;"
                           "background-color: rgb(52, 53, 65);")

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.nn = QSvgWidget('icons/robot.svg')
        self.nn.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.nn.renderer().setViewBox(QRect(0, 0, 245, 440))
        self.nn.setHidden(True)

        self.system_message_widget = SystemMessageWidget()
        self.message_display_widget = MessageDisplayWidget()
        self.input_widget = InputWidget()

        self.scroll = ScrollableMessageDisplay(self.message_display_widget)

        self.chat_container.addWidget(self.system_message_widget, 1)
        self.chat_container.addWidget(self.scroll, 13)
        self.chat_container.addWidget(self.nn, Qt.AlignmentFlag.AlignCenter)
        self.chat_container.addWidget(self.input_widget, 1)

    def display_messages(self, messages):
        for i in messages:
            self.message_display_widget.add_message(i['message'], i['role'])
        self.message_display_widget.container.setAlignment(Qt.AlignmentFlag.AlignBottom)
        QTimer.singleShot(5, self.scroll_to_bottom)
        self.input_widget.text_edit.setText('')

    def scroll_to_bottom(self):
        x = self.scroll.verticalScrollBar()
        self.scroll.verticalScrollBar().setValue(x.maximum())

    def clear(self):
        self.set_system_message('')
        while self.message_display_widget.container.count():
            child = self.message_display_widget.container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.message_display_widget.container.setAlignment(Qt.AlignmentFlag.AlignTop)

    def set_system_message(self, text):
        self.system_message_widget.system_message.setText(text)

    def about(self, show):
        self.nn.setHidden(not show)
        self.message_display_widget.setHidden(show)
        self.system_message_widget.setHidden(show)


class SystemMessageSignal(QObject):
    SystemMessageChanged = pyqtSignal(str)


class SystemMessageWidget(QWidget):
    def __init__(self):
        super().__init__()
        system_message_layout = QHBoxLayout()
        self.setLayout(system_message_layout)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #2A2B2E;"
                           "border-bottom-left-radius: 12px")

        label = QLabel("System Prompt")
        label.setContentsMargins(10, 0, 10, 0)
        label.setStyleSheet("background-color: #008080;"
                            "border-top-left-radius: 5px;"
                            "border-bottom-left-radius: 5px;"
                            "font-size: 13px")
        label.setMaximumHeight(30)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.system_message = QLineEdit()
        self.system_message.setEnabled(False)
        self.system_message.setContentsMargins(0, 0, 10, 0)
        self.system_message.setStyleSheet("background-color: #515473;"
                                          "border-top-right-radius: 5px;"
                                          "border-bottom-right-radius: 5px;"
                                          "border-bottom-left-radius: 0;"
                                          "padding-left: 5px;"
                                          "color: #C0C0C0")

        self.system_message.setFont(QFont('serif', 8, 400, True))
        self.system_message.setMaximumHeight(30)
        self.system_message.setText("You are a helpful assistant")

        self.system_message.setSizePolicy(label.sizePolicy())

        self.edit = ColorableButtonIcon('icons/edit.svg',
                                        "grey",
                                        "silver",
                                        None)

        self.confirm = QPushButton()
        self.confirm.setStyleSheet("padding: 4px")
        self.confirm.setIcon(QIcon("icons/confirm.svg"))
        self.cancel = QPushButton()
        self.cancel.setStyleSheet("padding: 4px")
        self.cancel.setIcon(QIcon("icons/cancel.svg"))

        self.confirm.setHidden(True)
        self.cancel.setHidden(True)

        self.edit.setStyleSheet(
            """
            QPushButton {
                padding: 4px ;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: darkslategrey;
            }
            QPushButton:pressed {
                background-color: #008080;
            }
            """

        )

        self.edit.clicked.connect(self.edit_slot)
        self.confirm.clicked.connect(self.confirm_slot)
        self.cancel.clicked.connect(self.cancel_slot)

        system_message_layout.addWidget(label, 3)
        system_message_layout.addWidget(self.system_message, 20)
        system_message_layout.addWidget(self.edit)
        system_message_layout.addWidget(self.confirm)
        system_message_layout.addWidget(self.cancel)
        system_message_layout.setSpacing(0)

        self.signal = SystemMessageSignal()
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


class HistoryWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.history_container = QVBoxLayout()
        self.history_container.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.history_container)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: rgb(32, 33, 35);"
                           "border: 0;")

        self.history_list = CustomQListWidget()
        self.new_chat_btn = QPushButton('New chat')
        with open("style/new_chat_btn.stylesheet", 'r') as f:
            self.new_chat_btn.setStyleSheet(f.read())

        self.history_container.addWidget(self.new_chat_btn)
        self.history_container.addWidget(self.history_list)

    def add(self, title):
        new_item = QListWidgetItem(title)
        new_item.setIcon(QIcon('icons/message.svg'))
        self.history_list.insertItem(0, new_item)
        self.history_list.setCurrentItem(new_item)


class InputWidget(QWidget):
    def __init__(self):
        super().__init__()
        input_widget_box = QHBoxLayout()
        self.setLayout(input_widget_box)
        self.text_edit = InputText()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.send_button = ColorableButtonIcon('icons/send.svg',
                                               'grey',
                                               'silver',
                                               None)
        input_widget_box.addWidget(self.text_edit)
        input_widget_box.addWidget(self.send_button)


class CustomQListWidget(QListWidget):
    def __init__(self):
        super().__init__()

        self.menu = QMenu()
        self.menu.setWindowFlags(Qt.WindowType.Popup |
                                 Qt.WindowType.FramelessWindowHint |
                                 Qt.WindowType.NoDropShadowWindowHint)
        self.menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        delete_action = self.menu.addAction(QIcon('icons/delete.svg'), "Delete")
        delete_action.triggered.connect(self.delete_action)
        with open('style/list.stylesheet', 'r') as f:
            self.setStyleSheet(f.read())
        self.menu.setStyleSheet("""
                                QMenu {
                                    background-color: #5d5d7a;
                                    border: 0px solid #303847;
                                    border-radius: 15px;
                                    color: rgb(206, 206, 206)
                                }
                                QMenu::item {
                                        background-color: transparent;
                                        padding:3px 20px;
                                        margin:5px 10px;
                                }

                                QMenu::item:selected {
                                    background-color: #8080a8;
                                }""")

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
        with open('style/scrollbar.stylesheet', 'r') as f:
            self.setStyleSheet(f.read())


class MessageDisplayWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.container = QVBoxLayout()
        self.container.setSpacing(0)
        self.container.addStretch(0)
        self.container.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.container)
        new_palette = QPalette()
        new_palette.setColor(self.backgroundRole(), QColor(52, 53, 65))
        self.setPalette(new_palette)
        self.setAutoFillBackground(True)

    def add_message(self, message, role):
        if role == 'assistant':
            pattern = re.compile(r"(.*)```python(.*?)```(.*)", flags=re.DOTALL)
            result = pattern.search(message)
            if result:
                pre_message, code, after_message = result.groups()
                self.container.addWidget(Message(pre_message.strip(), 'assistant'))
                self.container.addWidget(Code(code.strip()))
                self.container.addWidget(Message(after_message.strip(), 'assistant'))
            else:
                self.container.addWidget(Message(message, 'assistant'))
        else:
            self.container.addWidget(Message(message, role))
        self.container.setAlignment(Qt.AlignmentFlag.AlignBottom)


class ResizableQText(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

    def auto_resize(self):
        self.document().setTextWidth(self.viewport().width())
        margins = self.contentsMargins()
        height = int(self.document().size().height() + margins.top() + margins.bottom())
        self.setFixedHeight(height)

    def resizeEvent(self, event):
        self.auto_resize()


class InputText(ResizableQText):
    def __init__(self):
        super().__init__()
        self.setPlaceholderText('Send a message')
        self.textChanged.connect(self.auto_resize)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background-color: rgb(58, 60, 74);"
                           "color: darkgrey;"
                           "border-radius: 8px;"
                           "padding: 6px 6px 6px 6px")

    def keyPressEvent(self, e):
        key = e.key()
        modifier = QApplication.keyboardModifiers()
        if modifier != Qt.KeyboardModifier.ShiftModifier:
            if key == Qt.Key.Key_Enter or key == Qt.Key.Key_Return:
                if self.toPlainText().strip() != '':
                    self.window().send()
                QTimer.singleShot(5, lambda: self.setText(''))

        return super().keyPressEvent(e)


class Code(ResizableQText):
    def __init__(self, code):
        super().__init__()
        self.setStyleSheet(f"background-color: rgb(0, 0, 0);"
                           "background-origin: content;"
                           "border: 0px;"
                           "margin: 0 10px 0 10px;"
                           "padding-left: 70%;"
                           "padding-right: 70%;"
                           "padding-top: 10%;"
                           "padding-bottom: 10%")
        self.setTextColor(QColor('lightgrey'))
        self.setText(code)
        self.setReadOnly(True)
        self.highlighter = PythonHighlighter(self.document())


class Message(ResizableQText):
    def __init__(self, text, role):
        super().__init__()
        self.role = role
        self.setReadOnly(True)

        if role == 'user':
            self.setAlignment(Qt.AlignmentFlag.AlignLeft)
            color = "rgb(52, 53, 65)"
            icon = "icons/human.svg"
        else:
            self.setAlignment(Qt.AlignmentFlag.AlignRight)
            color = "rgb(68, 70, 84)"
            icon = "icons/ai.svg"

        self.setStyleSheet(f"background-color: {color};"
                           f"background-image: url({icon});"
                           "background-repeat: no-repeat;"
                           "background-position: left center;"
                           "background-origin: padding;"
                           "border: 0px;"
                           "margin: 0 10px 0 10px;"
                           "padding-left: 50%;"
                           "padding-right: 60%;"
                           "padding-top: 10%;"
                           "padding-bottom: 10%")

        self.setTextColor(QColor('lightgrey'))
        self.setFontPointSize(10)
        self.setText(text)
