import time
import re

import threading
import win32clipboard

from queue import Queue, Empty

test = """
       1        3       -4        3   678  1347  1.32681      6927     i  g1       1 
       2        5       -1      -14   310   808  0.80747      1714     i  g1       1 
       3        5       -2      -11   330   931  0.86173     10627     i  g1       1 
"""

class ClipboardWatchdog:
    """
    Class watching content of a clipboard. Relies on win32clipboard, part of pywin32
    """

    DELAY = 1.  # delay between test cycles

    STOP_MSG = "quit"

    def __init__(self, parent=None):
        super(ClipboardWatchdog, self).__init__()

        # parent object
        self.parent = parent

        # data lock
        self.data_lock = threading.Lock()
        self.data = None

        # queue to stop clipboard if necessary
        self.qstop_thread = Queue()

        self.th_clipboard = None

    def stop_polling(self):
        """
        Stops polling of the thread
        """
        if isinstance(self.th_clipboard, threading.Thread) and self.th_clipboard.is_alive():
            self.qstop_thread.put(self.STOP_MSG)
            self.qstop_thread.join()

    def debug(self, msg):
        if self.parent is not None:
            try:
                self.parent.debug(msg)
            except AttributeError:
                pass

    def start_polling(self):
        """
        Starts polling of a thread checking the clipoard values
        """
        self.debug("Starting clipboard polling")

        # stops last running thread if it was alive
        self.stop_polling()

        # starts thread watching the clipboard
        self.th_clipboard = threading.Thread(target=self._track_clipboard, args=[])
        self.th_clipboard.setDaemon(True)
        self.th_clipboard.start()

    def process_data(self, data):
        """
        Processes data if necessary and updates the parent class if necessary
        """
        bnew = False

        if self.data != data:
            self.data = data
            bnew = True

            data = self.preprocess(data)
            if data is not None:
                # self.debug(f"New data length is {len(data)};")
                pass

        if self.parent is not None and bnew and data is not None:
            try:
                self.parent.process_cbdata(data)
            except AttributeError:
                pass

    def preprocess(self, data):
        """
        Dummy function to be adjusted fro different tasks
        """
        return data

    def _track_clipboard(self):
        """
        Major thread watching clipboard content
        """
        while True:
            # performes a test on a thread quit event
            if self.test_quit():
                break

            ts = time.time()

            data = ""

            try:
                # make a snapshot only
                win32clipboard.OpenClipboard()
                data = win32clipboard.GetClipboardData()
                win32clipboard.CloseClipboard()
            except TypeError:
                pass

            if isinstance(data, str):
                with self.data_lock:
                    self.process_data(data)

            # performes a test on a thread quit event
            if self.test_quit():
                break

            # make a fixed interval between tests
            dt = self.DELAY - (time.time() - ts)
            if dt > 0:
                time.sleep(dt)
        self.debug("Clipboard polling stopped")

    def test_quit(self):
        """
        Performes a test of a thread quit event
        """
        res = False
        try:
            self.qstop_thread.get(block=False)
            self.qstop_thread.task_done()
            res = True
        except Empty:
            pass
        return res

    def __del__(self):
        self.stop_polling()


class CrysalisPeak:
    """
    Class holding information on individual crysalis points
    """

    def __init__(self, data):
        super(CrysalisPeak, self).__init__()

        # initialize points of the data
        (self.index, self.h, self.k, self.l, self.detx, self.dety, self.dspacing, self.intensity,
         self.indexing, self.group, self.profile) = data

        (self.index, self.h, self.k, self.l, self.detx, self.dety, self.dspacing, self.intensity,
         self.indexing, self.group, self.profile) = (
            int(self.index), float(self.h), float(self.k), float(self.l),
            int(self.detx), int(self.dety),
            float(self.dspacing), float(self.intensity),
            self.indexing, self.group, self.profile)

    def _test_indexing(self, value, test):
        res = False

        for el in test:
            if test in value.lower():
                res = True
                break

    def is_skipped(self):
        return self._test_indexing(self.indexing, 's')

    def is_wrong(self):
        return self._test_indexing(self.indexing, 'w')

    def is_bad(self):
        return self._test_indexing(self.indexing, 'ws')


class CrysalisPeaksCW(ClipboardWatchdog):
    """
    Class watching for copied table of crysalis peaks e.g.:
    1        3       -4        3   678  1347  1.32681      6927     i  g1       1

    """
    TEST_CRYSALIS_PEAKS = None

    def process_data(self, data):
        """
        Processes data if necessary and updates the parent class if necessary
        """
        bnew = False

        if self.data != data:
            self.data = data
            bnew = True

            data = self.preprocess(data)
            if data is None:
                return

            self.debug(f"New data length is {len(data[0])};")

            if self.parent is not None:
                try:
                    self.parent.process_cbdata(data)
                except AttributeError:
                    pass

    def test_crysalis_peaks(self, data):
        """
        Actual test if the information stored in a clipboard is valid
        """
        res = False

        if self.TEST_CRYSALIS_PEAKS is None:
            fmt = "^" + "\s+([^\s]+)" * 11 + "[\r\n\ \t]+$"
            self.TEST_CRYSALIS_PEAKS = re.compile(fmt, re.I + re.MULTILINE)

        p = self.TEST_CRYSALIS_PEAKS
        m = p.match(data)
        if m:
            res = True
        return res

    def preprocess(self, data):
        """
        Performs a  test of data, retrieves information and returns it as a list of peak classes
        None is returned when data is considered to be invalid
        """
        res = data
        mi, ma = None, None     # min and max values

        try:
            if not self.test_crysalis_peaks(data):
                raise ValueError("data is not crysalis peak data")

            res = []
            p = self.TEST_CRYSALIS_PEAKS
            m = p.findall(data)

            for el in m:
                tpts = CrysalisPeak(el)

                if mi is None or mi < tpts.intensity:
                    mi = tpts.intensity
                if ma is None or ma > tpts.intensity:
                    ma = tpts.intensity

                res.append(tpts)

            if len(res) > 0:
                # self.debug("Data is valid")
                res = [res, mi, ma]
        except ValueError as e:
            self.debug(f"Data is invalid: {e}")
            res = None
        return res