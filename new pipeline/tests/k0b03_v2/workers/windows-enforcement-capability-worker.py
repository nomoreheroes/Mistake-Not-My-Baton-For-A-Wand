"""Synthetic worker for the bounded K0b-03 Windows enforcement qualification.

This file is not a runtime launcher.  It is executed only inside the temporary
AppContainer and Job Object created by the separately authorized capability
probe.  Inputs and outputs are deliberately synthetic and non-secret.
"""

from __future__ import annotations

import argparse
import ctypes as ct
from ctypes import wintypes as wt
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time


TOKEN_QUERY = 0x0008
TOKEN_IS_APP_CONTAINER = 29
TOKEN_CAPABILITIES = 30
TOKEN_APP_CONTAINER_SID = 31
CREATE_NO_WINDOW = 0x08000000
INVALID_SOCKET = ct.c_size_t(-1).value
SOCKET_ERROR = -1
FIONBIO = 0x8004667E
WSAEWOULDBLOCK = 10035
SOL_SOCKET = 0xFFFF
SO_ERROR = 0x1007
QUALIFICATION_PROVENANCE = "v3_CHILD_IDENTITY_PROOF_FAILED"
CURRENT_SCENARIO: str | None = None
CURRENT_OPERATION_STEP: str | None = None
POPEN_STEPS: list[dict[str, object]] = []


class SID_AND_ATTRIBUTES(ct.Structure):
    _fields_ = [("Sid", ct.c_void_p), ("Attributes", wt.DWORD)]


class TOKEN_APPCONTAINER_INFORMATION(ct.Structure):
    _fields_ = [("TokenAppContainer", ct.c_void_p)]


SOCKET_T = ct.c_size_t


class SOCKADDR_IN(ct.Structure):
    _fields_ = [
        ("sin_family", ct.c_ushort),
        ("sin_port", ct.c_ushort),
        ("sin_addr", ct.c_ubyte * 4),
        ("sin_zero", ct.c_ubyte * 8),
    ]


class SOCKADDR_IN6(ct.Structure):
    _fields_ = [
        ("sin6_family", ct.c_ushort),
        ("sin6_port", ct.c_ushort),
        ("sin6_flowinfo", ct.c_ulong),
        ("sin6_addr", ct.c_ubyte * 16),
        ("sin6_scope_id", ct.c_ulong),
    ]


class FD_SET_ONE(ct.Structure):
    _fields_ = [("fd_count", ct.c_uint), ("fd_array", SOCKET_T * 1)]


class TIMEVAL(ct.Structure):
    _fields_ = [("tv_sec", ct.c_long), ("tv_usec", ct.c_long)]


def emit(value: dict[str, object]) -> None:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    sys.stdout.write(data + "\n")
    sys.stdout.flush()


def rd19_checkpoint(args: argparse.Namespace, name: str, **evidence: object) -> None:
    if not args.final_remediation_diagnostic and not args.active_process_accounting_diagnostic:
        return
    emit({"record_type": "RD19_CHECKPOINT", "checkpoint": name, **evidence})
    release = sys.stdin.buffer.read(1)
    if release != b"\x01":
        raise OSError(0, f"RD19 checkpoint release mismatch: {name}")


def close_child_stdin(child: subprocess.Popen[str]) -> None:
    if child.stdin is not None:
        child.stdin.close()
        child.stdin = None


def finish_child(child: subprocess.Popen[str] | None) -> None:
    if child is None:
        return
    close_child_stdin(child)
    if child.poll() is None:
        child.terminate()
    try:
        child.communicate(timeout=2.0)
    except subprocess.TimeoutExpired:
        child.kill()
        child.communicate(timeout=2.0)


def pipe_child(args: argparse.Namespace, scenario: str, *extra: str) -> subprocess.Popen[str]:
    return subprocess.Popen(
        child_command(args, scenario, *extra),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=CREATE_NO_WINDOW,
        text=True,
    )


def bounded_text(value: object, limit: int = 512) -> str:
    text = str(value)
    return text if len(text) <= limit else text[:limit] + "...[truncated]"


def exception_provenance(exc: BaseException, scenario: str | None, operation_step: str | None) -> dict[str, object]:
    return {
        "scenario": scenario,
        "operation_step": operation_step,
        "exception_type": type(exc).__name__,
        "message": bounded_text(exc),
        "args": [bounded_text(value, 256) for value in list(getattr(exc, "args", ()))[:8]],
        "winerror": getattr(exc, "winerror", None),
        "errno": getattr(exc, "errno", None),
    }


def begin_popen_step(args: argparse.Namespace, step: str) -> None:
    global CURRENT_OPERATION_STEP
    if args.case_remediation_diagnostic or args.final_remediation_diagnostic or args.active_process_accounting_diagnostic:
        CURRENT_OPERATION_STEP = step


