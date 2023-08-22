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
        if api_key == '':
            api_key = 'none'
        self.chat = ChatOpenAI(model_name=model, openai_api_key=api_key)
        self.max_tokens = 8192
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
            messages = []
            num_tokens = 0
            for x in reversed(self.session.messages):
                if num_tokens + self.chat.get_num_tokens(x['message']) > self.max_tokens:
                    break
                else:
                    num_tokens += self.chat.get_num_tokens(x['message'])
                    if x['role'] == 'user':
                        messages.append(HumanMessage(content=x['message']))
                    else:
                        messages.append(AIMessage(content=x['message']))
            messages.append(SystemMessage(content=self.session.system_message))
            messages = list(reversed(messages))
        try:
            self.signals.result.emit(self.chat.predict_messages(messages))
        except error.AuthenticationError:
            self.signals.result.emit("Incorrect API key")
        except Exception as e:
            self.signals.result.emit(str(e))
