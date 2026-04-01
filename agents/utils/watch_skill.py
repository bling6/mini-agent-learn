from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from agents.utils.skill_loader import SKILL_LOADER
import threading


DIR = Path.cwd()
# 指定要监听的文件夹路径
folder_to_watch = DIR / "skills"  # 修改为你的路径

class WatchSkillHandler(FileSystemEventHandler):
    # def on_created(self, event):
    #     if not event.is_directory:
    #         print(f"[新增] {event.src_path}")

    # def on_deleted(self, event):
    #     if not event.is_directory:
    #         print(f"[删除] {event.src_path}")

    def on_modified(self, event):
        if not event.is_directory:
            SKILL_LOADER.load_all()
            # print(f"[修改] {event.src_path}")

    def on_moved(self, event):
        if not event.is_directory:
            SKILL_LOADER.load_all()
            # print(f"[移动] {event.src_path} -> {event.dest_path}")


class ObserverWrapper:
    """封装 observer，不阻塞主线程"""

    def __init__(self, path, handler):
        self.observer = Observer()
        self.observer.schedule(handler, path, recursive=True)
        self._thread = None
        self._running = False

    def start(self):
        """非阻塞启动"""
        self._running = True
        self.observer.start()

        # 在后台线程等待
        self._thread = threading.Thread(target=self._wait)
        self._thread.start()

    def _wait(self):
        """后台等待"""
        try:
            self.observer.join()
        except:
            pass

    def stop(self):
        """停止监听"""
        self._running = False
        self.observer.stop()
        if self._thread:
            self._thread.join(timeout=2)

wrapper = ObserverWrapper(str(folder_to_watch), WatchSkillHandler())


def run_watch_skill():
    wrapper.start()

def stop_watch_skill():
    wrapper.stop()