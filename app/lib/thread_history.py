# from rich import Console

# LOG_COLOR = "[white on brick]"


class ThreadManager:
    # thread_conversations = {}

    def __init__(self):
        # self.thread_conversations = {}
        pass

    def addToThreadHistory(self, tid, role, message):
        # if tid not in self.thread_conversations:
        #     self.thread_conversations[tid] = ""
        #     print(f"+++ Creating new thread: {tid}")
        # self.thread_conversations[tid] += f"\n{role}:\n{message}\n"
        # print(f"<<< Updated thread {tid}: {self.thread_conversations[tid]}")
        pass

    def getThreadHistory(self, tid) -> str:
        pass
        # if tid in self.thread_conversations:
        #     print(f">>> Retrieving thread {tid}: {self.thread_conversations[tid]}")
        #     return self.thread_conversations[tid]
        # return ""
