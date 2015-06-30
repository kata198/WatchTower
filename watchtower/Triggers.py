'''
    Copyright (c) 2015 Tim Savannah Under terms of the LGPLv2.
    See LICENSE in the root directory for full terms.

    Triggers.py - Contains the various types of "Triggers". A trigger defines a pattern
    and respective action to perform.
'''
import fnmatch
import re
import types

from .Action import Action

try:
    # python 2
    StringTypes = types.StringTypes
except:
    # python 3
    StringTypes = (str,)

StringTypesOrCompiledRE = StringTypes + (re._pattern_type, )

# Possible validation errors raised by #_genericValidatePattern
_VALIDATE_STRING_BAD_TYPE = 1
_VALIDATE_STRING_EMPTY = 2
_VALIDATE_STRING_BAD_SLASH = 3
_VALIDATE_STRING_DOTS = 4

allDotsRE = re.compile('^[\.]+$')  # A string consisting only of dots
validGlobRE = re.compile('[\*\?]') # A string containing at least one directive-character in a glo

def _genericValidatePattern(theString, allowedTypes=StringTypes):
    '''
        _genericValidatePattern - Perform some basic validation common to all trigger patterns.

        @param theString <str> - String to validate
        @param allowedTypes list<types> - List/tuple of valid types. @see #StringTypes or #StringTypesOrCompiledRE globals in Triggers.py

        @return - one of the _VALIDATE_STRING_* errors above if that error detected, otherwise None.
    '''
    if type(theString) not in allowedTypes:
        return _VALIDATE_STRING_BAD_TYPE

    if not theString:
        return _VALIDATE_STRING_EMPTY
 
    if bool(allDotsRE.match(theString)) is True:
        return _VALIDATE_STRING_DOTS

    if '/' in theString:
        return _VALIDATE_STRING_BAD_SLASH

    return None

class Trigger(object):
    '''
        Trigger - A pattern and associated action pair.
    '''

    def __init__(self, pattern, action):
        '''
            __init__ - Create this object

            @param pattern <?> - The pattern that, if matched, performs the given action. See implementing class for valid types/details
            @param action <Watchtower.Action> - The action which will be executed should the pattern match an item

            @raises ValueError - if argumments are invalid
        '''
        # Validate this pattern
        self._validatePattern(pattern)

        # Process the given pattern if necessary
        self.pattern = self._processPattern(pattern)

        if not isinstance(action, Action):
            raise ValueError('Action "%s" [%s] must implement watchtower.Action' %(str(action), str(type(pattern))))

        self.action = action


    def getFilenameMatches(self, directoryContents):
        '''
            getFilenameMatches - Implemented by the various child classes, this method is given
                a list of filenames contained within the directory, and returns thosee that match this item.

                @param directoryContents list<str> - A list of names

                @return list<str> - A list of matched names
        '''
        raise NotImplemented('%s must implement getFilenameMatches.' %(self.__class__.__name__))

    # TODO:threaded?
    def runAction(self, matchName, actionData):
        '''
            runAction - Execute the action associated with this trigger on a paticular item

            @param matchName <str>     - The filename that matched
            @param actionData list<str> - The contents of the file (arguments). One item per line.
                If the file ends in a newline, it is stripped.
        '''
        self.action.handleAction(matchName, actionData)
        

    @classmethod
    def _validatePattern(cls, theString):
        '''
            _validatePattern - Performs validation and raises an exception with meaningful message on validation error.
                Extend this to add additional validatio

                @param theString <str> - The string to validate

                @raises - ValueError on validation error
        '''
        error = _genericValidatePattern(theString, cls._getValidTypes())

        if error is None:
            return

        myClassName = cls.__name__
        if error == _VALIDATE_STRING_BAD_TYPE:
            raise ValueError("Invalid type '%s' passed to %s. Must be a %s." %(type(theString), myClassName, cls._getValidTypeStr()))
        elif error == _VALIDATE_STRING_EMPTY:
            raise ValueError("Empty string passed to %s." %(myClassName,))
        elif error == _VALIDATE_STRING_DOTS:
            raise ValueError("String '%s' passed to '%s' cannot be all dots." %(theString, myClassName))
        elif error == _VALIDATE_STRING_BAD_SLASH:
            raise ValueError("String '%s' passed to '%s' cannot contain forward slash. Use basename only." %(theString, myClassName))

    @classmethod
    def _getValidTypeStr(cls):
        '''
            _getValidTypeStr - Returns a human-readable string that represents the "types" allowed for this Trigger.
        '''
        return 'string type'

    @classmethod
    def _getValidTypes(cls):
        '''

            _getValidTypes - Returns a list/tuple of types allowed for this trigger. Used for validation. Defaults to StringTypes
        '''
        return StringTypes

    @classmethod
    def _processPattern(cls, pattern):
        '''
            _processPattern - Perform any extra processing on pattern (e.x. compile a regex from str)
        '''
        return pattern

    def getPatternStr(self):
        '''
            getPatternStr - Get a string representing the original input given to this trigger
        '''
        return self.pattern

class TriggerRE(Trigger):
    '''
        A Trigger that uses a regular expression to match
    '''

    def getFilenameMatches(self, directoryContents):
        pattern = self.pattern
        return [item for item in directoryContents if bool(pattern.match(item))]

    @classmethod
    def _getValidTypeStr(cls):
        return 'compiled regular expression or string type'

    @classmethod
    def _getValidTypes(cls):
        return StringTypesOrCompiledRE

    @classmethod
    def _processPattern(cls, pattern):
        if isinstance(pattern,  re._pattern_type):
            return pattern
        return re.compile(pattern)

    def getPatternStr(self):
        return self.pattern.pattern

        
class TriggerGlob(Trigger):
    '''
        A trigger that uses globs to match (*, ?)
    '''

    def getFilenameMatches(self, directoryContents):
        return fnmatch.filter(directoryContents, self.pattern)

    @classmethod
    def _getValidTypeStr(cls):
        return 'glob pattern string'

    @classmethod
    def _validatePattern(cls, pattern):
        Trigger._validatePattern(pattern)
        if bool(validGlobRE.match(pattern)) is False:
            raise ValueError("Glob pattern '%s' contains neither a '?' nor '*'." %(pattern,))


class TriggerExactMatch(Trigger):
    '''
        TriggerExactMatch - A Trigger which requires an exact match
    '''

    def getFilenameMatches(self, directoryContents):
        if self.pattern in directoryContents:
            return [self.pattern]
        return []

class TriggerCaseInsensitiveMatch(Trigger):
    '''
        TriggerCaseInsensitiveMatch - A trigger which requiers an
            exact match of characters, but ignores case.
    '''

    def getFilenameMatches(self, directoryContents):
        for item in directoryContents:
            if item.lower() == self.pattern:
                return [item]
        return []


    def _processPattern(self, pattern):
        return pattern.lower()