def complete_popen_step(args: argparse.Namespace, step: str, result: str, pid: int | None = None) -> None:
    global CURRENT_OPERATION_STEP
    if args.case_remediation_diagnostic or args.final_remediation_diagnostic or args.active_process_accounting_diagnostic:
        POPEN_STEPS.append({"step": step, "result": result, "pid": pid})
        CURRENT_OPERATION_STEP = None


def win_error(name: str) -> OSError:
    return OSError(ct.get_last_error(), name)


def sid_string(sid: int) -> str:
    advapi32 = ct.WinDLL("advapi32.dll", use_last_error=True)
    kernel32 = ct.WinDLL("kernel32.dll", use_last_error=True)
    convert = advapi32.ConvertSidToStringSidW
    convert.argtypes = [ct.c_void_p, ct.POINTER(wt.LPWSTR)]
    convert.restype = wt.BOOL
    local_free = kernel32.LocalFree
    local_free.argtypes = [ct.c_void_p]
    local_free.restype = ct.c_void_p
    value = wt.LPWSTR()
    if not convert(ct.c_void_p(sid), ct.byref(value)):
        raise win_error("ConvertSidToStringSidW")
    try:
        return value.value
    finally:
        local_free(ct.cast(value, ct.c_void_p))


def token_information(info_class: int) -> tuple[object, int]:
    kernel32 = ct.WinDLL("kernel32.dll", use_last_error=True)
    advapi32 = ct.WinDLL("advapi32.dll", use_last_error=True)
    open_token = advapi32.OpenProcessToken
    open_token.argtypes = [wt.HANDLE, wt.DWORD, ct.POINTER(wt.HANDLE)]
    open_token.restype = wt.BOOL
    get_info = advapi32.GetTokenInformation
    get_info.argtypes = [wt.HANDLE, ct.c_int, ct.c_void_p, wt.DWORD, ct.POINTER(wt.DWORD)]
    get_info.restype = wt.BOOL
    close = kernel32.CloseHandle
    close.argtypes = [wt.HANDLE]
    close.restype = wt.BOOL
    current_process = kernel32.GetCurrentProcess
    current_process.argtypes = []
    current_process.restype = wt.HANDLE
    token = wt.HANDLE()
    if not open_token(current_process(), TOKEN_QUERY, ct.byref(token)):
        raise win_error("OpenProcessToken")
    try:
        required = wt.DWORD()
        get_info(token, info_class, None, 0, ct.byref(required))
        error = ct.get_last_error()
        if required.value == 0:
            raise OSError(error, f"GetTokenInformation({info_class}) size")
        buffer = ct.create_string_buffer(required.value)
        if not get_info(token, info_class, buffer, required.value, ct.byref(required)):
            raise win_error(f"GetTokenInformation({info_class})")
        return buffer, int(required.value)
    finally:
        close(token)


def own_identity() -> dict[str, object]:
    is_app_buffer, is_app_bytes = token_information(TOKEN_IS_APP_CONTAINER)
    if is_app_bytes < ct.sizeof(wt.DWORD):
        raise OSError(0, "TokenIsAppContainer ABI size mismatch")
    is_app = int.from_bytes(is_app_buffer.raw[: ct.sizeof(wt.DWORD)], "little")
    app_buffer, app_bytes = token_information(TOKEN_APP_CONTAINER_SID)
    if app_bytes < ct.sizeof(TOKEN_APPCONTAINER_INFORMATION):
        raise OSError(0, "TokenAppContainerSid ABI size mismatch")
    app_info = TOKEN_APPCONTAINER_INFORMATION.from_buffer(app_buffer)
    if is_app and not app_info.TokenAppContainer:
        raise OSError(0, "AppContainer token returned a NULL SID")
    advapi32 = ct.WinDLL("advapi32.dll", use_last_error=True)
    is_valid_sid = advapi32.IsValidSid
    is_valid_sid.argtypes = [ct.c_void_p]
    is_valid_sid.restype = wt.BOOL
    if app_info.TokenAppContainer and not is_valid_sid(app_info.TokenAppContainer):
        raise win_error("IsValidSid")
    appcontainer_sid = sid_string(app_info.TokenAppContainer) if app_info.TokenAppContainer else None
    caps_buffer, caps_bytes = token_information(TOKEN_CAPABILITIES)
    if caps_bytes < ct.sizeof(wt.DWORD):
        raise OSError(0, "TokenCapabilities ABI size mismatch")
    cap_count = int.from_bytes(caps_buffer.raw[: ct.sizeof(wt.DWORD)], "little")
    if is_app and cap_count != 0:
        raise OSError(0, "AppContainer worker capability count is nonzero")
    return {
        "pid": os.getpid(),
        "token_is_appcontainer": bool(is_app),
        "appcontainer_sid": appcontainer_sid,
        "capability_count": cap_count,
        "appcontainer_sid_valid": bool(app_info.TokenAppContainer),
        "token_information_bytes": {
            "TokenIsAppContainer": is_app_bytes,
            "TokenAppContainerSid": app_bytes,
            "TokenCapabilities": caps_bytes,
        },
        "qualification_provenance": QUALIFICATION_PROVENANCE,
    }


