import os
import subprocess 
import threading
import time
from datetime import datetime, timedelta
import sys
import json
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QMenu, QMenuBar
from PyQt5 import QtCore, QtGui, QtWidgets

from ui import main
class ConfirmDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, seconds=60):
        super().__init__(parent)
        self.setWindowTitle("Sleep confirmation")
        self.setModal(True)
        self.cancelled = False

        self.seconds = seconds

        layout = QtWidgets.QVBoxLayout(self)
        self.message = QtWidgets.QLabel("Are you still here? If you want to sleep the system, please click yes.")
        layout.addWidget(self.message)

        self.count_label = QtWidgets.QLabel("")
        layout.addWidget(self.count_label)

        btn_layout = QtWidgets.QHBoxLayout()
        self.yes_btn = QtWidgets.QPushButton("Yes")
        self.cancel_btn = QtWidgets.QPushButton("Cancel the timer")
        btn_layout.addWidget(self.yes_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._tick)
        self._update_label()
        self.timer.start(1000)

        self.yes_btn.clicked.connect(self._yes)
        self.cancel_btn.clicked.connect(self._cancel)

    def _update_label(self):
        self.count_label.setText(f"Auto-continue in: {self.seconds} s")

    def _tick(self):
        self.seconds -= 1
        if self.seconds <= 0:
            self.timer.stop()
            self.accept()
            return
        self._update_label()

    def _yes(self):
        self.timer.stop()
        self.accept()

    def _cancel(self):
        self.timer.stop()
        self.cancelled = True
        self.reject()


