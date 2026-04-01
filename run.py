"""
Nullifire Intumescent Calculator — Desktop Entry Point

Usage:
    python run.py          # Launch with PyWebView desktop window
    python run.py --dev    # Launch Flask only (use browser at http://127.0.0.1:5000)
"""
import sys
import threading

from app import create_app


def start_flask(app, ready_event):
    ready_event.set()
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)


def main():
    app = create_app()

    if '--dev' in sys.argv:
        print('Starting in dev mode — open http://127.0.0.1:5000 in your browser')
        app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=True)
        return

    import webview

    ready_event = threading.Event()
    flask_thread = threading.Thread(
        target=start_flask, args=(app, ready_event), daemon=True
    )
    flask_thread.start()
    ready_event.wait(timeout=5)

    webview.create_window(
        'Nullifire Intumescent Calculator',
        'http://127.0.0.1:5000',
        width=1400,
        height=900,
        min_size=(1024, 700),
    )
    webview.start()


if __name__ == '__main__':
    main()
