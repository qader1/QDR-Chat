from PyQt6.QtWidgets import (QApplication,
                             QMainWindow,
                             QPushButton,
                             QVBoxLayout,
                             QWidget,
                             QScrollArea,
                             QHBoxLayout,
                             QListWidget,
                             QTextEdit,
                             QListWidgetItem,
                             QMenu,
                             QSizeGrip,
                             QTextBrowser,
                             QSizePolicy)

from PyQt6.QtCore import QSize, Qt, QTimer, QThreadPool, QPointF
from PyQt6.QtGui import QColor, QPalette, QIcon, QMouseEvent
from api import OpenAIChat
from python_syntax_highlighting import PythonHighlighter
import random
import os
import uuid
import datetime
import pickle
import csv
import re
import pywinstyles
import json
import pathlib


app = QApplication([])

with open("key.json", 'r') as api_key:
    file = json.load(api_key)
API_KEY = file['api_key']
MODEL = file['model']


class MainWindow(QMainWindow):
    # TODO work on menu bar (change api key, model, themes if I felt like it)
    # TODO add a new text field for the system message
    # TODO syntax highlighting for code (needs fixing for messages with multiple blocks)
    # TODO Optimize layout
    def __init__(self):
        super().__init__()
        self.setWindowTitle('QDR Chat')
        self.resize(QSize(960, 540))

        self.main_container = QHBoxLayout()
        self.main_container.setSpacing(0)
        self.main_container.setContentsMargins(0, 0, 0, 0)
        self.main_widget = QWidget()
        self.main_widget.setLayout(self.main_container)
        self.setStyleSheet("border-width: 0px")

        self.history_container = QVBoxLayout()
        self.history_container.setContentsMargins(0, 0, 0, 0)
        self.history_widget = QWidget()
        self.history_widget.setLayout(self.history_container)
        self.history_widget.setStyleSheet("border: none;"
                                          "background-color: rgb(32, 33, 35);")

        self.chat_container = QVBoxLayout()
        self.chat_container.setContentsMargins(0, 0, 0, 0)
        self.chat_widget = QWidget()
        self.chat_widget.setLayout(self.chat_container)
        self.chat_widget.setStyleSheet("border: none;"
                                       "background-color: rgb(52, 53, 65);")

        self.main_container.addWidget(self.history_widget, 1)
        self.main_container.addWidget(self.chat_widget, 4)

        self.message_display_widget = MessageDisplayWidget()
        self.input_widget = QWidget()
        input_widget_box = QHBoxLayout()
        self.input_widget.setLayout(input_widget_box)

        self.scroll = QScrollArea()
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setWidget(self.message_display_widget)
        self.scroll.setWidgetResizable(True)
        with open('style/scrollbar.stylesheet', 'r') as f:
            self.scroll.setStyleSheet(f.read())

        self.text_edit = InputText()
        self.text_edit.setMinimumHeight(20)
        self.text_edit.setStyleSheet("background-color: rgb(58, 60, 74);"
                                     "color: darkgrey;"
                                     "border-radius: 8px;")

        self.send_button = QPushButton()
        self.send_button.setIcon(QIcon('icons/send.svg'))
        input_widget_box.addWidget(self.text_edit)
        input_widget_box.addWidget(self.send_button)

        self.chat_container.addWidget(self.scroll, 6)
        self.chat_container.addWidget(self.input_widget, 1)

        self.send_button.clicked.connect(self.send)
        self.setCentralWidget(self.main_widget)

        self.current_session = None

        self.new_chat_btn = QPushButton('New chat')
        with open("style/new_chat_btn.stylesheet", 'r') as f:
            self.new_chat_btn.setStyleSheet(f.read())

        self.new_chat_btn.clicked.connect(self.new_session)

        self.history_list = CustomQListWidget()
        with open('style/list.stylesheet', 'r') as f:
            self.history_list.setStyleSheet(f.read())
        self.get_history()
        self.history_list.itemPressed.connect(self.load_session)

        self.size_grib = QSizeGrip(self)

        self.history_container.addWidget(self.new_chat_btn)
        self.history_container.addWidget(self.history_list)
        self.history_container.addWidget(self.size_grib,
                                         alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)

        self.pool = QThreadPool()
        self.oldPos = self.pos()

        pywinstyles.change_header_color(self, color="#202123")
        pywinstyles.change_border_color(self, color="#515473")

    def mousePressEvent(self, event: QMouseEvent):
        self.oldPos = event.globalPosition()

    def mouseMoveEvent(self, event):
        delta = QPointF(event.globalPosition() - self.oldPos)
        self.move(int(self.x() + delta.x()), int(self.y() + delta.y()))
        self.oldPos = event.globalPosition()

    def send(self):
        if self.current_session is None:
            title = 'Dummy'+str(random.randint(1, 200))
            self.current_session = Session(title)
            new_item = QListWidgetItem(title)
            new_item.setIcon(QIcon('icons/message.svg'))
            self.history_list.insertItem(0, new_item)
            self.history_list.setCurrentItem(new_item)
        self.current_session.append_message(self.text_edit.toPlainText(), 'user')
        self.message_display_widget.add_message(self.text_edit.toPlainText(), 'user')
        self.run_model()
        QTimer.singleShot(5, self.scroll_to_bottom)
        self.text_edit.setText('')
        self.current_session.save()

    def run_model(self):
        llm = OpenAIChat(API_KEY, MODEL, self)
        llm.signals.started.connect(lambda: self.text_edit.setDisabled(True))
        llm.signals.result.connect(self.receive)
        self.pool.start(llm)

    def receive(self, result):
        self.current_session.append_message(result.content, 'assistant')
        self.message_display_widget.add_message(result.content, 'assistant')
        QTimer.singleShot(5, self.scroll_to_bottom)
        self.text_edit.setText('')
        self.text_edit.setDisabled(False)
        self.current_session.save()

    def load_session(self, item):
        self.clear()
        with open(f'history/history.csv', 'r') as f:
            reader = csv.reader(f)
            index = self.history_list.currentIndex()
            id_ = list(reader)[index.row()][0]
        with open(f'history/{id_}.chs', 'rb') as f:
            self.current_session = pickle.load(f)
        for i in self.current_session.messages:
            self.message_display_widget.add_message(i['message'], i['role'])
        self.message_display_widget.container.setAlignment(Qt.AlignmentFlag.AlignBottom)
        QTimer.singleShot(5, self.scroll_to_bottom)
        self.text_edit.setText('')

    def scroll_to_bottom(self):
        x = self.scroll.verticalScrollBar()
        self.scroll.verticalScrollBar().setValue(x.maximum())

    def get_history(self):
        if 'history.csv' not in os.listdir('history'):
            pathlib.Path("history/history.csv").touch()
        with open('history/history.csv', 'r') as csvfile:
            csv_reader = list(csv.reader(csvfile))
            if csv_reader is not None:
                for row in csv_reader:
                    item = QListWidgetItem(row[2])
                    item.setIcon(QIcon('icons/message.svg'))
                    self.history_list.addItem(item)

    def clear(self):
        while self.message_display_widget.container.count():
            child = self.message_display_widget.container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.message_display_widget.container.setAlignment(Qt.AlignmentFlag.AlignTop)

    def new_session(self):
        self.clear()
        self.history_list.setCurrentItem(None)
        self.current_session = None


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