def child_command(args: argparse.Namespace, scenario: str, *extra: str) -> list[str]:
    return [
        args.python,
        "-I",
        "-B",
        args.worker,
        "--scenario",
        scenario,
        "--python",
        args.python,
        "--worker",
        args.worker,
        *extra,
    ]


def scenario_identity(_: argparse.Namespace) -> None:
    emit({"result_code": "WORKER_IDENTITY", **own_identity()})


def scenario_sandbox_write(args: argparse.Namespace) -> None:
    target = Path(args.target)
    payload = b"pipeline-v2-capability-write-control\n"
    target.write_bytes(payload)
    emit({"result_code": "WORKER_SANDBOX_WRITE", "bytes": len(payload), "exists": target.is_file()})


def scenario_canary_write(args: argparse.Namespace) -> None:
    try:
        with open(args.target, "r+b", buffering=0) as stream:
            stream.seek(0)
            stream.write(b"MUTATION")
        emit({"result_code": "WORKER_CANARY_MUTATED"})
    except OSError as exc:
        emit({
            "result_code": "WORKER_CANARY_WRITE_DENIED",
            "winerror": getattr(exc, "winerror", None),
            "errno": exc.errno,
        })


def scenario_sleep(_: argparse.Namespace) -> None:
    time.sleep(10.0)
    emit({"result_code": "WORKER_SLEEP_COMPLETED_UNEXPECTEDLY"})


def scenario_cpu(_: argparse.Namespace) -> None:
    value = 1
    while True:
        value = (value * 1664525 + 1013904223) & 0xFFFFFFFF


def allocate_mebibytes(mebibytes: int) -> list[bytearray]:
    allocations: list[bytearray] = []
    for _ in range(mebibytes):
        chunk = bytearray(1024 * 1024)
        chunk[0] = 1
        chunk[-1] = 1
        allocations.append(chunk)
    return allocations


def scenario_process_memory(args: argparse.Namespace) -> None:
    try:
        allocations = allocate_mebibytes(args.mebibytes)
        emit({"result_code": "WORKER_MEMORY_ALLOCATION_COMPLETED", "allocated_mebibytes": len(allocations)})
    except MemoryError:
        emit({"result_code": "WORKER_MEMORY_ALLOCATION_DENIED", "requested_mebibytes": args.mebibytes})


def scenario_memory_child(args: argparse.Namespace) -> None:
    try:
        allocations = allocate_mebibytes(args.mebibytes)
        emit({"result_code": "WORKER_MEMORY_CHILD_READY", "pid": os.getpid(), "allocated_mebibytes": len(allocations)})
        time.sleep(10.0)
    except MemoryError:
        emit({"result_code": "WORKER_MEMORY_CHILD_DENIED", "pid": os.getpid()})


def scenario_job_memory(args: argparse.Namespace) -> None:
    rd19_checkpoint(args, "before_first_child", scenario="job_memory")
    begin_popen_step(args, "job_memory_first_child")
    child = pipe_child(args, "memory_child", "--mebibytes", "48")
    close_child_stdin(child)
    complete_popen_step(args, "job_memory_first_child", "created", child.pid)
    line = child.stdout.readline().strip() if child.stdout else ""
    rd19_checkpoint(
        args,
        "after_first_child",
        scenario="job_memory",
        child_pid=child.pid,
        child_ready_line=bounded_text(line, 256),
    )
    try:
        allocations = allocate_mebibytes(48)
        emit({
            "result_code": "WORKER_JOB_MEMORY_OBSERVED",
            "controller_mebibytes": len(allocations),
            "child_pid": child.pid,
            "child_line": line,
            **({"popen_steps": list(POPEN_STEPS)} if args.case_remediation_diagnostic or args.final_remediation_diagnostic else {}),
        })
        time.sleep(10.0)
    except MemoryError:
        emit({
            "result_code": "WORKER_JOB_MEMORY_DENIED",
            "child_pid": child.pid,
            **({"popen_steps": list(POPEN_STEPS)} if args.case_remediation_diagnostic or args.final_remediation_diagnostic else {}),
        })
    finally:
        finish_child(child)


