from PyQt5.QtCore import QRegularExpression
from PyQt5.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        self.highlightingRules = []

        # Keyword formatting
        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor(255, 153, 51))  # Orange
        keywordFormat.setFontWeight(QFont.Bold)
        keywords = [
            "and",
            "as",
            "assert",
            "break",
            "class",
            "continue",
            "def",
            "del",
            "elif",
            "else",
            "except",
            "False",
            "finally",
            "for",
            "from",
            "global",
            "if",
            "import",
            "in",
            "is",
            "lambda",
            "None",
            "nonlocal",
            "not",
            "or",
            "pass",
            "raise",
            "return",
            "True",
            "try",
            "while",
            "with",
            "yield",
        ]
        for word in keywords:
            pattern = QRegularExpression(r"\b" + word + r"\b")
            self.highlightingRules.append((pattern, keywordFormat))

        # String formatting
        stringFormat = QTextCharFormat()
        stringFormat.setForeground(QColor(153, 204, 0))  # Green
        self.highlightingRules.append(
            (QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), stringFormat)
        )
        self.highlightingRules.append(
            (QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"), stringFormat)
        )

        # Number formatting
        numberFormat = QTextCharFormat()
        numberFormat.setForeground(QColor(255, 102, 102))  # Light red
        self.highlightingRules.append((QRegularExpression(r"\b[0-9]+\b"), numberFormat))

        # Comment formatting
        commentFormat = QTextCharFormat()
        commentFormat.setForeground(QColor(153, 153, 153))  # Gray
        self.highlightingRules.append((QRegularExpression(r"#[^\n]*"), commentFormat))

        # Function formatting
        functionFormat = QTextCharFormat()
        functionFormat.setForeground(QColor(102, 204, 255))  # Light blue
        self.highlightingRules.append(
            (QRegularExpression(r"\b[A-Za-z0-9_]+(?=\()"), functionFormat)
        )

    def highlightBlock(self, text):
        for pattern, format in self.highlightingRules:
            matchIterator = pattern.globalMatch(text)
            while matchIterator.hasNext():
                match = matchIterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)
