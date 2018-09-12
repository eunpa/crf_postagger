import os
import psutil

installpath = os.path.sep.join(
    os.path.dirname(os.path.realpath(__file__)).split(os.path.sep)[:-1])

class Corpus:
    def __init__(self, path, num_sent=-1):
        self.path = path
        self.num_sent = num_sent
    def __iter__(self):
        with open(self.path, encoding='utf-8') as f:
            for i, sent in enumerate(f):
                if self.num_sent > 0 and i > self.num_sent:
                    break
                wordpos = [token.rsplit('/', 1) for token in sent.split()]
                yield wordpos

def check_dirs(path):
    dirname = os.path.dirname(path)
    if dirname and dirname != '.' and not os.path.exists(dirname):
        os.makedirs(dirname)

def get_process_memory():
    """It returns the memory usage of current process"""

    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 ** 3)