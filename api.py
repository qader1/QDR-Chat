from langchain.chat_models import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, pyqtSlot
from openai import error


class WorkerSignals(QObject):
    started = pyqtSignal()
    result = pyqtSignal(object)
    

class OpenAIChat(QRunnable):
    def __init__(self, api_key, model, session, query_title=None):
        super().__init__()
        self.chat = ChatOpenAI(model_name=model, openai_api_key=api_key)
        self.session = session
        self.query_title = query_title
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        self.signals.started.emit()

        if self.query_title is not None:
            system_message = (
                "Find the best title for the queries that you receive."
                "The queries could be anything from questions to general chat. "
                "Be very creative with the titles "
                "to minimize the chance of producing the same title for different queries. "
                "The title shouldn't be more than 4 words. "
            )
            messages = [SystemMessage(content=system_message), HumanMessage(content=self.query_title)]
        else:
            messages = [SystemMessage(content=self.session.system_message)]
            for x in self.session.messages:
                if x['role'] == 'user':
                    messages.append(HumanMessage(content=x['message']))
                else:
                    messages.append(AIMessage(content=x['message']))
        try:
            self.signals.result.emit(self.chat.predict_messages(messages))
        except error.AuthenticationError:
            self.signals.result.emit("Incorrect API key")
