#!/usr/bin/env python3
"""
service_pywin32.py - Install Valido as Windows Service using pywin32 (alternative to NSSM)
"""

import os
import sys
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import subprocess


class ValidoService(win32serviceutil.ServiceFramework):
    _svc_name_ = "Valido"
    _svc_display_name_ = "Valido PDF Validation Service"
    _svc_description_ = "Enterprise PDF validation service for automated document processing"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.process = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        if self.process:
            self.process.terminate()
            self.process.wait()

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))

        # Get the executable path
        exe_path = os.path.join(os.path.dirname(__file__), 'dist', 'valido.exe')
        if not os.path.exists(exe_path):
            servicemanager.LogErrorMsg(f"Executable not found: {exe_path}")
            return

        try:
            # Start the Valido process
            self.process = subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path))
            servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                                  0xF000,  # Custom event
                                  (self._svc_name_, f"Started process PID: {self.process.pid}"))

            # Wait for stop event
            win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

        except Exception as e:
            servicemanager.LogErrorMsg(f"Service failed: {e}")


if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(ValidoService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(ValidoService)