class MyQtApp(main.Ui_MainWindow, QtWidgets.QMainWindow):
    show_confirm = QtCore.pyqtSignal(object)
    start_exit_countdown_signal = QtCore.pyqtSignal()
    def __init__(self):
        super(MyQtApp, self).__init__()
        self.setupUi(self)
        self.setWindowTitle("Sleep Timer")

        # Timer starten
        self.timer = None
        self.countdown_end_time = None
        self.countdown_qtimer = QtCore.QTimer(self)
        self.countdown_qtimer.timeout.connect(self.update_countdown_label)

        # Exit countdown (10-second auto-close after timer finishes)
        self.exit_countdown_seconds = 0
        self.exit_countdown_qtimer = QtCore.QTimer(self)
        self.exit_countdown_qtimer.timeout.connect(self._exit_countdown_tick)
        # Dark mode & StyleSheet
        self.dark_mode = True
        self.load_config()
        self.stylesheet()
        self.action_Dark_Mode.triggered.connect(self.set_dark_mode)
        self.action_Light_Mode.triggered.connect(self.set_light_mode)

        # signal from worker to show confirmation dialog
        self.show_confirm.connect(self._on_show_confirm)
        self.start_exit_countdown_signal.connect(self._on_start_exit_countdown)
        # Connecting signals and slots
        self.cancel_button.clicked.connect(self.cancel_timer)
        self.exit_button.clicked.connect(self.cancel_timer)
        self.two_hours_button.clicked.connect(lambda: self.start_timer(2 * 60 * 60))
        self.one_hour_button.clicked.connect(lambda: self.start_timer(1 * 60 * 60))
        self.thirty_one_min_button.clicked.connect(lambda: self.start_timer(31 * 60))
        self.thirty_one_min_button.clicked.connect(lambda: self.start_timer(1 * 60))
        self.thirty_min_button.clicked.connect(lambda: self.start_timer(30 * 60))

    def start_timer(self, duration):
        # If a timer is already running, cancel it first.
        if self.timer:
            self.timer.cancel()
        # Set end time and start QTimer for UI updates
        self.countdown_end_time = datetime.now() + timedelta(seconds=duration)
        self.countdown_qtimer.start(1000)
        # Timer starten (logic only)
        self.timer = CountdownTimer(duration, self)
        self.timer.start()

    def cancel_timer(self):
        # Reset the timer
        if self.timer:
            self.timer.cancel()
            self.timer = None
        self.countdown_end_time = None
        self.countdown_qtimer.stop()
        self.time_label.setText("Please select a new time.")

    def _on_show_confirm(self, event):
        # event is a threading.Event passed by the timer thread
        dlg = ConfirmDialog(self, seconds=60)
        result = dlg.exec_()
        # if user chose to cancel the timer, stop it
        if getattr(dlg, 'cancelled', False):
            self.cancel_timer()
        # signal the worker thread to continue (or timeout)
        try:
            event.set()
        except Exception:
            pass

    def update_countdown_label(self):
        if not self.countdown_end_time:
            self.time_label.setText("Please select a new time.")
            self.countdown_qtimer.stop()
            return
        remaining = (self.countdown_end_time - datetime.now()).total_seconds()
        if remaining <= 0:
            self.time_label.setText("Shutting down now...")
            self.countdown_qtimer.stop()
            return
        hours, remainder = divmod(int(remaining), 3600)
        minutes, seconds = divmod(remainder, 60)
        time_str = "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
        shutdown_at = self.countdown_end_time.strftime("%H:%M:%S")
        self.time_label.setText(f"The system will shut down in: {time_str} at {shutdown_at}.")

    def _on_start_exit_countdown(self):
        """Start 10-second countdown before auto-closing the main window."""
        # Stop the main countdown timer display
        self.countdown_qtimer.stop()
        self.countdown_end_time = None
        
        # Hide all timer buttons so user sees only the exit countdown
        for btn in [self.two_hours_button, self.one_hour_button,
                   self.thirty_one_min_button, self.one_min_button,
                     self.thirty_min_button, self.cancel_button]:
            btn.setVisible(False)
        self.exit_button.setText("Exit Now")
 
         # Initialise and start the 10-second exit countdown
        self.exit_countdown_seconds = 10
        self._update_exit_label()
        self.exit_countdown_qtimer.start(1000)
 
    def _update_exit_label(self):
         self.time_label.setText(
             f"Media has been paused. This page will automatically close in {self.exit_countdown_seconds} seconds."
         )
 
    def _exit_countdown_tick(self):
        self.exit_countdown_seconds -= 1
        if self.exit_countdown_seconds <= 0:
             self.exit_countdown_qtimer.stop()
             self.close()
             return
        self._update_exit_label()
    def stylesheet(self):
        # StyleSheet
        for button in self.findChildren(QPushButton):
            button.setStyleSheet("QPushButton:hover { background-color: rgba(135, 167, 82, 100%); border: 1px solid #00FF00; }")
        for qmenu in self.findChildren(QMenu):
            qmenu.setStyleSheet("QMenu::item:selected { background-color: rgba(135, 167, 82, 100%); border: 1px solid #00FF00; color: #fff; }")
        for qmenubar in self.findChildren(QMenuBar):
            qmenubar.setStyleSheet("QMenuBar::item:selected { background-color: rgba(135, 167, 82, 100%); border: 1px solid #00FF00; color: #fff; }")

    def set_dark_mode(self):
        # Activate dark mode
        self.dark_mode = True
        self.setStyleSheet("background-color: #222222; color: #ffffff;")
        self.save_config()

    def set_light_mode(self):
        # Activate light mode
        self.dark_mode = False
        self.setStyleSheet("background-color: #ffffff; color: #000000;")
        self.save_config()

    def load_config(self):
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
                self.dark_mode = config["dark_mode"]
                if self.dark_mode:
                    self.set_dark_mode()
                else:
                    self.set_light_mode()
        except FileNotFoundError:
            pass

    def save_config(self):
        config = {"dark_mode": self.dark_mode}
        with open("config.json", "w") as f:
            json.dump(config, f)

    def closeEvent(self, event):
        self.cancel_timer()
        self.save_config()
        event.accept()