def scenario_pipe_smoke(args: argparse.Namespace) -> None:
    rd19_checkpoint(args, "before_first_child", scenario="pipe_smoke")
    begin_popen_step(args, "pipe_smoke_first_child")
    child = pipe_child(args, "child_sleep")
    close_child_stdin(child)
    complete_popen_step(args, "pipe_smoke_first_child", "created", child.pid)
    line = child.stdout.readline().strip() if child.stdout else ""
    rd19_checkpoint(
        args,
        "after_first_child",
        scenario="pipe_smoke",
        child_pid=child.pid,
        child_ready_line=bounded_text(line, 256),
    )
    try:
        emit({
            "result_code": "WORKER_PIPE_CHILD_READY",
            "child_pid": child.pid,
            "child_line": line,
            **({"popen_steps": list(POPEN_STEPS)} if args.case_remediation_diagnostic or args.final_remediation_diagnostic else {}),
        })
    finally:
        finish_child(child)


def scenario_active_process(args: argparse.Namespace) -> None:
    rd19_checkpoint(args, "before_first_child", scenario="active_process")
    begin_popen_step(args, "active_process_first_child")
    first = pipe_child(args, "child_sleep")
    close_child_stdin(first)
    complete_popen_step(args, "active_process_first_child", "created", first.pid)
    first_line = first.stdout.readline().strip() if first.stdout else ""
    rd19_checkpoint(
        args,
        "after_first_child",
        scenario="active_process",
        child_pid=first.pid,
        child_ready_line=bounded_text(first_line, 256),
    )
    second = None
    try:
        time.sleep(0.2)
        if args.active_process_accounting_diagnostic:
            second_stdout = ""
            second_stderr = ""
            second_exit_code = None
            second_exception = None
            second_observation_timeout = False
            second_execution_markers: list[dict[str, object]] = []
            try:
                rd19_checkpoint(args, "before_second_child", scenario="active_process", first_pid=first.pid)
                begin_popen_step(args, "active_process_second_child")
                second = pipe_child(args, "child_execution_marker_exit")
                close_child_stdin(second)
                complete_popen_step(args, "active_process_second_child", "created", second.pid)
                try:
                    second_stdout, second_stderr = second.communicate(timeout=1.0)
                    second_exit_code = second.returncode
                except subprocess.TimeoutExpired as exc:
                    second_observation_timeout = True
                    second_exception = exception_provenance(
                        exc,
                        "active_process",
                        "active_process_second_child_communicate",
                    )
                for line in second_stdout.splitlines():
                    try:
                        value = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if (
                        isinstance(value, dict)
                        and value.get("result_code") == "WORKER_SECOND_CHILD_EXECUTION_MARKER"
                    ):
                        second_execution_markers.append(value)
            except OSError as exc:
                second_exception = exception_provenance(exc, "active_process", CURRENT_OPERATION_STEP)
                complete_popen_step(args, "active_process_second_child", "denied", None)
            rd19_checkpoint(
                args,
                "after_second_child_attempt",
                scenario="active_process",
                first_pid=first.pid,
                second_pid=second.pid if second is not None else None,
                second_exit_code=second_exit_code,
                second_observation_timeout=second_observation_timeout,
                second_execution_marker_count=len(second_execution_markers),
            )
            emit({
                "result_code": "WORKER_ACTIVE_PROCESS_ACCOUNTING_OBSERVED",
                "first_pid": first.pid,
                "first_child_ready_line": bounded_text(first_line, 256),
                "second_popen_returned_pid": second.pid if second is not None else None,
                "second_exit_code": second_exit_code,
                "second_observation_timeout": second_observation_timeout,
                "second_exception": second_exception,
                "second_stdout": bounded_text(second_stdout, 512),
                "second_stdout_bytes": len(second_stdout.encode("utf-8")),
                "second_stderr": bounded_text(second_stderr, 512),
                "second_stderr_bytes": len(second_stderr.encode("utf-8")),
                "second_execution_marker_count": len(second_execution_markers),
                "second_execution_markers": second_execution_markers[:1],
                "popen_steps": list(POPEN_STEPS),
            })
            return
        try:
            rd19_checkpoint(args, "before_second_child", scenario="active_process", first_pid=first.pid)
            begin_popen_step(args, "active_process_second_child")
            second = pipe_child(args, "child_sleep")
            close_child_stdin(second)
            complete_popen_step(args, "active_process_second_child", "created", second.pid)
            emit({
                "result_code": "WORKER_SECOND_CHILD_CREATED",
                "first_pid": first.pid,
                "second_pid": second.pid,
                **({"popen_steps": list(POPEN_STEPS)} if args.case_remediation_diagnostic or args.final_remediation_diagnostic else {}),
            })
        except OSError as exc:
            diagnostic = exception_provenance(exc, "active_process", CURRENT_OPERATION_STEP)
            complete_popen_step(args, "active_process_second_child", "denied", None)
            emit({
                "result_code": "WORKER_SECOND_CHILD_DENIED",
                "first_pid": first.pid,
                "winerror": getattr(exc, "winerror", None),
                "errno": exc.errno,
                **({
                    "diagnostic_exception": diagnostic,
                    "popen_steps": list(POPEN_STEPS),
                } if args.case_remediation_diagnostic or args.final_remediation_diagnostic else {}),
            })
    finally:
        for child in (second, first):
            finish_child(child)


