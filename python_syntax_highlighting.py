import keyword
import sys
from PyQt6 import QtCore, QtWidgets, QtGui
from PyQt6.QtGui import QColorConstants as cc
import keyword
import re


BUILTINS = dir(__builtins__)
KEYWORDS = keyword.kwlist

# Python operators
operators = [
    '=',
    # Comparison
    '==', '!=', '<', '<=', '>', '>=',
    # Arithmetic
    '+', '-', '*', '/', '//', '%', '**',
    # In-place
    '+=', '-=', '*=', '/=', '%=',
    '^', '|', '&', '~', '>>', '<<',
]

# Python braces
braces = [
    '{', '}', '(', ')', '[', ']',
]


class PythonHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, doc):
        super().__init__(doc)

        self.styles = {
            'keyword': self.syntax_frmt(cc.Svg.orange),
            'operator': self.syntax_frmt(cc.Svg.lightgrey),
            'brace': self.syntax_frmt(cc.Svg.lightgrey),
            'defclass': self.syntax_frmt(cc.Svg.orange, 'bold'),
            'string': self.syntax_frmt(cc.Svg.lightgreen),
            'comment': self.syntax_frmt(cc.Svg.darkslategray, 'italic'),
            'self': self.syntax_frmt(cc.Svg.purple, 'italic'),
            'numbers': self.syntax_frmt(cc.Svg.dodgerblue),
            'builtins': self.syntax_frmt(cc.Svg.blueviolet)
        }

    def highlightBlock(self, text: str):
        font_frmt = QtGui.QTextCharFormat()
        font_frmt.setFontFamily("Fixedsys")
        self.setFormat(0, len(text), font_frmt)
        for desc, style in zip((operators, BUILTINS, KEYWORDS, braces), ('operator', 'builtins', 'keyword', 'brace')):
            for i in desc:
                expression = QtCore.QRegularExpression(rf"\b{i}\b")
                match = expression.globalMatch(text)
                while match.hasNext():
                    next_ = match.next()
                    self.setFormat(next_.capturedStart(), next_.capturedLength(), self.styles[style])

        digit = QtCore.QRegularExpression(rf'\d')
        match = digit.globalMatch(text)
        while match.hasNext():
            next_ = match.next()
            self.setFormat(next_.capturedStart(), next_.capturedLength(), self.styles['numbers'])

        comment = QtCore.QRegularExpression(rf'#.*')
        match = comment.globalMatch(text)
        while match.hasNext():
            next_ = match.next()
            self.setFormat(next_.capturedStart(), next_.capturedLength(), self.styles['comment'])

        line_strings_patterns = r"""(?:".*")|(?:'.*')"""
        strings = [x.span(0) for x in re.finditer(line_strings_patterns, text)]
        if strings:
            for i, j in strings:
                self.setFormat(i, j - i, self.styles['string'])

        multi_line_strings_double = r"(?:\"\"\")"
        self.setCurrentBlockState(1)
        multi_line_strings_double = [x.span(0) for x in re.finditer(multi_line_strings_double, text)]
        print(len(multi_line_strings_double))
        if len(multi_line_strings_double) == 2:
            self.setFormat(multi_line_strings_double[0][0],
                           len(text) - multi_line_strings_double[1][0],
                           self.styles['string'])
            return
        if multi_line_strings_double and self.previousBlockState() == 1:
            self.setCurrentBlockState(2)
            self.setFormat(multi_line_strings_double[0][0],
                           len(text) - multi_line_strings_double[0][0],
                           self.styles['string'])
            return
        elif multi_line_strings_double and self.previousBlockState() == 2:
            self.setCurrentBlockState(1)
            self.setFormat(0,
                           multi_line_strings_double[0][1],
                           self.styles['string'])
        elif not multi_line_strings_double and self.previousBlockState() == 2:
            self.setCurrentBlockState(2)
            self.setFormat(0,
                           len(text),
                           self.styles['string'])
            return

    @staticmethod
    def syntax_frmt(color, style=None):
        frmt = QtGui.QTextCharFormat()
        frmt.setFontFamily('Fixedsys')
        frmt.setForeground(color)
        if 'bold' == style:
            frmt.setFontWeight(700)
        if 'italic' == style:
            frmt.setFontItalic(True)
        else:
            frmt.setFontItalic(False)
            frmt.setFontWeight(400)

        return frmt

