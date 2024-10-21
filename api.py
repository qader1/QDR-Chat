from langchain.chat_models import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, pyqtSlot
import json
from openai import error


class WorkerSignals(QObject):
    started = pyqtSignal()
    result = pyqtSignal(object)
    memory = pyqtSignal(object)
    

class OpenAIChat(QRunnable):
    def __init__(self, api_key, model, session, query_title=None):
        super().__init__()
        if api_key == '':
            api_key = 'none'
        self.chat = ChatOpenAI(model_name=model, openai_api_key=api_key)
        self.max_tokens = 127_000
        self.session = session
        self.query_title = query_title
        self.signals = WorkerSignals()
        with open("history/memories.json", "r") as f:
            memory = json.load(f)
            name = memory["user"]
            ai = memory["ai"]
            memories = memory["memories"]
        memories = "\n".join([f"{x+1}. {memories[x]['date']}: {memories[x]['memory']}" for x in range(len(memories))])
        self.memory_prompt = f"You are a personal assistant to '{name}'. Your given name is '{ai}'.\n"\
        "You will be provided with memories from previous conversations that was saved"\
        f"using a long term memory mechanism. These memories are important for you and your relationship with '{name}'"
        f"use the memories to inform your interaction and to fulfill your task as assistant and friend.\n"
        f"list of memories with date:\n{memories}."\
        f"please follow the following instructions as well:\n"

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
            messages.append(SystemMessage(content=self.memory_prompt + self.session.system_message))
            messages = list(reversed(messages))
        try:
            self.signals.result.emit(self.chat.predict_messages(messages))
        except error.AuthenticationError:
            self.signals.result.emit("Incorrect API key")
        except Exception as e:
            self.signals.result.emit(str(e))


class Memories(QRunnable):
    def __init__(self, api_key, model, session):
        super().__init__()
        if api_key == '':
            api_key = 'none'
        self.chat = ChatOpenAI(model_name=model, openai_api_key=api_key)
        self.signals = WorkerSignals()

        memory_prompt = 'You are not a conversational AI and the user does not see your responses directly. your task is to manage long term memory.'\
        'For every message, when the user shares personal information about his preferences, real events, or circumstances.\n'\
        'you create a memory. If the message does not contain any information to remember, you return only the response "None".\n' \
        'The user might ask you to remember certain things, in the case, whatever they are, you should create a memory for them.\n'\
        'You are only provided the last message in conversations.\n'\
        'example 1:\n'\
        'user: I landed a job today at Microsoft as a software developer.\n'\
        'your response: Has landed a job at Microsoft as a software developer.\n'\
        'example 2:\n'\
        'user: write me a poem about cats\n'\
        'your response: None\n'\
        'example 3:\n'\
        'user: write me a poem about cats. I really like cats.\n'\
        'response: Likes cats\n'\
        'example 4:\n'\
        'user: is this a good idea?\n'\
        'response: None'

        self.memory_messages = [SystemMessage(content=memory_prompt),
                                HumanMessage(content=session.messages[-1]["message"])]
    @pyqtSlot()
    def run(self):
        self.signals.memory.emit(self.chat.predict_messages(self.memory_messages))

