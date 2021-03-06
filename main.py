import re
import time
import numpy
import threading
from spider import Spider

# the patten to extract file id from the HTML context
S_PATTERN_PDF = r'<span class="list-identifier">.*?\[<a href="/pdf/(.*?)" title="Download PDF">pdf</a>'
# the pattern to extract total entries number
S_PATTERN_EMTRIES = r'\[ total of (.*?) entries:'
BASE_URLs = (
    #  'https://arxiv.org',
    #'http://de.arxiv.org', can get real pdf on 20190409
    'http://cn.arxiv.org',
    #'http://lanl.arxiv.org', System Unavailable on 20190409
    'http://xxx.itp.ac.cn'
)
# the path to save the crawled files
SAVE_DIR = './pdfs/'
# It's a list of the file names to be crawled(Excluding file suffixes)
task_list = []
task_list_lock = threading.Lock()
spider = Spider(BASE_URLs[numpy.random.randint(0, len(BASE_URLs))], SAVE_DIR)
WORKER_NUM = 10
BEGIN_YEAR = 15
BEGIN_MONTH = 1
END_YEAR = 19
END_MONTH = 3


class Worker(threading.Thread):
    def __init__(self, thread_id, thread_name):
        threading.Thread.__init__(self)
        self.threadID = thread_id
        self.thread_name = thread_name

    def run(self):
        while True:
            task_list_lock.acquire()
            if len(task_list) == 0:
                task_list_lock.release()
                break
            file_id = task_list[0]
            task_list.pop(0)
            # Randomly select the mirror address to download
            spider.base_url = BASE_URLs[numpy.random.randint(0, len(BASE_URLs))]
            # sleep 2 seconds before downloading
            time.sleep(2)
            task_list_lock.release()
            file_name = "%s.pdf" % file_id
            file_url = '/pdf/%s' % file_id
            spider.get_file(file_name, file_url)
            # sleep 2 seconds after downloading
            time.sleep(2)


def download(_year, _month):
    global task_list
    #  skip means the offset, show means how many entries per page
    skip = 0
    show = 100
    page_url = '/list/cs/%02d%02d' % (_year, _month)
    page = spider.get_page(page_url)
    pattern_total = re.compile(S_PATTERN_EMTRIES, re.S)
    total_obj = re.search(pattern_total, page.decode('utf-8'))
    if not total_obj:
        print('total match failed:[%s]' % S_PATTERN_EMTRIES)
        return False
    total_num = int(total_obj.group(1))
    print("page_url:%s\ntotal_num:%d" % (page_url, total_num))
    while skip < total_num:
        # Randomly select the mirror address to download
        spider.base_url = BASE_URLs[numpy.random.randint(0, len(BASE_URLs))]
        #  e.g.:/list/cs/1801?skip=0&show=1000
        page_url = '/list/cs/%02d%02d?skip=%d&show=%d' % (_year, _month, skip, show)
        page = spider.get_page(page_url)
        pattern_pdf = re.compile(S_PATTERN_PDF, re.S)
        # get all the file id
        task_list = re.findall(pattern_pdf, page.decode('utf-8'))
        task_list_size = len(task_list)
        workers = []
        if task_list:
            for index in range(1, WORKER_NUM):
                worker = Worker(index, "Thread-%d" % index)
                worker.start()
                workers.append(worker)
            for worker in workers:
                worker.join()
        else:
            print('files match failed:[%s]' % S_PATTERN_PDF)
            return False
        print("Ranging from %d to %d was downloaded!" % (skip + 1, skip + task_list_size))
        skip = skip + show
        time.sleep(10)
    return True


if __name__ == '__main__':
    # Init date
    _year = END_YEAR
    _month = END_MONTH
    while _year > BEGIN_YEAR or (_year == BEGIN_YEAR and _month > BEGIN_MONTH):
        download(_year, _month)
        if _month == 1:
            _month = 12
            _year = _year - 1
        else:
            _month = _month - 1
    print("All tasks finished! Exiting Main Thread")