def stop_media_and_disconnect():
    
        # VLC
        subprocess.run([
            'osascript', '-e',
            'if application "VLC" is running then tell application "VLC" to quit'
        ])

        # QuickTime
        subprocess.run([
            'osascript', '-e',
            'if application "QuickTime Player" is running then tell application "QuickTime Player" to quit'
        ])

        # IINA
        subprocess.run([
            'osascript', '-e',
            'if application "IINA" is running then tell application "IINA" to quit'
        ])

        # Safari
        subprocess.run([
            'osascript', '-e',
            '''if application "Safari" is running then
                tell application "Safari"
                    repeat with w in windows
                        set tabCount to count of tabs of w
                        repeat with i from tabCount to 1 by -1
                            set t to tab i of w
                            set tabURL to URL of t

                            if tabURL contains "youtube.com/watch" or tabURL contains "netflix.com" or tabURL contains "bilibili.com" or tabURL contains "vimeo.com" then
                                close t
                            else
                                try
                                    set hasVideo to (do JavaScript "
                                        var v = document.querySelector('video');
                                        if(v){v.pause();}
                                        (v!==null).toString();
                                    " in t)
                                    if hasVideo is "true" then
                                        close t
                                    end if
                                end try
                            end if
                        end repeat
                    end repeat
                end tell
            end if'''
        ])
        subprocess.run([
            'osascript', '-e',
            '''if application "Google Chrome" is running then
                tell application "Google Chrome"
                    repeat with w in windows
                        set tabCount to count of tabs of w
                        repeat with i from tabCount to 1 by -1
                            set t to tab i of w
                            set tabURL to URL of t

                            if tabURL contains "youtube.com/watch" or tabURL contains "netflix.com" or tabURL contains "bilibili.com" or tabURL contains "vimeo.com" then
                                close t
                            else
                                try
                                    set hasVideo to (execute t javascript "
                                        var v = document.querySelector('video');
                                        if(v){v.pause();}
                                        (v!==null).toString();
                                    ")
                                    if hasVideo is "true" then
                                        close t
                                    end if
                                end try
                            end if
                        end repeat
                    end repeat
                end tell
            end if'''
        ])


class CountdownTimer:
    def __init__(self, duration, ui):
        self.duration = duration
        self.initial_duration = duration
        self.ui = ui
        self.end_time = datetime.now() + timedelta(seconds=duration)
        self.timer = None
        self.cancelled = False
        # event used to pause the worker when showing confirmation dialog
        self.pause_event = threading.Event()
        self.pause_event.set()

    def start(self):
        self.timer = threading.Thread(target=self.run)
        self.timer.start()

    def run(self):
        try:
            while self.duration and not self.cancelled:
                # Check for 30-minute interval (every 1800s) excluding initial moment
                if self.duration != self.initial_duration and self.duration % 1800 == 0:
                    # pause worker and request UI to show confirmation dialog
                    self.pause_event.clear()
                    try:
                        self.ui.show_confirm.emit(self.pause_event)
                    except Exception:
                        # if signal fails, just continue
                        self.pause_event.set()
                    # wait up to 60 seconds for user response
                    self.pause_event.wait(timeout=60)
                    # continue loop without decrementing during pause
                time.sleep(1)
                self.duration -= 1
            if not self.cancelled:
                stop_media_and_disconnect()
                try:
                    self.ui.start_exit_countdown_signal.emit()
                except Exception:
                    pass
        except KeyboardInterrupt:
            print("\nReset the timer")

    def cancel(self):
        self.cancelled = True
        try:
            # wake any wait on the pause event 
            self.pause_event.set()
        except Exception:
            pass

if __name__ == "__main__":
    def _parse_start_arg(argv):
        """Parse a start-duration argument from command line.

        Supported formats:
        - integers = seconds (e.g. 1800)
        - suffix 'm' for minutes (e.g. 30m)
        - suffix 'h' for hours (e.g. 1h)
        - presets: '30m', '1h', '2h'
        Returns seconds (int) or None.
        """
        if len(argv) < 2:
            return None
        s = str(argv[1]).lower()
        try:
            if s.endswith('m'):
                return int(s[:-1]) * 60
            if s.endswith('h'):
                return int(s[:-1]) * 3600
            return int(s)
        except Exception:
            return None

    start_duration = _parse_start_arg(sys.argv)

    app = QApplication(sys.argv)
    qt_app = MyQtApp()
    qt_app.show()

    # If a start duration was provided, schedule the timer to start
    # once the event loop is running to ensure UI is ready.
    if start_duration:
        QtCore.QTimer.singleShot(100, lambda: qt_app.start_timer(start_duration))

    sys.exit(app.exec_())
