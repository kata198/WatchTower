'''
    Copyright (c) 2015 Tim Savannah Under terms of the LGPLv2.
    See LICENSE in the root directory for full terms.

    Action.py - The action model which associates with a Trigger.
'''
import sys

class Action(object):
    '''
        Action - The model which encapsulates the action performed on Trigger matches.
    '''

    def __init__(self):
        pass

    def handleAction(self, matchedName, actionData):
        '''
            handleAction - Run an action on the matched entry

            @param matchedName <str> - The name of the file that was matched
            @param actionData list<str> - A list of arguments. These are the file contents, one per line. If file ends in newline, that line is omitted.
        '''
        raise NotImplemented('%s must implement handleAction' %(self.__class__.__name__,))

class EchoAction(Action):
    '''
        EchoAction - A sample action that can be used for debugging.
    '''

    def __init__(self, name='', outputHandle=sys.stdout):
        '''
            __init__ - Create this object

            @param name <str> - An optional name which will be printed in the output, to associate output to a codepath etc
            @param outputHandle <object> - A file or buffer or anything that implements the "write" function.
        '''

        self.name = name
        self.outputHandle = outputHandle

    def handleAction(self, matchedName, actionData):
        self.outputHandle.write('EchoAction %s called.\nName=%s\nData=%s\n\n' %(self.name, matchedName, actionData))
        if hasattr(self.outputHandle, 'flush'):
            self.outputHandle.flush()


