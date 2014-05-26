#-*- coding:utf-8 -*-

from inspect import getframeinfo 
from sys import _getframe as getframe 
from _testdouble import _TestDouble 
from dependencyinjection import DependencyInjection
from ludibrio.helpers import format_called

STOPRECORD = False
RECORDING = True


class Mock(_TestDouble):
    """Mocks are what we are talking about here:
    objects pre-programmed with expectations which form a
    specification of the calls they are expected to receive.
    """
    __expectation__ =[]#[MockedCall(attribute, args, kargs),]
    __recording__ = RECORDING
    __last_property_called__ = None
    __dependency_injection__ = None

    def __enter__(self):
        self.__expectation__ = []
        self.__recording__ = RECORDING
        self.__dependency_injection__ = DependencyInjection(double = self)
        return self

    def __methodCalled__(self, *args, **kargs):
        property = getframeinfo(getframe(1))[2]
        return self._property_called(property, args, kargs)

    def _property_called(self, property, args=[], kargs={}):
        if self.__recording__:
            self._new_expectation(MockedCall(property, args = args, kargs = kargs, response = self))
            return self 
        else:
            return self._expectancy_recorded(property, args, kargs)

    def __exit__(self, type, value, traceback):
        self.__dependency_injection__.restore_import()
        self.__recording__ = STOPRECORD

    def __setattr__(self, attr, value):
        if attr in dir(Mock):
            object.__setattr__(self, attr, value)
        else:
            self._property_called('__setattr__', args=[attr, value])

    def _new_expectation(self, attr):
        self.__expectation__.append(attr)

    def __rshift__(self, response):
            self.__expectation__[-1].set_response(response)
    __lshift__ = __rshift__ 

    def _expectancy_recorded(self, attr, args=[], kargs={}):
        try:
            if self._is_ordered():
                return self._call_mocked_ordered(attr, args, kargs)
            else:
                return self._call_mocked_unordered(attr, args, kargs)
        except (CallExpectation, IndexError):
            raise MockExpectationError(self._unexpected_call_msg(attr, args, kargs))

    def _unexpected_call_msg(self, attr, args, kargs):
        if attr == "__call__":
            attribute = self.__last_property_called__
        else:
            attribute = attr
        return "Mock Object received unexpected call:%s" % format_called(attribute, args, kargs)

    def _is_ordered(self):
        return self.__kargs__.get('ordered', True)

    def _call_mocked_unordered(self, attr, args, kargs):
        for number, call in enumerate(self.__expectation__):
            if call.has_callable(attr, args, kargs):
                call_mocked = self.__expectation__.pop(number)
                return call_mocked.call(attr, args, kargs)
        raise CallExpectation("Mock object has no called %s" %attr)

    def _call_mocked_ordered(self, attr, args, kargs):
        call_mocked = self.__expectation__.pop(0)
        return call_mocked.call(attr, args, kargs)

    def __getattr__(self, x):
        self.__last_property_called__ = x
        return self._property_called('__getattribute__',[x])

    def validate(self):
        self.__dependency_injection__.restore_object()
        if self.__expectation__:
            raise MockExpectationError(self._call_waiting_msg())

    def __del__(self):
        self.__dependency_injection__.restore_object()
        if self.__expectation__:
            print(self._call_waiting_msg())
    
    def _call_waiting_msg(self):
        call_wait = self.__expectation__.pop(0)
        if call_wait.attribute == "__call__":
            attribute = self.__last_property_called__
        else:
            attribute = call_wait.attribute
        return "Call waiting: %s" % format_called(attribute, call_wait.args, call_wait.kargs)


class MockedCall(object):
    def __init__(self, attribute, args=[], kargs={}, response = None):
        self.attribute = attribute 
        self.args = args 
        self.kargs = kargs 
        self.response = response 

    def __repr__(self):
        return str((self.attribute, self.args, self.kargs))

    def set_response(self, response):
        self.response = response

    def has_callable(self, attr, args, kargs):
        return (self.attribute, self.args, self.kargs) == (attr, args, kargs)

    def call(self, attribute, args=[], kargs={}):
        if(self.attribute == attribute 
        and self.args == args 
        and self.kargs == kargs):
            if isinstance(self.response, Exception):
                raise self.response 
            else:
                return self.response 
        else:
            raise CallExpectation('Mock Object received unexpected call.')


class MockExpectationError(AssertionError):
    """Extends AssertionError for unittest compatibility"""

class CallExpectation(AssertionError):
    """Extends AssertionError for unittest compatibility"""
