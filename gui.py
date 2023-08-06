from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QSize, QThreadPool, pyqtSlot
from api import OpenAIChat
from custom_widgets import *
import random
import os
import uuid
import datetime
import pickle
import csv
import pywinstyles
import json
import pathlib


app = QApplication([])

with open("key.json", 'r') as api_key:
    file = json.load(api_key)
API_KEY = file['api_key']
MODEL = file['model']


class MainWindow(QMainWindow):
    # TODO work on menu bar (change api key, model, themes maybe)
    # TODO fix highlighting when multiple blocks of code exist in one message
    def __init__(self):
        super().__init__()
        self.setWindowTitle('QDR Chat')
        self.resize(QSize(1440, 810))
        self.setWindowIcon(QIcon('icons/main_window.svg'))

        self.main_container = QHBoxLayout()
        self.main_container.setSpacing(0)
        self.main_container.setContentsMargins(0, 0, 0, 0)
        self.main_widget = QWidget()
        self.main_widget.setObjectName("main_widget")
        self.main_widget.setLayout(self.main_container)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        with open("style/style.qss") as f:
            self.setStyleSheet(f.read())

        self.history_widget = HistoryWidget()
        self.chat_widget = ChatWidget()
        self.chat_widget.about(True)

        self.get_history()
        self.history_widget.new_chat_btn.clicked.connect(self.new_session)
        self.history_widget.history_list.itemPressed.connect(self.load_session)

        self.main_container.addWidget(self.history_widget, 1)
        self.main_container.addWidget(self.chat_widget, 5)

        self.chat_widget.input_widget.send_button.clicked.connect(self.send)
        self.chat_widget.system_message_widget.signal.SystemMessageChanged.connect(self.edit_system_message)
        self.history_widget.history_list.clicked.connect(self.show_about)

        self.current_session = None

        self.pool = QThreadPool()
        self.oldPos = self.pos()
        pywinstyles.change_header_color(self, color="#202123")
        pywinstyles.change_border_color(self, color="#515473")

        self.setCentralWidget(self.main_widget)

    def send(self):
        if self.chat_widget.input_widget.text_edit.toPlainText() == '':
            return
        if self.current_session is None:
            title = 'Dummy'+str(random.randint(1, 200))
            self.current_session = Session(title)
            self.chat_widget.set_system_message(self.current_session.system_message)
            self.history_widget.add(title)
            self.show_about(False)

        self.current_session.append_message(
            self.chat_widget.input_widget.text_edit.toPlainText(), 'user'
        )
        self.chat_widget.message_display_widget.add_message(
            self.chat_widget.input_widget.text_edit.toPlainText(), 'user'
        )
        self.run_model()
        QTimer.singleShot(5, self.chat_widget.scroll_to_bottom)
        self.chat_widget.input_widget.text_edit.setText('')
        self.current_session.save()

    def edit_system_message(self, text):
        if self.current_session is None:
            title = 'Dummy' + str(random.randint(1, 200))
            self.current_session = Session(title)
            self.current_session.system_message = text
            self.history_widget.add(title)
            self.current_session.save()
        else:
            self.current_session.system_message = text

    def run_model(self):
        llm = OpenAIChat(API_KEY, MODEL, self.current_session)
        llm.signals.started.connect(lambda: self.chat_widget.input_widget.text_edit.setDisabled(True))
        llm.signals.result.connect(self.receive)
        self.pool.start(llm)

    def receive(self, result):
        self.current_session.append_message(result.content, 'assistant')
        self.chat_widget.message_display_widget.add_message(result.content, 'assistant')
        QTimer.singleShot(5, self.chat_widget.scroll_to_bottom)
        self.chat_widget.input_widget.text_edit.setText('')
        self.chat_widget.input_widget.text_edit.setDisabled(False)
        self.current_session.save()

    def load_session(self, item):
        self.chat_widget.clear()
        with open(f'history/history.csv', 'r') as f:
            reader = csv.reader(f)
            index = self.history_widget.history_list.currentIndex()
            id_ = list(reader)[index.row()][0]
        with open(f'history/{id_}.chs', 'rb') as f:
            self.current_session = pickle.load(f)
        self.chat_widget.set_system_message(self.current_session.system_message)
        self.chat_widget.display_messages(self.current_session.messages)
        self.chat_widget.scroll_to_bottom()

    def get_history(self):
        if 'history.csv' not in os.listdir('history'):
            pathlib.Path("history/history.csv").touch()
        with open('history/history.csv', 'r') as csvfile:
            csv_reader = list(csv.reader(csvfile))
            if csv_reader is not None:
                for row in csv_reader:
                    title = row[2]
                    self.history_widget.add(title)
        self.history_widget.history_list.clearSelection()

    def new_session(self):
        self.chat_widget.clear()
        self.chat_widget.set_system_message("You are a helpful assistant")
        self.history_widget.history_list.setCurrentItem(None)
        self.current_session = None
        self.chat_widget.about(True)

    def show_about(self, item):
        if item is None:
            self.chat_widget.about(True)
        else:
            self.chat_widget.about(False)


class Session:
    def __init__(self, title):
        self.title = title
        self.start = datetime.datetime.now()
        self.system_message = "You are a helpful assistant"
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
