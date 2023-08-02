from langchain.chat_models import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, pyqtSlot


class WorkerSignals(QObject):
    started = pyqtSignal()
    result = pyqtSignal(object)
    

class OpenAIChat(QRunnable):
    def __init__(self, api_key, model, session):
        super().__init__()
        self.chat = ChatOpenAI(model_name=model, openai_api_key=api_key)
        self.session = session
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        self.signals.started.emit()
        messages = [SystemMessage(content=self.session.system_message)]
        for x in self.session.messages:
            if x['role'] == 'user':
                messages.append(HumanMessage(content=x['message']))
            else:
                messages.append(AIMessage(content=x['message']))

        self.signals.result.emit(self.chat.predict_messages(messages))
