'''
    Copyright (c) 2015 Tim Savannah Under terms of the LGPLv2.
    See LICENSE in the root directory for full terms.

    WatchMan.py - Contains the main "runner" for WatchTower
'''
import os
import multiprocessing
import signal
import sys
import traceback
import time

from .Triggers import Trigger

DEFAULT_POLL_TIME = 5 # Default poll time, in second

DEFAULT_STOP_CHECK_INTERVAL = .25 # Interval to check if should continue. Sleeps in these increments up to pollTime.

SMALL_NUMBER = .0001 # A small number slightly greater than zero as the minimum time for poll/stop interval


class WatchMan(multiprocessing.Process):
    '''
        WatchMan - The main guard on duty. He/She watches a directory against a given list
          of triggers, and performs  the associated actions on the matched items.
    '''

    def __init__(self, rootDir, triggers, canMatchMultiple=False, pollTime=DEFAULT_POLL_TIME, stopCheckInterval=DEFAULT_STOP_CHECK_INTERVAL):
        '''
            __init__ - Create a WatchMan worker

            @param rootDir <str> - A string path to the directory to watch

            @param triggers list<watchtower.Trigger.Trigger> - list of Triggers to use on this directory

            @param canMatchMultiple bool - If true, the items can be matched by multiple triggers. Use this if you want an item to be
                handled multiple times, like overlapping data. Usually, and by default, this should be False.

            @param pollTime <float> - Number of seconds to rest in between polling the directory. Defaults to DEFAULT_POLL_TIME

            @param stopCheckInterval <float> - Number of seconds to sleep at one time; intervals of #pollTime. When time to sleep,
                it sleeps in increments of this length, testing if a stop signal was received  after each period.
                Example: if poll time is 1s and stopCheckInterval is .25, it will sleep 4 times and check if the stop
                signal was given after each sleep. 
        '''
        multiprocessing.Process.__init__(self)
        self.rootDir = rootDir
        self.triggers = triggers
        self.canMatchMultiple = canMatchMultiple
        i = 0

        for trigger in triggers:
            if not isinstance(trigger, Trigger):
                raise ValueError("Element %d, '%s' must implement watchtower.Trigger" %(i, str(trigger)))
            i += 1

        if rootDir.endswith('/'):
            rootDir = rootDir[:-1]

        if len(rootDir) == 0:
            rootDir = '.'

        if not os.path.isdir(rootDir):
            raise ValueError('"%s" is not a valid directory, ' %(rootDir,))

        self.rootDir = rootDir

        self.stopCheckInterval = float(stopCheckInterval)
        self.pollTime = float(pollTime)

        if self.stopCheckInterval < SMALL_NUMBER:
            raise ValueError('stopCheckInterval must be a positive number > %f' %(SMALL_NUMBER,) )
        if self.pollTime < SMALL_NUMBER:
            raise ValueError('pollTime must be a positive number > %f' %(SMALL_NUMBER,))

        if self.pollTime  < self.stopCheckInterval:
            sys.stderr.write('Warning, given poll time %f exceeds the check interval of %f. Will be rounded up to check interval.\n' %(self.pollTime, self.stopCheckInterval))
            self.pollTime = self.stopCheckInterval
        self.keepGoing = True

    def die(self, *args, **kwargs):
        '''
            die - Terminate this worker

            @param args/kwargs - junk for signal handler
        '''
        if self.keepGoing is False:
            return

        self.keepGoing = False
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGINT, signal.SIG_DFL)

    def cleanup(self):
        pass

    def run(self):
        '''
            run - start point of this process
        '''
        canMatchMultiple = self.canMatchMultiple # Make sure someone doesn't change this whilst executing..

        # Connect to our signal handler
        signal.signal(signal.SIGTERM, self.die)
        signal.signal(signal.SIGINT, self.die)

        while self.keepGoing is True:

            # Get directory contents
            try:
                directoryContents = {x for x in os.listdir(self.rootDir) if x and os.path.isfile(self.rootDir + '/' + x)}
            except Exception as e:
                sys.stderr.write('Issue getting directory contents [%s]: \n' %(self.rootDir,))
                sys.stderr.write(traceback.format_exc(sys.exc_info()) + '\n')
                time.sleep(self.pollTime / 5)
                continue

            # Construct absolute paths
            try:
                directoryContentsAbsolute = {item : (self.rootDir + '/' + item) for item in directoryContents}
            except SyntaxError: # Older python support
                directoryContentsAbsolute = {}
                for item in directoryContents:
                    directoryContentsAbsolute[item] = self.rootDir + '/' + item
            

            remainingContents = directoryContents
            if canMatchMultiple is True:
                matchedThisIteration = set()

            for trigger in self.triggers:
                try:
                    matches = trigger.getFilenameMatches(remainingContents)
                except Exception as e:
                    sys.stderr.write('Error getting matches on trigger %s [%s]\n%s\n' %
                        (trigger.getPatternStr(), 
                        trigger.__class__.__name__, 
                        traceback.format_exc(sys.exc_info())
                        )
                    )
                    continue
                if canMatchMultiple is False:
                    remainingContents = remainingContents.difference(matches)
                else:
                    matchedThisIteration = matchedThisIteration.union(matches)

                namesAndData = {}
                for match in matches:
                    try:
                        fullPath = directoryContentsAbsolute[match]
                        with open(fullPath, 'r') as f:
                            contents = f.read()
                    except Exception as e:
                        sys.stderr.write('Error reading file contents: %s\n%s\n' %(fullPath, traceback.format_exc(sys.exc_info())) )
                        continue

                    if contents.strip():
                        data = contents.split('\n')
                        if data[-1] == '':
                            data = data[:-1]
                    else:
                        data = []
                    namesAndData[match] = data

                allMatches = namesAndData.keys()
                for match in allMatches:
                    data = namesAndData[match]
                    try:
                        trigger.runAction(match, data)
                    except Exception as e:
                        # TODO: retries?
                        sys.stderr.write('Error handling action %s on %s. Data was: %s. Deleting task.\n%s\n' %(trigger.__class__.__name__, match, str(data), traceback.format_exc(sys.exc_info())))

                    # If multiple matches per round is allowed, don't remove here.
                    if self.canMatchMultiple is True:
                        continue
                    fullPath = directoryContentsAbsolute[match]
                    try:
                        os.remove(fullPath)
                    except Exception as e:
                        sys.stderr.write('Unable to remove completed task: %s\n' %(fullPath,))

            # END for trigger
            if self.canMatchMultiple is True:
                for match in matchedThisIteration:
                    fullPath = directoryContentsAbsolute[match]
                    try:
                        os.remove(fullPath)
                    except Exception as e:
                        sys.stderr.write('Unable to remove completed task: %s\n' %(fullPath,))

            timeSlept = 0.0
            while timeSlept < self.pollTime:
                time.sleep(self.stopCheckInterval)
                timeSlept += self.stopCheckInterval
                if self.keepGoing is False:
                    break
            
        self.die()
        sys.exit(0)
