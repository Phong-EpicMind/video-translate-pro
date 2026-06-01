import sys
import os
import time
import uvicorn
import webview
import socket

def find_free_port():
    """Find a free port on localhost"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def run_server(port):
    """Run uvicorn server"""
    # Force set base directory
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app import app
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

if __name__ == '__main__':
    import threading
    
    port = 8000
    # Test if 8000 is occupied, if so find another free port
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('127.0.0.1', 8000))
        s.close()
    except OSError:
        port = find_free_port()
        s.close()

    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    # Give uvicorn a split second to start up
    time.sleep(0.5)

    # Start PyWebview native window
    webview.create_window(
        "TranslateDub AI", 
        f"http://127.0.0.1:{port}", 
        width=1280, 
        height=800,
        min_size=(1024, 768)
    )
    webview.start()
