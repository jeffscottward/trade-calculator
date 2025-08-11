import sys
import tkinter as tk

# Monkey-patch for Python 3.13 compatibility
if sys.version_info >= (3, 13):
    original_trace_add = tk.Variable.trace_add
    
    def patched_trace(self, mode, callback):
        if mode == 'w':
            mode = 'write'
        elif mode == 'r':
            mode = 'read'
        elif mode == 'u':
            mode = 'unset'
        return original_trace_add(self, mode, callback)
    
    def patched_trace_variable(self, mode, callback):
        return patched_trace(self, mode, callback)
    
    tk.StringVar.trace = patched_trace
    tk.Variable.trace = patched_trace
    tk.Variable.trace_variable = patched_trace_variable
    tk.StringVar.trace_variable = patched_trace_variable