class InputText(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setPlaceholderText('Send a message')
        self.textChanged.connect(self.auto_resize)

    def auto_resize(self):
        self.document().setTextWidth(self.viewport().width())
        margins = self.contentsMargins()
        height = int(self.document().size().height() + margins.top() + margins.bottom())
        self.setFixedHeight(height)

    def resizeEvent(self, event):
        self.auto_resize()

    def keyPressEvent(self, e):
        key = e.key()
        modifier = QApplication.keyboardModifiers()
        if modifier != Qt.KeyboardModifier.ShiftModifier:
            if key == Qt.Key.Key_Enter or key == Qt.Key.Key_Return:
                if self.toPlainText().strip() != '':
                    self.window().send()
                QTimer.singleShot(5, lambda: self.setText(''))

        return super().keyPressEvent(e)


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


class ResizableQText(QTextBrowser):
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
        self.highlighter = PythonHighlighter(self.document())
        self.setText(code)


class Message(ResizableQText):
    def __init__(self, text, role):
        super().__init__()
        self.role = role

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


class Session:
    def __init__(self, title):
        self.title = title
        self.start = datetime.datetime.now()
        self.messages = []
        self.id_ = str(uuid.uuid4())

    def append_message(self, message, role):
        self.messages.append({"role": role, "message": message})

    def save(self):
        if self.id_ + '.chs' not in os.listdir('history'):
            with open('history/history.csv', 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
            rows.insert(0, [self.id_, self.start, self.title])
            with open('history/history.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(rows)
        with open(f'history/{self.id_}.chs', 'wb') as cls:
            pickle.dump(self, cls)


window = MainWindow()
window.show()
app.exec()
