from langchain.chat_models import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, pyqtSlot


class WorkerSignals(QObject):
    started = pyqtSignal()
    result = pyqtSignal(object)
    

class OpenAIChat(QRunnable):
    def __init__(self, api_key, model, main_window):
        super().__init__()
        self.chat = ChatOpenAI(model_name=model, openai_api_key=api_key)
        self.main_window = main_window
        self.system_message = SystemMessage(content="You are a helpful AI assistant.")
        self.signals = WorkerSignals()

    def set_system_message(self, message):
        self.system_message = SystemMessage(content=message)


    @pyqtSlot()
    def run(self):
        self.signals.started.emit()
        messages = [self.system_message]
        for x in self.main_window.current_session.messages:
            if x['role'] == 'user':
                messages.append(HumanMessage(content=x['message']))
            else:
                messages.append(AIMessage(content=x['message']))

        self.signals.result.emit(self.chat.predict_messages(messages))
