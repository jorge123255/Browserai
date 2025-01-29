# browser_tools.py
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage

def get_page_text(webview: QWebEngineView, callback):
    """
    Asynchronously fetches the text content of the current page.
    callback(text) is invoked once it's ready.
    """
    page = webview.page()
    page.toPlainText(callback)

def execute_js(webview: QWebEngineView, script, callback=None):
    """
    Execute a JavaScript snippet in the page. Optional callback for result.
    """
    page = webview.page()
    page.runJavaScript(script, callback)

    #You can expand these helpers for element selection, form filling, etc.
