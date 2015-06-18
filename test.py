#!/usr/bin/env python2

from watchtower.WatchMan import WatchMan
from watchtower.Action import EchoAction
from watchtower.Triggers import TriggerRE

wm = WatchMan('./testdir', [
        TriggerRE('^a',  EchoAction('hello')),
        TriggerRE('^a',  EchoAction('goodbye')),
    ],
    canMatchMultiple = True
    )

wm.run()
