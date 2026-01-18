from unittest import TestCase
from .state import INVARIANT_MARKER

from typing import TYPE_CHECKING, Callable
if TYPE_CHECKING:
    from .keaUtils import JsonResult

class BetterConsoleLogExtensionMixin:
    
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.showAll = True
        from .keaUtils import getFullPropName
        self.__getFullPropName = getFullPropName
    
    def getDescription(self: "JsonResult", test: "TestCase"):
        doc_first_line = test.shortDescription()
        if not self.is_property(test):
            return f"(%s)" % self.__getFullPropName(test)
        if self.descriptions and doc_first_line:
            doc_first_line = "# " + doc_first_line
            return '\n'.join((str(test), doc_first_line))
        else:
            return str(test)
    
    def startTest(self: "JsonResult", test):
        if self.showAll:
            if getattr(test, INVARIANT_MARKER, False):
                self.stream.writeln(f"[INFO] Executing invariant: {self.__getFullPropName(test)}")
                self.stream.flush()
                self._newline = True
            else:
                self.stream.write("[INFO] Start executing property: ")
                self.stream.writeln(self.getDescription(test))
                self.stream.flush()
                self._newline = True