def scenario_output(args: argparse.Namespace) -> None:
    chunk = b"O" * 4096
    remaining = args.output_bytes
    while remaining:
        data = chunk[: min(len(chunk), remaining)]
        os.write(sys.stdout.fileno(), data)
        remaining -= len(data)


def scenario_tree(args: argparse.Namespace) -> None:
    rd19_checkpoint(args, "before_tree_child", scenario="tree")
    begin_popen_step(args, "tree_child")
    child = pipe_child(args, "child_sleep")
    close_child_stdin(child)
    complete_popen_step(args, "tree_child", "created", child.pid)
    child_line = child.stdout.readline().strip() if child.stdout else ""
    rd19_checkpoint(
        args,
        "after_tree_child",
        scenario="tree",
        child_pid=child.pid,
        child_ready_line=bounded_text(child_line, 256),
    )
    emit({
        "result_code": "WORKER_TREE_READY",
        "worker_pid": os.getpid(),
        "child_pid": child.pid,
        "child_line": child_line,
        **({"popen_steps": list(POPEN_STEPS)} if args.case_remediation_diagnostic or args.final_remediation_diagnostic else {}),
    })
    time.sleep(10.0)


def scenario_egress(args: argparse.Namespace) -> None:
    family = socket.AF_INET6 if args.family == "IPv6" else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    connect_exception: dict[str, object] | None = None
    try:
        sock.connect((args.host, args.port))
        result_code = "WORKER_EGRESS_CONNECTED"
    except OSError as exc:
        result_code = "WORKER_EGRESS_DENIED"
        connect_exception = exception_provenance(exc, "egress", "socket_connect")
    finally:
        sock.close()
    connect_ex_result = None
    connect_ex_exception = None
    if args.case_remediation_diagnostic:
        diagnostic_sock = socket.socket(family, socket.SOCK_STREAM)
        diagnostic_sock.settimeout(2.0)
        try:
            connect_ex_result = diagnostic_sock.connect_ex((args.host, args.port))
        except OSError as exc:
            connect_ex_exception = exception_provenance(exc, "egress", "socket_connect_ex")
        finally:
            diagnostic_sock.close()
    emit({
        "result_code": result_code,
        "family": args.family,
        "winerror": connect_exception.get("winerror") if connect_exception else None,
        "errno": connect_exception.get("errno") if connect_exception else None,
        **({
            "endpoint": {"host": args.host, "port": args.port},
            "connect_exception": connect_exception,
            "connect_ex_result": connect_ex_result,
            "connect_ex_exception": connect_ex_exception,
        } if args.case_remediation_diagnostic else {}),
    })


