from __future__ import annotations

import sys

from owndash import APP_ID, APP_NAME, __version__


def main() -> int:
    try:
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("OwnDash requires PySide6. Install the project dependencies first.", file=sys.stderr)
        return 2

    from owndash.assets import app_icon_path
    from owndash.gui.app_window import SafeShutdownWindow as MainWindow
    from owndash.service.session_shutdown import bind_session_shutdown
    from owndash.service.startup import resolve_startup_arguments
    from owndash.single_instance import SingleInstanceServer, notify_existing_instance

    qt_argv, start_minimized = resolve_startup_arguments(sys.argv)
    app = QApplication(qt_argv)
    # The editor window may be hidden while the live dashboard keeps running in
    # the system tray.  Explicit quit actions still terminate the process.
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(f"{APP_NAME} {__version__}")
    app.setOrganizationName(APP_NAME)
    app.setDesktopFileName(APP_ID)

    # Only one OwnDash process should own the tray icon, sensors, profile state
    # and especially the USB display. A second launch simply raises the first.
    server_name = f"{APP_ID}.single-instance"
    if notify_existing_instance(server_name):
        return 0

    single_instance = SingleInstanceServer(server_name, app)
    if not single_instance.listen():
        print("OwnDash could not create its single-instance endpoint.", file=sys.stderr)
        return 3

    with app_icon_path() as icon_path:
        icon = QIcon(str(icon_path))
        app.setWindowIcon(icon)
        window = MainWindow()
        window.setWindowIcon(icon)
        bind_session_shutdown(app, window)

        def activate_primary_window() -> None:
            window.show()
            window.showNormal()
            window.raise_()
            window.activateWindow()

        single_instance.activation_requested.connect(activate_primary_window)

        if start_minimized:
            window.showMinimized()
        else:
            window.show()
            window.constrain_to_screen()

        # Covers the tiny startup window between listen() and signal hookup.
        if single_instance.consume_pending_activation():
            activate_primary_window()

        return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
