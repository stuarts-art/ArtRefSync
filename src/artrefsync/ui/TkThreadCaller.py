from queue import Empty, Queue
import ttkbootstrap as ttk
from threading import Event, Thread
import time
from artrefsync.config import config

import logging
logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


class TkThreadCaller:
    def __init__(self, root :ttk.Frame, event_name=None):
        self.event_name =f"<<{f'{event_name}_' if event_name else ""}gui_call>>"
        root.bind(self.event_name, self._gui_call_handler)
        self.root = root
        self.call_queue = Queue()

    class _GUICallData:
        def __init__(self, fn, response):
            self.fn = fn
            self.response = response
            self.reply = None
            self.reply_event = Event()

    def add(self, task: callable, on_finish:callable, *args, **kwargs) -> None:
        new_kwargs={"task": task, "on_finish": on_finish, "old_kwargs": kwargs}
        thread = Thread(
            target=self._start_thread,
            args=args,
            kwargs=new_kwargs,
            daemon=True)
        thread.start()
        
        
    def _start_thread(self, *args, **kwargs):
        task = kwargs["task"]
        on_finish = kwargs["on_finish"]
        old_kwargs = kwargs["old_kwargs"]
        if args and old_kwargs:
            response = task(*args, **old_kwargs)
        elif args:
            response = task(*args)
        else:
            response = task(**old_kwargs)
            
        data = self._GUICallData(on_finish, response)
        self.call_queue.put(data)
        self.root.event_generate(self.event_name, when="tail")
        data.reply_event.wait()
        return data.reply

    def _gui_call_handler(self, event):
        try:
            while True:
                data = self.call_queue.get_nowait()
                data.reply = data.fn(data.response)
                data.reply_event.set()
        except Empty:
            pass

    
def main():
    class _EventApp:
        def __init__(self):
            self.root = ttk.Window(themename="darkly", size=(1080,1080))
            self.frame = ttk.Frame(self.root)
            self.frame.pack()
            self.thread_caller = TkThreadCaller(self.root)
            self.root.after(10,self.after)
            self.root.mainloop()

        def after(self):
            self.thread_caller.add(self.slow_hello_world, self.build_example_frame,"test", "words", other="OTHER WORDS")
            
        def slow_hello_world(self, *args, **kwargs):
            print(args)
            print(kwargs)
            time.sleep(1)
            return f"Hello {" ".join([*args])} {kwargs}"

        def build_example_frame(self, data):
            label = ttk.Label(self.frame, text=data)
            label.pack()

    app = _EventApp()
    
if __name__ == "__main__":
    main()