def scenario_native_winsock(args: argparse.Namespace) -> None:
    family = socket.AF_INET6 if args.family == "IPv6" else socket.AF_INET
    ws2 = ct.WinDLL("ws2_32.dll", use_last_error=True)
    ws2.WSAStartup.argtypes = [ct.c_ushort, ct.c_void_p]
    ws2.WSAStartup.restype = ct.c_int
    ws2.WSACleanup.argtypes = []
    ws2.WSACleanup.restype = ct.c_int
    ws2.WSASocketW.argtypes = [ct.c_int, ct.c_int, ct.c_int, ct.c_void_p, wt.DWORD, wt.DWORD]
    ws2.WSASocketW.restype = SOCKET_T
    ws2.ioctlsocket.argtypes = [SOCKET_T, ct.c_long, ct.POINTER(ct.c_ulong)]
    ws2.ioctlsocket.restype = ct.c_int
    ws2.WSAConnect.argtypes = [SOCKET_T, ct.c_void_p, ct.c_int, ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p]
    ws2.WSAConnect.restype = ct.c_int
    ws2.WSAGetLastError.argtypes = []
    ws2.WSAGetLastError.restype = ct.c_int
    ws2.select.argtypes = [ct.c_int, ct.c_void_p, ct.POINTER(FD_SET_ONE), ct.POINTER(FD_SET_ONE), ct.POINTER(TIMEVAL)]
    ws2.select.restype = ct.c_int
    ws2.getsockopt.argtypes = [SOCKET_T, ct.c_int, ct.c_int, ct.c_void_p, ct.POINTER(ct.c_int)]
    ws2.getsockopt.restype = ct.c_int
    ws2.closesocket.argtypes = [SOCKET_T]
    ws2.closesocket.restype = ct.c_int

    wsa_buffer = ct.create_string_buffer(512)
    startup_result = int(ws2.WSAStartup(0x0202, wsa_buffer))
    sock = INVALID_SOCKET
    started = time.monotonic()
    watchdog_sequence = 0
    watchdog_pending_emitted = False
    evidence: dict[str, object] = {
        "result_code": "WORKER_NATIVE_WINSOCK_DIAGNOSTIC",
        "family": args.family,
        "endpoint": {"host": args.host, "port": args.port},
        "WSAStartup_result": startup_result,
        "immediate_return": None,
        "immediate_WSA_error": None,
        "select_return": None,
        "select_WSA_error": None,
        "write_ready": False,
        "exception_ready": False,
        "getsockopt_return": None,
        "getsockopt_WSA_error": None,
        "final_SO_ERROR": None,
    }

    def emit_watchdog_terminal(**fields: object) -> None:
        nonlocal watchdog_sequence
        watchdog_sequence += 1
        emit({
            "result_code": "WORKER_NATIVE_WINSOCK_TERMINAL_OBSERVATION",
            "sequence": watchdog_sequence,
            "family": args.family,
            "endpoint": {"host": args.host, "port": args.port},
            "socket_open": sock != INVALID_SOCKET,
            "elapsed_ms": int((time.monotonic() - started) * 1000),
            **fields,
        })

    try:
        if startup_result != 0:
            if args.trusted_pending_connect_watchdog:
                emit_watchdog_terminal(
                    WSAStartup_result=startup_result,
                    socket_created=False,
                    nonblocking_result=None,
                    immediate_return=None,
                    immediate_WSA_error=startup_result,
                    terminal_reason="WSAStartup_failure",
                )
                return
            emit({**evidence, "elapsed_ms": int((time.monotonic() - started) * 1000)})
            return
        sock = int(ws2.WSASocketW(family, socket.SOCK_STREAM, socket.IPPROTO_TCP, None, 0, 0))
        if sock == INVALID_SOCKET:
            evidence["immediate_WSA_error"] = int(ws2.WSAGetLastError())
            if args.trusted_pending_connect_watchdog:
                emit_watchdog_terminal(
                    WSAStartup_result=startup_result,
                    socket_created=False,
                    nonblocking_result=None,
                    immediate_return=None,
                    immediate_WSA_error=evidence["immediate_WSA_error"],
                    terminal_reason="WSASocketW_failure",
                )
                return
            emit({**evidence, "elapsed_ms": int((time.monotonic() - started) * 1000)})
            return
        nonblocking = ct.c_ulong(1)
        nonblocking_result = int(ws2.ioctlsocket(SOCKET_T(sock), FIONBIO, ct.byref(nonblocking)))
        if nonblocking_result == SOCKET_ERROR:
            evidence["immediate_WSA_error"] = int(ws2.WSAGetLastError())
            if args.trusted_pending_connect_watchdog:
                emit_watchdog_terminal(
                    WSAStartup_result=startup_result,
                    socket_created=True,
                    nonblocking_result=nonblocking_result,
                    immediate_return=None,
                    immediate_WSA_error=evidence["immediate_WSA_error"],
                    terminal_reason="ioctlsocket_failure",
                )
                return
            emit({**evidence, "elapsed_ms": int((time.monotonic() - started) * 1000)})
            return
        packed = socket.inet_pton(family, args.host)
        if family == socket.AF_INET6:
            address6 = SOCKADDR_IN6()
            address6.sin6_family = family
            address6.sin6_port = socket.htons(args.port)
            for index, value in enumerate(packed):
                address6.sin6_addr[index] = value
            address_pointer = ct.byref(address6)
            address_bytes = ct.sizeof(address6)
        else:
            address4 = SOCKADDR_IN()
            address4.sin_family = family
            address4.sin_port = socket.htons(args.port)
            for index, value in enumerate(packed):
                address4.sin_addr[index] = value
            address_pointer = ct.byref(address4)
            address_bytes = ct.sizeof(address4)
        immediate = int(ws2.WSAConnect(SOCKET_T(sock), address_pointer, address_bytes, None, None, None, None))
        evidence["immediate_return"] = immediate
        immediate_error = 0
        if immediate == SOCKET_ERROR:
            immediate_error = int(ws2.WSAGetLastError())
            evidence["immediate_WSA_error"] = immediate_error
            if args.trusted_pending_connect_watchdog:
                if immediate_error != WSAEWOULDBLOCK:
                    emit_watchdog_terminal(
                        WSAStartup_result=startup_result,
                        socket_created=True,
                        nonblocking_result=nonblocking_result,
                        immediate_return=immediate,
                        immediate_WSA_error=immediate_error,
                        terminal_reason="immediate_connect_terminal",
                    )
                    return
                watchdog_sequence = 1
                watchdog_pending_emitted = True
                emit({
                    "result_code": "WORKER_NATIVE_WINSOCK_PENDING_READY",
                    "sequence": watchdog_sequence,
                    "family": args.family,
                    "endpoint": {"host": args.host, "port": args.port},
                    "WSAStartup_result": startup_result,
                    "socket_created": True,
                    "nonblocking_result": nonblocking_result,
                    "immediate_return": immediate,
                    "immediate_WSA_error": immediate_error,
                    "socket_open": True,
                    "elapsed_ms": int((time.monotonic() - started) * 1000),
                })
                while True:
                    write_set = FD_SET_ONE(1, (SOCKET_T * 1)(sock))
                    exception_set = FD_SET_ONE(1, (SOCKET_T * 1)(sock))
                    timeout = TIMEVAL(0, 100_000)
                    selected = int(ws2.select(
                        0,
                        None,
                        ct.byref(write_set),
                        ct.byref(exception_set),
                        ct.byref(timeout),
                    ))
                    if selected == 0:
                        watchdog_sequence += 1
                        emit({
                            "result_code": "WORKER_NATIVE_WINSOCK_PENDING_SAMPLE",
                            "sequence": watchdog_sequence,
                            "family": args.family,
                            "endpoint": {"host": args.host, "port": args.port},
                            "select_return": selected,
                            "select_WSA_error": 0,
                            "write_ready": False,
                            "exception_ready": False,
                            "socket_open": True,
                            "elapsed_ms": int((time.monotonic() - started) * 1000),
                        })
                        continue
                    select_error = int(ws2.WSAGetLastError()) if selected == SOCKET_ERROR else 0
                    write_ready = bool(write_set.fd_count) if selected != SOCKET_ERROR else False
                    exception_ready = bool(exception_set.fd_count) if selected != SOCKET_ERROR else False
                    getsockopt_result: int | None = None
                    getsockopt_error: int | None = None
                    final_so_error: int | None = None
                    if selected > 0:
                        final_error = ct.c_int()
                        final_error_bytes = ct.c_int(ct.sizeof(final_error))
                        getsockopt_result = int(ws2.getsockopt(
                            SOCKET_T(sock),
                            SOL_SOCKET,
                            SO_ERROR,
                            ct.byref(final_error),
                            ct.byref(final_error_bytes),
                        ))
                        if getsockopt_result == SOCKET_ERROR:
                            getsockopt_error = int(ws2.WSAGetLastError())
                        else:
                            getsockopt_error = 0
                            final_so_error = int(final_error.value)
                    emit_watchdog_terminal(
                        WSAStartup_result=startup_result,
                        socket_created=True,
                        nonblocking_result=nonblocking_result,
                        immediate_return=immediate,
                        immediate_WSA_error=immediate_error,
                        select_return=selected,
                        select_WSA_error=select_error,
                        write_ready=write_ready,
                        exception_ready=exception_ready,
                        getsockopt_return=getsockopt_result,
                        getsockopt_WSA_error=getsockopt_error,
                        final_SO_ERROR=final_so_error,
                        terminal_reason=(
                            "select_error" if selected == SOCKET_ERROR
                            else "select_readiness_or_authoritative_SO_ERROR"
                        ),
                    )
                    return
            if immediate_error == WSAEWOULDBLOCK:
                write_set = FD_SET_ONE(1, (SOCKET_T * 1)(sock))
                exception_set = FD_SET_ONE(1, (SOCKET_T * 1)(sock))
                timeout = TIMEVAL(2, 0)
                selected = int(ws2.select(0, None, ct.byref(write_set), ct.byref(exception_set), ct.byref(timeout)))
                evidence["select_return"] = selected
                if selected == SOCKET_ERROR:
                    evidence["select_WSA_error"] = int(ws2.WSAGetLastError())
                else:
                    evidence["write_ready"] = bool(write_set.fd_count)
                    evidence["exception_ready"] = bool(exception_set.fd_count)
                final_error = ct.c_int()
                final_error_bytes = ct.c_int(ct.sizeof(final_error))
                getsockopt_result = int(ws2.getsockopt(
                    SOCKET_T(sock),
                    SOL_SOCKET,
                    SO_ERROR,
                    ct.byref(final_error),
                    ct.byref(final_error_bytes),
                ))
                evidence["getsockopt_return"] = getsockopt_result
                if getsockopt_result == SOCKET_ERROR:
                    evidence["getsockopt_WSA_error"] = int(ws2.WSAGetLastError())
                else:
                    evidence["final_SO_ERROR"] = int(final_error.value)
        else:
            evidence["immediate_WSA_error"] = 0
            evidence["final_SO_ERROR"] = 0
            if args.trusted_pending_connect_watchdog:
                emit_watchdog_terminal(
                    WSAStartup_result=startup_result,
                    socket_created=True,
                    nonblocking_result=nonblocking_result,
                    immediate_return=immediate,
                    immediate_WSA_error=0,
                    getsockopt_return=None,
                    getsockopt_WSA_error=None,
                    final_SO_ERROR=0,
                    terminal_reason="immediate_connect_success",
                )
                return
        evidence["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        emit(evidence)
    finally:
        if args.trusted_pending_connect_watchdog and watchdog_pending_emitted:
            watchdog_sequence += 1
            emit({
                "result_code": "WORKER_NATIVE_WINSOCK_SELF_CLOSE",
                "sequence": watchdog_sequence,
                "family": args.family,
                "endpoint": {"host": args.host, "port": args.port},
                "socket_open": False,
                "close_path_reached": True,
                "elapsed_ms": int((time.monotonic() - started) * 1000),
            })
        if sock != INVALID_SOCKET:
            ws2.closesocket(SOCKET_T(sock))
        if startup_result == 0:
            ws2.WSACleanup()


def scenario_child_sleep(_: argparse.Namespace) -> None:
    emit({"result_code": "WORKER_CHILD_SLEEP_READY", "pid": os.getpid()})
    time.sleep(10.0)


def scenario_child_execution_marker_exit(_: argparse.Namespace) -> None:
    emit({"result_code": "WORKER_SECOND_CHILD_EXECUTION_MARKER", "pid": os.getpid()})


SCENARIOS = {
    "identity": scenario_identity,
    "sandbox_write": scenario_sandbox_write,
    "canary_write": scenario_canary_write,
    "sleep": scenario_sleep,
    "cpu": scenario_cpu,
    "process_memory": scenario_process_memory,
    "memory_child": scenario_memory_child,
    "job_memory": scenario_job_memory,
    "pipe_smoke": scenario_pipe_smoke,
    "active_process": scenario_active_process,
    "output": scenario_output,
    "tree": scenario_tree,
    "egress": scenario_egress,
    "native_winsock": scenario_native_winsock,
    "child_sleep": scenario_child_sleep,
    "child_execution_marker_exit": scenario_child_execution_marker_exit,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--scenario", required=True, choices=sorted(SCENARIOS))
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--worker", default=str(Path(__file__).resolve()))
    parser.add_argument("--target")
    parser.add_argument("--mebibytes", type=int, default=128)
    parser.add_argument("--output-bytes", type=int, default=131072)
    parser.add_argument("--family", choices=["IPv4", "IPv6"])
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--case-remediation-diagnostic", action="store_true")
    parser.add_argument("--final-remediation-diagnostic", action="store_true")
    parser.add_argument("--active-process-accounting-diagnostic", action="store_true")
    parser.add_argument("--trusted-pending-connect-watchdog", action="store_true")
    return parser.parse_args()


def main() -> int:
    global CURRENT_SCENARIO, CURRENT_OPERATION_STEP, POPEN_STEPS
    args = parse_args()
    CURRENT_SCENARIO = args.scenario
    CURRENT_OPERATION_STEP = None
    POPEN_STEPS = []
    try:
        if args.trusted_pending_connect_watchdog and args.scenario != "native_winsock":
            raise ValueError("trusted pending-connect watchdog requires native_winsock")
        SCENARIOS[args.scenario](args)
        return 0
    except BaseException as exc:
        value = {
            "result_code": "WORKER_ERROR",
            "exception_type": type(exc).__name__,
            "winerror": getattr(exc, "winerror", None),
            "errno": getattr(exc, "errno", None),
        }
        if (
            args.case_remediation_diagnostic
            or args.final_remediation_diagnostic
            or args.active_process_accounting_diagnostic
            or args.trusted_pending_connect_watchdog
        ):
            value.update({
                "diagnostic_exception": exception_provenance(exc, CURRENT_SCENARIO, CURRENT_OPERATION_STEP),
                "popen_steps": list(POPEN_STEPS),
            })
        emit(value)
        return 70


if __name__ == "__main__":
    raise SystemExit(main())
