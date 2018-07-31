# MIT License
#
# Copyright (c) 2017-18 Felix Simkovic
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

__author__ = 'Felix Simkovic'
__version__ = '1.0'

from time import sleep

import logging
import os

from pyjob.cexec import cexec
from pyjob.queue import ClusterQueue

logger = logging.getLogger(__name__)


class SunGridEngine(ClusterQueue):
    """

    Examples
    --------

    The recommended way to use a :obj:`~pyjob.queue.Queue` is by
    creating a context and perform all actions within. The context will
    not be left until all submitted scripts have executed.

    >>> with SunGridEngine() as queue:
    ...     queue.submit(['script1.py', 'script2.sh', 'script3.pl'])
    
    A :obj:`~pyjob.queue.Queue` instance can also be assigned to a
    variable and used throughout. However, it is required to close the 
    :obj:`~pyjob.queue.Queue` explicitly.

    >>> queue = SungGridEngine()
    >>> queue.submit(['script1.py', 'script2.sh', 'script3.pl'])
    >>> queue.close()

    """

    TASK_ENV = 'SGE_TASK_ID'

    def __init__(self, *args, **kwargs):
        super(SunGridEngine, self).__init__(*args, **kwargs)

    def kill(self):
        if len(self.queue) > 0:
            cmd = ['qdel', ' '.join(map(str, self.queue))]
            cexec(cmd)
            self.queue = []

    def submit(self,
               script,
               array=None,
               deps=None,
               name=None,
               pe_opts=None,
               priority=None,
               queue=None,
               runtime=None,
               shell=None,
               threads=None):

        script, log = self.__class__.check_script(script)
        nscripts = len(script)

        if nscripts > 1:
            master, _ = self.prep_array_script(script, '.')
            script = [master]
            log = [os.devnull]
            shell = '/bin/sh'
            if array is None:
                array = [1, nscripts, nscripts]

        cmd = ['qsub', '-cwd', '-V', '-w', 'e', '-j', 'y']
        if array and len(array) == 3:
            cmd += ['-t', '{}-{}'.format(array[0], array[1]), '-tc', str(array[2])]
        elif array and len(array) == 2:
            cmd += ["-t", "{}-{}".format(array[0], array[1])]
        if deps:
            cmd += ["-hold_jid", "{}".format(",".join(map(str, deps)))]
        if log:
            cmd += ["-o", log[0]]
        if name:
            cmd += ["-N", name]
        if pe_opts:
            cmd += ["-pe"] + pe_opts.split()
        if priority:
            cmd += ["-p", str(priority)]
        if queue:
            cmd += ["-q", queue]
        if runtime:
            cmd += ["-l", "h_rt={}".format(runtime)]
        if shell:
            cmd += ["-S", shell]
        if threads:
            cmd += ["-pe mpi", str(threads)]

        stdout = cexec(cmd + script)
        if nscripts == 1:
            jobid = int(stdout.split()[2])
        else:
            jobid = int(stdout.split()[2].split('.')[0])
        self.queue.append(jobid)

    def wait(self):
        while len(self.queue) > 0:
            i = len(self.queue)
            while i > 0:
                cmd = ['qstat', '-j', str(self.queue[i - 1])]
                stdout = cexec(cmd, permit_nonzero=True)
                for line in stdout.split(os.linesep):
                    if 'jobs do not exist' in line:
                        self.queue.pop(i - 1)
                i -= 1
            sleep(5)
