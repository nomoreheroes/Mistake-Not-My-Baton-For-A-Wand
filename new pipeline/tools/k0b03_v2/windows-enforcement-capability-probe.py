"""Bounded host-specific Windows enforcement capability qualification.

The probe is intentionally standalone, stdlib-only, and non-runtime.  It owns
the exact temporary AppContainer profile, sandbox ACL, loopback listeners, Job
Objects, processes, handles, and cleanup for one authorized qualification
attempt.  It emits canonical JSON to stdout and never writes repository
evidence.
"""

from __future__ import annotations

import argparse
import ctypes as ct
from ctypes import wintypes as wt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import socket
import stat
import subprocess
import sys
import threading
import time
import winreg


PYTHON_PATH = "C:/ProgramData/anaconda3/python.exe"
PYTHON_SHA256 = "6965927a96b81d1717c1d2186de7feb9b29ebf8775464020ebc2f25de6ef8ee0"
PYTHON_BYTES = 104208
FIREWALL_API_SHA256 = "b310e551cff1d2d518b6fef6c86ba9d8ffc2816d4001597ee4f30a8f28f53b29"
FIREWALL_API_BYTES = 663552
PROJECTION_REQUEST_SHA256 = "f2fbc230aed9df1f5dc66fbc1b1b1afb7cc99ff24e13783f6e28f2f0084625f5"
PROJECTION_REQUEST_BYTES = 59032
PROJECTION_PATH_COUNT = 99
PROJECTION_CONTENT_BYTES = 10_477_161
PROJECTION_MANIFEST_BYTES = 9_422
PROJECTION_MANIFEST_SHA256 = "c602d91fbc090dd72912a60be97a7c51aeb832e38d6e96807950de1eeae28b5d"
PYTHON312_PTH_BYTES = b"Lib\nDLLs\n"
PYTHON312_PTH_SHA256 = "dda136779493f74b019f62e349c5506ff5d551f397c0eede6f1f09981d126e55"
WORKER_SHA256 = "78a39d7a788559145dba1de07ec0d8277d51ebd59e213c201df83684c10482e4"
WORKER_BYTES = 38_073
SUSPENDED_LAUNCH_DIAGNOSTIC_PROVENANCE = {
    "initial_qualification_stop": {
        "attempt": "A",
        "stop_code": "APPCONTAINER_PROCESS_CREATE_FAILED",
        "win32_code": 203,
    },
    "D1": "non_AppContainer_original_environment_desktop_NULL_create_success",
    "D2": "AppContainer_original_environment_desktop_NULL_win32_203",
    "D3": "AppContainer_original_environment_desktop_winsta0_default_win32_203",
    "D4": "AppContainer_exact_17_entry_environment_desktop_winsta0_default_create_success",
    "conclusion": "complete_successful_D4_configuration_retained_without_individual_variable_necessity_claim",
    "v2_attempt_A": {
        "stop_code": "SID_STRING_FAILED",
        "win32_code": 1337,
        "root_cause": "pointer_valued_token_information_detached_from_its_backing_buffer",
    },
    "v2_manual_cleanup": {
        "exact_suspended_unassigned_pid": 12160,
        "direct_termination_completed": True,
        "post_cleanup_residue": 0,
    },
    "v3_attempt_A": {
        "stop_code": "CHILD_IDENTITY_PROOF_FAILED",
        "attempt_B_started": False,
        "cause": "worker_pointer_valued_token_information_detached_from_its_backing_buffer",
    },
    "v3_post_stop_cleanup": {
        "process_profile_root_port_loopback_and_bytecode_residue": 0,
        "staging_or_commit_performed": False,
    },
}

TOKEN_QUERY = 0x0008
TOKEN_USER_CLASS = 1
TOKEN_ELEVATION_TYPE = 18
TOKEN_ELEVATION_CLASS = 20
TOKEN_INTEGRITY_LEVEL = 25
TOKEN_IS_APP_CONTAINER = 29
TOKEN_CAPABILITIES = 30
TOKEN_APP_CONTAINER_SID = 31

CREATE_SUSPENDED = 0x00000004
CREATE_UNICODE_ENVIRONMENT = 0x00000400
CREATE_NO_WINDOW = 0x08000000
EXTENDED_STARTUPINFO_PRESENT = 0x00080000
STARTF_USESTDHANDLES = 0x00000100
PROC_THREAD_ATTRIBUTE_HANDLE_LIST = 0x00020002
PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES = 0x00020009
HANDLE_FLAG_INHERIT = 0x00000001

JOB_OBJECT_LIMIT_PROCESS_TIME = 0x00000002
JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x00000008
JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000200
JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION = 0x00000400
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_BASIC_LIMIT_INFORMATION = 2
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
JOB_OBJECT_ASSOCIATE_COMPLETION_PORT_INFORMATION = 7
JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION = 1
JOB_OBJECT_BASIC_PROCESS_ID_LIST = 3
JOB_OBJECT_MSG_ACTIVE_PROCESS_ZERO = 4
JOB_OBJECT_MSG_END_OF_PROCESS_TIME = 2
JOB_OBJECT_MSG_ACTIVE_PROCESS_LIMIT = 3
JOB_OBJECT_MSG_NEW_PROCESS = 6
JOB_OBJECT_MSG_EXIT_PROCESS = 7
JOB_OBJECT_MSG_ABNORMAL_EXIT_PROCESS = 8
JOB_OBJECT_MSG_PROCESS_MEMORY_LIMIT = 9
JOB_OBJECT_MSG_JOB_MEMORY_LIMIT = 10

WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 258
INFINITE = 0xFFFFFFFF
STILL_ACTIVE = 259
ERROR_BROKEN_PIPE = 109
ERROR_INSUFFICIENT_BUFFER = 122
ERROR_ALREADY_EXISTS = 183
ERROR_ACCESS_DENIED = 5
ERROR_INVALID_PARAMETER = 87
WSAEACCES = 10013
WSAEWOULDBLOCK = 10035

SE_FILE_OBJECT = 1
OWNER_SECURITY_INFORMATION = 0x00000001
GROUP_SECURITY_INFORMATION = 0x00000002
DACL_SECURITY_INFORMATION = 0x00000004
SDDL_REVISION_1 = 1
GRANT_ACCESS = 1
TRUSTEE_IS_SID = 0
TRUSTEE_IS_UNKNOWN = 0
SUB_CONTAINERS_AND_OBJECTS_INHERIT = 0x3
FILE_GENERIC_READ = 0x00120089
FILE_GENERIC_WRITE = 0x00120116
FILE_GENERIC_EXECUTE = 0x001200A0
DELETE = 0x00010000
FILE_DELETE_CHILD = 0x00000040

SC_MANAGER_CONNECT = 0x0001
SERVICE_QUERY_STATUS = 0x0004
SC_STATUS_PROCESS_INFO = 0
SERVICE_RUNNING = 4
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400

ULONG_PTR = ct.c_size_t
SIZE_T = ct.c_size_t
INVALID_HANDLE_VALUE = ct.c_void_p(-1).value


class ProbeStop(RuntimeError):
    def __init__(self, code: str, detail: str, raw_code: int | None = None):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.raw_code = raw_code


class IdentityDiagnosticComplete(RuntimeError):
    pass


class CaseRemediationDiagnosticComplete(RuntimeError):
    pass


class FinalRemediationDiagnosticComplete(RuntimeError):
    pass


class ActiveProcessAccountingDiagnosticComplete(RuntimeError):
    pass


class ProcessTimeControlDiagnosticComplete(RuntimeError):
    pass


class LiveCompanionAttributionDiagnosticComplete(RuntimeError):
    pass


class NonNestedProcessTimeCausalDiagnosticComplete(RuntimeError):
    pass


class AppContainerProcessTimeInformationClassControlDiagnosticComplete(RuntimeError):
    pass


class AssignedSuspendedTargetFlagPreservationDiagnosticComplete(RuntimeError):
    pass


class TrustedCpuWatchdogDiagnosticComplete(RuntimeError):
    pass


class NativeWinsockIsolationControlDiagnosticComplete(RuntimeError):
    pass


class TrustedPendingConnectWatchdogDiagnosticComplete(RuntimeError):
    pass


class SID_AND_ATTRIBUTES(ct.Structure):
    _fields_ = [("Sid", ct.c_void_p), ("Attributes", wt.DWORD)]


class TOKEN_USER(ct.Structure):
    _fields_ = [("User", SID_AND_ATTRIBUTES)]


class TOKEN_MANDATORY_LABEL(ct.Structure):
    _fields_ = [("Label", SID_AND_ATTRIBUTES)]


class TOKEN_ELEVATION(ct.Structure):
    _fields_ = [("TokenIsElevated", wt.DWORD)]


class SECURITY_CAPABILITIES(ct.Structure):
    _fields_ = [
        ("AppContainerSid", ct.c_void_p),
        ("Capabilities", ct.POINTER(SID_AND_ATTRIBUTES)),
        ("CapabilityCount", wt.DWORD),
        ("Reserved", wt.DWORD),
    ]


class TOKEN_APPCONTAINER_INFORMATION(ct.Structure):
    _fields_ = [("TokenAppContainer", ct.c_void_p)]


class SECURITY_ATTRIBUTES(ct.Structure):
    _fields_ = [
        ("nLength", wt.DWORD),
        ("lpSecurityDescriptor", ct.c_void_p),
        ("bInheritHandle", wt.BOOL),
    ]


class STARTUPINFOW(ct.Structure):
    _fields_ = [
        ("cb", wt.DWORD),
        ("lpReserved", wt.LPWSTR),
        ("lpDesktop", wt.LPWSTR),
        ("lpTitle", wt.LPWSTR),
        ("dwX", wt.DWORD),
        ("dwY", wt.DWORD),
        ("dwXSize", wt.DWORD),
        ("dwYSize", wt.DWORD),
        ("dwXCountChars", wt.DWORD),
        ("dwYCountChars", wt.DWORD),
        ("dwFillAttribute", wt.DWORD),
        ("dwFlags", wt.DWORD),
        ("wShowWindow", wt.WORD),
        ("cbReserved2", wt.WORD),
        ("lpReserved2", ct.POINTER(wt.BYTE)),
        ("hStdInput", wt.HANDLE),
        ("hStdOutput", wt.HANDLE),
        ("hStdError", wt.HANDLE),
    ]


class STARTUPINFOEXW(ct.Structure):
    _fields_ = [("StartupInfo", STARTUPINFOW), ("lpAttributeList", ct.c_void_p)]


class PROCESS_INFORMATION(ct.Structure):
    _fields_ = [
        ("hProcess", wt.HANDLE),
        ("hThread", wt.HANDLE),
        ("dwProcessId", wt.DWORD),
        ("dwThreadId", wt.DWORD),
    ]


class FILETIME(ct.Structure):
    _fields_ = [("dwLowDateTime", wt.DWORD), ("dwHighDateTime", wt.DWORD)]


class PROCESS_BASIC_INFORMATION(ct.Structure):
    _fields_ = [
        ("Reserved1", ct.c_void_p),
        ("PebBaseAddress", ct.c_void_p),
        ("Reserved2", ct.c_void_p * 2),
        ("UniqueProcessId", ULONG_PTR),
        ("InheritedFromUniqueProcessId", ULONG_PTR),
    ]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ct.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ct.c_longlong),
        ("PerJobUserTimeLimit", ct.c_longlong),
        ("LimitFlags", wt.DWORD),
        ("MinimumWorkingSetSize", SIZE_T),
        ("MaximumWorkingSetSize", SIZE_T),
        ("ActiveProcessLimit", wt.DWORD),
        ("Affinity", ULONG_PTR),
        ("PriorityClass", wt.DWORD),
        ("SchedulingClass", wt.DWORD),
    ]


class IO_COUNTERS(ct.Structure):
    _fields_ = [
        ("ReadOperationCount", ct.c_ulonglong),
        ("WriteOperationCount", ct.c_ulonglong),
        ("OtherOperationCount", ct.c_ulonglong),
        ("ReadTransferCount", ct.c_ulonglong),
        ("WriteTransferCount", ct.c_ulonglong),
        ("OtherTransferCount", ct.c_ulonglong),
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ct.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", SIZE_T),
        ("JobMemoryLimit", SIZE_T),
        ("PeakProcessMemoryUsed", SIZE_T),
        ("PeakJobMemoryUsed", SIZE_T),
    ]


class JOBOBJECT_ASSOCIATE_COMPLETION_PORT(ct.Structure):
    _fields_ = [("CompletionKey", ct.c_void_p), ("CompletionPort", wt.HANDLE)]


class JOBOBJECT_BASIC_ACCOUNTING_INFORMATION(ct.Structure):
    _fields_ = [
        ("TotalUserTime", ct.c_longlong),
        ("TotalKernelTime", ct.c_longlong),
        ("ThisPeriodTotalUserTime", ct.c_longlong),
        ("ThisPeriodTotalKernelTime", ct.c_longlong),
        ("TotalPageFaultCount", wt.DWORD),
        ("TotalProcesses", wt.DWORD),
        ("ActiveProcesses", wt.DWORD),
        ("TotalTerminatedProcesses", wt.DWORD),
    ]


class JOBOBJECT_BASIC_PROCESS_ID_LIST_64(ct.Structure):
    _fields_ = [
        ("NumberOfAssignedProcesses", wt.DWORD),
        ("NumberOfProcessIdsInList", wt.DWORD),
        ("ProcessIdList", ULONG_PTR * 64),
    ]


class MULTIPLE_TRUSTEE_OPERATION(ct.c_int):
    pass


class TRUSTEE_FORM(ct.c_int):
    pass


class TRUSTEE_TYPE(ct.c_int):
    pass


class TRUSTEE_W(ct.Structure):
    pass


TRUSTEE_W._fields_ = [
    ("pMultipleTrustee", ct.POINTER(TRUSTEE_W)),
    ("MultipleTrusteeOperation", MULTIPLE_TRUSTEE_OPERATION),
    ("TrusteeForm", TRUSTEE_FORM),
    ("TrusteeType", TRUSTEE_TYPE),
    ("ptstrName", wt.LPWSTR),
]


class EXPLICIT_ACCESSW(ct.Structure):
    _fields_ = [
        ("grfAccessPermissions", wt.DWORD),
        ("grfAccessMode", ct.c_int),
        ("grfInheritance", wt.DWORD),
        ("Trustee", TRUSTEE_W),
    ]


class SERVICE_STATUS_PROCESS(ct.Structure):
    _fields_ = [
        ("dwServiceType", wt.DWORD),
        ("dwCurrentState", wt.DWORD),
        ("dwControlsAccepted", wt.DWORD),
        ("dwWin32ExitCode", wt.DWORD),
        ("dwServiceSpecificExitCode", wt.DWORD),
        ("dwCheckPoint", wt.DWORD),
        ("dwWaitHint", wt.DWORD),
        ("dwProcessId", wt.DWORD),
        ("dwServiceFlags", wt.DWORD),
    ]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_pin(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {"path": path.as_posix(), "sha256": sha256_bytes(data), "bytes": len(data)}


def reject_reparse_components(path: Path, code: str) -> None:
    if not path.is_absolute():
        raise ProbeStop(code, f"non_absolute:{path}")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        attributes = getattr(info, "st_file_attributes", 0)
        if stat.S_ISLNK(info.st_mode) or attributes & FILE_ATTRIBUTE_REPARSE_POINT:
            raise ProbeStop(code, current.as_posix())


def load_projection_contract(path: Path) -> dict[str, object]:
    reject_reparse_components(path, "PROJECTION_REQUEST_REPARSE")
    raw = path.read_bytes()
    request_pin = {"path": path.as_posix(), "sha256": sha256_bytes(raw), "bytes": len(raw)}
    if request_pin["sha256"] != PROJECTION_REQUEST_SHA256 or request_pin["bytes"] != PROJECTION_REQUEST_BYTES:
        raise ProbeStop("PROJECTION_REQUEST_PIN_MISMATCH", canonical(request_pin))
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        raise ProbeStop("PROJECTION_REQUEST_FORMAT_MISMATCH", path.as_posix())
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProbeStop("PROJECTION_REQUEST_PARSE_FAILED", f"{type(exc).__name__}:{exc}") from exc
    projection = document.get("corrected_runtime_projection", {})
    entries = projection.get("entries")
    if not isinstance(entries, list) or len(entries) != PROJECTION_PATH_COUNT:
        raise ProbeStop("PROJECTION_ENTRY_COUNT_MISMATCH", str(len(entries) if isinstance(entries, list) else None))
    seen: set[str] = set()
    lines: list[str] = []
    content_bytes = 0
    previous: str | None = None
    for ordinal, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ProbeStop("PROJECTION_ENTRY_TYPE_MISMATCH", str(ordinal))
        relative = entry.get("projection_relative_path")
        digest = entry.get("sha256")
        size = entry.get("bytes")
        source = entry.get("source_path")
        if not isinstance(relative, str) or not isinstance(digest, str) or not isinstance(size, int) or not isinstance(source, str):
            raise ProbeStop("PROJECTION_ENTRY_FIELD_MISMATCH", str(ordinal))
        pure = PurePosixPath(relative)
        if pure.is_absolute() or not pure.parts or any(part in ("", ".", "..") for part in pure.parts):
            raise ProbeStop("PROJECTION_RELATIVE_PATH_INVALID", relative)
        if relative in seen:
            raise ProbeStop("PROJECTION_DUPLICATE_PATH", relative)
        if previous is not None and relative <= previous:
            raise ProbeStop("PROJECTION_ORDINAL_ORDER_MISMATCH", relative)
        if len(digest) != 64 or digest != digest.lower() or any(value not in "0123456789abcdef" for value in digest):
            raise ProbeStop("PROJECTION_SHA256_FORMAT_MISMATCH", relative)
        if size < 0:
            raise ProbeStop("PROJECTION_SIZE_INVALID", relative)
        seen.add(relative)
        previous = relative
        content_bytes += size
        lines.append(f"{relative}\t{digest}\t{size}\n")
    manifest = "".join(lines).encode("utf-8")
    if (
        content_bytes != PROJECTION_CONTENT_BYTES
        or len(manifest) != PROJECTION_MANIFEST_BYTES
        or sha256_bytes(manifest) != PROJECTION_MANIFEST_SHA256
    ):
        raise ProbeStop(
            "PROJECTION_MANIFEST_MISMATCH",
            canonical({"content_bytes": content_bytes, "manifest_bytes": len(manifest), "sha256": sha256_bytes(manifest)}),
        )
    pth = next((entry for entry in entries if entry["projection_relative_path"] == "python312._pth"), None)
    if not pth or pth["sha256"] != PYTHON312_PTH_SHA256 or pth["bytes"] != len(PYTHON312_PTH_BYTES):
        raise ProbeStop("PROJECTION_PTH_CONTRACT_MISMATCH", canonical(pth))
    return {
        "request_pin": request_pin,
        "entries": entries,
        "path_count": len(entries),
        "content_bytes": content_bytes,
        "manifest_bytes": len(manifest),
        "manifest_sha256": sha256_bytes(manifest),
    }


def materialize_projection(contract: dict[str, object], runtime: Path) -> dict[str, object]:
    if runtime.exists():
        raise ProbeStop("PROJECTION_RUNTIME_ALREADY_EXISTS", runtime.as_posix())
    runtime.mkdir(parents=True)
    reject_reparse_components(runtime, "PROJECTION_DESTINATION_REPARSE")
    copied: list[dict[str, object]] = []
    total = 0
    for entry in contract["entries"]:
        relative = entry["projection_relative_path"]
        destination = runtime.joinpath(*PurePosixPath(relative).parts)
        if entry["source_path"] == "<generated-in-memory:python312._pth>":
            data = PYTHON312_PTH_BYTES
        else:
            source = Path(entry["source_path"])
            if not source.is_absolute() or not source.as_posix().casefold().startswith("c:/programdata/anaconda3/"):
                raise ProbeStop("PROJECTION_SOURCE_OUTSIDE_CLOSED_WORLD", source.as_posix())
            reject_reparse_components(source, "PROJECTION_SOURCE_REPARSE")
            if not source.is_file():
                raise ProbeStop("PROJECTION_SOURCE_NOT_FILE", source.as_posix())
            data = source.read_bytes()
        actual_hash = sha256_bytes(data)
        if len(data) != entry["bytes"] or actual_hash != entry["sha256"]:
            raise ProbeStop(
                "PROJECTION_SOURCE_PIN_MISMATCH",
                canonical({"relative": relative, "sha256": actual_hash, "bytes": len(data)}),
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        reject_reparse_components(destination.parent, "PROJECTION_DESTINATION_REPARSE")
        if destination.exists():
            raise ProbeStop("PROJECTION_DESTINATION_EXISTS", destination.as_posix())
        destination.write_bytes(data)
        destination_pin = file_pin(destination)
        if destination_pin["sha256"] != entry["sha256"] or destination_pin["bytes"] != entry["bytes"]:
            raise ProbeStop("PROJECTION_DESTINATION_PIN_MISMATCH", canonical(destination_pin))
        total += len(data)
        copied.append({
            "projection_relative_path": relative,
            "sha256": actual_hash,
            "bytes": len(data),
            "source_path": entry["source_path"],
        })
    if len(copied) != PROJECTION_PATH_COUNT or total != PROJECTION_CONTENT_BYTES:
        raise ProbeStop("PROJECTION_MATERIALIZATION_ACCOUNTING_MISMATCH", f"{len(copied)}/{total}")
    return {
        "request_pin": contract["request_pin"],
        "path_count": len(copied),
        "content_bytes": total,
        "manifest_bytes": contract["manifest_bytes"],
        "manifest_sha256": contract["manifest_sha256"],
        "python312_pth": file_pin(runtime / "python312._pth"),
        "projected_python": file_pin(runtime / "python.exe"),
        "bindings": copied,
    }


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def hresult_unsigned(value: int) -> int:
    return value & 0xFFFFFFFF


def hresult_failed(value: int) -> bool:
    return bool(hresult_unsigned(value) & 0x80000000)


def safe_handle_value(handle: object) -> int:
    value = getattr(handle, "value", handle)
    return int(value or 0)


class Native:
    def __init__(self) -> None:
        self.kernel32 = ct.WinDLL("kernel32.dll", use_last_error=True)
        self.advapi32 = ct.WinDLL("advapi32.dll", use_last_error=True)
        self.ntdll = ct.WinDLL("ntdll.dll", use_last_error=True)
        self.userenv = ct.WinDLL("userenv.dll", use_last_error=True)
        self.firewall = ct.WinDLL("FirewallAPI.dll", use_last_error=True)
        self._bind()

    def _bind(self) -> None:
        k = self.kernel32
        a = self.advapi32
        n = self.ntdll
        u = self.userenv
        f = self.firewall

        k.CloseHandle.argtypes = [wt.HANDLE]
        k.CloseHandle.restype = wt.BOOL
        k.LocalFree.argtypes = [ct.c_void_p]
        k.LocalFree.restype = ct.c_void_p
        k.CreatePipe.argtypes = [ct.POINTER(wt.HANDLE), ct.POINTER(wt.HANDLE), ct.POINTER(SECURITY_ATTRIBUTES), wt.DWORD]
        k.CreatePipe.restype = wt.BOOL
        k.SetHandleInformation.argtypes = [wt.HANDLE, wt.DWORD, wt.DWORD]
        k.SetHandleInformation.restype = wt.BOOL
        k.ReadFile.argtypes = [wt.HANDLE, ct.c_void_p, wt.DWORD, ct.POINTER(wt.DWORD), ct.c_void_p]
        k.ReadFile.restype = wt.BOOL
        k.WriteFile.argtypes = [wt.HANDLE, ct.c_void_p, wt.DWORD, ct.POINTER(wt.DWORD), ct.c_void_p]
        k.WriteFile.restype = wt.BOOL
        k.CreateJobObjectW.argtypes = [ct.c_void_p, wt.LPCWSTR]
        k.CreateJobObjectW.restype = wt.HANDLE
        k.SetInformationJobObject.argtypes = [wt.HANDLE, ct.c_int, ct.c_void_p, wt.DWORD]
        k.SetInformationJobObject.restype = wt.BOOL
        k.QueryInformationJobObject.argtypes = [wt.HANDLE, ct.c_int, ct.c_void_p, wt.DWORD, ct.POINTER(wt.DWORD)]
        k.QueryInformationJobObject.restype = wt.BOOL
        k.AssignProcessToJobObject.argtypes = [wt.HANDLE, wt.HANDLE]
        k.AssignProcessToJobObject.restype = wt.BOOL
        k.IsProcessInJob.argtypes = [wt.HANDLE, wt.HANDLE, ct.POINTER(wt.BOOL)]
        k.IsProcessInJob.restype = wt.BOOL
        k.TerminateJobObject.argtypes = [wt.HANDLE, wt.UINT]
        k.TerminateJobObject.restype = wt.BOOL
        k.CreateIoCompletionPort.argtypes = [wt.HANDLE, wt.HANDLE, ULONG_PTR, wt.DWORD]
        k.CreateIoCompletionPort.restype = wt.HANDLE
        k.GetQueuedCompletionStatus.argtypes = [wt.HANDLE, ct.POINTER(wt.DWORD), ct.POINTER(ULONG_PTR), ct.POINTER(ct.c_void_p), wt.DWORD]
        k.GetQueuedCompletionStatus.restype = wt.BOOL
        k.InitializeProcThreadAttributeList.argtypes = [ct.c_void_p, wt.DWORD, wt.DWORD, ct.POINTER(SIZE_T)]
        k.InitializeProcThreadAttributeList.restype = wt.BOOL
        k.UpdateProcThreadAttribute.argtypes = [ct.c_void_p, wt.DWORD, SIZE_T, ct.c_void_p, SIZE_T, ct.c_void_p, ct.c_void_p]
        k.UpdateProcThreadAttribute.restype = wt.BOOL
        k.DeleteProcThreadAttributeList.argtypes = [ct.c_void_p]
        k.DeleteProcThreadAttributeList.restype = None
        k.CreateProcessW.argtypes = [wt.LPCWSTR, wt.LPWSTR, ct.c_void_p, ct.c_void_p, wt.BOOL, wt.DWORD, ct.c_void_p, wt.LPCWSTR, ct.POINTER(STARTUPINFOW), ct.POINTER(PROCESS_INFORMATION)]
        k.CreateProcessW.restype = wt.BOOL
        k.ResumeThread.argtypes = [wt.HANDLE]
        k.ResumeThread.restype = wt.DWORD
        k.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
        k.WaitForSingleObject.restype = wt.DWORD
        k.GetExitCodeProcess.argtypes = [wt.HANDLE, ct.POINTER(wt.DWORD)]
        k.GetExitCodeProcess.restype = wt.BOOL
        k.GetProcessId.argtypes = [wt.HANDLE]
        k.GetProcessId.restype = wt.DWORD
        k.GetProcessTimes.argtypes = [wt.HANDLE, ct.POINTER(FILETIME), ct.POINTER(FILETIME), ct.POINTER(FILETIME), ct.POINTER(FILETIME)]
        k.GetProcessTimes.restype = wt.BOOL
        k.GetCurrentProcess.argtypes = []
        k.GetCurrentProcess.restype = wt.HANDLE
        k.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]
        k.TerminateProcess.restype = wt.BOOL
        k.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
        k.OpenProcess.restype = wt.HANDLE
        k.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ct.POINTER(wt.DWORD)]
        k.QueryFullProcessImageNameW.restype = wt.BOOL

        n.NtQueryInformationProcess.argtypes = [wt.HANDLE, ct.c_int, ct.c_void_p, wt.ULONG, ct.POINTER(wt.ULONG)]
        n.NtQueryInformationProcess.restype = ct.c_long

        a.OpenProcessToken.argtypes = [wt.HANDLE, wt.DWORD, ct.POINTER(wt.HANDLE)]
        a.OpenProcessToken.restype = wt.BOOL
        a.GetTokenInformation.argtypes = [wt.HANDLE, ct.c_int, ct.c_void_p, wt.DWORD, ct.POINTER(wt.DWORD)]
        a.GetTokenInformation.restype = wt.BOOL
        a.ConvertSidToStringSidW.argtypes = [ct.c_void_p, ct.POINTER(wt.LPWSTR)]
        a.ConvertSidToStringSidW.restype = wt.BOOL
        a.IsValidSid.argtypes = [ct.c_void_p]
        a.IsValidSid.restype = wt.BOOL
        a.EqualSid.argtypes = [ct.c_void_p, ct.c_void_p]
        a.EqualSid.restype = wt.BOOL
        a.FreeSid.argtypes = [ct.c_void_p]
        a.FreeSid.restype = ct.c_void_p
        a.GetNamedSecurityInfoW.argtypes = [wt.LPWSTR, ct.c_int, wt.DWORD, ct.POINTER(ct.c_void_p), ct.POINTER(ct.c_void_p), ct.POINTER(ct.c_void_p), ct.POINTER(ct.c_void_p), ct.POINTER(ct.c_void_p)]
        a.GetNamedSecurityInfoW.restype = wt.DWORD
        a.SetNamedSecurityInfoW.argtypes = [wt.LPWSTR, ct.c_int, wt.DWORD, ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p]
        a.SetNamedSecurityInfoW.restype = wt.DWORD
        a.SetEntriesInAclW.argtypes = [wt.ULONG, ct.POINTER(EXPLICIT_ACCESSW), ct.c_void_p, ct.POINTER(ct.c_void_p)]
        a.SetEntriesInAclW.restype = wt.DWORD
        a.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [ct.c_void_p, wt.DWORD, wt.DWORD, ct.POINTER(wt.LPWSTR), ct.POINTER(wt.DWORD)]
        a.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype = wt.BOOL
        a.OpenSCManagerW.argtypes = [wt.LPCWSTR, wt.LPCWSTR, wt.DWORD]
        a.OpenSCManagerW.restype = wt.HANDLE
        a.OpenServiceW.argtypes = [wt.HANDLE, wt.LPCWSTR, wt.DWORD]
        a.OpenServiceW.restype = wt.HANDLE
        a.QueryServiceStatusEx.argtypes = [wt.HANDLE, ct.c_int, ct.POINTER(wt.BYTE), wt.DWORD, ct.POINTER(wt.DWORD)]
        a.QueryServiceStatusEx.restype = wt.BOOL
        a.CloseServiceHandle.argtypes = [wt.HANDLE]
        a.CloseServiceHandle.restype = wt.BOOL

        u.CreateAppContainerProfile.argtypes = [wt.LPCWSTR, wt.LPCWSTR, wt.LPCWSTR, ct.POINTER(SID_AND_ATTRIBUTES), wt.DWORD, ct.POINTER(ct.c_void_p)]
        u.CreateAppContainerProfile.restype = ct.c_long
        u.DeleteAppContainerProfile.argtypes = [wt.LPCWSTR]
        u.DeleteAppContainerProfile.restype = ct.c_long
        u.DeriveAppContainerSidFromAppContainerName.argtypes = [wt.LPCWSTR, ct.POINTER(ct.c_void_p)]
        u.DeriveAppContainerSidFromAppContainerName.restype = ct.c_long

        f.NetworkIsolationGetAppContainerConfig.argtypes = [ct.POINTER(wt.DWORD), ct.POINTER(ct.POINTER(SID_AND_ATTRIBUTES))]
        f.NetworkIsolationGetAppContainerConfig.restype = wt.DWORD
        f.NetworkIsolationFreeAppContainers.argtypes = [ct.c_void_p]
        f.NetworkIsolationFreeAppContainers.restype = wt.DWORD

    def close(self, handle: object) -> None:
        if safe_handle_value(handle):
            self.kernel32.CloseHandle(handle)

    def sid_string(self, sid: object) -> str:
        text = wt.LPWSTR()
        if not self.advapi32.ConvertSidToStringSidW(sid, ct.byref(text)):
            raise ProbeStop("SID_STRING_FAILED", "ConvertSidToStringSidW", ct.get_last_error())
        try:
            return text.value
        finally:
            self.kernel32.LocalFree(ct.cast(text, ct.c_void_p))

    def token_buffer(self, process: object, info_class: int) -> tuple[object, int]:
        token = wt.HANDLE()
        if not self.advapi32.OpenProcessToken(process, TOKEN_QUERY, ct.byref(token)):
            raise ProbeStop("OPEN_CHILD_TOKEN_FAILED", "OpenProcessToken", ct.get_last_error())
        try:
            needed = wt.DWORD()
            self.advapi32.GetTokenInformation(token, info_class, None, 0, ct.byref(needed))
            error = ct.get_last_error()
            if needed.value == 0 or error != ERROR_INSUFFICIENT_BUFFER:
                raise ProbeStop("TOKEN_INFO_SIZE_FAILED", f"Token class {info_class}", error)
            buffer = ct.create_string_buffer(needed.value)
            if not self.advapi32.GetTokenInformation(token, info_class, buffer, needed.value, ct.byref(needed)):
                raise ProbeStop("TOKEN_INFO_FAILED", f"Token class {info_class}", ct.get_last_error())
            return buffer, int(needed.value)
        finally:
            self.close(token)

    def token_fixed_uint32(
        self,
        process: object,
        info_class: int,
        info_name: str,
    ) -> tuple[int, dict[str, object]]:
        if info_class not in (TOKEN_ELEVATION_TYPE, TOKEN_ELEVATION_CLASS):
            raise ProbeStop("TOKEN_FIXED_QUERY_CLASS_FORBIDDEN", f"{info_name}:{info_class}")
        token = wt.HANDLE()
        if not self.advapi32.OpenProcessToken(process, TOKEN_QUERY, ct.byref(token)):
            raise ProbeStop("OPEN_CHILD_TOKEN_FAILED", "OpenProcessToken", ct.get_last_error())
        try:
            value = wt.DWORD()
            returned = wt.DWORD()
            ct.set_last_error(0)
            result = bool(self.advapi32.GetTokenInformation(
                token,
                info_class,
                ct.byref(value),
                ct.sizeof(value),
                ct.byref(returned),
            ))
            error = ct.get_last_error()
            evidence = {
                "information_class_name": info_name,
                "information_class": info_class,
                "buffer_bytes": ct.sizeof(value),
                "GetTokenInformation_result": result,
                "GetTokenInformation_last_error": int(error),
                "ReturnLength": int(returned.value),
            }
            if not result:
                raise ProbeStop("TOKEN_FIXED_QUERY_FAILED", canonical(evidence), error)
            if int(returned.value) != ct.sizeof(value):
                raise ProbeStop("TOKEN_FIXED_QUERY_LENGTH_MISMATCH", canonical(evidence))
            return int(value.value), evidence
        finally:
            self.close(token)

    def process_identity(self, process: object) -> dict[str, object]:
        is_app_buffer, is_app_bytes = self.token_buffer(process, TOKEN_IS_APP_CONTAINER)
        if is_app_bytes < ct.sizeof(wt.DWORD):
            raise ProbeStop("TOKEN_IS_APPCONTAINER_ABI_MISMATCH", str(is_app_bytes))
        is_app = int.from_bytes(is_app_buffer.raw[: ct.sizeof(wt.DWORD)], "little")
        app_buffer, app_bytes = self.token_buffer(process, TOKEN_APP_CONTAINER_SID)
        if app_bytes < ct.sizeof(TOKEN_APPCONTAINER_INFORMATION):
            raise ProbeStop("TOKEN_APPCONTAINER_SID_ABI_MISMATCH", str(app_bytes))
        app = TOKEN_APPCONTAINER_INFORMATION.from_buffer(app_buffer)
        if is_app and not app.TokenAppContainer:
            raise ProbeStop("TOKEN_APPCONTAINER_SID_NULL", "AppContainer token returned a NULL SID")
        if app.TokenAppContainer and not self.advapi32.IsValidSid(app.TokenAppContainer):
            raise ProbeStop("TOKEN_APPCONTAINER_SID_INVALID", "IsValidSid", ct.get_last_error())
        appcontainer_sid = self.sid_string(app.TokenAppContainer) if app.TokenAppContainer else None
        caps_buffer, caps_bytes = self.token_buffer(process, TOKEN_CAPABILITIES)
        if caps_bytes < ct.sizeof(wt.DWORD):
            raise ProbeStop("TOKEN_CAPABILITIES_ABI_MISMATCH", str(caps_bytes))
        capability_count = int.from_bytes(caps_buffer.raw[: ct.sizeof(wt.DWORD)], "little")
        return {
            "token_is_appcontainer": bool(is_app),
            "appcontainer_sid": appcontainer_sid,
            "capability_count": capability_count,
            "token_information_bytes": {
                "TokenIsAppContainer": is_app_bytes,
                "TokenAppContainerSid": app_bytes,
                "TokenCapabilities": caps_bytes,
            },
            "appcontainer_sid_valid": bool(app.TokenAppContainer),
        }

    def live_process_attribution(self, process: object, notification_pid: int) -> dict[str, object]:
        if ct.sizeof(PROCESS_BASIC_INFORMATION) != 48:
            raise ProbeStop("PROCESS_BASIC_INFORMATION_ABI_SIZE_MISMATCH", str(ct.sizeof(PROCESS_BASIC_INFORMATION)))
        if PROCESS_BASIC_INFORMATION.InheritedFromUniqueProcessId.offset != 40:
            raise ProbeStop(
                "PROCESS_BASIC_INFORMATION_ABI_OFFSET_MISMATCH",
                str(PROCESS_BASIC_INFORMATION.InheritedFromUniqueProcessId.offset),
            )

        image_capacity = 32768
        image_buffer = ct.create_unicode_buffer(image_capacity)
        image_length = wt.DWORD(image_capacity)
        if not self.kernel32.QueryFullProcessImageNameW(process, 0, image_buffer, ct.byref(image_length)):
            raise ProbeStop("LIVE_IMAGE_QUERY_FAILED", str(notification_pid), ct.get_last_error())
        image = image_buffer.value
        if not image or not Path(image).is_absolute():
            raise ProbeStop("LIVE_IMAGE_PATH_NOT_ABSOLUTE", str(notification_pid))
        normalized_image = os.path.normpath(image).replace("\\", "/")

        basic = PROCESS_BASIC_INFORMATION()
        returned = wt.ULONG()
        status = int(self.ntdll.NtQueryInformationProcess(
            process,
            0,
            ct.byref(basic),
            ct.sizeof(basic),
            ct.byref(returned),
        ))
        if status != 0:
            raise ProbeStop("LIVE_PARENT_PID_QUERY_FAILED", str(notification_pid), status & 0xFFFFFFFF)
        if int(returned.value) not in (0, ct.sizeof(basic)):
            raise ProbeStop("LIVE_PARENT_PID_QUERY_LENGTH_MISMATCH", f"{notification_pid}:{returned.value}")

        user_buffer, user_bytes = self.token_buffer(process, TOKEN_USER_CLASS)
        if user_bytes < ct.sizeof(TOKEN_USER):
            raise ProbeStop("TOKEN_USER_ABI_MISMATCH", f"{notification_pid}:{user_bytes}")
        user = TOKEN_USER.from_buffer(user_buffer)
        if not user.User.Sid or not self.advapi32.IsValidSid(user.User.Sid):
            raise ProbeStop("TOKEN_USER_SID_INVALID", str(notification_pid), ct.get_last_error())
        user_sid = self.sid_string(user.User.Sid)

        integrity_buffer, integrity_bytes = self.token_buffer(process, TOKEN_INTEGRITY_LEVEL)
        if integrity_bytes < ct.sizeof(TOKEN_MANDATORY_LABEL):
            raise ProbeStop("TOKEN_INTEGRITY_ABI_MISMATCH", f"{notification_pid}:{integrity_bytes}")
        integrity = TOKEN_MANDATORY_LABEL.from_buffer(integrity_buffer)
        if not integrity.Label.Sid or not self.advapi32.IsValidSid(integrity.Label.Sid):
            raise ProbeStop("TOKEN_INTEGRITY_SID_INVALID", str(notification_pid), ct.get_last_error())
        integrity_sid = self.sid_string(integrity.Label.Sid)
        try:
            integrity_rid = int(integrity_sid.rsplit("-", 1)[1])
        except (IndexError, ValueError) as exc:
            raise ProbeStop("TOKEN_INTEGRITY_RID_PARSE_FAILED", f"{notification_pid}:{integrity_sid}") from exc
        integrity_levels = {
            0x0000: "untrusted",
            0x1000: "low",
            0x2000: "medium",
            0x2100: "medium_plus",
            0x3000: "high",
            0x4000: "system",
            0x5000: "protected",
        }

        elevation_type, elevation_type_query = self.token_fixed_uint32(
            process,
            TOKEN_ELEVATION_TYPE,
            "TokenElevationType",
        )
        elevation_value, elevation_query = self.token_fixed_uint32(
            process,
            TOKEN_ELEVATION_CLASS,
            "TokenElevation",
        )

        identity = self.process_identity(process)
        creation = FILETIME()
        exit_time = FILETIME()
        kernel = FILETIME()
        user_time = FILETIME()
        if not self.kernel32.GetProcessTimes(
            process,
            ct.byref(creation),
            ct.byref(exit_time),
            ct.byref(kernel),
            ct.byref(user_time),
        ):
            raise ProbeStop("LIVE_PROCESS_TIMES_QUERY_FAILED", str(notification_pid), ct.get_last_error())
        creation_time = (int(creation.dwHighDateTime) << 32) | int(creation.dwLowDateTime)

        return {
            "notification_PID": notification_pid,
            "normalized_executable_image_path": normalized_image,
            "parent_PID": int(basic.InheritedFromUniqueProcessId),
            "creation_FILETIME_100ns": creation_time,
            "token_user_SID": user_sid,
            "integrity": {
                "SID": integrity_sid,
                "RID": integrity_rid,
                "level": integrity_levels.get(integrity_rid, "unknown"),
            },
            "TokenElevationType": elevation_type,
            "TokenElevation": bool(elevation_value),
            "TokenIsAppContainer": identity["token_is_appcontainer"],
            "AppContainer_SID": identity["appcontainer_sid"],
            "capability_count": identity["capability_count"],
            "token_information_bytes": {
                "TokenUser": user_bytes,
                "TokenIntegrityLevel": integrity_bytes,
                "TokenElevationType": elevation_type_query["ReturnLength"],
                "TokenElevation": elevation_query["ReturnLength"],
                **identity["token_information_bytes"],
            },
            "fixed_size_token_queries": {
                "TokenElevationType": elevation_type_query,
                "TokenElevation": elevation_query,
            },
        }

    def loopback_exemptions(self) -> list[str]:
        count = wt.DWORD()
        values = ct.POINTER(SID_AND_ATTRIBUTES)()
        result = int(self.firewall.NetworkIsolationGetAppContainerConfig(ct.byref(count), ct.byref(values)))
        if result != 0:
            raise ProbeStop("NETWORK_ISOLATION_READBACK_FAILED", "NetworkIsolationGetAppContainerConfig", result)
        output: list[str] = []
        try:
            if values:
                for index in range(count.value):
                    output.append(self.sid_string(values[index].Sid))
        finally:
            if values:
                free_result = int(self.firewall.NetworkIsolationFreeAppContainers(ct.cast(values, ct.c_void_p)))
                if free_result != 0:
                    raise ProbeStop("NETWORK_ISOLATION_FREE_FAILED", "NetworkIsolationFreeAppContainers", free_result)
        return output

    def bfe_state(self) -> dict[str, object]:
        manager = self.advapi32.OpenSCManagerW(None, None, SC_MANAGER_CONNECT)
        if not manager:
            raise ProbeStop("BFE_MANAGER_OPEN_FAILED", "OpenSCManagerW", ct.get_last_error())
        service = None
        try:
            service = self.advapi32.OpenServiceW(manager, "BFE", SERVICE_QUERY_STATUS)
            if not service:
                raise ProbeStop("BFE_SERVICE_OPEN_FAILED", "OpenServiceW", ct.get_last_error())
            status = SERVICE_STATUS_PROCESS()
            needed = wt.DWORD()
            if not self.advapi32.QueryServiceStatusEx(
                service,
                SC_STATUS_PROCESS_INFO,
                ct.cast(ct.byref(status), ct.POINTER(wt.BYTE)),
                ct.sizeof(status),
                ct.byref(needed),
            ):
                raise ProbeStop("BFE_STATUS_FAILED", "QueryServiceStatusEx", ct.get_last_error())
            return {
                "state": int(status.dwCurrentState),
                "running": int(status.dwCurrentState) == SERVICE_RUNNING,
                "process_id": int(status.dwProcessId),
                "win32_exit_code": int(status.dwWin32ExitCode),
                "service_flags": int(status.dwServiceFlags),
            }
        finally:
            if service:
                self.advapi32.CloseServiceHandle(service)
            self.advapi32.CloseServiceHandle(manager)


class SecurityDescriptorSnapshot:
    def __init__(self, native: Native, path: Path):
        self.native = native
        self.path = path
        self.owner = ct.c_void_p()
        self.group = ct.c_void_p()
        self.dacl = ct.c_void_p()
        self.sd = ct.c_void_p()
        result = native.advapi32.GetNamedSecurityInfoW(
            str(path),
            SE_FILE_OBJECT,
            OWNER_SECURITY_INFORMATION | GROUP_SECURITY_INFORMATION | DACL_SECURITY_INFORMATION,
            ct.byref(self.owner),
            ct.byref(self.group),
            ct.byref(self.dacl),
            None,
            ct.byref(self.sd),
        )
        if result != 0:
            raise ProbeStop("SECURITY_DESCRIPTOR_READ_FAILED", str(path), int(result))
        self.sddl = self._sddl()

    def _sddl(self) -> str:
        value = wt.LPWSTR()
        length = wt.DWORD()
        if not self.native.advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW(
            self.sd,
            SDDL_REVISION_1,
            OWNER_SECURITY_INFORMATION | GROUP_SECURITY_INFORMATION | DACL_SECURITY_INFORMATION,
            ct.byref(value),
            ct.byref(length),
        ):
            raise ProbeStop("SDDL_CONVERSION_FAILED", str(self.path), ct.get_last_error())
        try:
            return value.value
        finally:
            self.native.kernel32.LocalFree(ct.cast(value, ct.c_void_p))

    def restore_dacl(self) -> None:
        result = self.native.advapi32.SetNamedSecurityInfoW(
            str(self.path),
            SE_FILE_OBJECT,
            DACL_SECURITY_INFORMATION,
            None,
            None,
            self.dacl,
            None,
        )
        if result != 0:
            raise ProbeStop("ACL_RESTORE_FAILED", str(self.path), int(result))

    def free(self) -> None:
        if self.sd:
            self.native.kernel32.LocalFree(self.sd)
            self.sd = ct.c_void_p()


def apply_sandbox_acl(native: Native, snapshot: SecurityDescriptorSnapshot, sid: object) -> None:
    trustee = TRUSTEE_W(
        None,
        MULTIPLE_TRUSTEE_OPERATION(0),
        TRUSTEE_FORM(TRUSTEE_IS_SID),
        TRUSTEE_TYPE(TRUSTEE_IS_UNKNOWN),
        ct.cast(sid, wt.LPWSTR),
    )
    access = EXPLICIT_ACCESSW(
        FILE_GENERIC_READ | FILE_GENERIC_WRITE | FILE_GENERIC_EXECUTE | DELETE | FILE_DELETE_CHILD,
        GRANT_ACCESS,
        SUB_CONTAINERS_AND_OBJECTS_INHERIT,
        trustee,
    )
    new_acl = ct.c_void_p()
    result = native.advapi32.SetEntriesInAclW(1, ct.byref(access), snapshot.dacl, ct.byref(new_acl))
    if result != 0:
        raise ProbeStop("ACL_BUILD_FAILED", str(snapshot.path), int(result))
    try:
        result = native.advapi32.SetNamedSecurityInfoW(
            str(snapshot.path),
            SE_FILE_OBJECT,
            DACL_SECURITY_INFORMATION,
            None,
            None,
            new_acl,
            None,
        )
        if result != 0:
            raise ProbeStop("ACL_APPLY_FAILED", str(snapshot.path), int(result))
    finally:
        native.kernel32.LocalFree(new_acl)


class OutputCollector:
    def __init__(self, native: Native, limit: int):
        self.native = native
        self.limit = limit
        self.total = 0
        self.prefix = bytearray()
        self.sha = hashlib.sha256()
        self.lock = threading.Lock()
        self.overflow = threading.Event()
        self.errors: list[dict[str, object]] = []
        self.threads: list[threading.Thread] = []

    def start(self, name: str, handle: object) -> None:
        thread = threading.Thread(target=self._read, args=(name, handle), daemon=True)
        self.threads.append(thread)
        thread.start()

    def _read(self, name: str, handle: object) -> None:
        buffer = ct.create_string_buffer(4096)
        read = wt.DWORD()
        try:
            while True:
                ok = self.native.kernel32.ReadFile(handle, buffer, len(buffer), ct.byref(read), None)
                if not ok:
                    error = ct.get_last_error()
                    if error == ERROR_BROKEN_PIPE:
                        break
                    self.errors.append({"stream": name, "winerror": error})
                    break
                if read.value == 0:
                    break
                data = buffer.raw[: read.value]
                with self.lock:
                    self.sha.update(data)
                    old = self.total
                    self.total += len(data)
                    if old < self.limit:
                        self.prefix.extend(data[: self.limit - old])
                    if self.total > self.limit:
                        self.overflow.set()
        finally:
            self.native.close(handle)

    def finish(self, timeout: float = 2.0) -> None:
        for thread in self.threads:
            thread.join(timeout)

    def snapshot(self) -> dict[str, object]:
        with self.lock:
            return {
                "total_bytes": self.total,
                "retained_prefix_bytes": len(self.prefix),
                "full_stream_sha256": self.sha.hexdigest(),
                "prefix_sha256": sha256_bytes(bytes(self.prefix)),
                "overflow": self.total > self.limit,
                "reader_errors": list(self.errors),
                "text_prefix": bytes(self.prefix).decode("utf-8", "replace"),
            }


class JobRun:
    def __init__(self, native: Native, sid: object, sandbox: Path, python: Path, worker: Path):
        self.native = native
        self.sid = sid
        self.sandbox = sandbox
        self.python = python
        self.worker = worker

    def _pipe(self) -> tuple[wt.HANDLE, wt.HANDLE]:
        attributes = SECURITY_ATTRIBUTES(ct.sizeof(SECURITY_ATTRIBUTES), None, True)
        read = wt.HANDLE()
        write = wt.HANDLE()
        if not self.native.kernel32.CreatePipe(ct.byref(read), ct.byref(write), ct.byref(attributes), 0):
            raise ProbeStop("PIPE_CREATE_FAILED", "CreatePipe", ct.get_last_error())
        return read, write

    def _set_not_inheritable(self, handle: object) -> None:
        if not self.native.kernel32.SetHandleInformation(handle, HANDLE_FLAG_INHERIT, 0):
            raise ProbeStop("HANDLE_INHERITANCE_FAILED", "SetHandleInformation", ct.get_last_error())

    def _environment(self) -> tuple[dict[str, str], object]:
        values = {
            "ALLUSERSPROFILE": "C:/ProgramData",
            "APPDATA": "C:/Users/Administrator/AppData/Roaming",
            "COMSPEC": "C:/Windows/System32/cmd.exe",
            "HOMEDRIVE": "C:",
            "HOMEPATH": "/Users/Administrator",
            "LOCALAPPDATA": "C:/Users/Administrator/AppData/Local",
            "ProgramData": "C:/ProgramData",
            "PUBLIC": "C:/Users/Public",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONUTF8": "1",
            "SystemDrive": "C:",
            "SystemRoot": "C:/Windows",
            "TEMP": str(self.sandbox / "tmp"),
            "TMP": str(self.sandbox / "tmp"),
            "USERPROFILE": "C:/Users/Administrator",
            "WINDIR": "C:/Windows",
        }
        block = "\0".join(f"{key}={values[key]}" for key in sorted(values, key=str.casefold)) + "\0\0"
        return values, ct.create_unicode_buffer(block)

    def _query_accounting(self, job: object, scenario: str) -> tuple[JOBOBJECT_BASIC_ACCOUNTING_INFORMATION, JOBOBJECT_EXTENDED_LIMIT_INFORMATION]:
        returned = wt.DWORD()
        accounting = JOBOBJECT_BASIC_ACCOUNTING_INFORMATION()
        if not self.native.kernel32.QueryInformationJobObject(
            job,
            JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION,
            ct.byref(accounting),
            ct.sizeof(accounting),
            ct.byref(returned),
        ):
            raise ProbeStop("JOB_ACCOUNTING_FAILED", scenario, ct.get_last_error())
        extended = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        if not self.native.kernel32.QueryInformationJobObject(
            job,
            JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            ct.byref(extended),
            ct.sizeof(extended),
            ct.byref(returned),
        ):
            raise ProbeStop("JOB_EXTENDED_QUERY_FAILED", scenario, ct.get_last_error())
        return accounting, extended

    def _accounting_projection(
        self,
        accounting: JOBOBJECT_BASIC_ACCOUNTING_INFORMATION,
        extended: JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
    ) -> dict[str, object]:
        return {
            "total_user_time_100ns": int(accounting.TotalUserTime),
            "total_kernel_time_100ns": int(accounting.TotalKernelTime),
            "total_processes": int(accounting.TotalProcesses),
            "active_processes": int(accounting.ActiveProcesses),
            "total_terminated_processes": int(accounting.TotalTerminatedProcesses),
            "peak_process_memory": int(extended.PeakProcessMemoryUsed),
            "peak_job_memory": int(extended.PeakJobMemoryUsed),
            "active_process_zero": int(accounting.ActiveProcesses) == 0,
        }

    def _query_effective_limits(self, job: object, scenario: str) -> dict[str, int]:
        returned = wt.DWORD()
        limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        ct.set_last_error(0)
        query_ok = bool(self.native.kernel32.QueryInformationJobObject(
            job,
            JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            ct.byref(limits),
            ct.sizeof(limits),
            ct.byref(returned),
        ))
        query_error = ct.get_last_error()
        if not query_ok:
            raise ProbeStop("JOB_LIMIT_READBACK_FAILED", scenario, query_error)
        return {
            "LimitFlags": int(limits.BasicLimitInformation.LimitFlags),
            "PerProcessUserTimeLimit": int(limits.BasicLimitInformation.PerProcessUserTimeLimit),
            "ProcessMemoryLimit": int(limits.ProcessMemoryLimit),
            "JobMemoryLimit": int(limits.JobMemoryLimit),
            "ActiveProcessLimit": int(limits.BasicLimitInformation.ActiveProcessLimit),
            "QueryInformationJobObject_result": int(query_ok),
            "QueryInformationJobObject_last_error": int(query_error),
            "QueryInformationJobObject_returned_length": int(returned.value),
        }

    def process_in_job(self, process: object, job: object | None, scenario: str, label: str) -> bool:
        in_job = wt.BOOL()
        ct.set_last_error(0)
        query_ok = bool(self.native.kernel32.IsProcessInJob(process, job, ct.byref(in_job)))
        query_error = ct.get_last_error()
        if not query_ok:
            raise ProbeStop("PROCESS_JOB_MEMBERSHIP_QUERY_FAILED", f"{scenario}:{label}", query_error)
        return bool(in_job.value)

    def _query_job_process_ids(self, job: object, scenario: str) -> dict[str, object]:
        returned = wt.DWORD()
        values = JOBOBJECT_BASIC_PROCESS_ID_LIST_64()
        if not self.native.kernel32.QueryInformationJobObject(
            job,
            JOB_OBJECT_BASIC_PROCESS_ID_LIST,
            ct.byref(values),
            ct.sizeof(values),
            ct.byref(returned),
        ):
            raise ProbeStop("JOB_PROCESS_ID_LIST_QUERY_FAILED", scenario, ct.get_last_error())
        count = int(values.NumberOfProcessIdsInList)
        assigned = int(values.NumberOfAssignedProcesses)
        if count > len(values.ProcessIdList) or assigned > len(values.ProcessIdList):
            raise ProbeStop("JOB_PROCESS_ID_LIST_BOUNDS_FAILED", f"{scenario}:{assigned}/{count}")
        return {
            "number_of_assigned_processes": assigned,
            "number_of_process_ids_in_list": count,
            "process_ids": [int(values.ProcessIdList[index]) for index in range(count)],
        }

    def _process_times(self, process: object, scenario: str) -> dict[str, int]:
        creation = FILETIME()
        exit_time = FILETIME()
        kernel = FILETIME()
        user = FILETIME()
        if not self.native.kernel32.GetProcessTimes(
            process,
            ct.byref(creation),
            ct.byref(exit_time),
            ct.byref(kernel),
            ct.byref(user),
        ):
            raise ProbeStop("PROCESS_TIMES_QUERY_FAILED", scenario, ct.get_last_error())
        to_int = lambda value: (int(value.dwHighDateTime) << 32) | int(value.dwLowDateTime)
        return {
            "creation_time_100ns": to_int(creation),
            "exit_time_100ns": to_int(exit_time),
            "kernel_time_100ns": to_int(kernel),
            "user_time_100ns": to_int(user),
        }

    def _collect_quiescence(
        self,
        job: object,
        completion: object,
        scenario: str,
        started: float,
        deadline_ms: int = 10_000,
        quiet_window_ms: int | None = None,
        initial_messages: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        k = self.native.kernel32
        deadline = time.monotonic() + deadline_ms / 1000.0
        messages: list[dict[str, object]] = list(initial_messages or [])
        snapshots: list[dict[str, object]] = []
        active_process_zero_seen = any(
            int(value.get("message", -1)) == JOB_OBJECT_MSG_ACTIVE_PROCESS_ZERO
            for value in messages
        )
        poll_count = 0
        last_snapshot_key: tuple[int, int, int] | None = None
        last_snapshot_ms = -500
        deadline_expired = False
        quiet_started: float | None = None
        quiet_window_completed = quiet_window_ms is None
        while True:
            poll_count += 1
            now = time.monotonic()
            offset_ms = int((now - started) * 1000)
            accounting, extended = self._query_accounting(job, scenario)
            projection = self._accounting_projection(accounting, extended)
            snapshot_key = (
                int(projection["active_processes"]),
                int(projection["total_processes"]),
                int(projection["total_terminated_processes"]),
            )
            if snapshot_key != last_snapshot_key or offset_ms - last_snapshot_ms >= 500:
                snapshots.append({"monotonic_offset_ms": offset_ms, **projection})
                last_snapshot_key = snapshot_key
                last_snapshot_ms = offset_ms
            if projection["active_process_zero"] and active_process_zero_seen:
                if quiet_window_ms is None:
                    break
                if quiet_started is None:
                    quiet_started = time.monotonic()
                if (time.monotonic() - quiet_started) * 1000 >= quiet_window_ms:
                    quiet_window_completed = True
                    break
            else:
                quiet_started = None
            remaining_ms = max(0, int((deadline - time.monotonic()) * 1000))
            if remaining_ms == 0:
                deadline_expired = True
                break
            message = wt.DWORD()
            key = ULONG_PTR()
            overlapped = ct.c_void_p()
            wait_ms = min(50, remaining_ms)
            ok = k.GetQueuedCompletionStatus(
                completion,
                ct.byref(message),
                ct.byref(key),
                ct.byref(overlapped),
                wait_ms,
            )
            if ok:
                quiet_started = None
                code = int(message.value)
                event = {
                    "message": code,
                    "monotonic_offset_ms": int((time.monotonic() - started) * 1000),
                    "completion_key": int(key.value),
                    "process_id_value": int(overlapped.value or 0),
                }
                messages.append(event)
                if code == JOB_OBJECT_MSG_ACTIVE_PROCESS_ZERO:
                    active_process_zero_seen = True
            else:
                error = ct.get_last_error()
                if error != WAIT_TIMEOUT:
                    raise ProbeStop("COMPLETION_PORT_READ_FAILED", scenario, error)
        final_accounting, final_extended = self._query_accounting(job, scenario)
        final_projection = self._accounting_projection(final_accounting, final_extended)
        final_process_ids = self._query_job_process_ids(job, scenario)
        final_PID_inventory_empty = bool(
            final_process_ids["number_of_assigned_processes"] == 0
            and final_process_ids["number_of_process_ids_in_list"] == 0
            and final_process_ids["process_ids"] == []
        )
        return {
            "deadline_ms": deadline_ms,
            "deadline_expired": deadline_expired,
            "poll_count": poll_count,
            "active_process_zero_message_seen": active_process_zero_seen,
            "quiet_window_ms": quiet_window_ms,
            "quiet_window_completed": quiet_window_completed,
            "messages": messages,
            "accounting_snapshots": snapshots,
            "final_accounting": final_projection,
            "final_process_ids": final_process_ids,
            "final_PID_inventory_empty": final_PID_inventory_empty,
            "quiescent": bool(
                final_projection["active_process_zero"]
                and active_process_zero_seen
                and final_PID_inventory_empty
                and not deadline_expired
            ),
        }

    def run(
        self,
        scenario: str,
        worker_args: list[str] | None = None,
        *,
        timeout_ms: int = 5000,
        process_time_limit: bool = False,
        process_memory_limit: bool = False,
        job_memory_limit: bool = False,
        terminate_on_ready: bool = False,
        output_limit: int = 65536,
        force_abort_before_job_assignment: bool = False,
        qualification_quiescence_required: bool = False,
        remediation_diagnostic: bool = False,
        final_remediation_diagnostic: bool = False,
        active_process_accounting_diagnostic: bool = False,
        process_time_control_diagnostic: bool = False,
        live_companion_attribution_diagnostic: bool = False,
        assigned_suspended_target_flag_preservation_diagnostic: bool = False,
        trusted_cpu_watchdog_enabled: bool = False,
        trusted_cpu_budget_100ns: int = 10_000_000,
        trusted_cpu_poll_interval_ms: int = 20,
        trusted_cpu_maximum_final_user_time_100ns: int = 15_000_000,
        trusted_pending_connect_watchdog_enabled: bool = False,
        trusted_pending_connect_listener: socket.socket | None = None,
        require_non_nested_target: bool = False,
        use_appcontainer: bool = True,
        active_process_limit: int | None = 2,
        defer_process_time_limit_until_assigned: bool = False,
        deferred_process_time_information_class: int = JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
        diagnostic_case_id: str | None = None,
        completion_quiet_window_ms: int | None = None,
        checkpoint_names: list[str] | None = None,
    ) -> dict[str, object]:
        worker_args = worker_args or []
        checkpoint_names = checkpoint_names or []
        if deferred_process_time_information_class not in (
            JOB_OBJECT_BASIC_LIMIT_INFORMATION,
            JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
        ):
            raise ProbeStop(
                "PROCESS_TIME_INFORMATION_CLASS_INVALID",
                str(deferred_process_time_information_class),
            )
        if deferred_process_time_information_class == JOB_OBJECT_BASIC_LIMIT_INFORMATION and not (
            (process_time_control_diagnostic or assigned_suspended_target_flag_preservation_diagnostic)
            and process_time_limit
            and defer_process_time_limit_until_assigned
            and active_process_limit is None
            and not process_memory_limit
            and not job_memory_limit
        ):
            raise ProbeStop("BASIC_PROCESS_TIME_INFORMATION_CLASS_SCOPE_MISMATCH", scenario)
        if diagnostic_case_id is not None and diagnostic_case_id not in {
            "IC-WIN-01",
            "IC-WIN-02",
            "IC-WIN-03",
            "IC-WIN-04",
            "AT-WIN-01",
            "AT-WIN-02",
            "RT-WIN-01",
            "RT-WIN-02",
            "RT-WIN-03",
            "RT-WIN-04",
            "RT-WIN-05",
            "RT-WIN-06",
            "RT-WIN-07",
            "RT-WIN-08",
            "WD-WIN-01",
            "WD-WIN-02",
            "WD-WIN-03",
            "WD-WIN-04",
            "WD-WIN-05",
            "WD-WIN-06",
            "WD-WIN-07",
            "WD-WIN-08",
        }:
            raise ProbeStop("DIAGNOSTIC_CASE_ID_INVALID", diagnostic_case_id)
        if trusted_cpu_watchdog_enabled and not (
            scenario == "cpu"
            and trusted_cpu_budget_100ns == 10_000_000
            and trusted_cpu_poll_interval_ms == 20
            and trusted_cpu_maximum_final_user_time_100ns == 15_000_000
            and timeout_ms == 5000
            and not process_time_limit
            and not defer_process_time_limit_until_assigned
            and active_process_limit is None
            and not process_memory_limit
            and not job_memory_limit
            and live_companion_attribution_diagnostic
            and require_non_nested_target
        ):
            raise ProbeStop(
                "TRUSTED_CPU_WATCHDOG_SCOPE_MISMATCH",
                canonical({
                    "scenario": scenario,
                    "trusted_cpu_budget_100ns": trusted_cpu_budget_100ns,
                    "trusted_cpu_poll_interval_ms": trusted_cpu_poll_interval_ms,
                    "trusted_cpu_maximum_final_user_time_100ns": (
                        trusted_cpu_maximum_final_user_time_100ns
                    ),
                    "timeout_ms": timeout_ms,
                    "process_time_limit": process_time_limit,
                    "defer_process_time_limit_until_assigned": defer_process_time_limit_until_assigned,
                    "active_process_limit": active_process_limit,
                    "process_memory_limit": process_memory_limit,
                    "job_memory_limit": job_memory_limit,
                    "live_companion_attribution_diagnostic": live_companion_attribution_diagnostic,
                    "require_non_nested_target": require_non_nested_target,
                }),
            )
        if trusted_pending_connect_watchdog_enabled and not (
            scenario == "native_winsock"
            and timeout_ms == 5000
            and not process_time_limit
            and not defer_process_time_limit_until_assigned
            and active_process_limit == 2
            and not process_memory_limit
            and not job_memory_limit
            and final_remediation_diagnostic
            and live_companion_attribution_diagnostic
            and trusted_pending_connect_listener is not None
            and completion_quiet_window_ms == 250
        ):
            raise ProbeStop(
                "TRUSTED_PENDING_CONNECT_WATCHDOG_SCOPE_MISMATCH",
                canonical({
                    "scenario": scenario,
                    "timeout_ms": timeout_ms,
                    "process_time_limit": process_time_limit,
                    "defer_process_time_limit_until_assigned": defer_process_time_limit_until_assigned,
                    "active_process_limit": active_process_limit,
                    "process_memory_limit": process_memory_limit,
                    "job_memory_limit": job_memory_limit,
                    "final_remediation_diagnostic": final_remediation_diagnostic,
                    "live_companion_attribution_diagnostic": live_companion_attribution_diagnostic,
                    "listener_present": trusted_pending_connect_listener is not None,
                    "completion_quiet_window_ms": completion_quiet_window_ms,
                }),
            )
        ic_win_basic_process_time_flags_only = bool(
            process_time_control_diagnostic
            and diagnostic_case_id in {
                "IC-WIN-03",
                "IC-WIN-04",
                "RT-WIN-02",
                "RT-WIN-04",
                "RT-WIN-05",
                "RT-WIN-07",
            }
            and deferred_process_time_information_class
            == JOB_OBJECT_BASIC_LIMIT_INFORMATION
            and process_time_limit
            and defer_process_time_limit_until_assigned
            and active_process_limit is None
            and not process_memory_limit
            and not job_memory_limit
        )
        if qualification_quiescence_required and not (
            scenario == "identity"
            and worker_args == []
            and timeout_ms == 5000
            and not process_time_limit
            and not process_memory_limit
            and not job_memory_limit
            and not terminate_on_ready
            and not force_abort_before_job_assignment
            and output_limit == 65536
            and not remediation_diagnostic
            and not final_remediation_diagnostic
            and not active_process_accounting_diagnostic
            and not process_time_control_diagnostic
            and not live_companion_attribution_diagnostic
            and not assigned_suspended_target_flag_preservation_diagnostic
            and not trusted_cpu_watchdog_enabled
            and not trusted_pending_connect_watchdog_enabled
            and not require_non_nested_target
            and use_appcontainer
            and active_process_limit == 2
            and not defer_process_time_limit_until_assigned
            and diagnostic_case_id is None
            and completion_quiet_window_ms is None
            and checkpoint_names == []
        ):
            raise ProbeStop("QUALIFICATION_QUIESCENCE_SCOPE_MISMATCH", scenario)
        diagnostic_mode = (
            qualification_quiescence_required
            or remediation_diagnostic
            or final_remediation_diagnostic
            or active_process_accounting_diagnostic
            or process_time_control_diagnostic
            or live_companion_attribution_diagnostic
            or assigned_suspended_target_flag_preservation_diagnostic
            or trusted_cpu_watchdog_enabled
            or trusted_pending_connect_watchdog_enabled
        )
        if checkpoint_names and not (final_remediation_diagnostic or active_process_accounting_diagnostic):
            raise ProbeStop("CHECKPOINT_SCOPE_MISMATCH", scenario)
        k = self.native.kernel32
        job = wt.HANDLE()
        completion = wt.HANDLE()
        process = PROCESS_INFORMATION()
        attr_buffer = None
        attr_initialized = False
        stdout_read = stdout_write = stderr_read = stderr_write = stdin_read = stdin_write = wt.HANDLE()
        collector: OutputCollector | None = None
        termination_reason = None
        assigned_before_resume = False
        resume_called = False
        direct_termination_before_resume = False
        identity: dict[str, object] | None = None
        job_messages: list[int] = []
        effective_job_limits: dict[str, int] | None = None
        initial_effective_job_limits: dict[str, int] | None = None
        target_process_times: dict[str, int] | None = None
        job_quiescence: dict[str, object] | None = None
        job_process_id_inventory: dict[str, object] = {}
        checkpoint_telemetry: list[dict[str, object]] = []
        limit_operations: list[dict[str, object]] = []
        job_membership: dict[str, object] = {}
        live_completion_events: list[dict[str, object]] = []
        live_processes: list[dict[str, object]] = []
        live_blocker: dict[str, object] | None = None
        live_target_notification_seen = False
        live_non_target_count = 0
        trusted_cpu_watchdog: dict[str, object] | None = None
        watchdog_monitor_started: float | None = None
        watchdog_sample_count = 0
        watchdog_all_GetProcessTimes_success = True
        watchdog_armed_before_resume = False
        watchdog_resume_thread_call_count = 0
        watchdog_initial_sample: dict[str, object] | None = None
        watchdog_previous_sample: dict[str, object] | None = None
        watchdog_trigger_sample: dict[str, object] | None = None
        watchdog_final_sample: dict[str, object] | None = None
        watchdog_failure_reason: str | None = None
        watchdog_termination: dict[str, object] | None = None
        watchdog_handle_process_id: int | None = None
        pending_connect_watchdog: dict[str, object] | None = None
        pending_connect_clock_started: float | None = None
        pending_connect_resume_offset_ms: int | None = None
        pending_connect_processed_records = 0
        pending_connect_parent_records: list[dict[str, object]] = []
        pending_connect_expected_sequence = 0
        pending_connect_ready_count = 0
        pending_connect_sample_count = 0
        pending_connect_ready_offset_ms: int | None = None
        pending_connect_last_sample_offset_ms: int | None = None
        pending_connect_maximum_sample_gap_ms = 0
        pending_connect_parent_poll_count = 0
        pending_connect_listener_accept_total = 0
        pending_connect_listener_observations: list[dict[str, object]] = []
        pending_connect_liveness_observations: list[dict[str, object]] = []
        pending_connect_failure_reason: str | None = None
        pending_connect_termination: dict[str, object] | None = None
        run_cleanup = {
            "process_handle_closed": False,
            "thread_handle_closed": False,
            "pipe_handles_closed": 0,
            "attribute_list_deleted": False,
            "Job_handle_closed": False,
            "completion_port_handle_closed": False,
        }
        live_started = time.monotonic()
        attempt_start_FILETIME_100ns = int(time.time_ns() // 100) + 116_444_736_000_000_000
        processed_checkpoint_count = 0
        inactive_after_termination = False
        command = [
            str(self.python),
            "-I",
            "-B",
            str(self.worker),
            "--scenario",
            scenario,
            "--python",
            str(self.python),
            "--worker",
            str(self.worker),
            *worker_args,
        ]
        if remediation_diagnostic:
            command.append("--case-remediation-diagnostic")
        if final_remediation_diagnostic:
            command.append("--final-remediation-diagnostic")
        if active_process_accounting_diagnostic:
            command.append("--active-process-accounting-diagnostic")
        if trusted_pending_connect_watchdog_enabled:
            command.append("--trusted-pending-connect-watchdog")

        def information_class_set_failure_detail(
            phase: str,
            information_class_value: int,
            information_class_name: str,
            structure_name: str,
            structure_size: int,
            limit_flags: int | None,
            per_process_user_time_limit: int | None,
            bool_result: bool,
            immediate_error: int,
        ) -> str:
            return canonical({
                "diagnostic_case_id": diagnostic_case_id,
                "worker_scenario": scenario,
                "use_appcontainer": use_appcontainer,
                "phase": phase,
                "information_class_value": information_class_value,
                "information_class_name": information_class_name,
                "structure_name": structure_name,
                "structure_size": structure_size,
                "LimitFlags": limit_flags,
                "PerProcessUserTimeLimit": per_process_user_time_limit,
                "bool_result": bool_result,
                "immediate_GetLastError": immediate_error,
            })

        def information_class_readback_mismatch_detail(
            phase: str,
            expected: dict[str, int],
            actual: dict[str, int],
        ) -> str:
            return canonical({
                "diagnostic_case_id": diagnostic_case_id,
                "worker_scenario": scenario,
                "use_appcontainer": use_appcontainer,
                "phase": phase,
                "information_class_value": JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                "information_class_name": "JobObjectExtendedLimitInformation",
                "structure_name": "JOBOBJECT_EXTENDED_LIMIT_INFORMATION",
                "structure_size": ct.sizeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION),
                "LimitFlags": actual.get("LimitFlags"),
                "PerProcessUserTimeLimit": actual.get("PerProcessUserTimeLimit"),
                "bool_result": bool(actual.get("QueryInformationJobObject_result")),
                "immediate_GetLastError": actual.get("QueryInformationJobObject_last_error"),
                "expected": expected,
                "actual": actual,
            })
        try:
            job = k.CreateJobObjectW(None, None)
            if not job:
                raise ProbeStop("JOB_CREATE_FAILED", scenario, ct.get_last_error())
            completion = k.CreateIoCompletionPort(INVALID_HANDLE_VALUE, None, 0, 1)
            if not completion:
                raise ProbeStop("COMPLETION_PORT_CREATE_FAILED", scenario, ct.get_last_error())
            association = JOBOBJECT_ASSOCIATE_COMPLETION_PORT(ct.c_void_p(1), completion)
            if not k.SetInformationJobObject(job, JOB_OBJECT_ASSOCIATE_COMPLETION_PORT_INFORMATION, ct.byref(association), ct.sizeof(association)):
                association_error = ct.get_last_error()
                detail = scenario
                if diagnostic_case_id is not None:
                    detail = information_class_set_failure_detail(
                        "completion_port_association",
                        JOB_OBJECT_ASSOCIATE_COMPLETION_PORT_INFORMATION,
                        "JobObjectAssociateCompletionPortInformation",
                        "JOBOBJECT_ASSOCIATE_COMPLETION_PORT",
                        ct.sizeof(association),
                        None,
                        None,
                        False,
                        association_error,
                    )
                raise ProbeStop("JOB_COMPLETION_ASSOCIATION_FAILED", detail, association_error)

            limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            flags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION
            if active_process_limit is not None:
                flags |= JOB_OBJECT_LIMIT_ACTIVE_PROCESS
                limits.BasicLimitInformation.ActiveProcessLimit = active_process_limit
            if process_time_limit and not defer_process_time_limit_until_assigned:
                flags |= JOB_OBJECT_LIMIT_PROCESS_TIME
                limits.BasicLimitInformation.PerProcessUserTimeLimit = 10_000_000
            if process_memory_limit:
                flags |= JOB_OBJECT_LIMIT_PROCESS_MEMORY
                limits.ProcessMemoryLimit = 67_108_864
            if job_memory_limit:
                flags |= JOB_OBJECT_LIMIT_JOB_MEMORY
                limits.JobMemoryLimit = 100_663_296
            limits.BasicLimitInformation.LimitFlags = flags
            ct.set_last_error(0)
            initial_limits_ok = bool(k.SetInformationJobObject(
                job,
                JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                ct.byref(limits),
                ct.sizeof(limits),
            ))
            initial_limits_error = ct.get_last_error()
            if process_time_control_diagnostic or assigned_suspended_target_flag_preservation_diagnostic:
                limit_operations.append({
                    "phase": "before_assignment_initial",
                    "SetInformationJobObject_result": initial_limits_ok,
                    "SetInformationJobObject_last_error": int(initial_limits_error),
                    "information_class": JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                    "information_class_name": "JobObjectExtendedLimitInformation",
                    "structure_name": "JOBOBJECT_EXTENDED_LIMIT_INFORMATION",
                    "LimitFlags": int(limits.BasicLimitInformation.LimitFlags),
                    "PerProcessUserTimeLimit": int(limits.BasicLimitInformation.PerProcessUserTimeLimit),
                    "information_length": ct.sizeof(limits),
                })
            if not initial_limits_ok:
                detail = scenario
                if diagnostic_case_id is not None:
                    detail = information_class_set_failure_detail(
                        "before_assignment_initial",
                        JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                        "JobObjectExtendedLimitInformation",
                        "JOBOBJECT_EXTENDED_LIMIT_INFORMATION",
                        ct.sizeof(limits),
                        int(limits.BasicLimitInformation.LimitFlags),
                        int(limits.BasicLimitInformation.PerProcessUserTimeLimit),
                        initial_limits_ok,
                        initial_limits_error,
                    )
                raise ProbeStop("JOB_LIMITS_FAILED", detail, initial_limits_error)
            if diagnostic_mode:
                effective_job_limits = self._query_effective_limits(job, scenario)
                if assigned_suspended_target_flag_preservation_diagnostic:
                    initial_effective_job_limits = dict(effective_job_limits)

            stdout_read, stdout_write = self._pipe()
            stderr_read, stderr_write = self._pipe()
            stdin_read, stdin_write = self._pipe()
            self._set_not_inheritable(stdout_read)
            self._set_not_inheritable(stderr_read)
            self._set_not_inheritable(stdin_write)

            attributes_size = SIZE_T()
            attribute_count = 2 if use_appcontainer else 1
            k.InitializeProcThreadAttributeList(None, attribute_count, 0, ct.byref(attributes_size))
            if ct.get_last_error() != ERROR_INSUFFICIENT_BUFFER or attributes_size.value == 0:
                raise ProbeStop("ATTRIBUTE_SIZE_FAILED", scenario, ct.get_last_error())
            attr_buffer = ct.create_string_buffer(attributes_size.value)
            attr_pointer = ct.cast(attr_buffer, ct.c_void_p)
            if not k.InitializeProcThreadAttributeList(attr_pointer, attribute_count, 0, ct.byref(attributes_size)):
                raise ProbeStop("ATTRIBUTE_INIT_FAILED", scenario, ct.get_last_error())
            attr_initialized = True
            security = None
            if use_appcontainer:
                security = SECURITY_CAPABILITIES(self.sid, None, 0, 0)
                if not k.UpdateProcThreadAttribute(
                    attr_pointer,
                    0,
                    PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES,
                    ct.byref(security),
                    ct.sizeof(security),
                    None,
                    None,
                ):
                    raise ProbeStop("SECURITY_CAPABILITIES_ATTRIBUTE_FAILED", scenario, ct.get_last_error())
            handles = (wt.HANDLE * 3)(stdin_read, stdout_write, stderr_write)
            if not k.UpdateProcThreadAttribute(
                attr_pointer,
                0,
                PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
                ct.cast(handles, ct.c_void_p),
                ct.sizeof(handles),
                None,
                None,
            ):
                raise ProbeStop("HANDLE_LIST_ATTRIBUTE_FAILED", scenario, ct.get_last_error())

            startup = STARTUPINFOEXW()
            startup.StartupInfo.cb = ct.sizeof(startup)
            startup.StartupInfo.dwFlags = STARTF_USESTDHANDLES
            startup.StartupInfo.lpDesktop = "winsta0\\default"
            startup.StartupInfo.hStdInput = stdin_read
            startup.StartupInfo.hStdOutput = stdout_write
            startup.StartupInfo.hStdError = stderr_write
            startup.lpAttributeList = attr_pointer
            command_line = ct.create_unicode_buffer(subprocess.list2cmdline(command))
            environment_values, environment_block = self._environment()
            flags_value = CREATE_SUSPENDED | EXTENDED_STARTUPINFO_PRESENT | CREATE_UNICODE_ENVIRONMENT | CREATE_NO_WINDOW
            if not k.CreateProcessW(
                str(self.python),
                command_line,
                None,
                None,
                True,
                flags_value,
                environment_block,
                str(self.sandbox),
                ct.byref(startup.StartupInfo),
                ct.byref(process),
            ):
                error = ct.get_last_error()
                raise ProbeStop("APPCONTAINER_PROCESS_CREATE_FAILED", scenario, error)

            self.native.close(stdout_write); stdout_write = wt.HANDLE()
            self.native.close(stderr_write); stderr_write = wt.HANDLE()
            self.native.close(stdin_read); stdin_read = wt.HANDLE()
            if assigned_suspended_target_flag_preservation_diagnostic:
                run_cleanup["pipe_handles_closed"] = int(run_cleanup["pipe_handles_closed"]) + 3
            if not (final_remediation_diagnostic or active_process_accounting_diagnostic):
                self.native.close(stdin_write); stdin_write = wt.HANDLE()
                if assigned_suspended_target_flag_preservation_diagnostic:
                    run_cleanup["pipe_handles_closed"] = int(run_cleanup["pipe_handles_closed"]) + 1

            identity = self.native.process_identity(process.hProcess)
            if use_appcontainer:
                if not identity["token_is_appcontainer"]:
                    raise ProbeStop("CHILD_NOT_APPCONTAINER", scenario)
                if identity["capability_count"] != 0:
                    raise ProbeStop("CHILD_CAPABILITIES_NONZERO", scenario)
            else:
                if identity["token_is_appcontainer"] or identity["appcontainer_sid"] is not None:
                    raise ProbeStop("NON_APPCONTAINER_CONTROL_IDENTITY_MISMATCH", scenario)
                if identity["capability_count"] != 0:
                    raise ProbeStop("NON_APPCONTAINER_CONTROL_CAPABILITIES_NONZERO", scenario)
            if (
                process_time_control_diagnostic
                or live_companion_attribution_diagnostic
                or assigned_suspended_target_flag_preservation_diagnostic
                or trusted_cpu_watchdog_enabled
                or trusted_pending_connect_watchdog_enabled
            ):
                job_membership["target_in_any_Job_before_owned_assignment"] = self.process_in_job(
                    process.hProcess,
                    None,
                    scenario,
                    "target_any_before_owned_assignment",
                )
                job_membership["target_in_owned_Job_before_assignment"] = self.process_in_job(
                    process.hProcess,
                    job,
                    scenario,
                    "target_owned_before_assignment",
                )
                if require_non_nested_target and (
                    job_membership["target_in_any_Job_before_owned_assignment"] is not False
                    or job_membership["target_in_owned_Job_before_assignment"] is not False
                ):
                    if not k.TerminateProcess(process.hProcess, 0xEE20):
                        raise ProbeStop(
                            "NESTED_TARGET_CLEANUP_TERMINATE_FAILED",
                            scenario,
                            ct.get_last_error(),
                        )
                    direct_termination_before_resume = True
                    if int(k.WaitForSingleObject(process.hProcess, 10_000)) != WAIT_OBJECT_0:
                        raise ProbeStop(
                            "NESTED_TARGET_CLEANUP_WAIT_FAILED",
                            scenario,
                            ct.get_last_error(),
                        )
                    raise ProbeStop(
                        "NESTED_TARGET_CONTEXT_REQUIRES_SEPARATE_DISPOSITION",
                        canonical({
                            "scenario": scenario,
                            "process_id": int(process.dwProcessId),
                            "created_suspended": True,
                            "resume_called": False,
                            "direct_termination_before_resume": True,
                            "job_membership": job_membership,
                        }),
                    )
            if force_abort_before_job_assignment:
                if not k.TerminateProcess(process.hProcess, 0xEE10):
                    raise ProbeStop("PRE_JOB_ABORT_TERMINATE_FAILED", scenario, ct.get_last_error())
                direct_termination_before_resume = True
                if int(k.WaitForSingleObject(process.hProcess, 10_000)) != WAIT_OBJECT_0:
                    raise ProbeStop("PRE_JOB_ABORT_WAIT_FAILED", scenario, ct.get_last_error())
                exit_code = wt.DWORD()
                if not k.GetExitCodeProcess(process.hProcess, ct.byref(exit_code)):
                    raise ProbeStop("PRE_JOB_ABORT_EXIT_CODE_FAILED", scenario, ct.get_last_error())
                return {
                    "scenario": scenario,
                    "command_argv": command,
                    "environment": environment_values,
                    "creation_flags": flags_value,
                    "created_suspended": True,
                    "assigned_before_resume": False,
                    "resume_called": False,
                    "direct_termination_before_resume": True,
                    "identity": identity,
                    "process_id": int(process.dwProcessId),
                    "exit_code": int(exit_code.value),
                    "inactive_after_termination": int(k.WaitForSingleObject(process.hProcess, 0)) == WAIT_OBJECT_0,
                }
            if not k.AssignProcessToJobObject(job, process.hProcess):
                error = ct.get_last_error()
                k.TerminateProcess(process.hProcess, 0xEE01)
                raise ProbeStop("JOB_ASSIGNMENT_FAILED", scenario, error)
            in_job = wt.BOOL()
            if not k.IsProcessInJob(process.hProcess, job, ct.byref(in_job)) or not in_job.value:
                k.TerminateProcess(process.hProcess, 0xEE02)
                raise ProbeStop("JOB_ASSIGNMENT_NOT_PROVEN", scenario, ct.get_last_error())
            assigned_before_resume = True
            if (
                process_time_control_diagnostic
                or live_companion_attribution_diagnostic
                or trusted_cpu_watchdog_enabled
                or trusted_pending_connect_watchdog_enabled
            ):
                job_membership["target_in_owned_Job_after_assignment"] = self.process_in_job(
                    process.hProcess,
                    job,
                    scenario,
                    "target_owned_after_assignment",
                )
            if process_time_limit and defer_process_time_limit_until_assigned:
                if deferred_process_time_information_class == JOB_OBJECT_EXTENDED_LIMIT_INFORMATION:
                    deferred_limits = limits
                    deferred_limit_fields = deferred_limits.BasicLimitInformation
                    deferred_information_class_name = "JobObjectExtendedLimitInformation"
                    deferred_structure_name = "JOBOBJECT_EXTENDED_LIMIT_INFORMATION"
                else:
                    deferred_limits = JOBOBJECT_BASIC_LIMIT_INFORMATION()
                    if (
                        assigned_suspended_target_flag_preservation_diagnostic
                        or ic_win_basic_process_time_flags_only
                    ):
                        deferred_limits.LimitFlags = JOB_OBJECT_LIMIT_PROCESS_TIME
                    else:
                        deferred_limits.LimitFlags = int(limits.BasicLimitInformation.LimitFlags)
                    deferred_limit_fields = deferred_limits
                    deferred_information_class_name = "JobObjectBasicLimitInformation"
                    deferred_structure_name = "JOBOBJECT_BASIC_LIMIT_INFORMATION"
                if not (
                    assigned_suspended_target_flag_preservation_diagnostic
                    or ic_win_basic_process_time_flags_only
                ):
                    deferred_limit_fields.LimitFlags = (
                        int(deferred_limit_fields.LimitFlags) | JOB_OBJECT_LIMIT_PROCESS_TIME
                    )
                deferred_limit_fields.PerProcessUserTimeLimit = 10_000_000
                ct.set_last_error(0)
                deferred_limits_ok = bool(k.SetInformationJobObject(
                    job,
                    deferred_process_time_information_class,
                    ct.byref(deferred_limits),
                    ct.sizeof(deferred_limits),
                ))
                deferred_limits_error = ct.get_last_error()
                if process_time_control_diagnostic or assigned_suspended_target_flag_preservation_diagnostic:
                    limit_operations.append({
                        "phase": "after_assignment_before_resume",
                        "SetInformationJobObject_result": deferred_limits_ok,
                        "SetInformationJobObject_last_error": int(deferred_limits_error),
                        "information_class": deferred_process_time_information_class,
                        "information_class_name": deferred_information_class_name,
                        "structure_name": deferred_structure_name,
                        "LimitFlags": int(deferred_limit_fields.LimitFlags),
                        "PerProcessUserTimeLimit": int(deferred_limit_fields.PerProcessUserTimeLimit),
                        "information_length": ct.sizeof(deferred_limits),
                    })
                if not deferred_limits_ok:
                    if not assigned_suspended_target_flag_preservation_diagnostic:
                        k.TerminateJobObject(job, 0xEE04)
                        detail = scenario
                        if diagnostic_case_id is not None:
                            detail = information_class_set_failure_detail(
                                "after_assignment_before_resume",
                                deferred_process_time_information_class,
                                deferred_information_class_name,
                                deferred_structure_name,
                                ct.sizeof(deferred_limits),
                                int(deferred_limit_fields.LimitFlags),
                                int(deferred_limit_fields.PerProcessUserTimeLimit),
                                deferred_limits_ok,
                                deferred_limits_error,
                            )
                        raise ProbeStop("DEFERRED_JOB_LIMITS_FAILED", detail, deferred_limits_error)
                effective_job_limits = self._query_effective_limits(job, scenario)
                if not assigned_suspended_target_flag_preservation_diagnostic and (
                    effective_job_limits["PerProcessUserTimeLimit"] != 10_000_000
                    or not (effective_job_limits["LimitFlags"] & JOB_OBJECT_LIMIT_PROCESS_TIME)
                    or (effective_job_limits["LimitFlags"] & JOB_OBJECT_LIMIT_ACTIVE_PROCESS)
                ):
                    k.TerminateJobObject(job, 0xEE05)
                    detail = canonical(effective_job_limits)
                    if diagnostic_case_id is not None:
                        detail = information_class_readback_mismatch_detail(
                            "after_assignment_before_resume_readback",
                            {
                                "LimitFlags_required_bits": JOB_OBJECT_LIMIT_PROCESS_TIME,
                                "LimitFlags_forbidden_bits": JOB_OBJECT_LIMIT_ACTIVE_PROCESS,
                                "PerProcessUserTimeLimit": 10_000_000,
                            },
                            effective_job_limits,
                        )
                    raise ProbeStop("DEFERRED_JOB_LIMIT_READBACK_MISMATCH", detail)
            if process_time_control_diagnostic or assigned_suspended_target_flag_preservation_diagnostic:
                if effective_job_limits is None:
                    effective_job_limits = self._query_effective_limits(job, scenario)
                if effective_job_limits.get("QueryInformationJobObject_returned_length") != ct.sizeof(
                    JOBOBJECT_EXTENDED_LIMIT_INFORMATION
                ):
                    k.TerminateJobObject(job, 0xEE06)
                    detail = canonical(effective_job_limits)
                    if diagnostic_case_id is not None:
                        detail = information_class_readback_mismatch_detail(
                            "after_assignment_before_resume_readback_length",
                            {
                                "QueryInformationJobObject_returned_length": ct.sizeof(
                                    JOBOBJECT_EXTENDED_LIMIT_INFORMATION
                                ),
                            },
                            effective_job_limits,
                        )
                    raise ProbeStop(
                        "JOB_LIMIT_READBACK_LENGTH_MISMATCH",
                        detail,
                    )
            if diagnostic_mode:
                before_resume = self._query_job_process_ids(job, scenario)
                job_process_id_inventory["before_worker_resume"] = before_resume
                job_process_id_inventory["before_explicit_Popen"] = {
                    **before_resume,
                    "capture_basis": "worker_suspended_before_any_worker_code_or_explicit_Popen",
                }
            def set_live_blocker(code: str, detail: str, raw_code: int | None = None) -> None:
                nonlocal live_blocker, termination_reason
                if live_blocker is None:
                    live_blocker = {"code": code, "detail": detail, "raw_code": raw_code}
                    termination_reason = "live_attribution_hard_stop"
                    k.TerminateJobObject(job, 0xEE27)

            def capture_live_PID(pid: int, phase: str) -> None:
                nonlocal live_target_notification_seen, live_non_target_count
                if pid <= 0:
                    set_live_blocker("LIVE_NOTIFICATION_PID_INVALID", f"{phase}:{pid}")
                    return
                is_target = pid == int(process.dwProcessId)
                if is_target:
                    if live_target_notification_seen:
                        set_live_blocker("LIVE_TARGET_NOTIFICATION_DUPLICATE", f"{phase}:{pid}")
                        return
                    live_target_notification_seen = True
                    relationship = "target"
                    explicit_assignment = True
                    live_process = process.hProcess
                    close_live_process = False
                else:
                    live_non_target_count += 1
                    relationship = "companion_candidate" if live_non_target_count == 1 else "uncontracted_process"
                    explicit_assignment = False
                    live_process = k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                    close_live_process = True
                    if not live_process:
                        set_live_blocker("LIVE_OPEN_PROCESS_FAILED", f"{phase}:{pid}", ct.get_last_error())
                        return
                try:
                    captured = self.native.live_process_attribution(live_process, pid)
                    capture_FILETIME_100ns = int(time.time_ns() // 100) + 116_444_736_000_000_000
                    creation_time = int(captured["creation_FILETIME_100ns"])
                    if not (
                        attempt_start_FILETIME_100ns - 20_000_000
                        <= creation_time
                        <= capture_FILETIME_100ns + 20_000_000
                    ):
                        raise ProbeStop(
                            "LIVE_CREATION_TIME_OUTSIDE_ATTEMPT",
                            f"{pid}:{creation_time}:{attempt_start_FILETIME_100ns}:{capture_FILETIME_100ns}",
                        )
                    captured.update({
                        "relationship": relationship,
                        "explicit_assignment_by_diagnostic": explicit_assignment,
                        "live_owned_Job_membership": self.process_in_job(
                            live_process,
                            job,
                            scenario,
                            f"live_owned:{pid}",
                        ),
                        "inherited_owned_Job_membership_evidence": bool(
                            not explicit_assignment
                            and self.process_in_job(live_process, job, scenario, f"live_inherited:{pid}")
                        ),
                        "capture_phase": phase,
                        "capture_FILETIME_100ns": capture_FILETIME_100ns,
                    })
                    live_processes.append(captured)
                    if relationship == "uncontracted_process":
                        set_live_blocker("LIVE_UNCONTRACTED_PROCESS", f"{phase}:{pid}")
                except ProbeStop as exc:
                    set_live_blocker(exc.code, exc.detail, exc.raw_code)
                finally:
                    if close_live_process:
                        self.native.close(live_process)

            def drain_live_completion(wait_ms: int, phase: str) -> bool:
                message = wt.DWORD()
                key = ULONG_PTR()
                overlapped = ct.c_void_p()
                ct.set_last_error(0)
                ok = k.GetQueuedCompletionStatus(
                    completion,
                    ct.byref(message),
                    ct.byref(key),
                    ct.byref(overlapped),
                    wait_ms,
                )
                if not ok:
                    error = ct.get_last_error()
                    if error == WAIT_TIMEOUT:
                        return False
                    set_live_blocker("LIVE_COMPLETION_PORT_READ_FAILED", phase, error)
                    return False
                event = {
                    "message": int(message.value),
                    "monotonic_offset_ms": int((time.monotonic() - live_started) * 1000),
                    "completion_key": int(key.value),
                    "process_id_value": int(overlapped.value or 0),
                    "phase": phase,
                }
                live_completion_events.append(event)
                if event["message"] == JOB_OBJECT_MSG_NEW_PROCESS:
                    capture_live_PID(int(event["process_id_value"]), phase)
                return True

            def capture_watchdog_sample(phase: str) -> dict[str, object]:
                nonlocal watchdog_sample_count, watchdog_all_GetProcessTimes_success
                watchdog_sample_count += 1
                creation = FILETIME()
                exit_time = FILETIME()
                kernel_time = FILETIME()
                user_time = FILETIME()
                ct.set_last_error(0)
                query_ok = bool(k.GetProcessTimes(
                    process.hProcess,
                    ct.byref(creation),
                    ct.byref(exit_time),
                    ct.byref(kernel_time),
                    ct.byref(user_time),
                ))
                query_error = ct.get_last_error()
                process_wait_result = int(k.WaitForSingleObject(process.hProcess, 0))
                process_active_state: bool | None
                if process_wait_result == WAIT_TIMEOUT:
                    process_active_state = True
                elif process_wait_result == WAIT_OBJECT_0:
                    process_active_state = False
                else:
                    process_active_state = None
                if not query_ok or process_active_state is None:
                    watchdog_all_GetProcessTimes_success = False

                def filetime_value(value: FILETIME) -> int:
                    return (int(value.dwHighDateTime) << 32) | int(value.dwLowDateTime)

                return {
                    "sequence": watchdog_sample_count,
                    "phase": phase,
                    "monotonic_offset_ms": (
                        int((time.monotonic() - watchdog_monitor_started) * 1000)
                        if watchdog_monitor_started is not None
                        else 0
                    ),
                    "target_creation_FILETIME_100ns": filetime_value(creation) if query_ok else None,
                    "user_time_100ns": filetime_value(user_time) if query_ok else None,
                    "kernel_time_100ns": filetime_value(kernel_time) if query_ok else None,
                    "process_active_state": process_active_state,
                    "process_wait_result": process_wait_result,
                    "GetProcessTimes_BOOL": query_ok,
                    "immediate_GetLastError": int(query_error),
                }

            def terminate_for_watchdog(reason: str, exit_code: int) -> dict[str, object]:
                nonlocal termination_reason, watchdog_termination
                ct.set_last_error(0)
                terminate_result = bool(k.TerminateJobObject(job, exit_code))
                terminate_error = ct.get_last_error()
                termination_reason = reason
                watchdog_termination = {
                    "reason": reason,
                    "exit_code": exit_code,
                    "TerminateJobObject_BOOL": terminate_result,
                    "immediate_GetLastError": int(terminate_error),
                    "monotonic_offset_ms": (
                        int((time.monotonic() - watchdog_monitor_started) * 1000)
                        if watchdog_monitor_started is not None
                        else 0
                    ),
                }
                return watchdog_termination

            def pending_connect_offset_ms() -> int:
                return (
                    int((time.monotonic() - pending_connect_clock_started) * 1000)
                    if pending_connect_clock_started is not None
                    else 0
                )

            def observe_pending_connect_listener(phase: str) -> int:
                nonlocal pending_connect_listener_accept_total
                if trusted_pending_connect_listener is None:
                    return 0
                observed = listener_accept_count(trusted_pending_connect_listener)
                pending_connect_listener_accept_total += observed
                pending_connect_listener_observations.append({
                    "phase": phase,
                    "parent_monotonic_offset_ms": pending_connect_offset_ms(),
                    "observed_accept_count": observed,
                    "cumulative_accept_count": pending_connect_listener_accept_total,
                })
                return observed

            def terminate_pending_connect(reason: str, exit_code: int) -> dict[str, object]:
                nonlocal termination_reason, pending_connect_termination
                if pending_connect_termination is not None:
                    return pending_connect_termination
                ct.set_last_error(0)
                terminate_result = bool(k.TerminateJobObject(job, exit_code))
                terminate_error = ct.get_last_error()
                termination_reason = reason
                pending_connect_termination = {
                    "reason": reason,
                    "exit_code": exit_code,
                    "TerminateJobObject_BOOL": terminate_result,
                    "immediate_GetLastError": int(terminate_error),
                    "parent_monotonic_offset_ms": pending_connect_offset_ms(),
                }
                return pending_connect_termination

            if live_companion_attribution_diagnostic:
                deadline = time.monotonic() + 2.0
                quiet_started: float | None = None
                while time.monotonic() < deadline and live_blocker is None:
                    received = drain_live_completion(20, "before_resume")
                    if received:
                        quiet_started = None
                    elif live_target_notification_seen:
                        if quiet_started is None:
                            quiet_started = time.monotonic()
                        elif (time.monotonic() - quiet_started) * 1000 >= 250:
                            break
                if not live_target_notification_seen and live_blocker is None:
                    set_live_blocker("LIVE_TARGET_NOTIFICATION_MISSING", "before_resume")

            if trusted_pending_connect_watchdog_enabled:
                pending_connect_clock_started = time.monotonic()
                if observe_pending_connect_listener("before_resume") != 0:
                    pending_connect_failure_reason = "listener_accept_before_resume"
                    direct_termination_before_resume = True
                    terminate_pending_connect(
                        "trusted_pending_connect_listener_accept_before_resume",
                        0xEE52,
                    )

            if trusted_cpu_watchdog_enabled:
                watchdog_monitor_started = time.monotonic()
                ct.set_last_error(0)
                watchdog_handle_process_id = int(k.GetProcessId(process.hProcess))
                handle_process_id_error = ct.get_last_error()
                if watchdog_handle_process_id != int(process.dwProcessId):
                    direct_termination_before_resume = True
                    termination = terminate_for_watchdog(
                        "trusted_cpu_watchdog_process_handle_mismatch",
                        0xEE40,
                    )
                    raise ProbeStop(
                        "TRUSTED_CPU_WATCHDOG_PROCESS_HANDLE_MISMATCH",
                        canonical({
                            "expected_process_id": int(process.dwProcessId),
                            "handle_process_id": watchdog_handle_process_id,
                            "GetProcessId_last_error": int(handle_process_id_error),
                            "termination": termination,
                        }),
                        int(handle_process_id_error),
                    )
                watchdog_initial_sample = capture_watchdog_sample("armed_before_resume")
                watchdog_previous_sample = watchdog_initial_sample
                if (
                    watchdog_initial_sample.get("GetProcessTimes_BOOL") is not True
                    or watchdog_initial_sample.get("process_active_state") is not True
                    or not isinstance(watchdog_initial_sample.get("user_time_100ns"), int)
                    or isinstance(watchdog_initial_sample.get("user_time_100ns"), bool)
                    or int(watchdog_initial_sample["user_time_100ns"]) >= trusted_cpu_budget_100ns
                ):
                    direct_termination_before_resume = True
                    termination = terminate_for_watchdog(
                        "trusted_cpu_watchdog_arm_failed",
                        0xEE41,
                    )
                    raise ProbeStop(
                        "TRUSTED_CPU_WATCHDOG_ARM_FAILED",
                        canonical({
                            "initial_sample": watchdog_initial_sample,
                            "termination": termination,
                        }),
                        watchdog_initial_sample.get("immediate_GetLastError"),
                    )
                watchdog_armed_before_resume = True

            if assigned_suspended_target_flag_preservation_diagnostic:
                if live_blocker is not None:
                    raise ProbeStop(
                        str(live_blocker["code"]),
                        str(live_blocker["detail"]),
                        live_blocker.get("raw_code"),
                    )
                control_started = time.monotonic()
                ct.set_last_error(0)
                owned_job_termination_result = bool(k.TerminateJobObject(job, 0xEE31))
                owned_job_termination_error = ct.get_last_error()
                if not owned_job_termination_result:
                    raise ProbeStop(
                        "ASSIGNED_TARGET_OWNED_JOB_TERMINATION_FAILED",
                        scenario,
                        owned_job_termination_error,
                    )
                termination_reason = "assigned_suspended_target_control_termination"
                direct_termination_before_resume = True
                wait_result = int(k.WaitForSingleObject(process.hProcess, 10_000))
                if wait_result != WAIT_OBJECT_0:
                    raise ProbeStop("ASSIGNED_TARGET_TERMINATION_WAIT_FAILED", scenario, wait_result)
                inactive_after_termination = int(k.WaitForSingleObject(process.hProcess, 0)) == WAIT_OBJECT_0
                exit_code = wt.DWORD()
                if not k.GetExitCodeProcess(process.hProcess, ct.byref(exit_code)):
                    raise ProbeStop("EXIT_CODE_FAILED", scenario, ct.get_last_error())
                target_process_times = self._process_times(process.hProcess, scenario)
                job_quiescence = self._collect_quiescence(
                    job,
                    completion,
                    scenario,
                    control_started,
                    quiet_window_ms=completion_quiet_window_ms,
                    initial_messages=live_completion_events,
                )
                accounting_projection = job_quiescence["final_accounting"]
                job_messages = [int(value["message"]) for value in job_quiescence["messages"]]
                job_process_id_inventory["after_scenario_completion"] = job_quiescence["final_process_ids"]
                empty_output = {
                    "total_bytes": 0,
                    "retained_prefix_bytes": 0,
                    "full_stream_sha256": sha256_bytes(b""),
                    "prefix_sha256": sha256_bytes(b""),
                    "overflow": False,
                    "reader_errors": [],
                    "text_prefix": "",
                }
                return {
                    "scenario": scenario,
                    "command_argv": command,
                    "environment": environment_values,
                    "creation_flags": flags_value,
                    "created_suspended": True,
                    "assigned_before_resume": assigned_before_resume,
                    "resume_called": False,
                    "resume_thread_call_count": 0,
                    "direct_termination_before_resume": direct_termination_before_resume,
                    "inactive_after_termination": inactive_after_termination,
                    "identity": identity,
                    "process_id": int(process.dwProcessId),
                    "exit_code": int(exit_code.value),
                    "termination_reason": termination_reason,
                    "ready_seen": False,
                    "worker_record_count": 0,
                    "output": empty_output,
                    "job_messages": job_messages,
                    "job_accounting": accounting_projection,
                    "initial_effective_job_limits": initial_effective_job_limits,
                    "effective_job_limits": effective_job_limits,
                    "target_process_times": target_process_times,
                    "job_process_id_inventory": job_process_id_inventory,
                    "job_quiescence": job_quiescence,
                    "checkpoint_telemetry": [],
                    "checkpoint_sequence_complete": True,
                    "use_appcontainer": use_appcontainer,
                    "job_membership": job_membership,
                    "limit_operations": limit_operations,
                    "owned_job_termination": {
                        "result": owned_job_termination_result,
                        "immediate_GetLastError": int(owned_job_termination_error),
                        "exit_code": 0xEE31,
                    },
                    "run_cleanup": run_cleanup,
                    "live_attribution": {
                        "attempt_start_FILETIME_100ns": attempt_start_FILETIME_100ns,
                        "target_notification_seen": live_target_notification_seen,
                        "non_target_notification_count": live_non_target_count,
                        "completion_events": live_completion_events,
                        "captured_processes": live_processes,
                        "blocker": live_blocker,
                    },
                }

            collector = OutputCollector(self.native, output_limit)
            collector.start("stdout", stdout_read); stdout_read = wt.HANDLE()
            collector.start("stderr", stderr_read); stderr_read = wt.HANDLE()
            if (final_remediation_diagnostic or active_process_accounting_diagnostic) and not checkpoint_names:
                self.native.close(stdin_write); stdin_write = wt.HANDLE()
            if live_blocker is None and pending_connect_failure_reason is None:
                if trusted_cpu_watchdog_enabled:
                    watchdog_resume_thread_call_count += 1
                if k.ResumeThread(process.hThread) == 0xFFFFFFFF:
                    k.TerminateJobObject(job, 0xEE03)
                    raise ProbeStop("RESUME_FAILED", scenario, ct.get_last_error())
                resume_called = True
                if trusted_pending_connect_watchdog_enabled:
                    pending_connect_resume_offset_ms = pending_connect_offset_ms()
            if diagnostic_mode:
                job_process_id_inventory["after_worker_resume"] = self._query_job_process_ids(job, scenario)
            self.native.close(process.hThread); process.hThread = wt.HANDLE()

            started = time.monotonic()
            ready_seen = False

            def release_new_checkpoints() -> None:
                nonlocal processed_checkpoint_count, stdin_write
                if not checkpoint_names:
                    return
                records: list[dict[str, object]] = []
                for line in collector.snapshot()["text_prefix"].splitlines():
                    try:
                        value = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(value, dict) and value.get("record_type") == "RD19_CHECKPOINT":
                        records.append(value)
                if len(records) < processed_checkpoint_count:
                    raise ProbeStop("CHECKPOINT_RECORD_COUNT_REGRESSION", scenario)
                for record in records[processed_checkpoint_count:]:
                    if processed_checkpoint_count >= len(checkpoint_names):
                        raise ProbeStop("CHECKPOINT_UNEXPECTED", canonical(record))
                    expected = checkpoint_names[processed_checkpoint_count]
                    actual = record.get("checkpoint")
                    if actual != expected:
                        raise ProbeStop("CHECKPOINT_ORDER_MISMATCH", f"{scenario}:{expected}:{actual}")
                    inventory = self._query_job_process_ids(job, scenario)
                    checkpoint_telemetry.append({
                        "sequence": processed_checkpoint_count + 1,
                        "name": actual,
                        "monotonic_offset_ms": int((time.monotonic() - started) * 1000),
                        "worker_record": record,
                        "job_process_ids": inventory,
                    })
                    release = ct.create_string_buffer(b"\x01")
                    written = wt.DWORD()
                    if not k.WriteFile(stdin_write, release, 1, ct.byref(written), None) or written.value != 1:
                        raise ProbeStop("CHECKPOINT_RELEASE_WRITE_FAILED", f"{scenario}:{actual}", ct.get_last_error())
                    processed_checkpoint_count += 1
                    if processed_checkpoint_count == len(checkpoint_names):
                        self.native.close(stdin_write); stdin_write = wt.HANDLE()

            def fail_pending_connect(reason: str) -> None:
                nonlocal pending_connect_failure_reason
                if pending_connect_failure_reason is None:
                    pending_connect_failure_reason = reason
                    terminate_pending_connect(
                        f"trusted_pending_connect_fail_closed:{reason}",
                        0xEE52,
                    )

            def observe_pending_connect_records() -> None:
                nonlocal pending_connect_processed_records
                nonlocal pending_connect_expected_sequence
                nonlocal pending_connect_ready_count
                nonlocal pending_connect_sample_count
                nonlocal pending_connect_ready_offset_ms
                nonlocal pending_connect_last_sample_offset_ms
                nonlocal pending_connect_maximum_sample_gap_ms
                if not trusted_pending_connect_watchdog_enabled:
                    return
                records: list[dict[str, object]] = []
                for line in collector.snapshot()["text_prefix"].splitlines():
                    try:
                        value = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(value, dict):
                        records.append(value)
                if len(records) < pending_connect_processed_records:
                    fail_pending_connect("worker_record_count_regression")
                    return
                for record in records[pending_connect_processed_records:]:
                    observed_offset_ms = pending_connect_offset_ms()
                    projected_record = dict(record)
                    projected_record["parent_observed_monotonic_offset_ms"] = observed_offset_ms
                    pending_connect_parent_records.append(projected_record)
                    result_code = record.get("result_code")
                    sequence = record.get("sequence")
                    if not isinstance(sequence, int) or isinstance(sequence, bool):
                        fail_pending_connect("worker_sequence_missing_or_invalid")
                        break
                    pending_connect_expected_sequence += 1
                    if sequence != pending_connect_expected_sequence:
                        fail_pending_connect("worker_sequence_non_contiguous")
                        break
                    if result_code == "WORKER_NATIVE_WINSOCK_PENDING_READY":
                        pending_connect_ready_count += 1
                        if (
                            pending_connect_ready_count != 1
                            or pending_connect_sample_count != 0
                            or sequence != 1
                            or record.get("WSAStartup_result") != 0
                            or record.get("socket_created") is not True
                            or record.get("nonblocking_result") != 0
                            or record.get("immediate_return") != -1
                            or record.get("immediate_WSA_error") != WSAEWOULDBLOCK
                            or record.get("socket_open") is not True
                        ):
                            fail_pending_connect("pending_ready_contract_mismatch")
                            break
                        pending_connect_ready_offset_ms = observed_offset_ms
                        pending_connect_last_sample_offset_ms = observed_offset_ms
                    elif result_code == "WORKER_NATIVE_WINSOCK_PENDING_SAMPLE":
                        if (
                            pending_connect_ready_count != 1
                            or record.get("select_return") != 0
                            or record.get("select_WSA_error") != 0
                            or record.get("write_ready") is not False
                            or record.get("exception_ready") is not False
                            or record.get("socket_open") is not True
                        ):
                            fail_pending_connect("pending_sample_contract_mismatch")
                            break
                        pending_connect_sample_count += 1
                        if pending_connect_last_sample_offset_ms is not None:
                            sample_gap = observed_offset_ms - pending_connect_last_sample_offset_ms
                            pending_connect_maximum_sample_gap_ms = max(
                                pending_connect_maximum_sample_gap_ms,
                                sample_gap,
                            )
                            if sample_gap > 250:
                                fail_pending_connect("parent_observed_sample_gap_exceeded")
                                break
                        pending_connect_last_sample_offset_ms = observed_offset_ms
                    elif result_code == "WORKER_NATIVE_WINSOCK_TERMINAL_OBSERVATION":
                        fail_pending_connect("terminal_observation")
                        break
                    elif result_code == "WORKER_NATIVE_WINSOCK_SELF_CLOSE":
                        fail_pending_connect("worker_self_close")
                        break
                    elif result_code == "WORKER_ERROR":
                        fail_pending_connect("worker_error")
                        break
                    else:
                        fail_pending_connect("unexpected_worker_record")
                        break
                pending_connect_processed_records = len(records)

            while True:
                if trusted_cpu_watchdog_enabled:
                    watchdog_sample = capture_watchdog_sample("monitor")
                    if watchdog_sample.get("GetProcessTimes_BOOL") is not True:
                        watchdog_failure_reason = "GetProcessTimes_failure"
                        terminate_for_watchdog(
                            "trusted_cpu_watchdog_GetProcessTimes_failure",
                            0xEE42,
                        )
                        break
                    if watchdog_sample.get("process_active_state") is not True:
                        watchdog_failure_reason = "target_natural_exit_before_budget"
                        terminate_for_watchdog(
                            "trusted_cpu_watchdog_target_exit_before_budget",
                            0xEE43,
                        )
                        break
                    sample_user_time = watchdog_sample.get("user_time_100ns")
                    if not isinstance(sample_user_time, int) or isinstance(sample_user_time, bool):
                        watchdog_failure_reason = "invalid_user_time_sample"
                        terminate_for_watchdog(
                            "trusted_cpu_watchdog_invalid_user_time_sample",
                            0xEE44,
                        )
                        break
                    if sample_user_time >= trusted_cpu_budget_100ns:
                        watchdog_trigger_sample = watchdog_sample
                        terminate_for_watchdog("trusted_cpu_watchdog_limit", 0xEE45)
                        break
                    watchdog_previous_sample = watchdog_sample
                if live_companion_attribution_diagnostic:
                    while drain_live_completion(0, "target_lifetime"):
                        if live_blocker is not None:
                            break
                    if live_blocker is not None:
                        if trusted_pending_connect_watchdog_enabled:
                            pending_connect_failure_reason = "live_attribution_blocker"
                        break
                if trusted_pending_connect_watchdog_enabled:
                    pending_connect_parent_poll_count += 1
                    if pending_connect_failure_reason is not None:
                        break
                    observe_pending_connect_records()
                    if pending_connect_failure_reason is not None:
                        break
                    observed_accepts = observe_pending_connect_listener("observation_poll")
                    if observed_accepts != 0:
                        fail_pending_connect("listener_accept_during_observation")
                        break
                    liveness_wait_result = int(k.WaitForSingleObject(process.hProcess, 0))
                    target_active = liveness_wait_result == WAIT_TIMEOUT
                    pending_connect_liveness_observations.append({
                        "parent_monotonic_offset_ms": pending_connect_offset_ms(),
                        "process_wait_result": liveness_wait_result,
                        "target_active": target_active,
                    })
                    if not target_active:
                        fail_pending_connect("target_inactive_before_parent_termination")
                        break
                    watchdog_elapsed_ms = pending_connect_offset_ms()
                    if pending_connect_ready_count == 0 and watchdog_elapsed_ms > 1500:
                        fail_pending_connect("pending_checkpoint_deadline_exceeded")
                        break
                    if pending_connect_ready_count > 1:
                        fail_pending_connect("duplicate_pending_ready")
                        break
                    if pending_connect_ready_offset_ms is not None:
                        checkpoint_latency_ms = (
                            pending_connect_ready_offset_ms
                            - int(pending_connect_resume_offset_ms or 0)
                        )
                        if checkpoint_latency_ms > 1500:
                            fail_pending_connect("pending_checkpoint_deadline_exceeded")
                            break
                        observation_duration_ms = watchdog_elapsed_ms - pending_connect_ready_offset_ms
                        last_sample_age_ms = (
                            watchdog_elapsed_ms - pending_connect_last_sample_offset_ms
                            if pending_connect_last_sample_offset_ms is not None
                            else None
                        )
                        if observation_duration_ms > 3000:
                            fail_pending_connect("observation_window_exceeded")
                            break
                        if observation_duration_ms >= 2500:
                            if (
                                pending_connect_sample_count == 0
                                or pending_connect_maximum_sample_gap_ms > 250
                                or last_sample_age_ms is None
                                or last_sample_age_ms > 250
                            ):
                                fail_pending_connect("observation_sample_contract_mismatch")
                                break
                            if observe_pending_connect_listener("immediately_before_termination") != 0:
                                fail_pending_connect("listener_accept_before_termination")
                                break
                            termination = terminate_pending_connect(
                                "trusted_pending_connect_watchdog_deadline",
                                0xEE51,
                            )
                            if (
                                termination.get("TerminateJobObject_BOOL") is not True
                                or termination.get("immediate_GetLastError") != 0
                            ):
                                pending_connect_failure_reason = "TerminateJobObject_failure"
                            break
                    if watchdog_elapsed_ms >= 5000:
                        fail_pending_connect("outer_wall_deadline_reached")
                        break
                release_new_checkpoints()
                wait_result = int(k.WaitForSingleObject(
                    process.hProcess,
                    trusted_cpu_poll_interval_ms if trusted_cpu_watchdog_enabled else 20,
                ))
                elapsed_ms = int((time.monotonic() - started) * 1000)
                if collector.overflow.is_set():
                    if trusted_cpu_watchdog_enabled:
                        watchdog_failure_reason = "output_limit_before_CPU_budget"
                        terminate_for_watchdog(
                            "trusted_cpu_watchdog_output_limit_fail_closed",
                            0xEE46,
                        )
                    elif trusted_pending_connect_watchdog_enabled:
                        fail_pending_connect("output_limit_fail_closed")
                    else:
                        termination_reason = "output_limit"
                        k.TerminateJobObject(job, 0xE004)
                    break
                if terminate_on_ready:
                    snapshot = collector.snapshot()
                    if "WORKER_TREE_READY" in snapshot["text_prefix"]:
                        ready_seen = True
                        termination_reason = "owned_tree_cancel"
                        k.TerminateJobObject(job, 0xE005)
                        break
                if wait_result == WAIT_OBJECT_0:
                    if trusted_cpu_watchdog_enabled:
                        watchdog_failure_reason = "target_natural_exit_before_budget"
                        terminate_for_watchdog(
                            "trusted_cpu_watchdog_target_exit_before_budget",
                            0xEE43,
                        )
                    elif trusted_pending_connect_watchdog_enabled:
                        fail_pending_connect("target_natural_exit_before_parent_termination")
                    elif termination_reason is None:
                        termination_reason = "process_exit"
                    break
                if wait_result != WAIT_TIMEOUT:
                    if trusted_cpu_watchdog_enabled:
                        watchdog_failure_reason = f"process_wait_failed:{wait_result}"
                        terminate_for_watchdog(
                            "trusted_cpu_watchdog_process_wait_fail_closed",
                            0xEE47,
                        )
                        break
                    if trusted_pending_connect_watchdog_enabled:
                        fail_pending_connect(f"process_wait_failed:{wait_result}")
                        break
                    raise ProbeStop("PROCESS_WAIT_FAILED", scenario, wait_result)
                if elapsed_ms >= timeout_ms:
                    if trusted_cpu_watchdog_enabled:
                        watchdog_failure_reason = "wall_deadline_before_CPU_budget"
                        terminate_for_watchdog(
                            "trusted_cpu_watchdog_wall_deadline",
                            0xEE48,
                        )
                    elif trusted_pending_connect_watchdog_enabled:
                        fail_pending_connect("outer_wall_deadline_reached")
                    else:
                        termination_reason = "wall_timeout"
                        k.TerminateJobObject(job, 0xE006)
                    break
            release_new_checkpoints()
            if live_companion_attribution_diagnostic:
                while drain_live_completion(0, "after_target_wait"):
                    if live_blocker is not None:
                        break
            if processed_checkpoint_count != len(checkpoint_names):
                raise ProbeStop(
                    "CHECKPOINT_SEQUENCE_INCOMPLETE",
                    f"{scenario}:{processed_checkpoint_count}/{len(checkpoint_names)}",
                )
            termination_wait_result = int(k.WaitForSingleObject(process.hProcess, 10_000))
            inactive_after_termination = int(k.WaitForSingleObject(process.hProcess, 0)) == WAIT_OBJECT_0
            if trusted_cpu_watchdog_enabled:
                watchdog_final_sample = capture_watchdog_sample("final_after_termination")
                final_user_time = watchdog_final_sample.get("user_time_100ns")
                trigger_user_time = (
                    watchdog_trigger_sample.get("user_time_100ns")
                    if watchdog_trigger_sample is not None
                    else None
                )
                trusted_cpu_watchdog = {
                    "enabled": True,
                    "armed_before_ResumeThread": watchdog_armed_before_resume,
                    "retained_original_target_process_handle": True,
                    "reopened_target_by_PID": False,
                    "expected_target_process_id": int(process.dwProcessId),
                    "handle_process_id": watchdog_handle_process_id,
                    "CPU_budget_100ns": trusted_cpu_budget_100ns,
                    "poll_interval_ms": trusted_cpu_poll_interval_ms,
                    "maximum_accepted_final_target_user_time_100ns": (
                        trusted_cpu_maximum_final_user_time_100ns
                    ),
                    "wall_fail_safe_deadline_ms": timeout_ms,
                    "resume_thread_call_count": watchdog_resume_thread_call_count,
                    "sample_count": watchdog_sample_count,
                    "all_GetProcessTimes_calls_successful": watchdog_all_GetProcessTimes_success,
                    "initial_sample": watchdog_initial_sample,
                    "previous_sample": watchdog_previous_sample,
                    "trigger_sample": watchdog_trigger_sample,
                    "trigger_monotonic_timestamp_ms": (
                        watchdog_trigger_sample.get("monotonic_offset_ms")
                        if watchdog_trigger_sample is not None
                        else None
                    ),
                    "CPU_overshoot_100ns": (
                        int(final_user_time) - trusted_cpu_budget_100ns
                        if isinstance(final_user_time, int) and not isinstance(final_user_time, bool)
                        else None
                    ),
                    "trigger_CPU_overshoot_100ns": (
                        int(trigger_user_time) - trusted_cpu_budget_100ns
                        if isinstance(trigger_user_time, int) and not isinstance(trigger_user_time, bool)
                        else None
                    ),
                    "termination": watchdog_termination,
                    "termination_wait_result": termination_wait_result,
                    "final_sample": watchdog_final_sample,
                    "failure_reason": watchdog_failure_reason,
                }
            self.native.close(stdout_write); stdout_write = wt.HANDLE()
            self.native.close(stderr_write); stderr_write = wt.HANDLE()
            collector.finish()
            if trusted_pending_connect_watchdog_enabled:
                observe_pending_connect_records()
            exit_code = wt.DWORD()
            if not k.GetExitCodeProcess(process.hProcess, ct.byref(exit_code)):
                raise ProbeStop("EXIT_CODE_FAILED", scenario, ct.get_last_error())
            if diagnostic_mode:
                target_process_times = self._process_times(process.hProcess, scenario)

            if diagnostic_mode:
                job_quiescence = self._collect_quiescence(
                    job,
                    completion,
                    scenario,
                    started,
                    quiet_window_ms=completion_quiet_window_ms,
                    initial_messages=live_completion_events if live_companion_attribution_diagnostic else None,
                )
                accounting_projection = job_quiescence["final_accounting"]
                job_messages = [int(value["message"]) for value in job_quiescence["messages"]]
                job_process_id_inventory["after_scenario_completion"] = job_quiescence["final_process_ids"]
                if process_time_limit and JOB_OBJECT_MSG_END_OF_PROCESS_TIME in job_messages:
                    termination_reason = "job_process_time_limit"
            else:
                accounting, extended = self._query_accounting(job, scenario)
                while True:
                    message = wt.DWORD()
                    key = ULONG_PTR()
                    overlapped = ct.c_void_p()
                    ok = k.GetQueuedCompletionStatus(completion, ct.byref(message), ct.byref(key), ct.byref(overlapped), 0)
                    if not ok and ct.get_last_error() == WAIT_TIMEOUT:
                        break
                    if not ok:
                        raise ProbeStop("COMPLETION_PORT_READ_FAILED", scenario, ct.get_last_error())
                    job_messages.append(int(message.value))
                accounting_projection = self._accounting_projection(accounting, extended)
            if trusted_pending_connect_watchdog_enabled:
                post_termination_accepts = observe_pending_connect_listener(
                    "after_termination_and_quiescence"
                )
                if post_termination_accepts != 0 and pending_connect_failure_reason is None:
                    pending_connect_failure_reason = "listener_accept_after_termination"
                output_snapshot = collector.snapshot()
                if output_snapshot.get("overflow") is not False and pending_connect_failure_reason is None:
                    pending_connect_failure_reason = "output_overflow"
                if output_snapshot.get("reader_errors") != [] and pending_connect_failure_reason is None:
                    pending_connect_failure_reason = "output_reader_error"
                accepted_termination = bool(
                    pending_connect_termination is not None
                    and pending_connect_termination.get("reason")
                    == "trusted_pending_connect_watchdog_deadline"
                    and pending_connect_termination.get("exit_code") == 0xEE51
                    and pending_connect_termination.get("TerminateJobObject_BOOL") is True
                    and pending_connect_termination.get("immediate_GetLastError") == 0
                )
                if accepted_termination and int(exit_code.value) != 0xEE51:
                    pending_connect_failure_reason = "target_exit_code_mismatch"
                termination_offset_ms = (
                    pending_connect_termination.get("parent_monotonic_offset_ms")
                    if pending_connect_termination is not None
                    else None
                )
                observation_duration_ms = (
                    int(termination_offset_ms) - pending_connect_ready_offset_ms
                    if isinstance(termination_offset_ms, int)
                    and pending_connect_ready_offset_ms is not None
                    else None
                )
                last_sample_age_ms = (
                    int(termination_offset_ms) - pending_connect_last_sample_offset_ms
                    if isinstance(termination_offset_ms, int)
                    and pending_connect_last_sample_offset_ms is not None
                    else None
                )
                pending_connect_watchdog = {
                    "enabled": True,
                    "pending_checkpoint_deadline_ms": 1500,
                    "worker_sample_interval_ms": 100,
                    "maximum_parent_observed_sample_gap_limit_ms": 250,
                    "required_observation_window_ms": 2500,
                    "maximum_accepted_observation_duration_ms": 3000,
                    "parent_poll_interval_ms": 20,
                    "outer_wall_deadline_ms": 5000,
                    "completion_port_quiet_window_ms": 250,
                    "accepted_termination_exit_code": 0xEE51,
                    "resume_parent_monotonic_offset_ms": pending_connect_resume_offset_ms,
                    "pending_ready_parent_monotonic_offset_ms": pending_connect_ready_offset_ms,
                    "checkpoint_latency_ms": (
                        pending_connect_ready_offset_ms - int(pending_connect_resume_offset_ms or 0)
                        if pending_connect_ready_offset_ms is not None
                        else None
                    ),
                    "observation_end_parent_monotonic_offset_ms": termination_offset_ms,
                    "observation_duration_ms": observation_duration_ms,
                    "parent_poll_count": pending_connect_parent_poll_count,
                    "pending_ready_count": pending_connect_ready_count,
                    "sample_count": pending_connect_sample_count,
                    "maximum_parent_observed_sample_gap_ms": (
                        pending_connect_maximum_sample_gap_ms
                    ),
                    "last_sample_age_before_termination_ms": last_sample_age_ms,
                    "parent_observed_worker_records": pending_connect_parent_records,
                    "listener_accept_observations": pending_connect_listener_observations,
                    "listener_accept_count_total": pending_connect_listener_accept_total,
                    "target_liveness_observations": pending_connect_liveness_observations,
                    "termination": pending_connect_termination,
                    "termination_wait_result": termination_wait_result,
                    "target_exit_code": int(exit_code.value),
                    "failure_reason": pending_connect_failure_reason,
                }
            return {
                "scenario": scenario,
                "command_argv": command,
                "environment": environment_values,
                "creation_flags": flags_value,
                "created_suspended": True,
                "assigned_before_resume": assigned_before_resume,
                "resume_called": resume_called,
                "direct_termination_before_resume": direct_termination_before_resume,
                "inactive_after_termination": inactive_after_termination,
                "identity": identity,
                "process_id": int(process.dwProcessId),
                "exit_code": int(exit_code.value),
                "termination_reason": termination_reason,
                "ready_seen": ready_seen,
                "output": collector.snapshot(),
                "job_messages": job_messages,
                "job_accounting": accounting_projection,
                **({
                    "effective_job_limits": effective_job_limits,
                    "target_process_times": target_process_times,
                    "job_process_id_inventory": job_process_id_inventory,
                    "job_quiescence": job_quiescence,
                    "checkpoint_telemetry": checkpoint_telemetry,
                    "checkpoint_sequence_complete": processed_checkpoint_count == len(checkpoint_names),
                    **({
                        "use_appcontainer": use_appcontainer,
                        "job_membership": job_membership,
                        "limit_operations": limit_operations,
                    } if process_time_control_diagnostic or live_companion_attribution_diagnostic else {}),
                    **({
                        "live_attribution": {
                            "attempt_start_FILETIME_100ns": attempt_start_FILETIME_100ns,
                            "target_notification_seen": live_target_notification_seen,
                            "non_target_notification_count": live_non_target_count,
                            "completion_events": live_completion_events,
                            "captured_processes": live_processes,
                            "blocker": live_blocker,
                        },
                    } if live_companion_attribution_diagnostic else {}),
                    **({
                        "trusted_cpu_watchdog": trusted_cpu_watchdog,
                    } if trusted_cpu_watchdog_enabled else {}),
                    **({
                        "trusted_pending_connect_watchdog": pending_connect_watchdog,
                    } if trusted_pending_connect_watchdog_enabled else {}),
                } if diagnostic_mode else {}),
            }
        finally:
            if process.hProcess:
                if self.native.kernel32.WaitForSingleObject(process.hProcess, 0) == WAIT_TIMEOUT:
                    if assigned_before_resume and job:
                        self.native.kernel32.TerminateJobObject(job, 0xEEFF)
                    else:
                        if not self.native.kernel32.TerminateProcess(process.hProcess, 0xEEFE):
                            raise ProbeStop("PRE_JOB_CLEANUP_TERMINATE_FAILED", scenario, ct.get_last_error())
                    if int(self.native.kernel32.WaitForSingleObject(process.hProcess, 10_000)) != WAIT_OBJECT_0:
                        raise ProbeStop("PROCESS_CLEANUP_WAIT_FAILED", scenario, ct.get_last_error())
                self.native.close(process.hProcess)
                if assigned_suspended_target_flag_preservation_diagnostic:
                    run_cleanup["process_handle_closed"] = True
            if process.hThread:
                self.native.close(process.hThread)
                if assigned_suspended_target_flag_preservation_diagnostic:
                    run_cleanup["thread_handle_closed"] = True
            if collector is not None:
                collector.finish()
            for handle in (stdout_read, stdout_write, stderr_read, stderr_write, stdin_read, stdin_write):
                handle_was_open = bool(handle)
                self.native.close(handle)
                if assigned_suspended_target_flag_preservation_diagnostic and handle_was_open:
                    run_cleanup["pipe_handles_closed"] = int(run_cleanup["pipe_handles_closed"]) + 1
            if attr_initialized and attr_buffer is not None:
                self.native.kernel32.DeleteProcThreadAttributeList(ct.cast(attr_buffer, ct.c_void_p))
                if assigned_suspended_target_flag_preservation_diagnostic:
                    run_cleanup["attribute_list_deleted"] = True
            if job:
                self.native.close(job)
                if assigned_suspended_target_flag_preservation_diagnostic:
                    run_cleanup["Job_handle_closed"] = True
            if completion:
                self.native.close(completion)
                if assigned_suspended_target_flag_preservation_diagnostic:
                    run_cleanup["completion_port_handle_closed"] = True


def parsed_worker_output(run: dict[str, object]) -> dict[str, object] | None:
    text = run["output"]["text_prefix"].strip()
    if not text:
        return None
    for line in text.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("record_type") != "RD19_CHECKPOINT":
            return value
    return None


def case(case_id: str, name: str, expected: str, passed: bool, **evidence: object) -> dict[str, object]:
    return {
        "id": case_id,
        "name": name,
        "expected_result_code": expected,
        "result_code": expected if passed else "FAILED_" + expected,
        "passed": passed,
        "evidence": evidence,
    }


def exclusive_listener(family: int, host: str, port: int) -> socket.socket:
    value = socket.socket(family, socket.SOCK_STREAM)
    try:
        value.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        if family == socket.AF_INET6:
            value.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        value.bind((host, port))
        value.listen(4)
        value.setblocking(False)
        return value
    except BaseException:
        value.close()
        raise


def listener_accept_count(listener: socket.socket) -> int:
    count = 0
    while True:
        try:
            connection, _ = listener.accept()
        except BlockingIOError:
            break
        else:
            count += 1
            connection.close()
    return count


def profile_registry_and_folder(sid_string: str) -> tuple[bool, Path]:
    base = "Software\\Classes\\Local Settings\\Software\\Microsoft\\Windows\\CurrentVersion\\AppContainer\\Mappings"
    exists = True
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base + "\\" + sid_string, 0, winreg.KEY_READ):
            pass
    except FileNotFoundError:
        exists = False
    folder = Path(os.environ["LOCALAPPDATA"]) / "Packages" / sid_string
    return exists, folder


def remove_tree_no_reparse(root: Path) -> None:
    if not root.exists():
        return
    attributes = getattr(root.lstat(), "st_file_attributes", 0)
    if attributes & FILE_ATTRIBUTE_REPARSE_POINT:
        raise ProbeStop("ROOT_REPARSE_DURING_CLEANUP", str(root))
    for entry in os.scandir(root):
        path = Path(entry.path)
        info = entry.stat(follow_symlinks=False)
        reparse = bool(getattr(info, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT)
        if reparse or entry.is_symlink():
            path.unlink()
        elif entry.is_dir(follow_symlinks=False):
            remove_tree_no_reparse(path)
        else:
            path.unlink()
    root.rmdir()


def process_active(native: Native, pid: int) -> bool:
    handle = native.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        error = ct.get_last_error()
        if error in (ERROR_INVALID_PARAMETER, ERROR_ACCESS_DENIED):
            return False
        raise ProbeStop("PROCESS_RESIDUE_QUERY_FAILED", str(pid), error)
    try:
        code = wt.DWORD()
        if not native.kernel32.GetExitCodeProcess(handle, ct.byref(code)):
            raise ProbeStop("PROCESS_RESIDUE_EXIT_CODE_FAILED", str(pid), ct.get_last_error())
        return int(code.value) == STILL_ACTIVE
    finally:
        native.close(handle)


def create_profile(native: Native, name: str) -> tuple[ct.c_void_p, str]:
    sid = ct.c_void_p()
    result = int(native.userenv.CreateAppContainerProfile(name, name, "Pipeline V2 bounded temporary capability qualification", None, 0, ct.byref(sid)))
    unsigned = hresult_unsigned(result)
    if unsigned == 0x800700B7:
        raise ProbeStop("PROFILE_ALREADY_EXISTS", name, unsigned)
    if hresult_failed(result):
        raise ProbeStop("PROFILE_CREATE_FAILED", name, unsigned)
    value = native.sid_string(sid)
    derived = ct.c_void_p()
    derive_result = int(native.userenv.DeriveAppContainerSidFromAppContainerName(name, ct.byref(derived)))
    if hresult_failed(derive_result):
        native.advapi32.FreeSid(sid)
        raise ProbeStop("PROFILE_SID_DERIVE_FAILED", name, hresult_unsigned(derive_result))
    try:
        if not native.advapi32.EqualSid(sid, derived):
            raise ProbeStop("PROFILE_SID_IDENTITY_MISMATCH", name)
    finally:
        native.advapi32.FreeSid(derived)
    return sid, value


def delete_profile(native: Native, name: str) -> None:
    result = int(native.userenv.DeleteAppContainerProfile(name))
    if hresult_failed(result):
        raise ProbeStop("PROFILE_DELETE_FAILED", name, hresult_unsigned(result))


def result_projection(cases: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "id": value["id"],
            "expected_result_code": value["expected_result_code"],
            "result_code": value["result_code"],
            "passed": value["passed"],
        }
        for value in cases
    ]


def failed_case_diagnostic_projection(cases: list[dict[str, object]]) -> list[dict[str, object]]:
    projected: list[dict[str, object]] = []
    for value in cases:
        if value["passed"]:
            continue
        evidence = value["evidence"]
        run = evidence.get("run")
        projected_run = None
        if isinstance(run, dict):
            output = run.get("output")
            projected_output = None
            if isinstance(output, dict):
                disclose_text = bool(
                    isinstance(output.get("total_bytes"), int)
                    and output["total_bytes"] <= 4096
                    and output.get("overflow") is False
                    and output.get("reader_errors") == []
                )
                projected_output = {
                    "total_bytes": output.get("total_bytes"),
                    "retained_prefix_bytes": output.get("retained_prefix_bytes"),
                    "full_stream_sha256": output.get("full_stream_sha256"),
                    "prefix_sha256": output.get("prefix_sha256"),
                    "overflow": output.get("overflow"),
                    "reader_errors": output.get("reader_errors"),
                    "replacement_character_count": output.get("replacement_character_count"),
                    "text_prefix_decoding": output.get("text_prefix_decoding"),
                    "text_prefix": output.get("text_prefix") if disclose_text else None,
                }
            projected_run = {
                "scenario": run.get("scenario"),
                "created_suspended": run.get("created_suspended"),
                "assigned_before_resume": run.get("assigned_before_resume"),
                "resume_called": run.get("resume_called"),
                "direct_termination_before_resume": run.get("direct_termination_before_resume"),
                "identity": run.get("identity"),
                "exit_code": run.get("exit_code"),
                "termination_reason": run.get("termination_reason"),
                "ready_seen": run.get("ready_seen"),
                "job_messages": run.get("job_messages"),
                "job_accounting": run.get("job_accounting"),
                "output": projected_output,
            }
        item = {
            "id": value["id"],
            "name": value["name"],
            "expected_result_code": value["expected_result_code"],
            "result_code": value["result_code"],
            "worker": evidence.get("worker"),
            "run": projected_run,
        }
        if value["id"] == "CP-WIN-05":
            item["predicate_components"] = evidence.get("predicate_components")
            item["forced_pre_Job_abort_result_code"] = evidence.get(
                "forced_pre_Job_abort_result_code"
            )
            item["forced_pre_Job_abort"] = evidence.get("forced_pre_Job_abort")
            item["identity_quiescence"] = evidence.get("identity_quiescence")
        if "listener_accept_count" in evidence:
            item["listener_accept_count"] = evidence["listener_accept_count"]
        projected.append(item)
    return projected


def parsed_worker_records(run: dict[str, object], limit: int = 16) -> list[dict[str, object]]:
    output = run.get("output")
    if not isinstance(output, dict):
        return []
    text = output.get("text_prefix")
    if not isinstance(text, str):
        return []
    records: list[dict[str, object]] = []
    for line in text.splitlines():
        if len(records) >= limit:
            break
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(value)
    return records


def bounded_output_projection(output: object) -> dict[str, object] | None:
    if not isinstance(output, dict):
        return None
    return {
        "total_bytes": output.get("total_bytes"),
        "retained_prefix_bytes": output.get("retained_prefix_bytes"),
        "full_stream_sha256": output.get("full_stream_sha256"),
        "prefix_sha256": output.get("prefix_sha256"),
        "overflow": output.get("overflow"),
        "reader_errors": output.get("reader_errors"),
        "replacement_character_count": output.get("replacement_character_count"),
        "text_prefix_decoding": output.get("text_prefix_decoding"),
    }


def remediation_run_projection(run: dict[str, object]) -> dict[str, object]:
    return {
        "scenario": run.get("scenario"),
        "created_suspended": run.get("created_suspended"),
        "assigned_before_resume": run.get("assigned_before_resume"),
        "resume_called": run.get("resume_called"),
        "direct_termination_before_resume": run.get("direct_termination_before_resume"),
        "inactive_after_termination": run.get("inactive_after_termination"),
        "identity": run.get("identity"),
        "process_id": run.get("process_id"),
        "exit_code": run.get("exit_code"),
        "termination_reason": run.get("termination_reason"),
        "ready_seen": run.get("ready_seen"),
        "effective_job_limits": run.get("effective_job_limits"),
        "target_process_times": run.get("target_process_times"),
        "job_messages": run.get("job_messages"),
        "job_accounting": run.get("job_accounting"),
        "job_quiescence": run.get("job_quiescence"),
        "job_process_id_inventory": run.get("job_process_id_inventory"),
        "checkpoint_telemetry": run.get("checkpoint_telemetry"),
        "checkpoint_sequence_complete": run.get("checkpoint_sequence_complete"),
        "worker_records": parsed_worker_records(run),
        "output": bounded_output_projection(run.get("output")),
    }


def process_time_control_run_projection(run: dict[str, object]) -> dict[str, object]:
    return {
        "scenario": run.get("scenario"),
        "use_appcontainer": run.get("use_appcontainer"),
        "created_suspended": run.get("created_suspended"),
        "assigned_before_resume": run.get("assigned_before_resume"),
        "resume_called": run.get("resume_called"),
        "inactive_after_termination": run.get("inactive_after_termination"),
        "identity": run.get("identity"),
        "process_id": run.get("process_id"),
        "exit_code": run.get("exit_code"),
        "termination_reason": run.get("termination_reason"),
        "job_membership": run.get("job_membership"),
        "limit_operations": run.get("limit_operations"),
        "effective_job_limits": run.get("effective_job_limits"),
        "target_process_times": run.get("target_process_times"),
        "job_messages": run.get("job_messages"),
        "job_accounting": run.get("job_accounting"),
        "job_quiescence": run.get("job_quiescence"),
        "job_process_id_inventory": run.get("job_process_id_inventory"),
        "worker_records": parsed_worker_records(run),
        "output": bounded_output_projection(run.get("output")),
    }


def non_nested_process_time_run_projection(run: dict[str, object]) -> dict[str, object]:
    projection = process_time_control_run_projection(run)
    projection["live_attribution"] = run.get("live_attribution")
    return projection


def trusted_cpu_watchdog_run_projection(run: dict[str, object]) -> dict[str, object]:
    return {
        "scenario": run.get("scenario"),
        "use_appcontainer": run.get("use_appcontainer"),
        "created_suspended": run.get("created_suspended"),
        "assigned_before_resume": run.get("assigned_before_resume"),
        "resume_called": run.get("resume_called"),
        "inactive_after_termination": run.get("inactive_after_termination"),
        "process_id": run.get("process_id"),
        "exit_code": run.get("exit_code"),
        "termination_reason": run.get("termination_reason"),
        "job_membership": run.get("job_membership"),
        "effective_job_limits": run.get("effective_job_limits"),
        "target_process_times": run.get("target_process_times"),
        "trusted_cpu_watchdog": run.get("trusted_cpu_watchdog"),
        "live_attribution": run.get("live_attribution"),
        "job_messages": run.get("job_messages"),
        "job_accounting": run.get("job_accounting"),
        "job_quiescence": run.get("job_quiescence"),
        "job_process_id_inventory": run.get("job_process_id_inventory"),
        "worker_records": parsed_worker_records(run),
        "output": bounded_output_projection(run.get("output")),
    }


def trusted_pending_connect_watchdog_run_projection(run: dict[str, object]) -> dict[str, object]:
    return {
        "scenario": run.get("scenario"),
        "use_appcontainer": run.get("use_appcontainer"),
        "created_suspended": run.get("created_suspended"),
        "assigned_before_resume": run.get("assigned_before_resume"),
        "resume_called": run.get("resume_called"),
        "inactive_after_termination": run.get("inactive_after_termination"),
        "identity": run.get("identity"),
        "process_id": run.get("process_id"),
        "exit_code": run.get("exit_code"),
        "termination_reason": run.get("termination_reason"),
        "job_membership": run.get("job_membership"),
        "effective_job_limits": run.get("effective_job_limits"),
        "trusted_pending_connect_watchdog": run.get("trusted_pending_connect_watchdog"),
        "live_attribution": run.get("live_attribution"),
        "job_messages": run.get("job_messages"),
        "job_accounting": run.get("job_accounting"),
        "job_quiescence": run.get("job_quiescence"),
        "job_process_id_inventory": run.get("job_process_id_inventory"),
        "worker_records": parsed_worker_records(run, limit=64),
        "output": bounded_output_projection(run.get("output")),
    }


def live_companion_attribution_run_projection(run: dict[str, object]) -> dict[str, object]:
    return {
        "scenario": run.get("scenario"),
        "created_suspended": run.get("created_suspended"),
        "assigned_before_resume": run.get("assigned_before_resume"),
        "resume_called": run.get("resume_called"),
        "inactive_after_termination": run.get("inactive_after_termination"),
        "process_id": run.get("process_id"),
        "exit_code": run.get("exit_code"),
        "termination_reason": run.get("termination_reason"),
        "job_membership": run.get("job_membership"),
        "live_attribution": run.get("live_attribution"),
        "job_accounting": run.get("job_accounting"),
        "job_quiescence": run.get("job_quiescence"),
        "job_process_id_inventory": run.get("job_process_id_inventory"),
        "worker_records": parsed_worker_records(run),
        "output": bounded_output_projection(run.get("output")),
    }


def capture_live_companion_attribution_diagnostic(
    runner: JobRun,
    child_pids: set[int],
    canary: Path,
    canary_before: str,
) -> dict[str, object]:
    run = runner.run(
        "identity",
        timeout_ms=5000,
        active_process_limit=None,
        live_companion_attribution_diagnostic=True,
        completion_quiet_window_ms=250,
    )
    target_pid = run.get("process_id")
    if isinstance(target_pid, int) and target_pid > 0:
        child_pids.add(target_pid)
    worker_records = parsed_worker_records(run)
    child_pids.update(worker_record_pids(worker_records))
    live = run.get("live_attribution") or {}
    captures = live.get("captured_processes") or []
    for captured in captures:
        if isinstance(captured, dict):
            pid = captured.get("notification_PID")
            if isinstance(pid, int) and pid > 0:
                child_pids.add(pid)

    target_captures = [
        value for value in captures
        if isinstance(value, dict) and value.get("relationship") == "target"
    ]
    companion_captures = [
        value for value in captures
        if isinstance(value, dict) and value.get("relationship") == "companion_candidate"
    ]
    uncontracted_captures = [
        value for value in captures
        if isinstance(value, dict) and value.get("relationship") == "uncontracted_process"
    ]
    membership = run.get("job_membership") or {}
    stream = run.get("output") or {}
    quiescence = run.get("job_quiescence") or {}
    blocker = live.get("blocker")

    worker_ok = bool(
        len(worker_records) == 1
        and worker_records[0].get("result_code") == "WORKER_IDENTITY"
        and worker_records[0].get("token_is_appcontainer") is True
        and worker_records[0].get("capability_count") == 0
    )
    target_ok = bool(
        len(target_captures) == 1
        and target_captures[0].get("notification_PID") == target_pid
        and target_captures[0].get("relationship") == "target"
        and target_captures[0].get("explicit_assignment_by_diagnostic") is True
        and target_captures[0].get("live_owned_Job_membership") is True
        and target_captures[0].get("TokenIsAppContainer") is True
        and target_captures[0].get("capability_count") == 0
        and membership.get("target_in_owned_Job_before_assignment") is False
        and membership.get("target_in_owned_Job_after_assignment") is True
    )
    companion_ok = bool(
        len(companion_captures) == 1
        and companion_captures[0].get("explicit_assignment_by_diagnostic") is False
        and companion_captures[0].get("live_owned_Job_membership") is True
        and companion_captures[0].get("inherited_owned_Job_membership_evidence") is True
    )
    output_ok = bool(stream.get("overflow") is False and stream.get("reader_errors") == [])
    quiescence_ok = bool(
        quiescence.get("deadline_expired") is False
        and quiescence.get("active_process_zero_message_seen") is True
        and quiescence.get("quiet_window_ms") == 250
        and quiescence.get("quiet_window_completed") is True
        and quiescence.get("final_PID_inventory_empty") is True
        and (quiescence.get("final_accounting") or {}).get("active_process_zero") is True
        and quiescence.get("quiescent") is True
        and run.get("inactive_after_termination") is True
    )

    derived_blocker: dict[str, object] | None = blocker if isinstance(blocker, dict) else None
    if derived_blocker is None and uncontracted_captures:
        derived_blocker = {
            "code": "LIVE_UNCONTRACTED_PROCESS",
            "detail": str(uncontracted_captures[0].get("notification_PID")),
            "raw_code": None,
        }
    if derived_blocker is None and not target_ok:
        derived_blocker = {"code": "LIVE_TARGET_CAPTURE_INCOMPLETE", "detail": "target predicate", "raw_code": None}
    if derived_blocker is None and run.get("resume_called") is True and not worker_ok:
        derived_blocker = {"code": "LIVE_WORKER_IDENTITY_MISMATCH", "detail": "worker record", "raw_code": None}
    if derived_blocker is None and not output_ok:
        derived_blocker = {"code": "LIVE_OUTPUT_CAPTURE_MISMATCH", "detail": "bounded output", "raw_code": None}
    if derived_blocker is None and not quiescence_ok:
        derived_blocker = {"code": "LIVE_JOB_QUIESCENCE_MISMATCH", "detail": "owned Job", "raw_code": None}

    if uncontracted_captures or (
        isinstance(derived_blocker, dict)
        and derived_blocker.get("code") == "LIVE_UNCONTRACTED_PROCESS"
    ):
        result_code = "UNCONTRACTED_PROCESS_CAPTURED_AND_OWNED_JOB_TERMINATED"
    elif derived_blocker is not None:
        result_code = "LIVE_ATTRIBUTION_INCOMPLETE_EXACT_BLOCKER"
    elif companion_ok:
        result_code = "COMPANION_PROCESS_ATTRIBUTED_LIVE"
    else:
        result_code = "LIVE_DIAGNOSTIC_COMPLETED_WITH_NO_COMPANION_OBSERVED"

    return {
        "schema": "pipeline-v2.k0b03-v2-windows-live-companion-attribution-diagnostic-v1",
        "attempt": "A",
        "status": "live_companion_attribution_diagnostic_captured",
        "result_code": result_code,
        "qualification_result": None,
        "enforcement_conclusion": None,
        "nested_Job_causality_conclusion": None,
        "CPU_enforcement_conclusion": None,
        "target_capture_count": len(target_captures),
        "companion_capture_count": len(companion_captures),
        "uncontracted_capture_count": len(uncontracted_captures),
        "blocker": derived_blocker,
        "run": live_companion_attribution_run_projection(run),
        "canary_unchanged_before_cleanup": canary.is_file() and file_pin(canary)["sha256"] == canary_before,
        "job_quiescence_verified_before_cleanup": quiescence_ok,
    }


def capture_process_time_control_diagnostic(
    runner: JobRun,
    child_pids: set[int],
    canary: Path,
    canary_before: str,
) -> dict[str, object]:
    parent_process = runner.native.kernel32.GetCurrentProcess()
    parent_in_any_job = runner.process_in_job(
        parent_process,
        None,
        "process_time_control",
        "parent_any_before_cases",
    )
    definitions = [
        ("PT-WIN-01", False, False, "non_AppContainer_limit_before_assignment"),
        ("PT-WIN-02", False, True, "non_AppContainer_limit_after_assignment_before_resume"),
        ("PT-WIN-03", True, False, "zero_capability_AppContainer_limit_before_assignment"),
        ("PT-WIN-04", True, True, "zero_capability_AppContainer_limit_after_assignment_before_resume"),
    ]
    rows: list[dict[str, object]] = []
    pass_by_id: dict[str, bool] = {}
    nested_target_membership = False
    for case_id, use_appcontainer, defer_limit, purpose in definitions:
        run = runner.run(
            "cpu",
            timeout_ms=5000,
            process_time_limit=True,
            final_remediation_diagnostic=False,
            process_time_control_diagnostic=True,
            use_appcontainer=use_appcontainer,
            active_process_limit=None,
            defer_process_time_limit_until_assigned=defer_limit,
            completion_quiet_window_ms=250,
        )
        process_id = run.get("process_id")
        if isinstance(process_id, int):
            child_pids.add(process_id)
        child_pids.update(worker_record_pids(parsed_worker_records(run)))
        limits = run.get("effective_job_limits") or {}
        process_times = run.get("target_process_times") or {}
        quiescence = run.get("job_quiescence") or {}
        membership = run.get("job_membership") or {}
        stream = run.get("output") or {}
        user_time = process_times.get("user_time_100ns")
        nested_target_membership = bool(
            nested_target_membership
            or membership.get("target_in_any_Job_before_owned_assignment") is True
        )
        passed = bool(
            run.get("created_suspended") is True
            and run.get("assigned_before_resume") is True
            and run.get("resume_called") is True
            and membership.get("target_in_owned_Job_before_assignment") is False
            and membership.get("target_in_owned_Job_after_assignment") is True
            and limits.get("PerProcessUserTimeLimit") == 10_000_000
            and int(limits.get("LimitFlags", 0)) & JOB_OBJECT_LIMIT_PROCESS_TIME
            and not (int(limits.get("LimitFlags", 0)) & JOB_OBJECT_LIMIT_ACTIVE_PROCESS)
            and limits.get("QueryInformationJobObject_result") == 1
            and limits.get("QueryInformationJobObject_last_error") == 0
            and limits.get("QueryInformationJobObject_returned_length") == 144
            and run.get("termination_reason") == "job_process_time_limit"
            and JOB_OBJECT_MSG_END_OF_PROCESS_TIME in (run.get("job_messages") or [])
            and isinstance(user_time, int)
            and not isinstance(user_time, bool)
            and 10_000_000 <= user_time <= 15_000_000
            and run.get("inactive_after_termination") is True
            and stream.get("overflow") is False
            and stream.get("reader_errors") == []
            and quiescence.get("deadline_expired") is False
            and quiescence.get("active_process_zero_message_seen") is True
            and quiescence.get("quiet_window_ms") == 250
            and quiescence.get("quiet_window_completed") is True
            and quiescence.get("final_PID_inventory_empty") is True
            and (quiescence.get("final_accounting") or {}).get("active_process_zero") is True
            and quiescence.get("quiescent") is True
        )
        pass_by_id[case_id] = passed
        rows.append({
            "id": case_id,
            "purpose": purpose,
            "passed": passed,
            "run": process_time_control_run_projection(run),
        })

    if parent_in_any_job or nested_target_membership:
        result_code = "NESTED_JOB_CONTEXT_PRESENT_REQUIRES_SEPARATE_DISPOSITION"
    elif all(pass_by_id.values()):
        result_code = "PROCESS_TIME_CONTROL_ALL_CASES_ENFORCED"
    elif (
        pass_by_id["PT-WIN-01"]
        and pass_by_id["PT-WIN-03"]
        and not pass_by_id["PT-WIN-02"]
        and not pass_by_id["PT-WIN-04"]
    ):
        result_code = "POST_ASSIGNMENT_PROCESS_TIME_LIMIT_NOT_ENFORCED"
    elif (
        pass_by_id["PT-WIN-01"]
        and pass_by_id["PT-WIN-02"]
        and (not pass_by_id["PT-WIN-03"] or not pass_by_id["PT-WIN-04"])
    ):
        result_code = "APPCONTAINER_SPECIFIC_PROCESS_TIME_LIMIT_NOT_ENFORCED"
    elif not pass_by_id["PT-WIN-01"] and not pass_by_id["PT-WIN-03"]:
        result_code = "HOST_WIDE_JOB_PROCESS_TIME_LIMIT_NOT_ENFORCED"
    else:
        result_code = "PROCESS_TIME_CONTROL_MIXED_RESULT_BLOCKER"
    return {
        "schema": "pipeline-v2.k0b03-v2-windows-process-time-control-diagnostic-v1",
        "attempt": "A",
        "status": "process_time_control_diagnostic_captured",
        "result_code": result_code,
        "qualification_result": None,
        "parent_in_any_Job_before_cases": parent_in_any_job,
        "matrix_expected_count": 4,
        "matrix_actual_count": len(rows),
        "passed_count": sum(1 for row in rows if row["passed"] is True),
        "failed_count": sum(1 for row in rows if row["passed"] is False),
        "errors_count": 0,
        "skips_count": 0,
        "rows": rows,
        "canary_unchanged_before_cleanup": canary.is_file() and file_pin(canary)["sha256"] == canary_before,
    }


def capture_non_nested_process_time_causal_diagnostic(
    runner: JobRun,
    child_pids: set[int],
    canary: Path,
    canary_before: str,
    launcher_gate: dict[str, object],
) -> dict[str, object]:
    if launcher_gate.get("current_process_in_any_Job") is not False:
        raise ProbeStop("NON_NESTED_LAUNCH_CONTEXT_REQUIRED", canonical(launcher_gate))
    definitions = [
        ("PT-WIN-01", False, False, "non_AppContainer_limit_before_assignment"),
        ("PT-WIN-02", False, True, "non_AppContainer_limit_after_assignment_before_resume"),
        ("PT-WIN-03", True, False, "zero_capability_AppContainer_limit_before_assignment"),
        ("PT-WIN-04", True, True, "zero_capability_AppContainer_limit_after_assignment_before_resume"),
    ]
    rows: list[dict[str, object]] = []
    pass_by_id: dict[str, bool] = {}
    all_quiescent = True
    for case_id, use_appcontainer, defer_limit, purpose in definitions:
        run = runner.run(
            "cpu",
            timeout_ms=5000,
            process_time_limit=True,
            process_time_control_diagnostic=True,
            live_companion_attribution_diagnostic=True,
            require_non_nested_target=True,
            use_appcontainer=use_appcontainer,
            active_process_limit=None,
            defer_process_time_limit_until_assigned=defer_limit,
            completion_quiet_window_ms=250,
        )
        process_id = run.get("process_id")
        if isinstance(process_id, int) and process_id > 0:
            child_pids.add(process_id)
        child_pids.update(worker_record_pids(parsed_worker_records(run)))
        live = run.get("live_attribution") or {}
        captures = live.get("captured_processes") or []
        for captured in captures:
            if isinstance(captured, dict):
                captured_pid = captured.get("notification_PID")
                if isinstance(captured_pid, int) and captured_pid > 0:
                    child_pids.add(captured_pid)
        uncontracted = [
            value for value in captures
            if isinstance(value, dict) and value.get("relationship") == "uncontracted_process"
        ]
        target_captures = [
            value for value in captures
            if isinstance(value, dict)
            and value.get("relationship") == "target"
            and value.get("notification_PID") == process_id
        ]
        limits = run.get("effective_job_limits") or {}
        process_times = run.get("target_process_times") or {}
        quiescence = run.get("job_quiescence") or {}
        membership = run.get("job_membership") or {}
        stream = run.get("output") or {}
        user_time = process_times.get("user_time_100ns")
        completion_events = quiescence.get("messages") or []
        target_end_of_process_time = any(
            isinstance(event, dict)
            and event.get("message") == JOB_OBJECT_MSG_END_OF_PROCESS_TIME
            and event.get("process_id_value") == process_id
            for event in completion_events
        )
        quiescent = bool(
            quiescence.get("deadline_expired") is False
            and quiescence.get("active_process_zero_message_seen") is True
            and quiescence.get("quiet_window_ms") == 250
            and quiescence.get("quiet_window_completed") is True
            and quiescence.get("final_PID_inventory_empty") is True
            and (quiescence.get("final_accounting") or {}).get("active_process_zero") is True
            and quiescence.get("quiescent") is True
        )
        all_quiescent = all_quiescent and quiescent
        passed = bool(
            run.get("created_suspended") is True
            and run.get("assigned_before_resume") is True
            and run.get("resume_called") is True
            and membership.get("target_in_any_Job_before_owned_assignment") is False
            and membership.get("target_in_owned_Job_before_assignment") is False
            and membership.get("target_in_owned_Job_after_assignment") is True
            and limits.get("PerProcessUserTimeLimit") == 10_000_000
            and int(limits.get("LimitFlags", 0)) & JOB_OBJECT_LIMIT_PROCESS_TIME
            and not (int(limits.get("LimitFlags", 0)) & JOB_OBJECT_LIMIT_ACTIVE_PROCESS)
            and limits.get("QueryInformationJobObject_result") == 1
            and limits.get("QueryInformationJobObject_last_error") == 0
            and limits.get("QueryInformationJobObject_returned_length") == 144
            and run.get("termination_reason") == "job_process_time_limit"
            and target_end_of_process_time
            and isinstance(user_time, int)
            and not isinstance(user_time, bool)
            and 10_000_000 <= user_time <= 15_000_000
            and len(target_captures) == 1
            and live.get("blocker") is None
            and not uncontracted
            and run.get("inactive_after_termination") is True
            and stream.get("overflow") is False
            and stream.get("reader_errors") == []
            and quiescent
        )
        pass_by_id[case_id] = passed
        rows.append({
            "id": case_id,
            "purpose": purpose,
            "passed": passed,
            "target_END_OF_PROCESS_TIME_message_seen": target_end_of_process_time,
            "uncontracted_process_count": len(uncontracted),
            "run": non_nested_process_time_run_projection(run),
        })

    if all(pass_by_id.values()):
        result_code = "PROCESS_TIME_CONTROL_ALL_CASES_ENFORCED_NON_NESTED"
    elif (
        pass_by_id["PT-WIN-01"]
        and pass_by_id["PT-WIN-03"]
        and not pass_by_id["PT-WIN-02"]
        and not pass_by_id["PT-WIN-04"]
    ):
        result_code = "POST_ASSIGNMENT_PROCESS_TIME_LIMIT_NOT_ENFORCED_NON_NESTED"
    elif (
        pass_by_id["PT-WIN-01"]
        and pass_by_id["PT-WIN-02"]
        and (not pass_by_id["PT-WIN-03"] or not pass_by_id["PT-WIN-04"])
    ):
        result_code = "APPCONTAINER_SPECIFIC_PROCESS_TIME_LIMIT_NOT_ENFORCED_NON_NESTED"
    elif (
        not pass_by_id["PT-WIN-01"]
        and pass_by_id["PT-WIN-02"]
        and not pass_by_id["PT-WIN-03"]
        and not pass_by_id["PT-WIN-04"]
    ):
        result_code = "ORDERING_AND_APPCONTAINER_PROCESS_TIME_LIMIT_MISMATCH_NON_NESTED"
    elif not any(pass_by_id.values()):
        result_code = "HOST_WIDE_JOB_PROCESS_TIME_LIMIT_NOT_ENFORCED_NON_NESTED"
    else:
        result_code = "PROCESS_TIME_CONTROL_NON_NESTED_MIXED_RESULT_BLOCKER"
    return {
        "schema": "pipeline-v2.k0b03-v2-windows-non-nested-process-time-causal-diagnostic-v1",
        "attempt": "A",
        "status": "non_nested_process_time_causal_diagnostic_captured",
        "result_code": result_code,
        "qualification_result": None,
        "launcher_gate": launcher_gate,
        "matrix_expected_count": 4,
        "matrix_actual_count": len(rows),
        "passed_count": sum(1 for row in rows if row["passed"] is True),
        "failed_count": sum(1 for row in rows if row["passed"] is False),
        "errors_count": 0,
        "skips_count": 0,
        "rows": rows,
        "canary_unchanged_before_cleanup": canary.is_file() and file_pin(canary)["sha256"] == canary_before,
        "job_quiescence_verified_before_cleanup": all_quiescent,
    }


def capture_appcontainer_process_time_information_class_control_diagnostic(
    runner: JobRun,
    child_pids: set[int],
    canary: Path,
    canary_before: str,
    launcher_gate: dict[str, object],
) -> dict[str, object]:
    if launcher_gate.get("current_process_in_any_Job") is not False:
        raise ProbeStop("NON_NESTED_LAUNCH_CONTEXT_REQUIRED", canonical(launcher_gate))
    definitions = [
        (
            "IC-WIN-01",
            False,
            JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            "non_AppContainer_post_assignment_JobObjectExtendedLimitInformation",
        ),
        (
            "IC-WIN-02",
            True,
            JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            "zero_capability_AppContainer_post_assignment_JobObjectExtendedLimitInformation",
        ),
        (
            "IC-WIN-03",
            False,
            JOB_OBJECT_BASIC_LIMIT_INFORMATION,
            "non_AppContainer_post_assignment_JobObjectBasicLimitInformation",
        ),
        (
            "IC-WIN-04",
            True,
            JOB_OBJECT_BASIC_LIMIT_INFORMATION,
            "zero_capability_AppContainer_post_assignment_JobObjectBasicLimitInformation",
        ),
    ]
    rows: list[dict[str, object]] = []
    pass_by_id: dict[str, bool] = {}
    all_quiescent = True
    for case_id, use_appcontainer, information_class, purpose in definitions:
        expected_structure_name = (
            "JOBOBJECT_BASIC_LIMIT_INFORMATION"
            if information_class == JOB_OBJECT_BASIC_LIMIT_INFORMATION
            else "JOBOBJECT_EXTENDED_LIMIT_INFORMATION"
        )
        expected_information_class_name = (
            "JobObjectBasicLimitInformation"
            if information_class == JOB_OBJECT_BASIC_LIMIT_INFORMATION
            else "JobObjectExtendedLimitInformation"
        )
        expected_information_length = (
            ct.sizeof(JOBOBJECT_BASIC_LIMIT_INFORMATION)
            if information_class == JOB_OBJECT_BASIC_LIMIT_INFORMATION
            else ct.sizeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION)
        )
        run = runner.run(
            "cpu",
            timeout_ms=5000,
            process_time_limit=True,
            process_time_control_diagnostic=True,
            live_companion_attribution_diagnostic=True,
            require_non_nested_target=True,
            use_appcontainer=use_appcontainer,
            active_process_limit=None,
            defer_process_time_limit_until_assigned=True,
            deferred_process_time_information_class=information_class,
            diagnostic_case_id=case_id,
            completion_quiet_window_ms=250,
        )
        process_id = run.get("process_id")
        if isinstance(process_id, int) and process_id > 0:
            child_pids.add(process_id)
        child_pids.update(worker_record_pids(parsed_worker_records(run)))
        live = run.get("live_attribution") or {}
        captures = live.get("captured_processes") or []
        for captured in captures:
            if isinstance(captured, dict):
                captured_pid = captured.get("notification_PID")
                if isinstance(captured_pid, int) and captured_pid > 0:
                    child_pids.add(captured_pid)
        target_captures = [
            value for value in captures
            if isinstance(value, dict)
            and value.get("relationship") == "target"
            and value.get("notification_PID") == process_id
        ]
        uncontracted = [
            value for value in captures
            if isinstance(value, dict) and value.get("relationship") == "uncontracted_process"
        ]
        limits = run.get("effective_job_limits") or {}
        process_times = run.get("target_process_times") or {}
        quiescence = run.get("job_quiescence") or {}
        membership = run.get("job_membership") or {}
        stream = run.get("output") or {}
        operations = run.get("limit_operations") or []
        user_time = process_times.get("user_time_100ns")
        completion_events = quiescence.get("messages") or []
        target_end_of_process_time = any(
            isinstance(event, dict)
            and event.get("message") == JOB_OBJECT_MSG_END_OF_PROCESS_TIME
            and event.get("process_id_value") == process_id
            for event in completion_events
        )
        quiescent = bool(
            quiescence.get("deadline_expired") is False
            and quiescence.get("active_process_zero_message_seen") is True
            and quiescence.get("quiet_window_ms") == 250
            and quiescence.get("quiet_window_completed") is True
            and quiescence.get("final_PID_inventory_empty") is True
            and (quiescence.get("final_accounting") or {}).get("active_process_zero") is True
            and quiescence.get("quiescent") is True
        )
        all_quiescent = all_quiescent and quiescent
        initial_operation = operations[0] if len(operations) == 2 else {}
        deferred_operation = operations[1] if len(operations) == 2 else {}
        target_capture = target_captures[0] if len(target_captures) == 1 else {}
        expected_flags = (
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            | JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION
            | JOB_OBJECT_LIMIT_PROCESS_TIME
        )
        expected_set_flags = (
            JOB_OBJECT_LIMIT_PROCESS_TIME
            if information_class == JOB_OBJECT_BASIC_LIMIT_INFORMATION
            else expected_flags
        )
        passed = bool(
            run.get("created_suspended") is True
            and run.get("assigned_before_resume") is True
            and run.get("resume_called") is True
            and run.get("use_appcontainer") is use_appcontainer
            and membership.get("target_in_any_Job_before_owned_assignment") is False
            and membership.get("target_in_owned_Job_before_assignment") is False
            and membership.get("target_in_owned_Job_after_assignment") is True
            and len(operations) == 2
            and initial_operation.get("phase") == "before_assignment_initial"
            and initial_operation.get("information_class") == JOB_OBJECT_EXTENDED_LIMIT_INFORMATION
            and initial_operation.get("information_length") == ct.sizeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION)
            and initial_operation.get("LimitFlags") == (
                JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION
            )
            and initial_operation.get("PerProcessUserTimeLimit") == 0
            and initial_operation.get("SetInformationJobObject_result") is True
            and initial_operation.get("SetInformationJobObject_last_error") == 0
            and deferred_operation.get("phase") == "after_assignment_before_resume"
            and deferred_operation.get("information_class") == information_class
            and deferred_operation.get("information_class_name") == expected_information_class_name
            and deferred_operation.get("structure_name") == expected_structure_name
            and deferred_operation.get("information_length") == expected_information_length
            and deferred_operation.get("LimitFlags") == expected_set_flags
            and deferred_operation.get("PerProcessUserTimeLimit") == 10_000_000
            and deferred_operation.get("SetInformationJobObject_result") is True
            and deferred_operation.get("SetInformationJobObject_last_error") == 0
            and limits.get("LimitFlags") == expected_flags
            and limits.get("PerProcessUserTimeLimit") == 10_000_000
            and limits.get("ActiveProcessLimit") == 0
            and limits.get("QueryInformationJobObject_result") == 1
            and limits.get("QueryInformationJobObject_last_error") == 0
            and limits.get("QueryInformationJobObject_returned_length") == 144
            and run.get("termination_reason") == "job_process_time_limit"
            and target_end_of_process_time
            and isinstance(user_time, int)
            and not isinstance(user_time, bool)
            and 10_000_000 <= user_time <= 15_000_000
            and len(target_captures) == 1
            and target_capture.get("TokenIsAppContainer") is use_appcontainer
            and target_capture.get("capability_count") == 0
            and live.get("blocker") is None
            and not uncontracted
            and run.get("inactive_after_termination") is True
            and stream.get("overflow") is False
            and stream.get("reader_errors") == []
            and quiescent
        )
        pass_by_id[case_id] = passed
        rows.append({
            "id": case_id,
            "purpose": purpose,
            "identity": "zero_capability_AppContainer" if use_appcontainer else "non_AppContainer",
            "information_class": information_class,
            "information_class_name": expected_information_class_name,
            "structure_name": expected_structure_name,
            "structure_bytes": expected_information_length,
            "passed": passed,
            "target_END_OF_PROCESS_TIME_message_seen": target_end_of_process_time,
            "uncontracted_process_count": len(uncontracted),
            "run": non_nested_process_time_run_projection(run),
        })

    if all(pass_by_id.values()):
        result_code = "EXTENDED_AND_BASIC_APPCONTAINER_PROCESS_TIME_ENFORCED"
    elif (
        pass_by_id["IC-WIN-01"]
        and not pass_by_id["IC-WIN-02"]
        and pass_by_id["IC-WIN-03"]
        and pass_by_id["IC-WIN-04"]
    ):
        result_code = "BASIC_INFORMATION_CLASS_REMEDIATES_APPCONTAINER_PROCESS_TIME"
    elif (
        pass_by_id["IC-WIN-01"]
        and not pass_by_id["IC-WIN-02"]
        and pass_by_id["IC-WIN-03"]
        and not pass_by_id["IC-WIN-04"]
    ):
        result_code = "APPCONTAINER_PROCESS_TIME_NOT_ENFORCED_ACROSS_INFORMATION_CLASSES"
    elif not pass_by_id["IC-WIN-01"] or not pass_by_id["IC-WIN-03"]:
        result_code = "NON_APPCONTAINER_CONTROL_REGRESSION"
    else:
        result_code = "APPCONTAINER_PROCESS_TIME_INFORMATION_CLASS_CONTROL_MIXED_RESULT_BLOCKER"
    return {
        "schema": "pipeline-v2.k0b03-v2-windows-AppContainer-process-time-information-class-control-diagnostic-v1",
        "attempt": "A",
        "status": "appcontainer_process_time_information_class_control_diagnostic_captured",
        "result_code": result_code,
        "qualification_result": None,
        "CPU_prerequisite_disposition": "pending_fresh_context_read_only_review",
        "launcher_gate": launcher_gate,
        "matrix_expected_count": 4,
        "matrix_actual_count": len(rows),
        "passed_count": sum(1 for row in rows if row["passed"] is True),
        "failed_count": sum(1 for row in rows if row["passed"] is False),
        "errors_count": 0,
        "skips_count": 0,
        "rows": rows,
        "canary_unchanged_before_cleanup": canary.is_file() and file_pin(canary)["sha256"] == canary_before,
        "job_quiescence_verified_before_cleanup": all_quiescent,
    }


def capture_process_time_enforcement_repeatability_diagnostic(
    runner: JobRun,
    child_pids: set[int],
    canary: Path,
    canary_before: str,
    launcher_gate: dict[str, object],
) -> dict[str, object]:
    if launcher_gate.get("current_process_in_any_Job") is not False:
        raise ProbeStop("NON_NESTED_LAUNCH_CONTEXT_REQUIRED", canonical(launcher_gate))
    definitions = [
        (
            "RT-WIN-01",
            False,
            JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            "extended_non_AppContainer_repetition_1",
        ),
        (
            "RT-WIN-02",
            True,
            JOB_OBJECT_BASIC_LIMIT_INFORMATION,
            "Basic_PROCESS_TIME_only_AppContainer_repetition_1",
        ),
        (
            "RT-WIN-03",
            True,
            JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            "extended_AppContainer_repetition_1",
        ),
        (
            "RT-WIN-04",
            False,
            JOB_OBJECT_BASIC_LIMIT_INFORMATION,
            "Basic_PROCESS_TIME_only_non_AppContainer_repetition_1",
        ),
        (
            "RT-WIN-05",
            False,
            JOB_OBJECT_BASIC_LIMIT_INFORMATION,
            "Basic_PROCESS_TIME_only_non_AppContainer_repetition_2",
        ),
        (
            "RT-WIN-06",
            True,
            JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            "extended_AppContainer_repetition_2",
        ),
        (
            "RT-WIN-07",
            True,
            JOB_OBJECT_BASIC_LIMIT_INFORMATION,
            "Basic_PROCESS_TIME_only_AppContainer_repetition_2",
        ),
        (
            "RT-WIN-08",
            False,
            JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            "extended_non_AppContainer_repetition_2",
        ),
    ]
    rows: list[dict[str, object]] = []
    all_quiescent = True
    for ordinal, (case_id, use_appcontainer, information_class, purpose) in enumerate(definitions, 1):
        expected_structure_name = (
            "JOBOBJECT_BASIC_LIMIT_INFORMATION"
            if information_class == JOB_OBJECT_BASIC_LIMIT_INFORMATION
            else "JOBOBJECT_EXTENDED_LIMIT_INFORMATION"
        )
        expected_information_class_name = (
            "JobObjectBasicLimitInformation"
            if information_class == JOB_OBJECT_BASIC_LIMIT_INFORMATION
            else "JobObjectExtendedLimitInformation"
        )
        expected_information_length = (
            ct.sizeof(JOBOBJECT_BASIC_LIMIT_INFORMATION)
            if information_class == JOB_OBJECT_BASIC_LIMIT_INFORMATION
            else ct.sizeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION)
        )
        run = runner.run(
            "cpu",
            timeout_ms=5000,
            process_time_limit=True,
            process_time_control_diagnostic=True,
            live_companion_attribution_diagnostic=True,
            require_non_nested_target=True,
            use_appcontainer=use_appcontainer,
            active_process_limit=None,
            defer_process_time_limit_until_assigned=True,
            deferred_process_time_information_class=information_class,
            diagnostic_case_id=case_id,
            completion_quiet_window_ms=250,
        )
        process_id = run.get("process_id")
        if isinstance(process_id, int) and process_id > 0:
            child_pids.add(process_id)
        child_pids.update(worker_record_pids(parsed_worker_records(run)))
        live = run.get("live_attribution") or {}
        captures = live.get("captured_processes") or []
        for captured in captures:
            if isinstance(captured, dict):
                captured_pid = captured.get("notification_PID")
                if isinstance(captured_pid, int) and captured_pid > 0:
                    child_pids.add(captured_pid)
        target_captures = [
            value for value in captures
            if isinstance(value, dict)
            and value.get("relationship") == "target"
            and value.get("notification_PID") == process_id
        ]
        companion_captures = [
            value for value in captures
            if isinstance(value, dict) and value.get("relationship") == "companion_candidate"
        ]
        uncontracted = [
            value for value in captures
            if isinstance(value, dict) and value.get("relationship") == "uncontracted_process"
        ]
        limits = run.get("effective_job_limits") or {}
        process_times = run.get("target_process_times") or {}
        quiescence = run.get("job_quiescence") or {}
        membership = run.get("job_membership") or {}
        stream = run.get("output") or {}
        operations = run.get("limit_operations") or []
        user_time = process_times.get("user_time_100ns")
        completion_events = quiescence.get("messages") or []
        target_end_events = [
            event for event in completion_events
            if isinstance(event, dict)
            and event.get("message") == JOB_OBJECT_MSG_END_OF_PROCESS_TIME
            and event.get("process_id_value") == process_id
        ]
        target_end_of_process_time = bool(target_end_events)
        new_process_pids = sorted(
            int(event.get("process_id_value"))
            for event in completion_events
            if isinstance(event, dict)
            and event.get("message") == JOB_OBJECT_MSG_NEW_PROCESS
            and isinstance(event.get("process_id_value"), int)
            and int(event.get("process_id_value")) > 0
        )
        captured_pids = sorted(
            int(value.get("notification_PID"))
            for value in captures
            if isinstance(value, dict)
            and isinstance(value.get("notification_PID"), int)
            and int(value.get("notification_PID")) > 0
        )
        quiescent = bool(
            quiescence.get("deadline_expired") is False
            and quiescence.get("active_process_zero_message_seen") is True
            and quiescence.get("quiet_window_ms") == 250
            and quiescence.get("quiet_window_completed") is True
            and quiescence.get("final_PID_inventory_empty") is True
            and (quiescence.get("final_accounting") or {}).get("active_process_zero") is True
            and quiescence.get("quiescent") is True
        )
        all_quiescent = all_quiescent and quiescent
        initial_operation = operations[0] if len(operations) == 2 else {}
        deferred_operation = operations[1] if len(operations) == 2 else {}
        target_capture = target_captures[0] if len(target_captures) == 1 else {}
        companion_capture = companion_captures[0] if len(companion_captures) == 1 else {}
        expected_flags = (
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            | JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION
            | JOB_OBJECT_LIMIT_PROCESS_TIME
        )
        expected_set_flags = (
            JOB_OBJECT_LIMIT_PROCESS_TIME
            if information_class == JOB_OBJECT_BASIC_LIMIT_INFORMATION
            else expected_flags
        )
        common_contract = bool(
            run.get("created_suspended") is True
            and run.get("assigned_before_resume") is True
            and run.get("resume_called") is True
            and run.get("use_appcontainer") is use_appcontainer
            and membership.get("target_in_any_Job_before_owned_assignment") is False
            and membership.get("target_in_owned_Job_before_assignment") is False
            and membership.get("target_in_owned_Job_after_assignment") is True
            and len(operations) == 2
            and initial_operation.get("phase") == "before_assignment_initial"
            and initial_operation.get("information_class") == JOB_OBJECT_EXTENDED_LIMIT_INFORMATION
            and initial_operation.get("information_length") == ct.sizeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION)
            and initial_operation.get("LimitFlags") == (
                JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION
            )
            and initial_operation.get("PerProcessUserTimeLimit") == 0
            and initial_operation.get("SetInformationJobObject_result") is True
            and initial_operation.get("SetInformationJobObject_last_error") == 0
            and deferred_operation.get("phase") == "after_assignment_before_resume"
            and deferred_operation.get("information_class") == information_class
            and deferred_operation.get("information_class_name") == expected_information_class_name
            and deferred_operation.get("structure_name") == expected_structure_name
            and deferred_operation.get("information_length") == expected_information_length
            and deferred_operation.get("LimitFlags") == expected_set_flags
            and deferred_operation.get("PerProcessUserTimeLimit") == 10_000_000
            and deferred_operation.get("SetInformationJobObject_result") is True
            and deferred_operation.get("SetInformationJobObject_last_error") == 0
            and limits.get("LimitFlags") == expected_flags
            and limits.get("PerProcessUserTimeLimit") == 10_000_000
            and limits.get("ActiveProcessLimit") == 0
            and limits.get("QueryInformationJobObject_result") == 1
            and limits.get("QueryInformationJobObject_last_error") == 0
            and limits.get("QueryInformationJobObject_returned_length") == 144
            and isinstance(process_times.get("creation_time_100ns"), int)
            and isinstance(process_times.get("exit_time_100ns"), int)
            and isinstance(user_time, int)
            and not isinstance(user_time, bool)
            and len(target_captures) == 1
            and target_capture.get("TokenIsAppContainer") is use_appcontainer
            and target_capture.get("capability_count") == 0
            and len(companion_captures) == 1
            and str(companion_capture.get("normalized_executable_image_path", "")).casefold()
            == "c:/windows/system32/conhost.exe"
            and companion_capture.get("TokenIsAppContainer") is use_appcontainer
            and companion_capture.get("capability_count") == 0
            and live.get("blocker") is None
            and not uncontracted
            and new_process_pids == captured_pids
            and process_id in new_process_pids
            and run.get("inactive_after_termination") is True
            and stream.get("overflow") is False
            and stream.get("reader_errors") == []
            and quiescent
        )
        positive_enforcement = bool(
            common_contract
            and run.get("termination_reason") == "job_process_time_limit"
            and target_end_of_process_time
        )
        within_acceptance_window = bool(
            positive_enforcement
            and isinstance(user_time, int)
            and not isinstance(user_time, bool)
            and 10_000_000 <= user_time <= 15_000_000
        )
        late_positive_enforcement = bool(
            positive_enforcement
            and isinstance(user_time, int)
            and not isinstance(user_time, bool)
            and user_time > 15_000_000
        )
        enforcement_not_proven = bool(
            common_contract
            and run.get("termination_reason") == "wall_timeout"
            and not target_end_of_process_time
        )
        if within_acceptance_window:
            repeatability_signature = "enforced_within_acceptance_window"
        elif late_positive_enforcement:
            repeatability_signature = "enforced_outside_acceptance_window"
        elif enforcement_not_proven:
            repeatability_signature = "enforcement_not_proven"
        else:
            repeatability_signature = "contract_mismatch"
        rows.append({
            "id": case_id,
            "ordinal": ordinal,
            "purpose": purpose,
            "identity": "zero_capability_AppContainer" if use_appcontainer else "non_AppContainer",
            "information_class": information_class,
            "information_class_name": expected_information_class_name,
            "structure_name": expected_structure_name,
            "structure_bytes": expected_information_length,
            "strict_acceptance_passed": within_acceptance_window,
            "common_contract_satisfied": common_contract,
            "positive_target_specific_enforcement_evidence": positive_enforcement,
            "late_positive_enforcement_evidence": late_positive_enforcement,
            "enforcement_not_proven": enforcement_not_proven,
            "repeatability_signature": repeatability_signature,
            "target_END_OF_PROCESS_TIME_message_seen": target_end_of_process_time,
            "target_END_OF_PROCESS_TIME_observation_monotonic_offsets_ms": [
                event.get("monotonic_offset_ms") for event in target_end_events
            ],
            "target_creation_FILETIME_100ns": process_times.get("creation_time_100ns"),
            "target_exit_FILETIME_100ns": process_times.get("exit_time_100ns"),
            "target_live_capture_FILETIME_100ns": target_capture.get("capture_FILETIME_100ns"),
            "target_user_time_100ns": user_time,
            "target_kernel_time_100ns": process_times.get("kernel_time_100ns"),
            "live_NEW_PROCESS_PIDs": new_process_pids,
            "live_attributed_PIDs": captured_pids,
            "target_capture_count": len(target_captures),
            "companion_capture_count": len(companion_captures),
            "uncontracted_process_count": len(uncontracted),
            "run": non_nested_process_time_run_projection(run),
        })

    rows_by_id = {str(row["id"]): row for row in rows}
    repetition_pairs = [
        ("RT-WIN-01", "RT-WIN-08"),
        ("RT-WIN-02", "RT-WIN-07"),
        ("RT-WIN-03", "RT-WIN-06"),
        ("RT-WIN-04", "RT-WIN-05"),
    ]
    pair_agreement = {
        f"{first}/{second}": rows_by_id[first]["repeatability_signature"]
        == rows_by_id[second]["repeatability_signature"]
        for first, second in repetition_pairs
    }
    signatures = [str(row["repeatability_signature"]) for row in rows]
    positive_evidence = [bool(row["positive_target_specific_enforcement_evidence"]) for row in rows]
    if any(signature == "contract_mismatch" for signature in signatures):
        result_code = "PROCESS_TIME_REPEATABILITY_CONTRACT_MISMATCH"
    elif not all(pair_agreement.values()):
        result_code = "PROCESS_TIME_ENFORCEMENT_NONDETERMINISTIC_ON_CURRENT_HOST"
    elif all(signature == "enforced_within_acceptance_window" for signature in signatures):
        result_code = "PROCESS_TIME_ENFORCEMENT_REPEATABLE_WITHIN_ACCEPTANCE_WINDOW"
    elif all(positive_evidence):
        result_code = "PROCESS_TIME_ENFORCEMENT_REPEATABLE_BUT_ACCEPTANCE_WINDOW_REQUIRES_MEASUREMENT_BASED_REVIEW"
    elif all(signature == "enforcement_not_proven" for signature in signatures):
        result_code = "PROCESS_TIME_ENFORCEMENT_NOT_PROVEN"
    else:
        result_code = "PROCESS_TIME_ENFORCEMENT_CLASS_OR_IDENTITY_PATTERN_REPRODUCED"
    return {
        "schema": "pipeline-v2.k0b03-v2-windows-process-time-enforcement-repeatability-diagnostic-v1",
        "attempt": "A",
        "status": "process_time_enforcement_repeatability_diagnostic_captured",
        "result_code": result_code,
        "qualification_result": None,
        "CPU_prerequisite_disposition": "pending_fresh_context_read_only_review",
        "launcher_gate": launcher_gate,
        "matrix_expected_count": 8,
        "matrix_actual_count": len(rows),
        "passed_count": sum(1 for row in rows if row["strict_acceptance_passed"] is True),
        "failed_count": sum(1 for row in rows if row["strict_acceptance_passed"] is False),
        "errors_count": 0,
        "skips_count": 0,
        "repetition_pair_agreement": pair_agreement,
        "rows": rows,
        "canary_unchanged_before_cleanup": canary.is_file() and file_pin(canary)["sha256"] == canary_before,
        "job_quiescence_verified_before_cleanup": all_quiescent,
    }


def capture_trusted_cpu_watchdog_diagnostic(
    runner: JobRun,
    child_pids: set[int],
    canary: Path,
    canary_before: str,
    launcher_gate: dict[str, object],
) -> dict[str, object]:
    if launcher_gate.get("current_process_in_any_Job") is not False:
        raise ProbeStop("NON_NESTED_LAUNCH_CONTEXT_REQUIRED", canonical(launcher_gate))
    definitions = [
        ("WD-WIN-01", False, 1),
        ("WD-WIN-02", True, 1),
        ("WD-WIN-03", True, 2),
        ("WD-WIN-04", False, 2),
        ("WD-WIN-05", False, 3),
        ("WD-WIN-06", True, 3),
        ("WD-WIN-07", True, 4),
        ("WD-WIN-08", False, 4),
    ]
    rows: list[dict[str, object]] = []
    all_quiescent = True
    first_failure_classification: str | None = None
    for ordinal, (case_id, use_appcontainer, repetition) in enumerate(definitions, 1):
        run = runner.run(
            "cpu",
            timeout_ms=5000,
            process_time_limit=False,
            process_memory_limit=False,
            job_memory_limit=False,
            process_time_control_diagnostic=False,
            live_companion_attribution_diagnostic=True,
            trusted_cpu_watchdog_enabled=True,
            trusted_cpu_budget_100ns=10_000_000,
            trusted_cpu_poll_interval_ms=20,
            trusted_cpu_maximum_final_user_time_100ns=15_000_000,
            require_non_nested_target=True,
            use_appcontainer=use_appcontainer,
            active_process_limit=None,
            defer_process_time_limit_until_assigned=False,
            diagnostic_case_id=case_id,
            completion_quiet_window_ms=250,
        )
        process_id = run.get("process_id")
        if isinstance(process_id, int) and process_id > 0:
            child_pids.add(process_id)
        child_pids.update(worker_record_pids(parsed_worker_records(run)))
        live = run.get("live_attribution") or {}
        captures = live.get("captured_processes") or []
        for captured in captures:
            if isinstance(captured, dict):
                captured_pid = captured.get("notification_PID")
                if isinstance(captured_pid, int) and captured_pid > 0:
                    child_pids.add(captured_pid)
        target_captures = [
            value for value in captures
            if isinstance(value, dict)
            and value.get("relationship") == "target"
            and value.get("notification_PID") == process_id
        ]
        companion_captures = [
            value for value in captures
            if isinstance(value, dict) and value.get("relationship") == "companion_candidate"
        ]
        uncontracted = [
            value for value in captures
            if isinstance(value, dict) and value.get("relationship") == "uncontracted_process"
        ]
        target_capture = target_captures[0] if len(target_captures) == 1 else {}
        companion_capture = companion_captures[0] if len(companion_captures) == 1 else {}
        limits = run.get("effective_job_limits") or {}
        process_times = run.get("target_process_times") or {}
        watchdog = run.get("trusted_cpu_watchdog") or {}
        membership = run.get("job_membership") or {}
        quiescence = run.get("job_quiescence") or {}
        stream = run.get("output") or {}
        completion_events = quiescence.get("messages") or []
        new_process_pids = sorted(
            int(event.get("process_id_value"))
            for event in completion_events
            if isinstance(event, dict)
            and event.get("message") == JOB_OBJECT_MSG_NEW_PROCESS
            and isinstance(event.get("process_id_value"), int)
            and int(event.get("process_id_value")) > 0
        )
        captured_pids = sorted(
            int(value.get("notification_PID"))
            for value in captures
            if isinstance(value, dict)
            and isinstance(value.get("notification_PID"), int)
            and int(value.get("notification_PID")) > 0
        )
        target_end_events = [
            event for event in completion_events
            if isinstance(event, dict)
            and event.get("message") == JOB_OBJECT_MSG_END_OF_PROCESS_TIME
            and event.get("process_id_value") == process_id
        ]
        initial_sample = watchdog.get("initial_sample") or {}
        previous_sample = watchdog.get("previous_sample") or {}
        trigger_sample = watchdog.get("trigger_sample") or {}
        final_sample = watchdog.get("final_sample") or {}
        termination = watchdog.get("termination") or {}
        final_user_time = final_sample.get("user_time_100ns")
        trigger_user_time = trigger_sample.get("user_time_100ns")
        previous_user_time = previous_sample.get("user_time_100ns")
        quiescent = bool(
            quiescence.get("deadline_expired") is False
            and quiescence.get("active_process_zero_message_seen") is True
            and quiescence.get("quiet_window_ms") == 250
            and quiescence.get("quiet_window_completed") is True
            and quiescence.get("final_PID_inventory_empty") is True
            and (quiescence.get("final_accounting") or {}).get("active_process_zero") is True
            and quiescence.get("quiescent") is True
        )
        all_quiescent = all_quiescent and quiescent
        watchdog_contract = bool(
            run.get("created_suspended") is True
            and run.get("assigned_before_resume") is True
            and run.get("resume_called") is True
            and run.get("use_appcontainer") is use_appcontainer
            and membership.get("target_in_any_Job_before_owned_assignment") is False
            and membership.get("target_in_owned_Job_before_assignment") is False
            and membership.get("target_in_owned_Job_after_assignment") is True
            and limits.get("LimitFlags") == (
                JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION
            )
            and not (int(limits.get("LimitFlags", 0)) & JOB_OBJECT_LIMIT_PROCESS_TIME)
            and limits.get("PerProcessUserTimeLimit") == 0
            and limits.get("ActiveProcessLimit") == 0
            and limits.get("QueryInformationJobObject_result") == 1
            and limits.get("QueryInformationJobObject_last_error") == 0
            and limits.get("QueryInformationJobObject_returned_length") == 144
            and watchdog.get("enabled") is True
            and watchdog.get("armed_before_ResumeThread") is True
            and watchdog.get("retained_original_target_process_handle") is True
            and watchdog.get("reopened_target_by_PID") is False
            and watchdog.get("expected_target_process_id") == process_id
            and watchdog.get("handle_process_id") == process_id
            and watchdog.get("CPU_budget_100ns") == 10_000_000
            and watchdog.get("poll_interval_ms") == 20
            and watchdog.get("maximum_accepted_final_target_user_time_100ns") == 15_000_000
            and watchdog.get("wall_fail_safe_deadline_ms") == 5000
            and watchdog.get("resume_thread_call_count") == 1
            and watchdog.get("all_GetProcessTimes_calls_successful") is True
            and watchdog.get("failure_reason") is None
            and initial_sample.get("phase") == "armed_before_resume"
            and initial_sample.get("GetProcessTimes_BOOL") is True
            and initial_sample.get("process_active_state") is True
            and isinstance(previous_user_time, int)
            and not isinstance(previous_user_time, bool)
            and previous_user_time < 10_000_000
            and isinstance(trigger_user_time, int)
            and not isinstance(trigger_user_time, bool)
            and trigger_user_time >= 10_000_000
            and isinstance(final_user_time, int)
            and not isinstance(final_user_time, bool)
            and final_user_time >= trigger_user_time
            and watchdog.get("CPU_overshoot_100ns") == final_user_time - 10_000_000
            and watchdog.get("trigger_CPU_overshoot_100ns") == trigger_user_time - 10_000_000
            and termination.get("reason") == "trusted_cpu_watchdog_limit"
            and termination.get("exit_code") == 0xEE45
            and termination.get("TerminateJobObject_BOOL") is True
            and termination.get("immediate_GetLastError") == 0
            and watchdog.get("termination_wait_result") == WAIT_OBJECT_0
            and run.get("termination_reason") == "trusted_cpu_watchdog_limit"
            and run.get("inactive_after_termination") is True
            and process_times.get("user_time_100ns") == final_user_time
            and len(target_end_events) == 0
            and len(target_captures) == 1
            and target_capture.get("TokenIsAppContainer") is use_appcontainer
            and target_capture.get("capability_count") == 0
            and target_capture.get("explicit_assignment_by_diagnostic") is True
            and len(companion_captures) == 1
            and str(companion_capture.get("normalized_executable_image_path", "")).casefold()
            == "c:/windows/system32/conhost.exe"
            and companion_capture.get("parent_PID") == process_id
            and companion_capture.get("TokenIsAppContainer") is use_appcontainer
            and companion_capture.get("capability_count") == 0
            and companion_capture.get("explicit_assignment_by_diagnostic") is False
            and companion_capture.get("inherited_owned_Job_membership_evidence") is True
            and companion_capture.get("live_owned_Job_membership") is True
            and live.get("blocker") is None
            and not uncontracted
            and new_process_pids == captured_pids
            and process_id in new_process_pids
            and stream.get("overflow") is False
            and stream.get("reader_errors") == []
            and quiescent
        )
        within_bound = bool(
            watchdog_contract
            and isinstance(final_user_time, int)
            and not isinstance(final_user_time, bool)
            and 10_000_000 <= final_user_time <= 15_000_000
        )
        if within_bound:
            disposition = "watchdog_enforced_within_bound"
        elif (
            isinstance(final_user_time, int)
            and not isinstance(final_user_time, bool)
            and final_user_time > 15_000_000
        ):
            disposition = "watchdog_bound_exceeded"
            first_failure_classification = "TRUSTED_CPU_WATCHDOG_BOUND_EXCEEDED"
        elif (
            watchdog.get("failure_reason") is not None
            or termination.get("TerminateJobObject_BOOL") is not True
            or run.get("termination_reason") != "trusted_cpu_watchdog_limit"
            or live.get("blocker") is not None
        ):
            disposition = "watchdog_fail_closed_blocker"
            first_failure_classification = "TRUSTED_CPU_WATCHDOG_FAIL_CLOSED_BLOCKER"
        else:
            disposition = "watchdog_contract_not_repeatable"
            first_failure_classification = "TRUSTED_CPU_WATCHDOG_NONDETERMINISTIC_ON_CURRENT_HOST"
        rows.append({
            "id": case_id,
            "ordinal": ordinal,
            "identity": "zero_capability_AppContainer" if use_appcontainer else "non_AppContainer",
            "repetition": repetition,
            "passed": within_bound,
            "disposition": disposition,
            "final_target_user_time_100ns": final_user_time,
            "CPU_overshoot_100ns": watchdog.get("CPU_overshoot_100ns"),
            "target_END_OF_PROCESS_TIME_message_count": len(target_end_events),
            "live_NEW_PROCESS_PIDs": new_process_pids,
            "live_attributed_PIDs": captured_pids,
            "target_capture_count": len(target_captures),
            "companion_capture_count": len(companion_captures),
            "uncontracted_process_count": len(uncontracted),
            "run": trusted_cpu_watchdog_run_projection(run),
        })
        if not within_bound:
            break

    passed_count = sum(1 for row in rows if row["passed"] is True)
    if len(rows) == 8 and passed_count == 8:
        result_code = "TRUSTED_CPU_WATCHDOG_REPEATABLE_WITHIN_BOUND"
    else:
        result_code = first_failure_classification or "TRUSTED_CPU_WATCHDOG_NONDETERMINISTIC_ON_CURRENT_HOST"
    return {
        "schema": "pipeline-v2.k0b03-v2-windows-trusted-CPU-watchdog-diagnostic-v1",
        "attempt": "A",
        "status": "trusted_cpu_watchdog_diagnostic_captured",
        "result_code": result_code,
        "qualification_result": None,
        "CPU_prerequisite_disposition": "pending_fresh_context_security_review",
        "launcher_gate": launcher_gate,
        "matrix_expected_count": 8,
        "matrix_actual_count": len(rows),
        "passed_count": passed_count,
        "failed_count": sum(1 for row in rows if row["passed"] is False),
        "errors_count": 0,
        "skips_count": 0,
        "terminal_no_loop_rule_applies": result_code != "TRUSTED_CPU_WATCHDOG_REPEATABLE_WITHIN_BOUND",
        "rows": rows,
        "canary_unchanged_before_cleanup": canary.is_file() and file_pin(canary)["sha256"] == canary_before,
        "job_quiescence_verified_before_cleanup": all_quiescent,
    }


def capture_assigned_suspended_target_flag_preservation_diagnostic(
    runner: JobRun,
    child_pids: set[int],
    canary: Path,
    canary_before: str,
    launcher_gate: dict[str, object],
) -> dict[str, object]:
    if launcher_gate.get("current_process_in_any_Job") is not False:
        raise ProbeStop("NON_NESTED_LAUNCH_CONTEXT_REQUIRED", canonical(launcher_gate))
    definitions = [
        (
            "AT-WIN-01",
            False,
            "assigned_non_AppContainer_suspended_target_Basic_PROCESS_TIME_only_flag_preservation",
        ),
        (
            "AT-WIN-02",
            True,
            "assigned_zero_capability_AppContainer_suspended_target_Basic_PROCESS_TIME_only_flag_preservation",
        ),
    ]
    baseline_flags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION
    expected_flags = baseline_flags | JOB_OBJECT_LIMIT_PROCESS_TIME
    rows: list[dict[str, object]] = []
    all_quiescent = True
    for case_id, use_appcontainer, purpose in definitions:
        run = runner.run(
            "cpu",
            timeout_ms=5000,
            process_time_limit=True,
            process_time_control_diagnostic=True,
            live_companion_attribution_diagnostic=True,
            assigned_suspended_target_flag_preservation_diagnostic=True,
            require_non_nested_target=True,
            use_appcontainer=use_appcontainer,
            active_process_limit=None,
            defer_process_time_limit_until_assigned=True,
            deferred_process_time_information_class=JOB_OBJECT_BASIC_LIMIT_INFORMATION,
            diagnostic_case_id=case_id,
            completion_quiet_window_ms=250,
        )
        process_id = run.get("process_id")
        if isinstance(process_id, int) and process_id > 0:
            child_pids.add(process_id)
        worker_records = parsed_worker_records(run)
        child_pids.update(worker_record_pids(worker_records))
        live = run.get("live_attribution") or {}
        captures = live.get("captured_processes") or []
        for captured in captures:
            if isinstance(captured, dict):
                captured_pid = captured.get("notification_PID")
                if isinstance(captured_pid, int) and captured_pid > 0:
                    child_pids.add(captured_pid)
        target_captures = [
            value for value in captures
            if isinstance(value, dict)
            and value.get("relationship") == "target"
            and value.get("notification_PID") == process_id
        ]
        uncontracted = [
            value for value in captures
            if isinstance(value, dict) and value.get("relationship") == "uncontracted_process"
        ]
        quiescence = run.get("job_quiescence") or {}
        completion_events = quiescence.get("messages") or []
        new_process_pids = sorted(
            int(value.get("process_id_value"))
            for value in completion_events
            if isinstance(value, dict)
            and value.get("message") == JOB_OBJECT_MSG_NEW_PROCESS
            and isinstance(value.get("process_id_value"), int)
            and int(value.get("process_id_value")) > 0
        )
        captured_pids = sorted(
            int(value.get("notification_PID"))
            for value in captures
            if isinstance(value, dict)
            and isinstance(value.get("notification_PID"), int)
            and int(value.get("notification_PID")) > 0
        )
        initial_readback = run.get("initial_effective_job_limits") or {}
        readback = run.get("effective_job_limits") or {}
        operations = run.get("limit_operations") or []
        initial_operation = operations[0] if len(operations) == 2 else {}
        basic_operation = operations[1] if len(operations) == 2 else {}
        membership = run.get("job_membership") or {}
        output = run.get("output") or {}
        owned_termination = run.get("owned_job_termination") or {}
        run_cleanup = run.get("run_cleanup") or {}
        target_capture = target_captures[0] if len(target_captures) == 1 else {}
        quiescent = bool(
            quiescence.get("deadline_expired") is False
            and quiescence.get("active_process_zero_message_seen") is True
            and quiescence.get("quiet_window_ms") == 250
            and quiescence.get("quiet_window_completed") is True
            and quiescence.get("final_PID_inventory_empty") is True
            and (quiescence.get("final_accounting") or {}).get("active_process_zero") is True
            and quiescence.get("quiescent") is True
        )
        all_quiescent = all_quiescent and quiescent
        common_contract = bool(
            run.get("created_suspended") is True
            and run.get("assigned_before_resume") is True
            and run.get("resume_called") is False
            and run.get("resume_thread_call_count") == 0
            and run.get("direct_termination_before_resume") is True
            and run.get("worker_record_count") == 0
            and worker_records == []
            and run.get("use_appcontainer") is use_appcontainer
            and membership.get("target_in_any_Job_before_owned_assignment") is False
            and membership.get("target_in_owned_Job_before_assignment") is False
            and membership.get("target_in_owned_Job_after_assignment") is True
            and len(operations) == 2
            and initial_operation.get("phase") == "before_assignment_initial"
            and initial_operation.get("information_class") == JOB_OBJECT_EXTENDED_LIMIT_INFORMATION
            and initial_operation.get("information_length") == ct.sizeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION)
            and initial_operation.get("LimitFlags") == baseline_flags
            and initial_operation.get("PerProcessUserTimeLimit") == 0
            and initial_operation.get("SetInformationJobObject_result") is True
            and initial_operation.get("SetInformationJobObject_last_error") == 0
            and initial_readback.get("QueryInformationJobObject_result") == 1
            and initial_readback.get("QueryInformationJobObject_last_error") == 0
            and initial_readback.get("QueryInformationJobObject_returned_length") == 144
            and initial_readback.get("LimitFlags") == baseline_flags
            and initial_readback.get("PerProcessUserTimeLimit") == 0
            and initial_readback.get("ActiveProcessLimit") == 0
            and basic_operation.get("phase") == "after_assignment_before_resume"
            and basic_operation.get("information_class") == JOB_OBJECT_BASIC_LIMIT_INFORMATION
            and basic_operation.get("information_class_name") == "JobObjectBasicLimitInformation"
            and basic_operation.get("structure_name") == "JOBOBJECT_BASIC_LIMIT_INFORMATION"
            and basic_operation.get("information_length") == ct.sizeof(JOBOBJECT_BASIC_LIMIT_INFORMATION)
            and basic_operation.get("LimitFlags") == JOB_OBJECT_LIMIT_PROCESS_TIME
            and basic_operation.get("PerProcessUserTimeLimit") == 10_000_000
            and readback.get("QueryInformationJobObject_result") == 1
            and readback.get("QueryInformationJobObject_last_error") == 0
            and readback.get("QueryInformationJobObject_returned_length") == 144
            and len(target_captures) == 1
            and target_capture.get("TokenIsAppContainer") is use_appcontainer
            and target_capture.get("capability_count") == 0
            and live.get("blocker") is None
            and not uncontracted
            and new_process_pids == captured_pids
            and process_id in new_process_pids
            and owned_termination.get("result") is True
            and owned_termination.get("immediate_GetLastError") == 0
            and run.get("termination_reason") == "assigned_suspended_target_control_termination"
            and run.get("inactive_after_termination") is True
            and output.get("total_bytes") == 0
            and output.get("overflow") is False
            and output.get("reader_errors") == []
            and run_cleanup.get("process_handle_closed") is True
            and run_cleanup.get("thread_handle_closed") is True
            and run_cleanup.get("pipe_handles_closed") == 6
            and run_cleanup.get("attribute_list_deleted") is True
            and run_cleanup.get("Job_handle_closed") is True
            and run_cleanup.get("completion_port_handle_closed") is True
            and quiescent
        )
        basic_set_succeeded = basic_operation.get("SetInformationJobObject_result") is True
        basic_set_rejected = bool(
            common_contract and basic_operation.get("SetInformationJobObject_result") is False
        )
        preservation = bool(
            common_contract
            and basic_set_succeeded
            and basic_operation.get("SetInformationJobObject_last_error") == 0
            and readback.get("LimitFlags") == expected_flags
            and readback.get("PerProcessUserTimeLimit") == 10_000_000
            and readback.get("ActiveProcessLimit") == 0
            and int(readback.get("LimitFlags", 0)) & JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            and int(readback.get("LimitFlags", 0)) & JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION
        )
        replacement = bool(
            common_contract
            and basic_set_succeeded
            and (
                not (int(readback.get("LimitFlags", 0)) & JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)
                or not (int(readback.get("LimitFlags", 0)) & JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION)
            )
        )
        rows.append({
            "id": case_id,
            "purpose": purpose,
            "identity": "zero_capability_AppContainer" if use_appcontainer else "non_AppContainer",
            "passed": preservation,
            "common_contract_satisfied": common_contract,
            "basic_set_succeeded": basic_set_succeeded,
            "basic_set_rejected": basic_set_rejected,
            "extended_flags_replaced": replacement,
            "live_NEW_PROCESS_PIDs": new_process_pids,
            "live_attributed_PIDs": captured_pids,
            "uncontracted_process_count": len(uncontracted),
            "run": {
                **non_nested_process_time_run_projection(run),
                "initial_effective_job_limits": initial_readback,
                "resume_thread_call_count": run.get("resume_thread_call_count"),
                "worker_record_count": run.get("worker_record_count"),
                "owned_job_termination": owned_termination,
                "run_cleanup": run_cleanup,
            },
        })

    by_id = {str(row["id"]): row for row in rows}
    if all(row["passed"] is True for row in rows):
        result_code = "ASSIGNED_SUSPENDED_TARGET_BASIC_PROCESS_TIME_PRESERVES_EXTENDED_FLAGS_BOTH_IDENTITIES"
    elif by_id["AT-WIN-01"]["basic_set_rejected"] is True:
        result_code = "ASSIGNED_TARGET_BASIC_SET_REJECTED_NON_APPCONTAINER"
    elif by_id["AT-WIN-02"]["basic_set_rejected"] is True:
        result_code = "ASSIGNED_TARGET_BASIC_SET_REJECTED_APPCONTAINER"
    elif any(row["extended_flags_replaced"] is True for row in rows):
        result_code = "ASSIGNED_TARGET_BASIC_SET_REPLACES_EXTENDED_FLAGS"
    else:
        result_code = "ASSIGNED_TARGET_CONTROL_CONTRACT_MISMATCH"
    return {
        "schema": "pipeline-v2.k0b03-v2-windows-assigned-suspended-target-flag-preservation-diagnostic-v1",
        "attempt": "A",
        "status": "assigned_suspended_target_flag_preservation_diagnostic_captured",
        "result_code": result_code,
        "qualification_result": None,
        "CPU_enforcement_conclusion": None,
        "launcher_gate": launcher_gate,
        "matrix_expected_count": 2,
        "matrix_actual_count": len(rows),
        "passed_count": sum(1 for row in rows if row["passed"] is True),
        "failed_count": sum(1 for row in rows if row["passed"] is False),
        "errors_count": 0,
        "skips_count": 0,
        "rows": rows,
        "canary_unchanged_before_cleanup": canary.is_file() and file_pin(canary)["sha256"] == canary_before,
        "job_quiescence_verified_before_cleanup": all_quiescent,
    }


def worker_record_pids(records: list[dict[str, object]]) -> set[int]:
    result: set[int] = set()
    for record in records:
        for key in ("pid", "worker_pid", "child_pid", "first_pid", "second_pid"):
            value = record.get(key)
            if isinstance(value, int) and value > 0:
                result.add(value)
        steps = record.get("popen_steps")
        if isinstance(steps, list):
            for step in steps:
                if isinstance(step, dict):
                    value = step.get("pid")
                    if isinstance(value, int) and value > 0:
                        result.add(value)
    return result


def capture_case_remediation_diagnostic(
    runner: JobRun,
    args: argparse.Namespace,
    sid_string: str,
    listeners: list[socket.socket],
    child_pids: set[int],
) -> dict[str, object]:
    rows: list[dict[str, object]] = []

    def remember(run: dict[str, object]) -> dict[str, object]:
        process_id = run.get("process_id")
        if isinstance(process_id, int):
            child_pids.add(process_id)
        child_pids.update(worker_record_pids(parsed_worker_records(run)))
        return run

    forced_abort_run = remember(runner.run(
        "identity",
        force_abort_before_job_assignment=True,
        remediation_diagnostic=True,
    ))
    identity_run = remember(runner.run("identity", remediation_diagnostic=True))
    identity_output = parsed_worker_output(identity_run)
    forced_components = {
        "created_suspended": forced_abort_run.get("created_suspended") is True,
        "not_assigned_before_resume": forced_abort_run.get("assigned_before_resume") is False,
        "resume_not_called": forced_abort_run.get("resume_called") is False,
        "direct_termination_before_resume": forced_abort_run.get("direct_termination_before_resume") is True,
        "inactive_after_termination": forced_abort_run.get("inactive_after_termination") is True,
        "exact_AppContainer_SID": (forced_abort_run.get("identity") or {}).get("appcontainer_sid") == sid_string,
        "AppContainer_SID_valid": (forced_abort_run.get("identity") or {}).get("appcontainer_sid_valid") is True,
        "zero_capabilities": (forced_abort_run.get("identity") or {}).get("capability_count") == 0,
    }
    identity_components = {
        "worker_record_present": identity_output is not None,
        "worker_result_WORKER_IDENTITY": bool(identity_output and identity_output.get("result_code") == "WORKER_IDENTITY"),
        "worker_AppContainer": bool(identity_output and identity_output.get("token_is_appcontainer") is True),
        "worker_exact_SID": bool(identity_output and identity_output.get("appcontainer_sid") == sid_string),
        "worker_zero_capabilities": bool(identity_output and identity_output.get("capability_count") == 0),
        "parent_exact_SID": (identity_run.get("identity") or {}).get("appcontainer_sid") == sid_string,
        "parent_zero_capabilities": (identity_run.get("identity") or {}).get("capability_count") == 0,
        "created_suspended": identity_run.get("created_suspended") is True,
        "assigned_before_resume": identity_run.get("assigned_before_resume") is True,
        "resume_called": identity_run.get("resume_called") is True,
        "final_ActiveProcesses_zero": (identity_run.get("job_accounting") or {}).get("active_process_zero") is True,
        "ACTIVE_PROCESS_ZERO_message_seen": (identity_run.get("job_quiescence") or {}).get("active_process_zero_message_seen") is True,
    }
    rows.append({
        "id": "RD-WIN-01",
        "purpose": "CP-WIN-05 forced-abort and normal-identity full predicate decomposition",
        "forced_abort_predicate_components": forced_components,
        "normal_identity_predicate_components": identity_components,
        "forced_abort_run": remediation_run_projection(forced_abort_run),
        "normal_identity_run": remediation_run_projection(identity_run),
    })
    rows.append({
        "id": "RD-WIN-02",
        "purpose": "effective Job-limit readback and bounded active-process-zero completion ordering",
        "effective_job_limits": identity_run.get("effective_job_limits"),
        "job_quiescence": identity_run.get("job_quiescence"),
        "job_process_id_inventory": identity_run.get("job_process_id_inventory"),
    })

    cpu_run = remember(runner.run(
        "cpu",
        timeout_ms=5000,
        process_time_limit=True,
        remediation_diagnostic=True,
    ))
    rows.append({
        "id": "RD-WIN-03",
        "purpose": "CPU-limit target-process telemetry without accepting wall-time fallback",
        "run": remediation_run_projection(cpu_run),
        "wall_time_fallback_accepted": False,
    })

    job_memory_run = remember(runner.run(
        "job_memory",
        job_memory_limit=True,
        timeout_ms=5000,
        remediation_diagnostic=True,
    ))
    rows.append({
        "id": "RD-WIN-04",
        "purpose": "job-memory first-Popen provenance",
        "run": remediation_run_projection(job_memory_run),
    })

    active_process_run = remember(runner.run(
        "active_process",
        timeout_ms=5000,
        remediation_diagnostic=True,
    ))
    rows.append({
        "id": "RD-WIN-05",
        "purpose": "active-process first and second Popen provenance plus Job process inventory",
        "run": remediation_run_projection(active_process_run),
    })

    tree_run = remember(runner.run(
        "tree",
        terminate_on_ready=True,
        timeout_ms=5000,
        remediation_diagnostic=True,
    ))
    rows.append({
        "id": "RD-WIN-06",
        "purpose": "owned-tree first-Popen provenance",
        "run": remediation_run_projection(tree_run),
    })

    ipv4_run = remember(runner.run(
        "egress",
        ["--family", "IPv4", "--host", args.ipv4_host, "--port", str(args.ipv4_port)],
        remediation_diagnostic=True,
    ))
    ipv4_accepts = listener_accept_count(listeners[0])
    rows.append({
        "id": "RD-WIN-07",
        "purpose": "IPv4 connect and separate connect_ex raw provenance",
        "listener_accept_count": ipv4_accepts,
        "run": remediation_run_projection(ipv4_run),
    })

    ipv6_run = remember(runner.run(
        "egress",
        ["--family", "IPv6", "--host", args.ipv6_host, "--port", str(args.ipv6_port)],
        remediation_diagnostic=True,
    ))
    ipv6_accepts = listener_accept_count(listeners[1])
    rows.append({
        "id": "RD-WIN-08",
        "purpose": "IPv6 connect and separate connect_ex raw provenance",
        "listener_accept_count": ipv6_accepts,
        "run": remediation_run_projection(ipv6_run),
    })
    return {
        "schema": "pipeline-v2.k0b03-v2-windows-case-remediation-diagnostic-v1",
        "attempt": "A",
        "status": "evidence_captured_pending_final_remediation_design",
        "result_code": "CASE_REMEDIATION_DIAGNOSTIC_CAPTURED",
        "qualification_result": None,
        "matrix_expected_count": 9,
        "rows": rows,
    }


def native_winsock_terminal_disposition(worker: dict[str, object] | None) -> dict[str, object]:
    projection: dict[str, object] = {
        "disposition": None,
        "terminal_WSA_error": None,
        "terminal_error_source": None,
        "final_SO_ERROR_authoritative": False,
        "projection_blocker": None,
    }
    if worker is None or worker.get("result_code") != "WORKER_NATIVE_WINSOCK_DIAGNOSTIC":
        projection["projection_blocker"] = "native_Winsock_worker_record_absent_or_unexpected"
        return projection
    startup_result = worker.get("WSAStartup_result")
    immediate_return = worker.get("immediate_return")
    immediate_error = worker.get("immediate_WSA_error")
    select_return = worker.get("select_return")
    write_ready = worker.get("write_ready") is True
    exception_ready = worker.get("exception_ready") is True
    getsockopt_return = worker.get("getsockopt_return")
    final_so_error = worker.get("final_SO_ERROR")
    if startup_result != 0:
        projection["disposition"] = "startup_failure"
    elif immediate_return == 0:
        projection["disposition"] = "connected_immediate"
    elif immediate_return == -1 and immediate_error != WSAEWOULDBLOCK:
        projection["disposition"] = "terminal_immediate_error"
        projection["terminal_WSA_error"] = immediate_error
        projection["terminal_error_source"] = "immediate_WSA_error"
    elif immediate_return == -1 and immediate_error == WSAEWOULDBLOCK:
        if select_return == -1:
            projection["disposition"] = "select_failure"
            projection["terminal_WSA_error"] = worker.get("select_WSA_error")
            projection["terminal_error_source"] = "select_WSA_error"
        elif select_return == 0:
            projection["disposition"] = "pending_timeout"
        elif isinstance(select_return, int) and not isinstance(select_return, bool) and select_return > 0:
            if not (write_ready or exception_ready):
                projection["disposition"] = "select_fd_set_contract_mismatch"
            elif getsockopt_return != 0:
                projection["disposition"] = "getsockopt_failure"
                projection["terminal_WSA_error"] = worker.get("getsockopt_WSA_error")
                projection["terminal_error_source"] = "getsockopt_WSA_error"
            else:
                projection["final_SO_ERROR_authoritative"] = True
                if final_so_error == 0:
                    projection["disposition"] = "connected_after_pending"
                else:
                    projection["disposition"] = "terminal_deferred_error"
                    projection["terminal_WSA_error"] = final_so_error
                    projection["terminal_error_source"] = "final_SO_ERROR"
        else:
            projection["projection_blocker"] = "pending_select_result_contract_mismatch"
    else:
        projection["projection_blocker"] = "immediate_connect_result_contract_mismatch"
    return projection


def capture_native_winsock_isolation_control_diagnostic(
    runner: JobRun,
    args: argparse.Namespace,
    sid_string: str,
    listeners: list[socket.socket],
    child_pids: set[int],
    canary: Path,
    canary_before: str,
) -> dict[str, object]:
    definitions = [
        ("NW-WIN-01", False, "IPv4", args.ipv4_host, args.ipv4_port, 0, "positive-connect control"),
        ("NW-WIN-02", True, "IPv4", args.ipv4_host, args.ipv4_port, 0, "denial observation"),
        ("NW-WIN-03", False, "IPv6", args.ipv6_host, args.ipv6_port, 1, "positive-connect control"),
        ("NW-WIN-04", True, "IPv6", args.ipv6_host, args.ipv6_port, 1, "denial observation"),
    ]
    if len(listeners) != 2:
        raise ProbeStop("NATIVE_WINSOCK_CONTROL_LISTENER_COUNT_MISMATCH", str(len(listeners)))
    rows: list[dict[str, object]] = []
    all_quiescent = True
    for case_id, use_appcontainer, family, host, port, listener_index, purpose in definitions:
        run = runner.run(
            "native_winsock",
            ["--family", family, "--host", host, "--port", str(port)],
            timeout_ms=5000,
            process_time_limit=False,
            process_memory_limit=False,
            job_memory_limit=False,
            final_remediation_diagnostic=True,
            use_appcontainer=use_appcontainer,
            active_process_limit=2,
        )
        process_id = run.get("process_id")
        if isinstance(process_id, int) and process_id > 0:
            child_pids.add(process_id)
        child_pids.update(worker_record_pids(parsed_worker_records(run)))
        worker = parsed_worker_output(run)
        terminal = native_winsock_terminal_disposition(worker)
        accept_count = listener_accept_count(listeners[listener_index])
        identity = run.get("identity") or {}
        output = run.get("output") or {}
        quiescence = run.get("job_quiescence") or {}
        final_accounting = quiescence.get("final_accounting") or {}
        final_process_ids = quiescence.get("final_process_ids") or {}
        quiescent = bool(
            quiescence.get("deadline_expired") is False
            and quiescence.get("active_process_zero_message_seen") is True
            and quiescence.get("quiet_window_completed") is True
            and quiescence.get("final_PID_inventory_empty") is True
            and final_accounting.get("active_process_zero") is True
            and final_process_ids.get("number_of_assigned_processes") == 0
            and final_process_ids.get("process_ids") == []
            and quiescence.get("quiescent") is True
        )
        all_quiescent = all_quiescent and quiescent
        identity_ok = bool(
            identity.get("token_is_appcontainer") is use_appcontainer
            and identity.get("capability_count") == 0
            and (
                (
                    use_appcontainer
                    and identity.get("appcontainer_sid") == sid_string
                    and identity.get("appcontainer_sid_valid") is True
                )
                or (
                    not use_appcontainer
                    and identity.get("appcontainer_sid") is None
                    and identity.get("appcontainer_sid_valid") is False
                )
            )
        )
        common_ok = bool(
            worker is not None
            and worker.get("result_code") == "WORKER_NATIVE_WINSOCK_DIAGNOSTIC"
            and worker.get("family") == family
            and worker.get("endpoint") == {"host": host, "port": port}
            and terminal.get("projection_blocker") is None
            and run.get("created_suspended") is True
            and run.get("assigned_before_resume") is True
            and run.get("resume_called") is True
            and run.get("exit_code") == 0
            and run.get("inactive_after_termination") is True
            and identity_ok
            and output.get("overflow") is False
            and output.get("reader_errors") == []
            and quiescent
        )
        if use_appcontainer:
            passed = bool(
                common_ok
                and terminal.get("disposition") in {
                    "terminal_immediate_error",
                    "terminal_deferred_error",
                }
                and terminal.get("terminal_WSA_error") == WSAEACCES
                and accept_count == 0
            )
        else:
            passed = bool(
                common_ok
                and terminal.get("disposition") in {
                    "connected_immediate",
                    "connected_after_pending",
                }
                and accept_count == 1
            )
        rows.append({
            "id": case_id,
            "purpose": purpose,
            "identity": "zero-capability AppContainer" if use_appcontainer else "non-AppContainer",
            "family": family,
            "endpoint": {"host": host, "port": port},
            "passed": passed,
            "evidence": {
                "worker": worker,
                "terminal_disposition": terminal,
                "listener_accept_count": accept_count,
                "identity_confirmed": identity_ok,
                "Job_quiescence_confirmed": quiescent,
                "run": remediation_run_projection(run),
            },
        })

    positive_rows = [row for row in rows if row["identity"] == "non-AppContainer"]
    appcontainer_rows = [row for row in rows if row["identity"] == "zero-capability AppContainer"]
    positive_controls_passed = all(row["passed"] is True for row in positive_rows)
    appcontainer_controls_passed = all(row["passed"] is True for row in appcontainer_rows)
    appcontainer_signatures = [
        (
            (row.get("evidence") or {}).get("terminal_disposition", {}).get("disposition"),
            (row.get("evidence") or {}).get("terminal_disposition", {}).get("terminal_WSA_error"),
        )
        for row in appcontainer_rows
    ]
    appcontainer_pending = all(
        signature == ("pending_timeout", None)
        and (row.get("evidence") or {}).get("listener_accept_count") == 0
        for row, signature in zip(appcontainer_rows, appcontainer_signatures)
    )
    if not positive_controls_passed:
        status = "stop_inconclusive"
        result_code = "NATIVE_WINSOCK_POSITIVE_CONTROL_FAILED"
    elif appcontainer_controls_passed:
        status = "native_winsock_four_case_control_pass_candidate_pending_read_only_review"
        result_code = "NATIVE_WINSOCK_FOUR_CASE_CONTROL_WSAEACCES_CONFIRMED"
    elif appcontainer_pending:
        status = "blocking_host_capability_result"
        result_code = "APPCONTAINER_LOOPBACK_PENDING_WITHOUT_WSAEACCES_ON_CURRENT_HOST"
    elif len(set(appcontainer_signatures)) > 1:
        status = "stop_inconclusive"
        result_code = "IPV4_IPV6_NETWORK_DISPOSITION_DIVERGENCE"
    else:
        status = "stop_inconclusive"
        result_code = "NATIVE_WINSOCK_APPCONTAINER_TERMINAL_DISPOSITION_NOT_ACCEPTED"
    return {
        "schema": "pipeline-v2.k0b03-v2-windows-native-Winsock-isolation-control-diagnostic-v1",
        "attempt": "A",
        "status": status,
        "result_code": result_code,
        "qualification_result": None,
        "matrix_expected_count": 4,
        "matrix_actual_count": len(rows),
        "passed_count": sum(1 for row in rows if row["passed"] is True),
        "failed_count": sum(1 for row in rows if row["passed"] is False),
        "errors_count": 0,
        "skips_count": 0,
        "positive_controls_passed": positive_controls_passed,
        "AppContainer_controls_passed": appcontainer_controls_passed,
        "AppContainer_family_signatures": appcontainer_signatures,
        "rows": rows,
        "canary_unchanged_before_cleanup": canary.is_file() and file_pin(canary)["sha256"] == canary_before,
        "job_quiescence_verified_before_cleanup": all_quiescent,
    }


def capture_trusted_pending_connect_watchdog_diagnostic(
    runner: JobRun,
    args: argparse.Namespace,
    sid_string: str,
    listeners: list[socket.socket],
    child_pids: set[int],
    canary: Path,
    canary_before: str,
) -> dict[str, object]:
    definitions = [
        ("NW-WD-01", False, "IPv4", args.ipv4_host, args.ipv4_port, 0, "positive-connect control"),
        ("NW-WD-02", True, "IPv4", args.ipv4_host, args.ipv4_port, 0, "trusted pending-connect watchdog"),
        ("NW-WD-03", False, "IPv6", args.ipv6_host, args.ipv6_port, 1, "positive-connect control"),
        ("NW-WD-04", True, "IPv6", args.ipv6_host, args.ipv6_port, 1, "trusted pending-connect watchdog"),
    ]
    if len(listeners) != 2:
        raise ProbeStop("TRUSTED_PENDING_CONNECT_LISTENER_COUNT_MISMATCH", str(len(listeners)))
    rows: list[dict[str, object]] = []
    all_quiescent = True
    first_failure_classification: str | None = None

    def quiescence_ok(run: dict[str, object]) -> bool:
        quiescence = run.get("job_quiescence") or {}
        final_accounting = quiescence.get("final_accounting") or {}
        final_process_ids = quiescence.get("final_process_ids") or {}
        return bool(
            quiescence.get("deadline_expired") is False
            and quiescence.get("active_process_zero_message_seen") is True
            and quiescence.get("quiet_window_ms") == 250
            and quiescence.get("quiet_window_completed") is True
            and quiescence.get("final_PID_inventory_empty") is True
            and final_accounting.get("active_process_zero") is True
            and final_process_ids.get("number_of_assigned_processes") == 0
            and final_process_ids.get("process_ids") == []
            and quiescence.get("quiescent") is True
        )

    for case_id, use_appcontainer, family, host, port, listener_index, purpose in definitions:
        run = runner.run(
            "native_winsock",
            ["--family", family, "--host", host, "--port", str(port)],
            timeout_ms=5000,
            process_time_limit=False,
            process_memory_limit=False,
            job_memory_limit=False,
            final_remediation_diagnostic=True,
            live_companion_attribution_diagnostic=use_appcontainer,
            trusted_pending_connect_watchdog_enabled=use_appcontainer,
            trusted_pending_connect_listener=(listeners[listener_index] if use_appcontainer else None),
            use_appcontainer=use_appcontainer,
            active_process_limit=2,
            completion_quiet_window_ms=250,
        )
        process_id = run.get("process_id")
        if isinstance(process_id, int) and process_id > 0:
            child_pids.add(process_id)
        child_pids.update(worker_record_pids(parsed_worker_records(run, limit=64)))
        identity = run.get("identity") or {}
        output = run.get("output") or {}
        quiescent = quiescence_ok(run)
        all_quiescent = all_quiescent and quiescent
        identity_ok = bool(
            identity.get("token_is_appcontainer") is use_appcontainer
            and identity.get("capability_count") == 0
            and (
                (
                    use_appcontainer
                    and identity.get("appcontainer_sid") == sid_string
                    and identity.get("appcontainer_sid_valid") is True
                )
                or (
                    not use_appcontainer
                    and identity.get("appcontainer_sid") is None
                    and identity.get("appcontainer_sid_valid") is False
                )
            )
        )
        accept_count: int | None = None
        terminal: dict[str, object] | None = None
        watchdog: dict[str, object] | None = None
        live: dict[str, object] | None = None
        if not use_appcontainer:
            worker = parsed_worker_output(run)
            terminal = native_winsock_terminal_disposition(worker)
            accept_count = listener_accept_count(listeners[listener_index])
            passed = bool(
                worker is not None
                and worker.get("result_code") == "WORKER_NATIVE_WINSOCK_DIAGNOSTIC"
                and worker.get("family") == family
                and worker.get("endpoint") == {"host": host, "port": port}
                and terminal.get("projection_blocker") is None
                and terminal.get("disposition") in {
                    "connected_immediate",
                    "connected_after_pending",
                }
                and terminal.get("final_SO_ERROR_authoritative") is True
                and worker.get("final_SO_ERROR") == 0
                and accept_count == 1
                and run.get("created_suspended") is True
                and run.get("assigned_before_resume") is True
                and run.get("resume_called") is True
                and run.get("exit_code") == 0
                and run.get("inactive_after_termination") is True
                and identity_ok
                and output.get("overflow") is False
                and output.get("reader_errors") == []
                and quiescent
            )
            if not passed:
                first_failure_classification = (
                    "TRUSTED_PENDING_CONNECT_WATCHDOG_POSITIVE_CONTROL_FAILED"
                )
        else:
            watchdog = run.get("trusted_pending_connect_watchdog") or {}
            live = run.get("live_attribution") or {}
            captures = live.get("captured_processes") or []
            for captured in captures:
                if isinstance(captured, dict):
                    captured_pid = captured.get("notification_PID")
                    if isinstance(captured_pid, int) and captured_pid > 0:
                        child_pids.add(captured_pid)
            target_captures = [
                value for value in captures
                if isinstance(value, dict)
                and value.get("relationship") == "target"
                and value.get("notification_PID") == process_id
            ]
            companion_captures = [
                value for value in captures
                if isinstance(value, dict)
                and value.get("relationship") == "companion_candidate"
            ]
            uncontracted = [
                value for value in captures
                if isinstance(value, dict)
                and value.get("relationship") == "uncontracted_process"
            ]
            target_capture = target_captures[0] if len(target_captures) == 1 else {}
            companion_capture = companion_captures[0] if len(companion_captures) == 1 else {}
            completion_events = (run.get("job_quiescence") or {}).get("messages") or []
            new_process_pids = sorted(
                int(event.get("process_id_value"))
                for event in completion_events
                if isinstance(event, dict)
                and event.get("message") == JOB_OBJECT_MSG_NEW_PROCESS
                and isinstance(event.get("process_id_value"), int)
                and int(event.get("process_id_value")) > 0
            )
            captured_pids = sorted(
                int(value.get("notification_PID"))
                for value in captures
                if isinstance(value, dict)
                and isinstance(value.get("notification_PID"), int)
                and int(value.get("notification_PID")) > 0
            )
            records = watchdog.get("parent_observed_worker_records") or []
            ready_records = [
                value for value in records
                if isinstance(value, dict)
                and value.get("result_code") == "WORKER_NATIVE_WINSOCK_PENDING_READY"
            ]
            sample_records = [
                value for value in records
                if isinstance(value, dict)
                and value.get("result_code") == "WORKER_NATIVE_WINSOCK_PENDING_SAMPLE"
            ]
            terminal_records = [
                value for value in records
                if isinstance(value, dict)
                and value.get("result_code") == "WORKER_NATIVE_WINSOCK_TERMINAL_OBSERVATION"
            ]
            self_close_records = [
                value for value in records
                if isinstance(value, dict)
                and value.get("result_code") == "WORKER_NATIVE_WINSOCK_SELF_CLOSE"
            ]
            ready = ready_records[0] if len(ready_records) == 1 else {}
            sequences = [value.get("sequence") for value in records if isinstance(value, dict)]
            liveness = watchdog.get("target_liveness_observations") or []
            listener_observations = watchdog.get("listener_accept_observations") or []
            termination = watchdog.get("termination") or {}
            limits = run.get("effective_job_limits") or {}
            membership = run.get("job_membership") or {}
            previous_positive_passed = bool(rows and rows[-1].get("passed") is True)
            passed = bool(
                previous_positive_passed
                and run.get("created_suspended") is True
                and run.get("assigned_before_resume") is True
                and run.get("resume_called") is True
                and run.get("inactive_after_termination") is True
                and identity_ok
                and membership.get("target_in_owned_Job_before_assignment") is False
                and membership.get("target_in_owned_Job_after_assignment") is True
                and limits.get("LimitFlags") == (
                    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                    | JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION
                    | JOB_OBJECT_LIMIT_ACTIVE_PROCESS
                )
                and limits.get("ActiveProcessLimit") == 2
                and len(target_captures) == 1
                and target_capture.get("TokenIsAppContainer") is True
                and target_capture.get("AppContainer_SID") == sid_string
                and target_capture.get("capability_count") == 0
                and len(companion_captures) == 1
                and companion_capture.get("explicit_assignment_by_diagnostic") is False
                and companion_capture.get("inherited_owned_Job_membership_evidence") is True
                and companion_capture.get("live_owned_Job_membership") is True
                and companion_capture.get("TokenIsAppContainer") is True
                and companion_capture.get("AppContainer_SID") == sid_string
                and companion_capture.get("capability_count") == 0
                and uncontracted == []
                and live.get("blocker") is None
                and live.get("target_notification_seen") is True
                and live.get("non_target_notification_count") == 1
                and new_process_pids == captured_pids
                and len(new_process_pids) == 2
                and len(ready_records) == 1
                and ready.get("sequence") == 1
                and ready.get("family") == family
                and ready.get("endpoint") == {"host": host, "port": port}
                and ready.get("WSAStartup_result") == 0
                and ready.get("socket_created") is True
                and ready.get("nonblocking_result") == 0
                and ready.get("immediate_return") == -1
                and ready.get("immediate_WSA_error") == WSAEWOULDBLOCK
                and ready.get("socket_open") is True
                and watchdog.get("pending_ready_count") == 1
                and isinstance(watchdog.get("checkpoint_latency_ms"), int)
                and 0 <= int(watchdog["checkpoint_latency_ms"]) <= 1500
                and watchdog.get("sample_count") == len(sample_records)
                and len(sample_records) > 0
                and sequences == list(range(1, len(records) + 1))
                and all(
                    value.get("select_return") == 0
                    and value.get("select_WSA_error") == 0
                    and value.get("write_ready") is False
                    and value.get("exception_ready") is False
                    and value.get("socket_open") is True
                    for value in sample_records
                )
                and terminal_records == []
                and self_close_records == []
                and isinstance(watchdog.get("observation_duration_ms"), int)
                and 2500 <= int(watchdog["observation_duration_ms"]) <= 3000
                and isinstance(watchdog.get("maximum_parent_observed_sample_gap_ms"), int)
                and int(watchdog["maximum_parent_observed_sample_gap_ms"]) <= 250
                and isinstance(watchdog.get("last_sample_age_before_termination_ms"), int)
                and int(watchdog["last_sample_age_before_termination_ms"]) <= 250
                and watchdog.get("listener_accept_count_total") == 0
                and listener_observations != []
                and all(
                    value.get("observed_accept_count") == 0
                    and value.get("cumulative_accept_count") == 0
                    for value in listener_observations
                )
                and liveness != []
                and all(value.get("target_active") is True for value in liveness)
                and termination.get("reason") == "trusted_pending_connect_watchdog_deadline"
                and termination.get("exit_code") == 0xEE51
                and termination.get("TerminateJobObject_BOOL") is True
                and termination.get("immediate_GetLastError") == 0
                and watchdog.get("termination_wait_result") == WAIT_OBJECT_0
                and watchdog.get("target_exit_code") == 0xEE51
                and watchdog.get("failure_reason") is None
                and run.get("exit_code") == 0xEE51
                and output.get("overflow") is False
                and output.get("reader_errors") == []
                and quiescent
            )
            accept_count = int(watchdog.get("listener_accept_count_total", -1))
            if not passed:
                first_failure_classification = (
                    "TRUSTED_PENDING_CONNECT_WATCHDOG_ENFORCEMENT_NOT_PROVEN"
                )
        rows.append({
            "id": case_id,
            "purpose": purpose,
            "identity": "zero-capability AppContainer" if use_appcontainer else "non-AppContainer",
            "family": family,
            "endpoint": {"host": host, "port": port},
            "passed": passed,
            "evidence": {
                "identity_confirmed": identity_ok,
                "listener_accept_count": accept_count,
                "terminal_disposition": terminal,
                "watchdog": watchdog,
                "live_attribution": live,
                "Job_quiescence_confirmed": quiescent,
                "run": trusted_pending_connect_watchdog_run_projection(run),
            },
        })
        if not passed:
            break

    passed_count = sum(1 for row in rows if row.get("passed") is True)
    failed_count = sum(1 for row in rows if row.get("passed") is False)
    success = bool(
        len(rows) == 4
        and passed_count == 4
        and failed_count == 0
        and all_quiescent
    )
    return {
        "schema": "pipeline-v2.k0b03-v2-windows-trusted-pending-connect-watchdog-diagnostic-v1",
        "attempt": "A",
        "status": (
            "trusted_pending_connect_watchdog_pass_candidate_pending_read_only_review"
            if success
            else "stop_inconclusive"
        ),
        "result_code": (
            "TRUSTED_PENDING_CONNECT_WATCHDOG_DIAGNOSTIC_CAPTURED"
            if success
            else first_failure_classification or "TRUSTED_PENDING_CONNECT_WATCHDOG_ENFORCEMENT_NOT_PROVEN"
        ),
        "qualification_result": None,
        "matrix_expected_count": 4,
        "matrix_actual_count": len(rows),
        "passed_count": passed_count,
        "failed_count": failed_count,
        "errors_count": 0,
        "skips_count": 0,
        "rows": rows,
        "canary_unchanged_before_cleanup": canary.is_file() and file_pin(canary)["sha256"] == canary_before,
        "job_quiescence_verified_before_cleanup": all_quiescent,
    }


def capture_final_remediation_diagnostic(
    runner: JobRun,
    args: argparse.Namespace,
    sid_string: str,
    listeners: list[socket.socket],
    child_pids: set[int],
    canary: Path,
    canary_before: str,
    launcher_gate: dict[str, object],
) -> dict[str, object]:
    if launcher_gate.get("current_process_in_any_Job") is not False:
        raise ProbeStop("NON_NESTED_LAUNCH_CONTEXT_REQUIRED", canonical(launcher_gate))
    rows: list[dict[str, object]] = []

    def remember(run: dict[str, object]) -> dict[str, object]:
        process_id = run.get("process_id")
        if isinstance(process_id, int):
            child_pids.add(process_id)
        child_pids.update(worker_record_pids(parsed_worker_records(run)))
        return run

    def add_row(case_id: str, purpose: str, passed: bool, **evidence: object) -> None:
        rows.append({"id": case_id, "purpose": purpose, "passed": passed, "evidence": evidence})

    def result(status: str, result_code: str) -> dict[str, object]:
        return {
            "schema": "pipeline-v2.k0b03-v2-windows-final-remediation-diagnostic-v1",
            "attempt": "A",
            "status": status,
            "result_code": result_code,
            "qualification_result": None,
            "launcher_gate": launcher_gate,
            "matrix_expected_count": 10,
            "errors_count": 0,
            "skips_count": 0,
            "rows": rows,
            "canary_unchanged_before_cleanup": canary.is_file() and file_pin(canary)["sha256"] == canary_before,
        }

    def quiescence_ok(run: dict[str, object]) -> bool:
        quiescence = run.get("job_quiescence") or {}
        return bool(
            quiescence.get("quiescent") is True
            and quiescence.get("active_process_zero_message_seen") is True
            and quiescence.get("final_PID_inventory_empty") is True
            and (quiescence.get("final_accounting") or {}).get("active_process_zero") is True
            and run.get("inactive_after_termination") is True
        )

    def checkpoint(run: dict[str, object], name: str) -> dict[str, object] | None:
        matches = [
            value
            for value in (run.get("checkpoint_telemetry") or [])
            if isinstance(value, dict) and value.get("name") == name
        ]
        return matches[0] if len(matches) == 1 else None

    forced_abort_run = remember(runner.run(
        "identity",
        force_abort_before_job_assignment=True,
        final_remediation_diagnostic=True,
        active_process_limit=2,
    ))
    identity_run = remember(runner.run(
        "identity",
        final_remediation_diagnostic=True,
        active_process_limit=2,
    ))
    identity_output = parsed_worker_output(identity_run)
    FR01_ok = bool(
        forced_abort_run.get("created_suspended") is True
        and forced_abort_run.get("assigned_before_resume") is False
        and forced_abort_run.get("resume_called") is False
        and forced_abort_run.get("direct_termination_before_resume") is True
        and forced_abort_run.get("inactive_after_termination") is True
        and (forced_abort_run.get("identity") or {}).get("appcontainer_sid") == sid_string
        and (forced_abort_run.get("identity") or {}).get("capability_count") == 0
        and identity_output is not None
        and identity_output.get("result_code") == "WORKER_IDENTITY"
        and identity_output.get("appcontainer_sid") == sid_string
        and identity_output.get("capability_count") == 0
        and quiescence_ok(identity_run)
    )
    add_row(
        "FR-WIN-01",
        "final forced-abort and identity Job quiescence",
        FR01_ok,
        forced_abort_run=remediation_run_projection(forced_abort_run),
        identity_run=remediation_run_projection(identity_run),
        worker=identity_output,
    )
    if not FR01_ok:
        return result("stop_inconclusive", "FR_WIN_01_QUIESCENCE_OR_IDENTITY_MISMATCH")

    pipe_run = remember(runner.run(
        "pipe_smoke",
        final_remediation_diagnostic=True,
        active_process_limit=3,
        checkpoint_names=["before_first_child", "after_first_child"],
    ))
    pipe_output = parsed_worker_output(pipe_run)
    pipe_before = checkpoint(pipe_run, "before_first_child")
    pipe_after = checkpoint(pipe_run, "after_first_child")
    FR02_ok = bool(
        pipe_run.get("checkpoint_sequence_complete") is True
        and pipe_before is not None
        and pipe_after is not None
        and pipe_output is not None
        and pipe_output.get("result_code") == "WORKER_PIPE_CHILD_READY"
        and (pipe_run.get("effective_job_limits") or {}).get("ActiveProcessLimit") == 3
        and quiescence_ok(pipe_run)
    )
    add_row(
        "FR-WIN-02",
        "DEVNULL-free anonymous-pipe child smoke",
        FR02_ok,
        run=remediation_run_projection(pipe_run),
        worker=pipe_output,
    )
    if not FR02_ok:
        return result("stop_inconclusive", "FR_WIN_02_PIPE_TRANSPORT_MISMATCH")

    job_memory_run = remember(runner.run(
        "job_memory",
        job_memory_limit=True,
        timeout_ms=5000,
        final_remediation_diagnostic=True,
        active_process_limit=4,
        checkpoint_names=["before_first_child", "after_first_child"],
    ))
    job_memory_output = parsed_worker_output(job_memory_run)
    job_memory_before = checkpoint(job_memory_run, "before_first_child")
    job_memory_after = checkpoint(job_memory_run, "after_first_child")
    job_memory_limits = job_memory_run.get("effective_job_limits") or {}
    job_memory_accounting = job_memory_run.get("job_accounting") or {}
    job_memory_stream = job_memory_run.get("output") or {}
    job_memory_messages = job_memory_run.get("job_messages") or []
    job_memory_before_ids = set(
        (job_memory_before or {}).get("job_process_ids", {}).get("process_ids") or []
    )
    job_memory_after_ids = set(
        (job_memory_after or {}).get("job_process_ids", {}).get("process_ids") or []
    )
    job_memory_after_record = (job_memory_after or {}).get("worker_record") or {}
    job_memory_child_pid = job_memory_after_record.get("child_pid")
    job_memory_child_ready: dict[str, object] | None = None
    child_ready_line = job_memory_after_record.get("child_ready_line")
    if isinstance(child_ready_line, str):
        try:
            parsed_child_ready = json.loads(child_ready_line)
        except json.JSONDecodeError:
            parsed_child_ready = None
        if isinstance(parsed_child_ready, dict):
            job_memory_child_ready = parsed_child_ready
    job_memory_pid_delta = job_memory_after_ids - job_memory_before_ids
    peak_job_memory = job_memory_accounting.get("peak_job_memory")
    FR03_ok = bool(
        job_memory_run.get("checkpoint_sequence_complete") is True
        and job_memory_before is not None
        and job_memory_after is not None
        and job_memory_limits.get("ActiveProcessLimit") == 4
        and job_memory_limits.get("JobMemoryLimit") == 100_663_296
        and job_memory_limits.get("LimitFlags") == 9736
        and (job_memory_before.get("job_process_ids") or {}).get("number_of_process_ids_in_list") == 2
        and (job_memory_after.get("job_process_ids") or {}).get("number_of_process_ids_in_list") == 4
        and len(job_memory_before_ids) == 2
        and len(job_memory_after_ids) == 4
        and len(job_memory_pid_delta) == 2
        and isinstance(job_memory_child_pid, int)
        and job_memory_child_pid not in job_memory_before_ids
        and job_memory_child_pid in job_memory_after_ids
        and job_memory_child_ready is not None
        and job_memory_child_ready.get("result_code") == "WORKER_MEMORY_CHILD_READY"
        and job_memory_child_ready.get("allocated_mebibytes") == 48
        and job_memory_output is not None
        and job_memory_output.get("result_code") == "WORKER_JOB_MEMORY_DENIED"
        and JOB_OBJECT_MSG_JOB_MEMORY_LIMIT in job_memory_messages
        and isinstance(peak_job_memory, int)
        and 100_663_296 <= peak_job_memory <= 101_711_872
        and job_memory_stream.get("overflow") is False
        and job_memory_stream.get("reader_errors") == []
        and quiescence_ok(job_memory_run)
    )
    add_row(
        "FR-WIN-03",
        "job_memory_enforcement_after_first_child_topology_proof_with_ActiveProcessLimit_4",
        FR03_ok,
        run=remediation_run_projection(job_memory_run),
        worker=job_memory_output,
    )
    if not FR03_ok:
        return result("stop_inconclusive", "FR_WIN_03_JOB_MEMORY_TOPOLOGY_ENFORCEMENT_MISMATCH")

    active_run = remember(runner.run(
        "active_process",
        timeout_ms=5000,
        final_remediation_diagnostic=True,
        active_process_accounting_diagnostic=True,
        active_process_limit=2,
        checkpoint_names=[
            "before_first_child",
            "after_first_child",
            "before_second_child",
            "after_second_child_attempt",
        ],
    ))
    active_output = parsed_worker_output(active_run)
    active_before = checkpoint(active_run, "before_first_child")
    active_after = checkpoint(active_run, "after_first_child")
    active_before_second = checkpoint(active_run, "before_second_child")
    active_after_second = checkpoint(active_run, "after_second_child_attempt")
    active_limits = active_run.get("effective_job_limits") or {}
    active_stream = active_run.get("output") or {}
    active_messages = active_run.get("job_messages") or []
    active_quiescence = active_run.get("job_quiescence") or {}
    before_inventory = (active_before or {}).get("job_process_ids") or {}
    after_inventory = (active_after or {}).get("job_process_ids") or {}
    before_second_inventory = (active_before_second or {}).get("job_process_ids") or {}
    after_second_inventory = (active_after_second or {}).get("job_process_ids") or {}
    before_list = before_inventory.get("process_ids") or []
    after_list = after_inventory.get("process_ids") or []
    before_second_list = before_second_inventory.get("process_ids") or []
    after_second_list = after_second_inventory.get("process_ids") or []
    before_ids = set(before_list)
    after_ids = set(after_list)
    before_second_ids = set(before_second_list)
    after_second_ids = set(after_second_list)
    after_record = (active_after or {}).get("worker_record") or {}
    first_pid = after_record.get("child_pid")
    first_ready = False
    first_ready_line = after_record.get("child_ready_line")
    if isinstance(first_ready_line, str):
        try:
            first_ready_value = json.loads(first_ready_line)
        except json.JSONDecodeError:
            first_ready_value = None
        first_ready = bool(
            isinstance(first_ready_value, dict)
            and first_ready_value.get("result_code") == "WORKER_CHILD_SLEEP_READY"
            and first_ready_value.get("pid") == first_pid
        )

    def unique_positive_PID_list(values: object) -> bool:
        return bool(
            isinstance(values, list)
            and all(
                isinstance(value, int) and not isinstance(value, bool) and value > 0
                for value in values
            )
            and len(values) == len(set(values))
        )

    first_PID_delta = after_ids - before_ids
    FR04_ok = bool(
        active_run.get("checkpoint_sequence_complete") is True
        and active_before is not None
        and active_after is not None
        and active_before_second is not None
        and active_after_second is not None
        and active_limits.get("ActiveProcessLimit") == 2
        and active_limits.get("LimitFlags") == 9224
        and unique_positive_PID_list(before_list)
        and len(before_list) > 0
        and before_inventory.get("number_of_process_ids_in_list") == len(before_list)
        and unique_positive_PID_list(after_list)
        and unique_positive_PID_list(before_second_list)
        and unique_positive_PID_list(after_second_list)
        and isinstance(first_pid, int)
        and not isinstance(first_pid, bool)
        and first_pid > 0
        and first_ready
        and first_pid not in before_ids
        and first_pid in after_ids
        and first_pid in before_second_ids
        and len(first_PID_delta) > 0
        and first_pid in first_PID_delta
        and before_second_ids == after_ids
    )
    add_row(
        "FR-WIN-04",
        "ActiveProcessLimit control, first-child readiness, and physical PID evidence without a charge-count claim",
        FR04_ok,
        before_first_child=active_before,
        after_first_child=active_after,
        before_second_child=active_before_second,
        after_second_child_attempt=active_after_second,
        first_child_PID=first_pid,
        first_child_readiness=first_ready,
        after_first_minus_before_first_PID_delta=sorted(first_PID_delta),
        run=remediation_run_projection(active_run),
    )
    if not FR04_ok:
        return result("stop_inconclusive", "FR_WIN_04_ACTIVE_PROCESS_CONTROL_MISMATCH")

    active_steps = active_output.get("popen_steps") if active_output else None
    second_steps = [
        value
        for value in (active_steps if isinstance(active_steps, list) else [])
        if isinstance(value, dict) and value.get("step") == "active_process_second_child"
    ]
    second_created = bool(len(second_steps) == 1 and second_steps[0].get("result") == "created")
    second_denied = bool(len(second_steps) == 1 and second_steps[0].get("result") == "denied")
    second_PID = active_output.get("second_popen_returned_pid") if isinstance(active_output, dict) else None
    second_exit_code = active_output.get("second_exit_code") if isinstance(active_output, dict) else None
    second_exception = active_output.get("second_exception") if isinstance(active_output, dict) else None
    second_exception_bounded = bool(
        isinstance(second_exception, dict)
        and set(second_exception) == {
            "scenario",
            "operation_step",
            "exception_type",
            "message",
            "args",
            "winerror",
            "errno",
        }
        and isinstance(second_exception.get("message"), str)
        and len(second_exception["message"]) <= 526
        and isinstance(second_exception.get("args"), list)
        and len(second_exception["args"]) <= 8
        and all(isinstance(value, str) and len(value) <= 270 for value in second_exception["args"])
    )
    second_stdout = active_output.get("second_stdout") if isinstance(active_output, dict) else None
    second_stderr = active_output.get("second_stderr") if isinstance(active_output, dict) else None
    second_output_bounded = bool(
        isinstance(second_stdout, str)
        and len(second_stdout) <= 526
        and isinstance(second_stderr, str)
        and len(second_stderr) <= 526
        and isinstance(active_output.get("second_stdout_bytes"), int)
        and isinstance(active_output.get("second_stderr_bytes"), int)
    ) if isinstance(active_output, dict) else False
    second_marker_absent = bool(
        isinstance(active_output, dict)
        and active_output.get("second_execution_marker_count") == 0
        and active_output.get("second_execution_markers") == []
    )
    second_PID_absent_after = bool(not isinstance(second_PID, int) or second_PID not in after_second_ids)
    final_process_ids = (active_quiescence.get("final_process_ids") or {}).get("process_ids") or []
    second_PID_absent_final = bool(not isinstance(second_PID, int) or second_PID not in final_process_ids)
    exact_limit_message = active_messages.count(JOB_OBJECT_MSG_ACTIVE_PROCESS_LIMIT) == 1
    denied_disposition = bool(
        second_denied
        and second_steps[0].get("pid") is None
        and second_PID is None
        and second_exit_code is None
        and second_exception_bounded
        and second_exception.get("exception_type") == "OSError"
    )
    created_then_terminated_disposition = bool(
        second_created
        and isinstance(second_steps[0].get("pid"), int)
        and not isinstance(second_steps[0].get("pid"), bool)
        and second_steps[0]["pid"] > 0
        and second_PID == second_steps[0]["pid"]
        and isinstance(second_exit_code, int)
        and not isinstance(second_exit_code, bool)
        and second_output_bounded
        and second_marker_absent
        and second_PID_absent_after
        and second_PID_absent_final
    )
    FR05_ok = bool(
        active_output is not None
        and active_output.get("result_code") == "WORKER_ACTIVE_PROCESS_ACCOUNTING_OBSERVED"
        and len(second_steps) == 1
        and active_output.get("second_observation_timeout") is False
        and exact_limit_message
        and second_marker_absent
        and second_PID_absent_after
        and second_PID_absent_final
        and active_stream.get("overflow") is False
        and active_stream.get("reader_errors") == []
        and quiescence_ok(active_run)
        and (denied_disposition or created_then_terminated_disposition)
    )
    add_row(
        "FR-WIN-05",
        "exact second-child ActiveProcessLimit enforcement proof",
        FR05_ok,
        worker=active_output,
        disposition=(
            "Popen_raises_OSError_before_PID_publication"
            if denied_disposition
            else "Popen_returns_PID_then_Job_terminates_before_execution_marker"
            if created_then_terminated_disposition
            else None
        ),
        active_process_limit_message_count=active_messages.count(JOB_OBJECT_MSG_ACTIVE_PROCESS_LIMIT),
        second_PID_absent_after_checkpoint=second_PID_absent_after,
        second_PID_absent_final_inventory=second_PID_absent_final,
        run=remediation_run_projection(active_run),
    )
    if not FR05_ok:
        return result("stop_inconclusive", "FR_WIN_05_ACTIVE_PROCESS_DENIAL_MISMATCH")

    tree_run = remember(runner.run(
        "tree",
        terminate_on_ready=True,
        timeout_ms=5000,
        final_remediation_diagnostic=True,
        active_process_limit=3,
        checkpoint_names=["before_tree_child", "after_tree_child"],
    ))
    tree_output = parsed_worker_output(tree_run)
    tree_before = checkpoint(tree_run, "before_tree_child")
    tree_after = checkpoint(tree_run, "after_tree_child")
    tree_limits = tree_run.get("effective_job_limits") or {}
    tree_stream = tree_run.get("output") or {}
    tree_messages = tree_run.get("job_messages") or []
    tree_quiescence = tree_run.get("job_quiescence") or {}
    tree_before_inventory = (tree_before or {}).get("job_process_ids") or {}
    tree_after_inventory = (tree_after or {}).get("job_process_ids") or {}
    tree_before_list = tree_before_inventory.get("process_ids") or []
    tree_after_list = tree_after_inventory.get("process_ids") or []
    tree_before_ids = set(tree_before_list)
    tree_after_ids = set(tree_after_list)
    tree_PID_delta = tree_after_ids - tree_before_ids
    tree_target_PID = tree_run.get("process_id")
    tree_after_record = (tree_after or {}).get("worker_record") or {}
    tree_checkpoint_child_PID = tree_after_record.get("child_pid")
    tree_checkpoint_ready: dict[str, object] | None = None
    tree_checkpoint_ready_line = tree_after_record.get("child_ready_line")
    if isinstance(tree_checkpoint_ready_line, str):
        try:
            parsed_tree_checkpoint_ready = json.loads(tree_checkpoint_ready_line)
        except json.JSONDecodeError:
            parsed_tree_checkpoint_ready = None
        if isinstance(parsed_tree_checkpoint_ready, dict):
            tree_checkpoint_ready = parsed_tree_checkpoint_ready
    tree_worker_ready: dict[str, object] | None = None
    tree_worker_ready_line = tree_output.get("child_line") if isinstance(tree_output, dict) else None
    if isinstance(tree_worker_ready_line, str):
        try:
            parsed_tree_worker_ready = json.loads(tree_worker_ready_line)
        except json.JSONDecodeError:
            parsed_tree_worker_ready = None
        if isinstance(parsed_tree_worker_ready, dict):
            tree_worker_ready = parsed_tree_worker_ready
    tree_steps = tree_output.get("popen_steps") if isinstance(tree_output, dict) else None
    tree_child_steps = [
        value
        for value in (tree_steps if isinstance(tree_steps, list) else [])
        if isinstance(value, dict) and value.get("step") == "tree_child"
    ]
    tree_child_step = tree_child_steps[0] if len(tree_child_steps) == 1 else None
    tree_child_PID = tree_output.get("child_pid") if isinstance(tree_output, dict) else None
    tree_checkpoint_names = [
        value.get("name")
        for value in (tree_run.get("checkpoint_telemetry") or [])
        if isinstance(value, dict)
    ]
    FR06_ok = bool(
        tree_run.get("checkpoint_sequence_complete") is True
        and tree_before is not None
        and tree_after is not None
        and tree_checkpoint_names == ["before_tree_child", "after_tree_child"]
        and tree_limits.get("ActiveProcessLimit") == 3
        and tree_limits.get("LimitFlags") == 9224
        and unique_positive_PID_list(tree_before_list)
        and unique_positive_PID_list(tree_after_list)
        and len(tree_before_list) > 0
        and len(tree_after_list) > 0
        and tree_before_inventory.get("number_of_process_ids_in_list") == len(tree_before_list)
        and tree_after_inventory.get("number_of_process_ids_in_list") == len(tree_after_list)
        and isinstance(tree_target_PID, int)
        and not isinstance(tree_target_PID, bool)
        and tree_target_PID > 0
        and tree_target_PID in tree_before_ids
        and tree_target_PID in tree_after_ids
        and tree_child_step is not None
        and tree_child_step.get("result") == "created"
        and isinstance(tree_child_step.get("pid"), int)
        and not isinstance(tree_child_step.get("pid"), bool)
        and tree_child_step["pid"] > 0
        and tree_child_PID == tree_child_step["pid"]
        and tree_checkpoint_child_PID == tree_child_PID
        and tree_child_PID not in tree_before_ids
        and tree_child_PID in tree_after_ids
        and len(tree_PID_delta) > 0
        and tree_child_PID in tree_PID_delta
        and tree_checkpoint_ready is not None
        and tree_checkpoint_ready.get("result_code") == "WORKER_CHILD_SLEEP_READY"
        and tree_checkpoint_ready.get("pid") == tree_child_PID
        and tree_output is not None
        and tree_output.get("result_code") == "WORKER_TREE_READY"
        and tree_output.get("worker_pid") == tree_target_PID
        and tree_output.get("child_pid") == tree_child_PID
        and tree_worker_ready is not None
        and tree_worker_ready.get("result_code") == "WORKER_CHILD_SLEEP_READY"
        and tree_worker_ready.get("pid") == tree_child_PID
        and tree_run.get("ready_seen") is True
        and tree_run.get("termination_reason") == "owned_tree_cancel"
        and tree_run.get("exit_code") == 57349
        and tree_stream.get("overflow") is False
        and tree_stream.get("reader_errors") == []
        and tree_messages.count(JOB_OBJECT_MSG_ACTIVE_PROCESS_ZERO) == 1
        and tree_quiescence.get("quiescent") is True
        and tree_quiescence.get("deadline_expired") is False
        and tree_quiescence.get("active_process_zero_message_seen") is True
        and (tree_quiescence.get("final_accounting") or {}).get("active_process_zero") is True
        and tree_quiescence.get("final_PID_inventory_empty") is True
        and tree_run.get("inactive_after_termination") is True
        and quiescence_ok(tree_run)
    )
    add_row(
        "FR-WIN-06",
        "owned_process_tree_execution_cancellation_and_final_Job_quiescence_without_raw_PID_charge_count_claim",
        FR06_ok,
        worker=tree_output,
        before_tree_child=tree_before,
        after_tree_child=tree_after,
        child_readiness=tree_checkpoint_ready,
        after_minus_before_PID_delta=sorted(tree_PID_delta),
        active_process_zero_message_count=tree_messages.count(JOB_OBJECT_MSG_ACTIVE_PROCESS_ZERO),
        run=remediation_run_projection(tree_run),
    )
    if not FR06_ok:
        return result("stop_inconclusive", "FR_WIN_06_PROCESS_TREE_MISMATCH")

    cpu_run = remember(runner.run(
        "cpu",
        timeout_ms=5000,
        process_time_limit=False,
        final_remediation_diagnostic=True,
        active_process_limit=None,
        defer_process_time_limit_until_assigned=False,
        live_companion_attribution_diagnostic=True,
        trusted_cpu_watchdog_enabled=True,
        trusted_cpu_budget_100ns=10_000_000,
        trusted_cpu_poll_interval_ms=20,
        trusted_cpu_maximum_final_user_time_100ns=15_000_000,
        require_non_nested_target=True,
        completion_quiet_window_ms=250,
    ))
    cpu_process_id = cpu_run.get("process_id")
    cpu_times = cpu_run.get("target_process_times") or {}
    cpu_limits = cpu_run.get("effective_job_limits") or {}
    cpu_watchdog = cpu_run.get("trusted_cpu_watchdog") or {}
    cpu_membership = cpu_run.get("job_membership") or {}
    cpu_quiescence = cpu_run.get("job_quiescence") or {}
    cpu_stream = cpu_run.get("output") or {}
    cpu_live = cpu_run.get("live_attribution") or {}
    cpu_captures = cpu_live.get("captured_processes") or []
    for captured in cpu_captures:
        if isinstance(captured, dict):
            captured_pid = captured.get("notification_PID")
            if isinstance(captured_pid, int) and captured_pid > 0:
                child_pids.add(captured_pid)
    cpu_target_captures = [
        value for value in cpu_captures
        if isinstance(value, dict)
        and value.get("relationship") == "target"
        and value.get("notification_PID") == cpu_process_id
    ]
    cpu_companion_captures = [
        value for value in cpu_captures
        if isinstance(value, dict) and value.get("relationship") == "companion_candidate"
    ]
    cpu_uncontracted_captures = [
        value for value in cpu_captures
        if isinstance(value, dict) and value.get("relationship") == "uncontracted_process"
    ]
    cpu_target_capture = cpu_target_captures[0] if len(cpu_target_captures) == 1 else {}
    cpu_companion_capture = cpu_companion_captures[0] if len(cpu_companion_captures) == 1 else {}
    cpu_completion_events = cpu_quiescence.get("messages") or []
    cpu_new_process_pids = sorted(
        int(event.get("process_id_value"))
        for event in cpu_completion_events
        if isinstance(event, dict)
        and event.get("message") == JOB_OBJECT_MSG_NEW_PROCESS
        and isinstance(event.get("process_id_value"), int)
        and int(event.get("process_id_value")) > 0
    )
    cpu_captured_pids = sorted(
        int(value.get("notification_PID"))
        for value in cpu_captures
        if isinstance(value, dict)
        and isinstance(value.get("notification_PID"), int)
        and int(value.get("notification_PID")) > 0
    )
    cpu_target_end_events = [
        event for event in cpu_completion_events
        if isinstance(event, dict)
        and event.get("message") == JOB_OBJECT_MSG_END_OF_PROCESS_TIME
        and event.get("process_id_value") == cpu_process_id
    ]
    cpu_initial_sample = cpu_watchdog.get("initial_sample") or {}
    cpu_previous_sample = cpu_watchdog.get("previous_sample") or {}
    cpu_trigger_sample = cpu_watchdog.get("trigger_sample") or {}
    cpu_final_sample = cpu_watchdog.get("final_sample") or {}
    cpu_termination = cpu_watchdog.get("termination") or {}
    cpu_previous_user_time = cpu_previous_sample.get("user_time_100ns")
    cpu_trigger_user_time = cpu_trigger_sample.get("user_time_100ns")
    cpu_final_user_time = cpu_final_sample.get("user_time_100ns")
    FR07_ok = bool(
        cpu_run.get("created_suspended") is True
        and cpu_run.get("assigned_before_resume") is True
        and cpu_run.get("resume_called") is True
        and cpu_run.get("use_appcontainer") is True
        and cpu_membership.get("target_in_any_Job_before_owned_assignment") is False
        and cpu_membership.get("target_in_owned_Job_before_assignment") is False
        and cpu_membership.get("target_in_owned_Job_after_assignment") is True
        and cpu_limits.get("LimitFlags") == (
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION
        )
        and not (int(cpu_limits.get("LimitFlags", 0)) & JOB_OBJECT_LIMIT_PROCESS_TIME)
        and cpu_limits.get("PerProcessUserTimeLimit") == 0
        and cpu_limits.get("ActiveProcessLimit") == 0
        and cpu_limits.get("QueryInformationJobObject_result") == 1
        and cpu_limits.get("QueryInformationJobObject_last_error") == 0
        and cpu_limits.get("QueryInformationJobObject_returned_length") == 144
        and cpu_watchdog.get("enabled") is True
        and cpu_watchdog.get("armed_before_ResumeThread") is True
        and cpu_watchdog.get("retained_original_target_process_handle") is True
        and cpu_watchdog.get("reopened_target_by_PID") is False
        and cpu_watchdog.get("expected_target_process_id") == cpu_process_id
        and cpu_watchdog.get("handle_process_id") == cpu_process_id
        and cpu_watchdog.get("CPU_budget_100ns") == 10_000_000
        and cpu_watchdog.get("poll_interval_ms") == 20
        and cpu_watchdog.get("maximum_accepted_final_target_user_time_100ns") == 15_000_000
        and cpu_watchdog.get("wall_fail_safe_deadline_ms") == 5000
        and cpu_watchdog.get("resume_thread_call_count") == 1
        and cpu_watchdog.get("all_GetProcessTimes_calls_successful") is True
        and cpu_watchdog.get("failure_reason") is None
        and cpu_initial_sample.get("phase") == "armed_before_resume"
        and cpu_initial_sample.get("GetProcessTimes_BOOL") is True
        and cpu_initial_sample.get("process_active_state") is True
        and isinstance(cpu_previous_user_time, int)
        and not isinstance(cpu_previous_user_time, bool)
        and cpu_previous_user_time < 10_000_000
        and isinstance(cpu_trigger_user_time, int)
        and not isinstance(cpu_trigger_user_time, bool)
        and cpu_trigger_user_time >= 10_000_000
        and isinstance(cpu_final_user_time, int)
        and not isinstance(cpu_final_user_time, bool)
        and 10_000_000 <= cpu_final_user_time <= 15_000_000
        and cpu_final_user_time >= cpu_trigger_user_time
        and cpu_watchdog.get("CPU_overshoot_100ns") == cpu_final_user_time - 10_000_000
        and cpu_watchdog.get("trigger_CPU_overshoot_100ns") == cpu_trigger_user_time - 10_000_000
        and cpu_termination.get("reason") == "trusted_cpu_watchdog_limit"
        and cpu_termination.get("exit_code") == 0xEE45
        and cpu_termination.get("TerminateJobObject_BOOL") is True
        and cpu_termination.get("immediate_GetLastError") == 0
        and cpu_watchdog.get("termination_wait_result") == WAIT_OBJECT_0
        and cpu_run.get("termination_reason") == "trusted_cpu_watchdog_limit"
        and cpu_run.get("inactive_after_termination") is True
        and cpu_times.get("user_time_100ns") == cpu_final_user_time
        and len(cpu_target_end_events) == 0
        and len(cpu_target_captures) == 1
        and cpu_target_capture.get("TokenIsAppContainer") is True
        and cpu_target_capture.get("AppContainer_SID") == sid_string
        and cpu_target_capture.get("capability_count") == 0
        and cpu_target_capture.get("explicit_assignment_by_diagnostic") is True
        and len(cpu_companion_captures) == 1
        and str(cpu_companion_capture.get("normalized_executable_image_path", "")).casefold()
        == "c:/windows/system32/conhost.exe"
        and cpu_companion_capture.get("parent_PID") == cpu_process_id
        and cpu_companion_capture.get("TokenIsAppContainer") is True
        and cpu_companion_capture.get("AppContainer_SID") == sid_string
        and cpu_companion_capture.get("capability_count") == 0
        and cpu_companion_capture.get("explicit_assignment_by_diagnostic") is False
        and cpu_companion_capture.get("inherited_owned_Job_membership_evidence") is True
        and cpu_companion_capture.get("live_owned_Job_membership") is True
        and cpu_live.get("blocker") is None
        and not cpu_uncontracted_captures
        and len(cpu_new_process_pids) == 2
        and len(set(cpu_new_process_pids)) == 2
        and cpu_new_process_pids == cpu_captured_pids
        and cpu_process_id in cpu_new_process_pids
        and cpu_stream.get("overflow") is False
        and cpu_stream.get("reader_errors") == []
        and cpu_quiescence.get("deadline_expired") is False
        and cpu_quiescence.get("active_process_zero_message_seen") is True
        and cpu_quiescence.get("quiet_window_ms") == 250
        and cpu_quiescence.get("quiet_window_completed") is True
        and cpu_quiescence.get("final_PID_inventory_empty") is True
        and (cpu_quiescence.get("final_accounting") or {}).get("active_process_zero") is True
        and cpu_quiescence.get("quiescent") is True
        and quiescence_ok(cpu_run)
    )
    add_row(
        "FR-WIN-07",
        "trusted_target_user_time_CPU_watchdog_enforcement_with_retained_handle_and_owned_Job_fail_closed_termination",
        FR07_ok,
        target_END_OF_PROCESS_TIME_message_count=len(cpu_target_end_events),
        live_NEW_PROCESS_PIDs=cpu_new_process_pids,
        live_attributed_PIDs=cpu_captured_pids,
        target_capture_count=len(cpu_target_captures),
        companion_capture_count=len(cpu_companion_captures),
        uncontracted_process_count=len(cpu_uncontracted_captures),
        run=trusted_cpu_watchdog_run_projection(cpu_run),
    )
    if not FR07_ok:
        return result("stop_inconclusive", "FR_WIN_07_TRUSTED_CPU_WATCHDOG_MISMATCH")

    def capture_network_watchdog_successor(
        family: str,
        host: str,
        port: int,
        listener_index: int,
    ) -> tuple[bool, dict[str, object]]:
        endpoint_arguments = ["--family", family, "--host", host, "--port", str(port)]
        positive_run = remember(runner.run(
            "native_winsock",
            endpoint_arguments,
            final_remediation_diagnostic=True,
            active_process_limit=2,
            use_appcontainer=False,
        ))
        positive_worker = parsed_worker_output(positive_run)
        positive_terminal = native_winsock_terminal_disposition(positive_worker)
        positive_accept_count = listener_accept_count(listeners[listener_index])
        positive_output = positive_run.get("output") or {}
        positive_ok = bool(
            positive_worker is not None
            and positive_worker.get("result_code") == "WORKER_NATIVE_WINSOCK_DIAGNOSTIC"
            and positive_worker.get("family") == family
            and positive_worker.get("endpoint") == {"host": host, "port": port}
            and positive_terminal.get("projection_blocker") is None
            and positive_terminal.get("disposition") in {
                "connected_immediate",
                "connected_after_pending",
            }
            and positive_terminal.get("final_SO_ERROR_authoritative") is True
            and positive_worker.get("final_SO_ERROR") == 0
            and positive_accept_count == 1
            and positive_run.get("created_suspended") is True
            and positive_run.get("assigned_before_resume") is True
            and positive_run.get("resume_called") is True
            and positive_run.get("exit_code") == 0
            and positive_run.get("inactive_after_termination") is True
            and positive_output.get("overflow") is False
            and positive_output.get("reader_errors") == []
            and quiescence_ok(positive_run)
        )
        positive_evidence = {
            "passed": positive_ok,
            "worker": positive_worker,
            "terminal_disposition": positive_terminal,
            "listener_accept_count": positive_accept_count,
            "run": trusted_pending_connect_watchdog_run_projection(positive_run),
        }
        if not positive_ok:
            return False, {
                "architecture": "trusted_pending_connect_watchdog_enforcement",
                "native_WSAEACCES_proven": False,
                "positive_control": positive_evidence,
                "AppContainer_watchdog": None,
            }

        watchdog_run = remember(runner.run(
            "native_winsock",
            endpoint_arguments,
            timeout_ms=5000,
            process_time_limit=False,
            process_memory_limit=False,
            job_memory_limit=False,
            final_remediation_diagnostic=True,
            live_companion_attribution_diagnostic=True,
            trusted_pending_connect_watchdog_enabled=True,
            trusted_pending_connect_listener=listeners[listener_index],
            use_appcontainer=True,
            active_process_limit=2,
            completion_quiet_window_ms=250,
        ))
        watchdog_process_id = watchdog_run.get("process_id")
        watchdog_identity = watchdog_run.get("identity") or {}
        watchdog_output = watchdog_run.get("output") or {}
        watchdog_limits = watchdog_run.get("effective_job_limits") or {}
        watchdog_membership = watchdog_run.get("job_membership") or {}
        watchdog_quiescence = watchdog_run.get("job_quiescence") or {}
        watchdog = watchdog_run.get("trusted_pending_connect_watchdog") or {}
        live = watchdog_run.get("live_attribution") or {}
        captures = live.get("captured_processes") or []
        for captured in captures:
            if isinstance(captured, dict):
                captured_pid = captured.get("notification_PID")
                if isinstance(captured_pid, int) and captured_pid > 0:
                    child_pids.add(captured_pid)
        target_captures = [
            value for value in captures
            if isinstance(value, dict)
            and value.get("relationship") == "target"
            and value.get("notification_PID") == watchdog_process_id
        ]
        companion_captures = [
            value for value in captures
            if isinstance(value, dict) and value.get("relationship") == "companion_candidate"
        ]
        uncontracted_captures = [
            value for value in captures
            if isinstance(value, dict) and value.get("relationship") == "uncontracted_process"
        ]
        target_capture = target_captures[0] if len(target_captures) == 1 else {}
        companion_capture = companion_captures[0] if len(companion_captures) == 1 else {}
        completion_events = watchdog_quiescence.get("messages") or []
        new_process_pids = sorted(
            int(event.get("process_id_value"))
            for event in completion_events
            if isinstance(event, dict)
            and event.get("message") == JOB_OBJECT_MSG_NEW_PROCESS
            and isinstance(event.get("process_id_value"), int)
            and int(event.get("process_id_value")) > 0
        )
        captured_pids = sorted(
            int(value.get("notification_PID"))
            for value in captures
            if isinstance(value, dict)
            and isinstance(value.get("notification_PID"), int)
            and int(value.get("notification_PID")) > 0
        )
        records = watchdog.get("parent_observed_worker_records") or []
        ready_records = [
            value for value in records
            if isinstance(value, dict)
            and value.get("result_code") == "WORKER_NATIVE_WINSOCK_PENDING_READY"
        ]
        sample_records = [
            value for value in records
            if isinstance(value, dict)
            and value.get("result_code") == "WORKER_NATIVE_WINSOCK_PENDING_SAMPLE"
        ]
        terminal_records = [
            value for value in records
            if isinstance(value, dict)
            and value.get("result_code") == "WORKER_NATIVE_WINSOCK_TERMINAL_OBSERVATION"
        ]
        self_close_records = [
            value for value in records
            if isinstance(value, dict)
            and value.get("result_code") == "WORKER_NATIVE_WINSOCK_SELF_CLOSE"
        ]
        ready = ready_records[0] if len(ready_records) == 1 else {}
        sequences = [value.get("sequence") for value in records if isinstance(value, dict)]
        liveness = watchdog.get("target_liveness_observations") or []
        listener_observations = watchdog.get("listener_accept_observations") or []
        termination = watchdog.get("termination") or {}
        expected_target_image = str(runner.python).replace("\\", "/").casefold()
        watchdog_ok = bool(
            watchdog_run.get("created_suspended") is True
            and watchdog_run.get("assigned_before_resume") is True
            and watchdog_run.get("resume_called") is True
            and watchdog_run.get("use_appcontainer") is True
            and watchdog_run.get("inactive_after_termination") is True
            and watchdog_identity.get("token_is_appcontainer") is True
            and watchdog_identity.get("appcontainer_sid") == sid_string
            and watchdog_identity.get("appcontainer_sid_valid") is True
            and watchdog_identity.get("capability_count") == 0
            and watchdog_membership.get("target_in_owned_Job_before_assignment") is False
            and watchdog_membership.get("target_in_owned_Job_after_assignment") is True
            and watchdog_limits.get("LimitFlags") == (
                JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                | JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION
                | JOB_OBJECT_LIMIT_ACTIVE_PROCESS
            )
            and watchdog_limits.get("ActiveProcessLimit") == 2
            and len(target_captures) == 1
            and str(target_capture.get("normalized_executable_image_path", "")).casefold()
            == expected_target_image
            and target_capture.get("TokenIsAppContainer") is True
            and target_capture.get("AppContainer_SID") == sid_string
            and target_capture.get("capability_count") == 0
            and target_capture.get("explicit_assignment_by_diagnostic") is True
            and target_capture.get("live_owned_Job_membership") is True
            and len(companion_captures) == 1
            and str(companion_capture.get("normalized_executable_image_path", "")).casefold()
            == "c:/windows/system32/conhost.exe"
            and companion_capture.get("parent_PID") == watchdog_process_id
            and companion_capture.get("TokenIsAppContainer") is True
            and companion_capture.get("AppContainer_SID") == sid_string
            and companion_capture.get("capability_count") == 0
            and companion_capture.get("explicit_assignment_by_diagnostic") is False
            and companion_capture.get("inherited_owned_Job_membership_evidence") is True
            and companion_capture.get("live_owned_Job_membership") is True
            and not uncontracted_captures
            and live.get("blocker") is None
            and live.get("target_notification_seen") is True
            and live.get("non_target_notification_count") == 1
            and len(new_process_pids) == 2
            and len(set(new_process_pids)) == 2
            and new_process_pids == captured_pids
            and len(ready_records) == 1
            and ready.get("sequence") == 1
            and ready.get("family") == family
            and ready.get("endpoint") == {"host": host, "port": port}
            and ready.get("WSAStartup_result") == 0
            and ready.get("socket_created") is True
            and ready.get("nonblocking_result") == 0
            and ready.get("immediate_return") == -1
            and ready.get("immediate_WSA_error") == WSAEWOULDBLOCK
            and ready.get("socket_open") is True
            and watchdog.get("pending_ready_count") == 1
            and isinstance(watchdog.get("checkpoint_latency_ms"), int)
            and 0 <= int(watchdog["checkpoint_latency_ms"]) <= 1500
            and watchdog.get("sample_count") == len(sample_records)
            and len(sample_records) > 0
            and sequences == list(range(1, len(records) + 1))
            and all(
                value.get("select_return") == 0
                and value.get("select_WSA_error") == 0
                and value.get("write_ready") is False
                and value.get("exception_ready") is False
                and value.get("socket_open") is True
                for value in sample_records
            )
            and not terminal_records
            and not self_close_records
            and isinstance(watchdog.get("observation_duration_ms"), int)
            and 2500 <= int(watchdog["observation_duration_ms"]) <= 3000
            and isinstance(watchdog.get("maximum_parent_observed_sample_gap_ms"), int)
            and int(watchdog["maximum_parent_observed_sample_gap_ms"]) <= 250
            and isinstance(watchdog.get("last_sample_age_before_termination_ms"), int)
            and int(watchdog["last_sample_age_before_termination_ms"]) <= 250
            and watchdog.get("listener_accept_count_total") == 0
            and listener_observations != []
            and all(
                value.get("observed_accept_count") == 0
                and value.get("cumulative_accept_count") == 0
                for value in listener_observations
            )
            and liveness != []
            and all(value.get("target_active") is True for value in liveness)
            and termination.get("reason") == "trusted_pending_connect_watchdog_deadline"
            and termination.get("exit_code") == 0xEE51
            and termination.get("TerminateJobObject_BOOL") is True
            and termination.get("immediate_GetLastError") == 0
            and watchdog.get("termination_wait_result") == WAIT_OBJECT_0
            and watchdog.get("target_exit_code") == 0xEE51
            and watchdog.get("failure_reason") is None
            and watchdog_run.get("termination_reason") == "trusted_pending_connect_watchdog_deadline"
            and watchdog_run.get("exit_code") == 0xEE51
            and watchdog_output.get("overflow") is False
            and watchdog_output.get("reader_errors") == []
            and (watchdog_run.get("job_messages") or []).count(
                JOB_OBJECT_MSG_ACTIVE_PROCESS_ZERO
            ) == 1
            and watchdog_quiescence.get("deadline_expired") is False
            and watchdog_quiescence.get("active_process_zero_message_seen") is True
            and watchdog_quiescence.get("quiet_window_ms") == 250
            and watchdog_quiescence.get("quiet_window_completed") is True
            and watchdog_quiescence.get("final_PID_inventory_empty") is True
            and (watchdog_quiescence.get("final_accounting") or {}).get(
                "active_process_zero"
            ) is True
            and watchdog_quiescence.get("quiescent") is True
            and quiescence_ok(watchdog_run)
        )
        watchdog_evidence = {
            "passed": watchdog_ok,
            "pending_ready_count": len(ready_records),
            "sample_count": len(sample_records),
            "sample_sequence_contiguous": sequences == list(range(1, len(records) + 1)),
            "terminal_observation_count": len(terminal_records),
            "worker_self_close_count": len(self_close_records),
            "listener_accept_observations": listener_observations,
            "target_liveness_observations": liveness,
            "termination": termination,
            "live_attribution": live,
            "uncontracted_process_count": len(uncontracted_captures),
            "live_NEW_PROCESS_PIDs": new_process_pids,
            "live_attributed_PIDs": captured_pids,
            "run": trusted_pending_connect_watchdog_run_projection(watchdog_run),
        }
        return positive_ok and watchdog_ok, {
            "architecture": "trusted_pending_connect_watchdog_enforcement",
            "native_WSAEACCES_proven": False,
            "positive_control": positive_evidence,
            "AppContainer_watchdog": watchdog_evidence,
        }

    FR08_ok, FR08_evidence = capture_network_watchdog_successor(
        "IPv4",
        args.ipv4_host,
        args.ipv4_port,
        0,
    )
    add_row(
        "FR-WIN-08",
        "IPv4 trusted_pending_connect_watchdog_enforcement",
        FR08_ok,
        **FR08_evidence,
    )
    if not FR08_ok:
        return result(
            "stop_inconclusive",
            "FR_WIN_08_TRUSTED_PENDING_CONNECT_WATCHDOG_MISMATCH",
        )

    FR09_ok, FR09_evidence = capture_network_watchdog_successor(
        "IPv6",
        args.ipv6_host,
        args.ipv6_port,
        1,
    )
    add_row(
        "FR-WIN-09",
        "IPv6 trusted_pending_connect_watchdog_enforcement",
        FR09_ok,
        **FR09_evidence,
    )
    if not FR09_ok:
        return result(
            "stop_inconclusive",
            "FR_WIN_09_TRUSTED_PENDING_CONNECT_WATCHDOG_MISMATCH",
        )
    return result(
        "final_remediation_diagnostic_pass_candidate_pending_read_only_review",
        "FINAL_REMEDIATION_DIAGNOSTIC_CAPTURED",
    )


def capture_active_process_accounting_diagnostic(
    runner: JobRun,
    child_pids: set[int],
    canary: Path,
    canary_before: str,
) -> dict[str, object]:
    rows: list[dict[str, object]] = []

    def add_row(case_id: str, purpose: str, passed: bool, **evidence: object) -> None:
        rows.append({"id": case_id, "purpose": purpose, "passed": passed, "evidence": evidence})

    def checkpoint(run: dict[str, object], name: str) -> dict[str, object] | None:
        matches = [
            value
            for value in (run.get("checkpoint_telemetry") or [])
            if isinstance(value, dict) and value.get("name") == name
        ]
        return matches[0] if len(matches) == 1 else None

    run = runner.run(
        "active_process",
        timeout_ms=5000,
        active_process_accounting_diagnostic=True,
        active_process_limit=2,
        checkpoint_names=[
            "before_first_child",
            "after_first_child",
            "before_second_child",
            "after_second_child_attempt",
        ],
    )
    process_id = run.get("process_id")
    if isinstance(process_id, int):
        child_pids.add(process_id)
    records = parsed_worker_records(run)
    child_pids.update(worker_record_pids(records))
    worker = parsed_worker_output(run)
    before_first = checkpoint(run, "before_first_child")
    after_first = checkpoint(run, "after_first_child")
    before_second = checkpoint(run, "before_second_child")
    after_second = checkpoint(run, "after_second_child_attempt")
    limits = run.get("effective_job_limits") or {}
    output = run.get("output") or {}
    messages = run.get("job_messages") or []
    quiescence = run.get("job_quiescence") or {}

    before_ids = set((before_first or {}).get("job_process_ids", {}).get("process_ids") or [])
    after_first_ids = set((after_first or {}).get("job_process_ids", {}).get("process_ids") or [])
    before_second_ids = set((before_second or {}).get("job_process_ids", {}).get("process_ids") or [])
    after_second_ids = set((after_second or {}).get("job_process_ids", {}).get("process_ids") or [])
    after_first_record = (after_first or {}).get("worker_record") or {}
    after_second_record = (after_second or {}).get("worker_record") or {}
    first_pid = after_first_record.get("child_pid")
    second_pid = worker.get("second_popen_returned_pid") if isinstance(worker, dict) else None
    first_ready = False
    first_ready_line = after_first_record.get("child_ready_line")
    if isinstance(first_ready_line, str):
        try:
            first_ready_value = json.loads(first_ready_line)
        except json.JSONDecodeError:
            first_ready_value = None
        first_ready = bool(
            isinstance(first_ready_value, dict)
            and first_ready_value.get("result_code") == "WORKER_CHILD_SLEEP_READY"
            and first_ready_value.get("pid") == first_pid
        )

    limits_ok = bool(limits.get("ActiveProcessLimit") == 2 and limits.get("LimitFlags") == 9224)
    add_row(
        "AP-WIN-01",
        "effective ActiveProcessLimit and LimitFlags readback",
        limits_ok,
        effective_job_limits=limits,
    )

    baseline_inventory_ok = bool(
        before_first is not None
        and len(before_ids) == len((before_first.get("job_process_ids") or {}).get("process_ids") or [])
        and (before_first.get("job_process_ids") or {}).get("number_of_process_ids_in_list") == len(before_ids)
        and len(before_ids) > 0
    )
    add_row(
        "AP-WIN-02",
        "before-first-child inventory and baseline PID set",
        baseline_inventory_ok,
        before_first_child=before_first,
        baseline_PID_set=sorted(before_ids),
    )

    first_child_ok = bool(
        run.get("checkpoint_sequence_complete") is True
        and after_first is not None
        and before_second is not None
        and after_second is not None
        and isinstance(first_pid, int)
        and first_ready
        and first_pid not in before_ids
        and first_pid in after_first_ids
        and first_pid in before_second_ids
    )
    add_row(
        "AP-WIN-03",
        "first-child Popen readiness and explicit PID presence",
        first_child_ok,
        first_pid=first_pid,
        first_child_ready=first_ready,
        checkpoint_names=[
            value.get("name") for value in (run.get("checkpoint_telemetry") or []) if isinstance(value, dict)
        ],
    )

    inventory_ok = bool(
        len(after_first_ids) == len((after_first or {}).get("job_process_ids", {}).get("process_ids") or [])
        and len(before_second_ids) == len((before_second or {}).get("job_process_ids", {}).get("process_ids") or [])
        and len(after_second_ids) == len((after_second or {}).get("job_process_ids", {}).get("process_ids") or [])
        and after_first_ids - before_ids
        and before_second_ids == after_first_ids
    )
    add_row(
        "AP-WIN-04",
        "after-first-child physical inventory and PID delta without charge-count claim",
        inventory_ok,
        before_first=before_first,
        after_first=after_first,
        before_second=before_second,
        after_second=after_second,
        deltas={
            "after_first_minus_before_first": sorted(after_first_ids - before_ids),
            "after_second_minus_before_second": sorted(after_second_ids - before_second_ids),
            "before_second_minus_after_second": sorted(before_second_ids - after_second_ids),
        },
    )

    steps = worker.get("popen_steps") if isinstance(worker, dict) else None
    second_steps = [
        value
        for value in (steps if isinstance(steps, list) else [])
        if isinstance(value, dict) and value.get("step") == "active_process_second_child"
    ]
    second_created = bool(len(second_steps) == 1 and second_steps[0].get("result") == "created")
    second_denied = bool(len(second_steps) == 1 and second_steps[0].get("result") == "denied")
    second_observation_ok = bool(
        isinstance(worker, dict)
        and worker.get("result_code") == "WORKER_ACTIVE_PROCESS_ACCOUNTING_OBSERVED"
        and len(second_steps) == 1
        and worker.get("second_observation_timeout") is False
        and (
            (second_denied and second_pid is None and isinstance(worker.get("second_exception"), dict))
            or (second_created and isinstance(second_pid, int) and isinstance(worker.get("second_exit_code"), int))
        )
    )
    add_row(
        "AP-WIN-05",
        "bounded second-child Popen and completion disposition",
        second_observation_ok,
        worker=worker,
        run=remediation_run_projection(run),
    )

    message_ok = JOB_OBJECT_MSG_ACTIVE_PROCESS_LIMIT in messages
    add_row(
        "AP-WIN-06",
        "explicit JOB_OBJECT_MSG_ACTIVE_PROCESS_LIMIT evidence",
        message_ok,
        job_messages=messages,
    )

    marker_absent = bool(isinstance(worker, dict) and worker.get("second_execution_marker_count") == 0)
    no_persistent_second_pid = bool(not isinstance(second_pid, int) or second_pid not in after_second_ids)
    denial_ok = bool(marker_absent and no_persistent_second_pid)
    add_row(
        "AP-WIN-07",
        "second-child execution marker absent and no persistent second PID",
        denial_ok,
        second_pid=second_pid,
        second_execution_marker_count=worker.get("second_execution_marker_count") if isinstance(worker, dict) else None,
        after_second_process_ids=sorted(after_second_ids),
    )

    quiescence_ok = bool(
        output.get("overflow") is False
        and output.get("reader_errors") == []
        and quiescence.get("quiescent") is True
        and quiescence.get("active_process_zero_message_seen") is True
        and quiescence.get("final_PID_inventory_empty") is True
        and (quiescence.get("final_accounting") or {}).get("active_process_zero") is True
        and run.get("inactive_after_termination") is True
    )
    passed = len(rows) == 7 and all(value.get("passed") is True for value in rows)
    return {
        "schema": "pipeline-v2.k0b03-v2-windows-active-process-accounting-diagnostic-v1",
        "attempt": "A",
        "status": (
            "active_process_accounting_diagnostic_pass_candidate_pending_read_only_review"
            if passed else "stop_inconclusive"
        ),
        "result_code": (
            "ACTIVE_PROCESS_ACCOUNTING_DIAGNOSTIC_CAPTURED"
            if passed else "ACTIVE_PROCESS_LIMIT_ENFORCEMENT_NOT_PROVEN"
        ),
        "qualification_result": None,
        "matrix_expected_count": 8,
        "rows": rows,
        "canary_unchanged_before_cleanup": canary.is_file() and file_pin(canary)["sha256"] == canary_before,
        "job_quiescence_verified_before_cleanup": quiescence_ok,
        "job_quiescence_evidence": quiescence,
    }


def qualify(args: argparse.Namespace) -> dict[str, object]:
    native = Native()
    root = Path(args.root)
    sandbox = root / "sandbox"
    runtime = sandbox / "runtime"
    sandbox_tmp = sandbox / "tmp"
    sandbox_worker = sandbox / "windows-enforcement-capability-worker.py"
    write_control = sandbox / "write-control.bin"
    canary_dir = root / "host-canary"
    canary = canary_dir / "read-only-canary.bin"
    parent_evidence = root / "parent-evidence"
    source_worker = Path(args.worker)
    source_python = Path(PYTHON_PATH)
    projected_python = runtime / "python.exe"
    projection_request = Path(args.projection_request)
    parent = root.parent
    profile_created = False
    sid = ct.c_void_p()
    sid_string = None
    sandbox_snapshot: SecurityDescriptorSnapshot | None = None
    parent_before = SecurityDescriptorSnapshot(native, parent)
    listeners: list[socket.socket] = []
    child_pids: set[int] = set()
    cases: list[dict[str, object]] = []
    cleanup_errors: list[dict[str, object]] = []
    identity_diagnostic: dict[str, object] | None = None
    case_remediation_diagnostic: dict[str, object] | None = None
    final_remediation_diagnostic: dict[str, object] | None = None
    active_process_accounting_diagnostic: dict[str, object] | None = None
    process_time_control_diagnostic: dict[str, object] | None = None
    live_companion_attribution_diagnostic: dict[str, object] | None = None
    non_nested_process_time_causal_diagnostic: dict[str, object] | None = None
    appcontainer_process_time_information_class_control_diagnostic: dict[str, object] | None = None
    process_time_enforcement_repeatability_diagnostic: dict[str, object] | None = None
    assigned_suspended_target_flag_preservation_diagnostic: dict[str, object] | None = None
    trusted_cpu_watchdog_diagnostic: dict[str, object] | None = None
    native_winsock_isolation_control_diagnostic: dict[str, object] | None = None
    trusted_pending_connect_watchdog_diagnostic: dict[str, object] | None = None
    projection_materialization: dict[str, object] | None = None
    bfe_before = native.bfe_state()
    exemptions_before = native.loopback_exemptions()
    canary_bytes = b"pipeline-v2-host-canary-v1\n"
    canary_before = sha256_bytes(canary_bytes)
    started = time.monotonic()
    try:
        python_pin = file_pin(source_python)
        projection_contract = load_projection_contract(projection_request)
        firewall_pin = file_pin(Path("C:/Windows/System32/FirewallAPI.dll"))
        host_ok = (
            python_pin["sha256"] == PYTHON_SHA256
            and python_pin["bytes"] == PYTHON_BYTES
            and firewall_pin["sha256"] == FIREWALL_API_SHA256
            and firewall_pin["bytes"] == FIREWALL_API_BYTES
            and bfe_before["running"]
        )
        cases.append(case("CP-WIN-01", "host_API_ABI_and_binary_pins", "PASS_HOST_API_ABI_PINS", host_ok,
                          python_pin=python_pin, firewall_pin=firewall_pin, BFE=bfe_before,
                          pointer_bytes=ct.sizeof(ct.c_void_p), structure_sizes={
                              "STARTUPINFOW": ct.sizeof(STARTUPINFOW),
                              "STARTUPINFOEXW": ct.sizeof(STARTUPINFOEXW),
                              "PROCESS_INFORMATION": ct.sizeof(PROCESS_INFORMATION),
                              "SECURITY_CAPABILITIES": ct.sizeof(SECURITY_CAPABILITIES),
                              "JOBOBJECT_EXTENDED_LIMIT_INFORMATION": ct.sizeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION),
                          }))
        if not host_ok:
            raise ProbeStop("HOST_PIN_OR_BFE_MISMATCH", args.attempt)
        if root.exists():
            raise ProbeStop("ROOT_ALREADY_EXISTS", str(root))
        derived = ct.c_void_p()
        derive_result = int(native.userenv.DeriveAppContainerSidFromAppContainerName(args.profile, ct.byref(derived)))
        if hresult_failed(derive_result):
            raise ProbeStop("PROFILE_PREFLIGHT_DERIVE_FAILED", args.profile, hresult_unsigned(derive_result))
        try:
            derived_text = native.sid_string(derived)
        finally:
            native.advapi32.FreeSid(derived)
        mapping_exists, package_folder = profile_registry_and_folder(derived_text)
        if mapping_exists or package_folder.exists():
            raise ProbeStop("PROFILE_NAMESPACE_EXISTS", args.profile)
        if not (
            args.process_time_control_diagnostic_only
            or args.live_companion_attribution_diagnostic_only
            or args.non_nested_process_time_causal_diagnostic_only
            or args.appcontainer_process_time_information_class_control_diagnostic_only
            or args.process_time_enforcement_repeatability_diagnostic_only
            or args.assigned_suspended_target_flag_preservation_diagnostic_only
            or args.trusted_cpu_watchdog_diagnostic_only
        ):
            listeners = [
                exclusive_listener(socket.AF_INET, args.ipv4_host, args.ipv4_port),
                exclusive_listener(socket.AF_INET6, args.ipv6_host, args.ipv6_port),
            ]
        cases.append(case("CP-WIN-02", "root_profile_port_namespace_preflight", "PASS_NAMESPACE_PREFLIGHT", True,
                          root_absent=True, profile_mapping_absent=True, package_folder_absent=True,
                          endpoints=[] if (
                              args.process_time_control_diagnostic_only
                              or args.live_companion_attribution_diagnostic_only
                              or args.non_nested_process_time_causal_diagnostic_only
                              or args.appcontainer_process_time_information_class_control_diagnostic_only
                              or args.process_time_enforcement_repeatability_diagnostic_only
                              or args.assigned_suspended_target_flag_preservation_diagnostic_only
                              or args.trusted_cpu_watchdog_diagnostic_only
                          ) else [
                              f"{args.ipv4_host}:{args.ipv4_port}",
                              f"[{args.ipv6_host}]:{args.ipv6_port}",
                          ]))

        sid, sid_string = create_profile(native, args.profile)
        profile_created = True
        if sid_string in native.loopback_exemptions():
            raise ProbeStop("PROFILE_HAS_LOOPBACK_EXEMPTION", sid_string)
        cases.append(case("CP-WIN-03", "temporary_profile_creation_and_SID_identity", "PASS_PROFILE_SID_IDENTITY", True,
                          profile=args.profile, sid=sid_string, zero_network_capabilities_declared=True,
                          loopback_exemptions=exemptions_before))

        sandbox_tmp.mkdir(parents=True)
        canary_dir.mkdir()
        parent_evidence.mkdir()
        shutil.copyfile(source_worker, sandbox_worker)
        if file_pin(source_worker)["sha256"] != file_pin(sandbox_worker)["sha256"]:
            raise ProbeStop("WORKER_COPY_MISMATCH", str(sandbox_worker))
        projection_materialization = materialize_projection(projection_contract, runtime)
        canary.write_bytes(canary_bytes)
        sandbox_snapshot = SecurityDescriptorSnapshot(native, sandbox)
        apply_sandbox_acl(native, sandbox_snapshot, sid)

        cases[-1]["evidence"]["runtime_projection"] = projection_materialization
        runner = JobRun(native, sid, sandbox, projected_python, sandbox_worker)
        if args.trusted_pending_connect_watchdog_diagnostic_only:
            if args.attempt != "A":
                raise ProbeStop(
                    "TRUSTED_PENDING_CONNECT_WATCHDOG_DIAGNOSTIC_ATTEMPT_FORBIDDEN",
                    args.attempt,
                )
            trusted_pending_connect_watchdog_diagnostic = (
                capture_trusted_pending_connect_watchdog_diagnostic(
                    runner,
                    args,
                    sid_string,
                    listeners,
                    child_pids,
                    canary,
                    canary_before,
                )
            )
            raise TrustedPendingConnectWatchdogDiagnosticComplete()
        if args.native_winsock_isolation_control_diagnostic_only:
            if args.attempt != "A":
                raise ProbeStop(
                    "NATIVE_WINSOCK_ISOLATION_CONTROL_DIAGNOSTIC_ATTEMPT_FORBIDDEN",
                    args.attempt,
                )
            native_winsock_isolation_control_diagnostic = (
                capture_native_winsock_isolation_control_diagnostic(
                    runner,
                    args,
                    sid_string,
                    listeners,
                    child_pids,
                    canary,
                    canary_before,
                )
            )
            raise NativeWinsockIsolationControlDiagnosticComplete()
        if args.trusted_cpu_watchdog_diagnostic_only:
            if args.attempt != "A":
                raise ProbeStop(
                    "TRUSTED_CPU_WATCHDOG_DIAGNOSTIC_ATTEMPT_FORBIDDEN",
                    args.attempt,
                )
            trusted_cpu_watchdog_diagnostic = capture_trusted_cpu_watchdog_diagnostic(
                runner,
                child_pids,
                canary,
                canary_before,
                args.non_nested_launcher_gate,
            )
            raise TrustedCpuWatchdogDiagnosticComplete()
        if args.assigned_suspended_target_flag_preservation_diagnostic_only:
            if args.attempt != "A":
                raise ProbeStop(
                    "ASSIGNED_SUSPENDED_TARGET_FLAG_PRESERVATION_DIAGNOSTIC_ATTEMPT_FORBIDDEN",
                    args.attempt,
                )
            assigned_suspended_target_flag_preservation_diagnostic = (
                capture_assigned_suspended_target_flag_preservation_diagnostic(
                    runner,
                    child_pids,
                    canary,
                    canary_before,
                    args.non_nested_launcher_gate,
                )
            )
            raise AssignedSuspendedTargetFlagPreservationDiagnosticComplete()
        if args.process_time_enforcement_repeatability_diagnostic_only:
            if args.attempt != "A":
                raise ProbeStop(
                    "PROCESS_TIME_ENFORCEMENT_REPEATABILITY_DIAGNOSTIC_ATTEMPT_FORBIDDEN",
                    args.attempt,
                )
            process_time_enforcement_repeatability_diagnostic = (
                capture_process_time_enforcement_repeatability_diagnostic(
                    runner,
                    child_pids,
                    canary,
                    canary_before,
                    args.non_nested_launcher_gate,
                )
            )
            raise AppContainerProcessTimeInformationClassControlDiagnosticComplete()
        if args.appcontainer_process_time_information_class_control_diagnostic_only:
            if args.attempt != "A":
                raise ProbeStop(
                    "APPCONTAINER_PROCESS_TIME_INFORMATION_CLASS_CONTROL_DIAGNOSTIC_ATTEMPT_FORBIDDEN",
                    args.attempt,
                )
            appcontainer_process_time_information_class_control_diagnostic = (
                capture_appcontainer_process_time_information_class_control_diagnostic(
                    runner,
                    child_pids,
                    canary,
                    canary_before,
                    args.non_nested_launcher_gate,
                )
            )
            raise AppContainerProcessTimeInformationClassControlDiagnosticComplete()
        if args.non_nested_process_time_causal_diagnostic_only:
            if args.attempt != "A":
                raise ProbeStop("NON_NESTED_PROCESS_TIME_DIAGNOSTIC_ATTEMPT_FORBIDDEN", args.attempt)
            non_nested_process_time_causal_diagnostic = capture_non_nested_process_time_causal_diagnostic(
                runner,
                child_pids,
                canary,
                canary_before,
                args.non_nested_launcher_gate,
            )
            raise NonNestedProcessTimeCausalDiagnosticComplete()
        if args.live_companion_attribution_diagnostic_only:
            if args.attempt != "A":
                raise ProbeStop("LIVE_COMPANION_ATTRIBUTION_DIAGNOSTIC_ATTEMPT_FORBIDDEN", args.attempt)
            live_companion_attribution_diagnostic = capture_live_companion_attribution_diagnostic(
                runner,
                child_pids,
                canary,
                canary_before,
            )
            raise LiveCompanionAttributionDiagnosticComplete()
        if args.process_time_control_diagnostic_only:
            if args.attempt != "A":
                raise ProbeStop("PROCESS_TIME_CONTROL_DIAGNOSTIC_ATTEMPT_FORBIDDEN", args.attempt)
            process_time_control_diagnostic = capture_process_time_control_diagnostic(
                runner,
                child_pids,
                canary,
                canary_before,
            )
            raise ProcessTimeControlDiagnosticComplete()
        if args.active_process_accounting_diagnostic_only:
            if args.attempt != "A":
                raise ProbeStop("ACTIVE_PROCESS_ACCOUNTING_DIAGNOSTIC_ATTEMPT_FORBIDDEN", args.attempt)
            active_process_accounting_diagnostic = capture_active_process_accounting_diagnostic(
                runner,
                child_pids,
                canary,
                canary_before,
            )
            raise ActiveProcessAccountingDiagnosticComplete()
        if args.final_remediation_diagnostic_only:
            if args.attempt != "A":
                raise ProbeStop("FINAL_REMEDIATION_DIAGNOSTIC_ATTEMPT_FORBIDDEN", args.attempt)
            final_remediation_diagnostic = capture_final_remediation_diagnostic(
                runner,
                args,
                sid_string,
                listeners,
                child_pids,
                canary,
                canary_before,
                args.non_nested_launcher_gate,
            )
            raise FinalRemediationDiagnosticComplete()
        if args.case_remediation_diagnostic_only:
            if args.attempt != "A":
                raise ProbeStop("CASE_REMEDIATION_DIAGNOSTIC_ATTEMPT_FORBIDDEN", args.attempt)
            case_remediation_diagnostic = capture_case_remediation_diagnostic(
                runner,
                args,
                sid_string,
                listeners,
                child_pids,
            )
            raise CaseRemediationDiagnosticComplete()
        forced_abort_run = runner.run("identity", force_abort_before_job_assignment=True)
        child_pids.add(forced_abort_run["process_id"])
        forced_abort_components = {
            "created_suspended": forced_abort_run["created_suspended"] is True,
            "not_assigned_before_resume": forced_abort_run["assigned_before_resume"] is False,
            "resume_not_called": forced_abort_run["resume_called"] is False,
            "direct_termination_before_resume": forced_abort_run["direct_termination_before_resume"] is True,
            "inactive_after_termination": forced_abort_run["inactive_after_termination"] is True,
            "exact_AppContainer_SID": forced_abort_run["identity"]["appcontainer_sid"] == sid_string,
            "AppContainer_SID_valid": forced_abort_run["identity"]["appcontainer_sid_valid"] is True,
            "zero_capabilities": forced_abort_run["identity"]["capability_count"] == 0,
            "process_inactive": not process_active(native, forced_abort_run["process_id"]),
        }
        forced_abort_ok = all(forced_abort_components.values())
        if args.identity_diagnostic_only:
            identity_run = runner.run("identity")
        else:
            identity_run = runner.run("identity", qualification_quiescence_required=True)
        child_pids.add(identity_run["process_id"])
        identity_output = parsed_worker_output(identity_run)
        identity_ok = bool(
            identity_output
            and identity_output.get("result_code") == "WORKER_IDENTITY"
            and identity_output.get("token_is_appcontainer") is True
            and identity_output.get("appcontainer_sid") == sid_string
            and identity_output.get("capability_count") == 0
            and identity_run["identity"]["appcontainer_sid"] == sid_string
            and identity_run["identity"]["capability_count"] == 0
        )
        if args.identity_diagnostic_only:
            worker_error = identity_output if identity_output and identity_output.get("result_code") == "WORKER_ERROR" else None
            diagnostic_output = identity_run["output"]
            disclosure_ok = bool(
                diagnostic_output["retained_prefix_bytes"] <= 4096
                and diagnostic_output["total_bytes"] <= 4096
                and diagnostic_output["overflow"] is False
                and diagnostic_output["reader_errors"] == []
            )
            if not disclosure_ok:
                raise ProbeStop(
                    "DIAGNOSTIC_OUTPUT_DISCLOSURE_LIMIT_EXCEEDED",
                    canonical({
                        "retained_prefix_bytes": diagnostic_output["retained_prefix_bytes"],
                        "total_bytes": diagnostic_output["total_bytes"],
                        "overflow": diagnostic_output["overflow"],
                        "reader_errors": diagnostic_output["reader_errors"],
                    }),
                )
            diagnostic_text = diagnostic_output["text_prefix"]
            identity_diagnostic = {
                "typed_result_code": "IDENTITY_DIAGNOSTIC_CAPTURED",
                "parent_identity": identity_run["identity"],
                "worker_first_parsed_JSON_object": identity_output,
                "worker_result_code": identity_output.get("result_code") if identity_output else None,
                "worker_error": {
                    "exception_type": worker_error.get("exception_type"),
                    "message": worker_error.get("message"),
                    "winerror": worker_error.get("winerror"),
                    "errno": worker_error.get("errno"),
                } if worker_error else None,
                "worker_process": {
                    "exit_code": identity_run["exit_code"],
                    "termination_reason": identity_run["termination_reason"],
                    "created_suspended": identity_run["created_suspended"],
                    "assigned_before_resume": identity_run["assigned_before_resume"],
                    "resume_called": identity_run["resume_called"],
                    "active_process_zero": identity_run["job_accounting"]["active_process_zero"],
                    "job_messages": identity_run["job_messages"],
                    "job_accounting": identity_run["job_accounting"],
                },
                "worker_output": {
                    "total_bytes": identity_run["output"]["total_bytes"],
                    "retained_prefix_bytes": identity_run["output"]["retained_prefix_bytes"],
                    "full_stream_sha256": identity_run["output"]["full_stream_sha256"],
                    "prefix_sha256": identity_run["output"]["prefix_sha256"],
                    "overflow": identity_run["output"]["overflow"],
                    "reader_errors": identity_run["output"]["reader_errors"],
                    "text_prefix": diagnostic_text,
                    "text_prefix_decoding": "utf-8-errors-replace",
                    "replacement_character_count": diagnostic_text.count("\ufffd"),
                },
                "runtime_projection": {
                    "request_pin": projection_materialization["request_pin"],
                    "path_count": projection_materialization["path_count"],
                    "content_bytes": projection_materialization["content_bytes"],
                    "manifest_bytes": projection_materialization["manifest_bytes"],
                    "manifest_sha256": projection_materialization["manifest_sha256"],
                    "python312_pth": projection_materialization["python312_pth"],
                    "projected_python": projection_materialization["projected_python"],
                },
                "forced_pre_Job_abort": {
                    "identity": forced_abort_run["identity"],
                    "created_suspended": forced_abort_run["created_suspended"],
                    "assigned_before_resume": forced_abort_run["assigned_before_resume"],
                    "resume_called": forced_abort_run["resume_called"],
                    "direct_termination_before_resume": forced_abort_run["direct_termination_before_resume"],
                    "inactive_after_termination": forced_abort_run["inactive_after_termination"],
                    "result_ok": forced_abort_ok,
                },
                "identity_predicate_result": identity_ok,
            }
            raise IdentityDiagnosticComplete()
        cases.append(case("CP-WIN-04", "child_AppContainer_token_exact_SID_and_zero_capabilities", "PASS_CHILD_APPCONTAINER_ZERO_CAPABILITIES", identity_ok,
                          parent_token_observation=identity_run["identity"], worker_token_observation=identity_output))
        identity_quiescence = identity_run.get("job_quiescence") or {}
        identity_final_accounting = identity_quiescence.get("final_accounting") or {}
        identity_final_process_ids = identity_quiescence.get("final_process_ids") or {}
        identity_quiescence_components = {
            "created_suspended": identity_run.get("created_suspended") is True,
            "assigned_before_resume": identity_run.get("assigned_before_resume") is True,
            "resume_called": identity_run.get("resume_called") is True,
            "target_inactive": identity_run.get("inactive_after_termination") is True,
            "quiescence_deadline_not_expired": identity_quiescence.get("deadline_expired") is False,
            "ACTIVE_PROCESS_ZERO_message_seen": identity_quiescence.get("active_process_zero_message_seen") is True,
            "final_ActiveProcesses_zero": identity_final_accounting.get("active_process_zero") is True,
            "final_PID_inventory_empty": identity_quiescence.get("final_PID_inventory_empty") is True,
            "quiescent": identity_quiescence.get("quiescent") is True,
        }
        cp_win_05_ok = bool(
            forced_abort_ok
            and all(identity_quiescence_components.values())
        )
        forced_abort_projection = {
            "scenario": forced_abort_run.get("scenario"),
            "created_suspended": forced_abort_run.get("created_suspended"),
            "assigned_before_resume": forced_abort_run.get("assigned_before_resume"),
            "resume_called": forced_abort_run.get("resume_called"),
            "direct_termination_before_resume": forced_abort_run.get("direct_termination_before_resume"),
            "inactive_after_termination": forced_abort_run.get("inactive_after_termination"),
            "identity": forced_abort_run.get("identity"),
            "process_id": forced_abort_run.get("process_id"),
            "exit_code": forced_abort_run.get("exit_code"),
            "termination_reason": forced_abort_run.get("termination_reason"),
            "output": bounded_output_projection(forced_abort_run.get("output")),
        }
        identity_quiescence_projection = {
            "deadline_ms": identity_quiescence.get("deadline_ms"),
            "deadline_expired": identity_quiescence.get("deadline_expired"),
            "poll_count": identity_quiescence.get("poll_count"),
            "active_process_zero_message_seen": identity_quiescence.get("active_process_zero_message_seen"),
            "quiet_window_ms": identity_quiescence.get("quiet_window_ms"),
            "quiet_window_completed": identity_quiescence.get("quiet_window_completed"),
            "ordered_Job_messages": identity_quiescence.get("messages"),
            "accounting_snapshots": identity_quiescence.get("accounting_snapshots"),
            "final_accounting": identity_final_accounting,
            "final_process_ids": identity_final_process_ids,
            "final_PID_inventory_empty": identity_quiescence.get("final_PID_inventory_empty"),
            "quiescent": identity_quiescence.get("quiescent"),
        }
        cases.append(case("CP-WIN-05", "suspended_launch_Job_assignment_before_resume", "PASS_SUSPENDED_ASSIGN_RESUME_ORDER",
                          cp_win_05_ok,
                          forced_pre_Job_abort_result_code="PASS_FORCED_PRE_JOB_ABORT_TERMINATE_BEFORE_RESUME_ZERO_RESIDUE" if forced_abort_ok else "FAILED_FORCED_PRE_JOB_ABORT_TERMINATE_BEFORE_RESUME_ZERO_RESIDUE",
                          predicate_components={
                              "forced_abort": forced_abort_components,
                              "normal_identity": identity_quiescence_components,
                          },
                          forced_pre_Job_abort=forced_abort_projection,
                          run=identity_run,
                          worker=identity_output,
                          identity_quiescence=identity_quiescence_projection))
        if not identity_ok:
            raise ProbeStop("CHILD_IDENTITY_PROOF_FAILED", args.attempt)

        write_run = runner.run("sandbox_write", ["--target", str(write_control)])
        child_pids.add(write_run["process_id"])
        write_output = parsed_worker_output(write_run)
        write_ok = bool(write_output and write_output.get("result_code") == "WORKER_SANDBOX_WRITE" and write_control.is_file())
        cases.append(case("CP-WIN-06", "permitted_sandbox_write_control", "PASS_SANDBOX_WRITE_CONTROL", write_ok,
                          worker=write_output, output=write_run["output"], file=file_pin(write_control) if write_control.exists() else None))

        canary_run = runner.run("canary_write", ["--target", str(canary)])
        child_pids.add(canary_run["process_id"])
        canary_output = parsed_worker_output(canary_run)
        canary_after = file_pin(canary)
        canary_ok = bool(canary_output and canary_output.get("result_code") == "WORKER_CANARY_WRITE_DENIED" and canary_after["sha256"] == canary_before)
        cases.append(case("CP-WIN-07", "protected_host_canary_write_denial", "BLOCKED_HOST_CANARY_WRITE", canary_ok,
                          worker=canary_output, canary=canary_after))

        wall_run = runner.run("sleep", timeout_ms=1500)
        child_pids.add(wall_run["process_id"])
        wall_ok = wall_run["termination_reason"] == "wall_timeout" and wall_run["job_accounting"]["active_process_zero"]
        cases.append(case("CP-WIN-08", "wall_timeout_enforcement", "BLOCKED_WALL_TIMEOUT", wall_ok, run=wall_run))

        cpu_run = runner.run(
            "cpu",
            timeout_ms=5000,
            process_time_limit=False,
            final_remediation_diagnostic=True,
            active_process_limit=None,
            defer_process_time_limit_until_assigned=False,
            live_companion_attribution_diagnostic=True,
            trusted_cpu_watchdog_enabled=True,
            trusted_cpu_budget_100ns=10_000_000,
            trusted_cpu_poll_interval_ms=20,
            trusted_cpu_maximum_final_user_time_100ns=15_000_000,
            require_non_nested_target=True,
            completion_quiet_window_ms=250,
        )
        cpu_process_id = cpu_run.get("process_id")
        if isinstance(cpu_process_id, int) and cpu_process_id > 0:
            child_pids.add(cpu_process_id)
        child_pids.update(worker_record_pids(parsed_worker_records(cpu_run)))
        cpu_times = cpu_run.get("target_process_times") or {}
        cpu_limits = cpu_run.get("effective_job_limits") or {}
        cpu_watchdog = cpu_run.get("trusted_cpu_watchdog") or {}
        cpu_membership = cpu_run.get("job_membership") or {}
        cpu_quiescence = cpu_run.get("job_quiescence") or {}
        cpu_stream = cpu_run.get("output") or {}
        cpu_live = cpu_run.get("live_attribution") or {}
        cpu_captures = cpu_live.get("captured_processes") or []
        for captured in cpu_captures:
            if isinstance(captured, dict):
                captured_pid = captured.get("notification_PID")
                if isinstance(captured_pid, int) and captured_pid > 0:
                    child_pids.add(captured_pid)
        cpu_target_captures = [
            value for value in cpu_captures
            if isinstance(value, dict)
            and value.get("relationship") == "target"
            and value.get("notification_PID") == cpu_process_id
        ]
        cpu_companion_captures = [
            value for value in cpu_captures
            if isinstance(value, dict) and value.get("relationship") == "companion_candidate"
        ]
        cpu_uncontracted_captures = [
            value for value in cpu_captures
            if isinstance(value, dict) and value.get("relationship") == "uncontracted_process"
        ]
        cpu_target_capture = cpu_target_captures[0] if len(cpu_target_captures) == 1 else {}
        cpu_companion_capture = cpu_companion_captures[0] if len(cpu_companion_captures) == 1 else {}
        cpu_completion_events = cpu_quiescence.get("messages") or []
        cpu_new_process_pids = sorted(
            int(event.get("process_id_value"))
            for event in cpu_completion_events
            if isinstance(event, dict)
            and event.get("message") == JOB_OBJECT_MSG_NEW_PROCESS
            and isinstance(event.get("process_id_value"), int)
            and int(event.get("process_id_value")) > 0
        )
        cpu_captured_pids = sorted(
            int(value.get("notification_PID"))
            for value in cpu_captures
            if isinstance(value, dict)
            and isinstance(value.get("notification_PID"), int)
            and int(value.get("notification_PID")) > 0
        )
        cpu_target_end_events = [
            event for event in cpu_completion_events
            if isinstance(event, dict)
            and event.get("message") == JOB_OBJECT_MSG_END_OF_PROCESS_TIME
            and event.get("process_id_value") == cpu_process_id
        ]
        cpu_initial_sample = cpu_watchdog.get("initial_sample") or {}
        cpu_previous_sample = cpu_watchdog.get("previous_sample") or {}
        cpu_trigger_sample = cpu_watchdog.get("trigger_sample") or {}
        cpu_final_sample = cpu_watchdog.get("final_sample") or {}
        cpu_termination = cpu_watchdog.get("termination") or {}
        cpu_previous_user_time = cpu_previous_sample.get("user_time_100ns")
        cpu_trigger_user_time = cpu_trigger_sample.get("user_time_100ns")
        cpu_final_user_time = cpu_final_sample.get("user_time_100ns")
        cpu_ok = bool(
            cpu_run.get("created_suspended") is True
            and cpu_run.get("assigned_before_resume") is True
            and cpu_run.get("resume_called") is True
            and cpu_run.get("use_appcontainer") is True
            and cpu_membership.get("target_in_any_Job_before_owned_assignment") is False
            and cpu_membership.get("target_in_owned_Job_before_assignment") is False
            and cpu_membership.get("target_in_owned_Job_after_assignment") is True
            and cpu_limits.get("LimitFlags") == (
                JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION
            )
            and not (int(cpu_limits.get("LimitFlags", 0)) & JOB_OBJECT_LIMIT_PROCESS_TIME)
            and cpu_limits.get("PerProcessUserTimeLimit") == 0
            and cpu_limits.get("ActiveProcessLimit") == 0
            and cpu_limits.get("QueryInformationJobObject_result") == 1
            and cpu_limits.get("QueryInformationJobObject_last_error") == 0
            and cpu_limits.get("QueryInformationJobObject_returned_length") == 144
            and cpu_watchdog.get("enabled") is True
            and cpu_watchdog.get("armed_before_ResumeThread") is True
            and cpu_watchdog.get("retained_original_target_process_handle") is True
            and cpu_watchdog.get("reopened_target_by_PID") is False
            and cpu_watchdog.get("expected_target_process_id") == cpu_process_id
            and cpu_watchdog.get("handle_process_id") == cpu_process_id
            and cpu_watchdog.get("CPU_budget_100ns") == 10_000_000
            and cpu_watchdog.get("poll_interval_ms") == 20
            and cpu_watchdog.get("maximum_accepted_final_target_user_time_100ns") == 15_000_000
            and cpu_watchdog.get("wall_fail_safe_deadline_ms") == 5000
            and cpu_watchdog.get("resume_thread_call_count") == 1
            and cpu_watchdog.get("all_GetProcessTimes_calls_successful") is True
            and cpu_watchdog.get("failure_reason") is None
            and cpu_initial_sample.get("phase") == "armed_before_resume"
            and cpu_initial_sample.get("GetProcessTimes_BOOL") is True
            and cpu_initial_sample.get("process_active_state") is True
            and isinstance(cpu_previous_user_time, int)
            and not isinstance(cpu_previous_user_time, bool)
            and cpu_previous_user_time < 10_000_000
            and isinstance(cpu_trigger_user_time, int)
            and not isinstance(cpu_trigger_user_time, bool)
            and cpu_trigger_user_time >= 10_000_000
            and isinstance(cpu_final_user_time, int)
            and not isinstance(cpu_final_user_time, bool)
            and 10_000_000 <= cpu_final_user_time <= 15_000_000
            and cpu_final_user_time >= cpu_trigger_user_time
            and cpu_watchdog.get("CPU_overshoot_100ns") == cpu_final_user_time - 10_000_000
            and cpu_watchdog.get("trigger_CPU_overshoot_100ns") == cpu_trigger_user_time - 10_000_000
            and cpu_termination.get("reason") == "trusted_cpu_watchdog_limit"
            and cpu_termination.get("exit_code") == 0xEE45
            and cpu_termination.get("TerminateJobObject_BOOL") is True
            and cpu_termination.get("immediate_GetLastError") == 0
            and cpu_watchdog.get("termination_wait_result") == WAIT_OBJECT_0
            and cpu_run.get("termination_reason") == "trusted_cpu_watchdog_limit"
            and cpu_run.get("inactive_after_termination") is True
            and cpu_times.get("user_time_100ns") == cpu_final_user_time
            and len(cpu_target_end_events) == 0
            and len(cpu_target_captures) == 1
            and cpu_target_capture.get("TokenIsAppContainer") is True
            and cpu_target_capture.get("AppContainer_SID") == sid_string
            and cpu_target_capture.get("capability_count") == 0
            and cpu_target_capture.get("explicit_assignment_by_diagnostic") is True
            and len(cpu_companion_captures) == 1
            and str(cpu_companion_capture.get("normalized_executable_image_path", "")).casefold()
            == "c:/windows/system32/conhost.exe"
            and cpu_companion_capture.get("parent_PID") == cpu_process_id
            and cpu_companion_capture.get("TokenIsAppContainer") is True
            and cpu_companion_capture.get("AppContainer_SID") == sid_string
            and cpu_companion_capture.get("capability_count") == 0
            and cpu_companion_capture.get("explicit_assignment_by_diagnostic") is False
            and cpu_companion_capture.get("inherited_owned_Job_membership_evidence") is True
            and cpu_companion_capture.get("live_owned_Job_membership") is True
            and cpu_live.get("blocker") is None
            and not cpu_uncontracted_captures
            and len(cpu_new_process_pids) == 2
            and len(set(cpu_new_process_pids)) == 2
            and cpu_new_process_pids == cpu_captured_pids
            and cpu_process_id in cpu_new_process_pids
            and cpu_stream.get("overflow") is False
            and cpu_stream.get("reader_errors") == []
            and cpu_quiescence.get("deadline_expired") is False
            and cpu_quiescence.get("active_process_zero_message_seen") is True
            and cpu_quiescence.get("quiet_window_ms") == 250
            and cpu_quiescence.get("quiet_window_completed") is True
            and cpu_quiescence.get("final_PID_inventory_empty") is True
            and (cpu_quiescence.get("final_accounting") or {}).get("active_process_zero") is True
            and cpu_quiescence.get("quiescent") is True
        )
        cases.append(case(
            "CP-WIN-09",
            "trusted_target_user_time_CPU_watchdog_enforcement",
            "BLOCKED_TRUSTED_CPU_WATCHDOG",
            cpu_ok,
            architecture="trusted_target_user_time_CPU_watchdog",
            native_END_OF_PROCESS_TIME_proven=False,
            target_END_OF_PROCESS_TIME_message_count=len(cpu_target_end_events),
            live_NEW_PROCESS_PIDs=cpu_new_process_pids,
            live_attributed_PIDs=cpu_captured_pids,
            target_capture_count=len(cpu_target_captures),
            companion_capture_count=len(cpu_companion_captures),
            uncontracted_process_count=len(cpu_uncontracted_captures),
            run=trusted_cpu_watchdog_run_projection(cpu_run),
        ))

        process_memory_run = runner.run("process_memory", ["--mebibytes", "128"], process_memory_limit=True)
        child_pids.add(process_memory_run["process_id"])
        process_memory_output = parsed_worker_output(process_memory_run)
        process_memory_ok = bool(
            (process_memory_output and process_memory_output.get("result_code") == "WORKER_MEMORY_ALLOCATION_DENIED")
            or JOB_OBJECT_MSG_PROCESS_MEMORY_LIMIT in process_memory_run["job_messages"]
        )
        cases.append(case("CP-WIN-10", "process_memory_enforcement", "BLOCKED_PROCESS_MEMORY_LIMIT", process_memory_ok,
                          worker=process_memory_output, run=process_memory_run))

        job_memory_run = runner.run("job_memory", job_memory_limit=True, timeout_ms=5000)
        child_pids.add(job_memory_run["process_id"])
        job_memory_output = parsed_worker_output(job_memory_run)
        job_memory_ok = bool(
            JOB_OBJECT_MSG_JOB_MEMORY_LIMIT in job_memory_run["job_messages"]
            or (job_memory_output and job_memory_output.get("result_code") == "WORKER_JOB_MEMORY_DENIED")
        )
        cases.append(case("CP-WIN-11", "job_memory_enforcement", "BLOCKED_JOB_MEMORY_LIMIT", job_memory_ok,
                          worker=job_memory_output, run=job_memory_run))

        process_count_run = runner.run("active_process", timeout_ms=5000)
        child_pids.add(process_count_run["process_id"])
        process_count_output = parsed_worker_output(process_count_run)
        process_count_ok = bool(
            process_count_output and process_count_output.get("result_code") == "WORKER_SECOND_CHILD_DENIED"
            and (process_count_output.get("winerror") in (None, 1816) or JOB_OBJECT_MSG_ACTIVE_PROCESS_LIMIT in process_count_run["job_messages"])
        )
        cases.append(case("CP-WIN-12", "active_process_count_enforcement", "BLOCKED_ACTIVE_PROCESS_LIMIT", process_count_ok,
                          worker=process_count_output, run=process_count_run))

        output_run = runner.run("output", ["--output-bytes", "131072"], output_limit=65536)
        child_pids.add(output_run["process_id"])
        output_ok = output_run["termination_reason"] == "output_limit" and output_run["output"]["total_bytes"] > 65536
        cases.append(case("CP-WIN-13", "combined_output_enforcement", "BLOCKED_OUTPUT_LIMIT", output_ok, run=output_run))

        tree_run = runner.run("tree", terminate_on_ready=True, timeout_ms=5000)
        child_pids.add(tree_run["process_id"])
        tree_output = parsed_worker_output(tree_run)
        if tree_output and tree_output.get("child_pid"):
            child_pids.add(int(tree_output["child_pid"]))
        tree_ok = tree_run["termination_reason"] == "owned_tree_cancel" and tree_run["job_accounting"]["active_process_zero"]
        cases.append(case("CP-WIN-14", "owned_process_tree_cancellation", "CANCELLED_OWNED_TREE_ACTIVE_PROCESS_ZERO", tree_ok,
                          worker=tree_output, run=tree_run))

        def capture_qualification_network_watchdog_successor(
            family: str,
            host: str,
            port: int,
            listener_index: int,
        ) -> tuple[bool, dict[str, object]]:
            endpoint_arguments = ["--family", family, "--host", host, "--port", str(port)]
            positive_run = runner.run(
                "native_winsock",
                endpoint_arguments,
                final_remediation_diagnostic=True,
                active_process_limit=2,
                use_appcontainer=False,
            )
            positive_process_id = positive_run.get("process_id")
            if isinstance(positive_process_id, int) and positive_process_id > 0:
                child_pids.add(positive_process_id)
            child_pids.update(worker_record_pids(parsed_worker_records(positive_run)))
            positive_worker = parsed_worker_output(positive_run)
            positive_terminal = native_winsock_terminal_disposition(positive_worker)
            positive_accept_count = listener_accept_count(listeners[listener_index])
            positive_output = positive_run.get("output") or {}
            positive_quiescence = positive_run.get("job_quiescence") or {}
            positive_ok = bool(
                positive_worker is not None
                and positive_worker.get("result_code") == "WORKER_NATIVE_WINSOCK_DIAGNOSTIC"
                and positive_worker.get("family") == family
                and positive_worker.get("endpoint") == {"host": host, "port": port}
                and positive_worker.get("immediate_WSA_error") == WSAEWOULDBLOCK
                and positive_terminal.get("projection_blocker") is None
                and positive_terminal.get("disposition") in {
                    "connected_immediate",
                    "connected_after_pending",
                }
                and positive_terminal.get("final_SO_ERROR_authoritative") is True
                and positive_worker.get("final_SO_ERROR") == 0
                and positive_accept_count == 1
                and positive_run.get("created_suspended") is True
                and positive_run.get("assigned_before_resume") is True
                and positive_run.get("resume_called") is True
                and positive_run.get("exit_code") == 0
                and positive_run.get("inactive_after_termination") is True
                and positive_output.get("overflow") is False
                and positive_output.get("reader_errors") == []
                and positive_quiescence.get("deadline_expired") is False
                and positive_quiescence.get("active_process_zero_message_seen") is True
                and positive_quiescence.get("final_PID_inventory_empty") is True
                and (positive_quiescence.get("final_accounting") or {}).get(
                    "active_process_zero"
                ) is True
                and positive_quiescence.get("quiescent") is True
            )
            positive_evidence = {
                "passed": positive_ok,
                "worker": positive_worker,
                "terminal_disposition": positive_terminal,
                "listener_accept_count": positive_accept_count,
                "run": trusted_pending_connect_watchdog_run_projection(positive_run),
            }
            if not positive_ok:
                return False, {
                    "architecture": "trusted_pending_connect_watchdog_enforcement",
                    "native_WSAEACCES_proven": False,
                    "positive_control": positive_evidence,
                    "AppContainer_watchdog": None,
                }

            watchdog_run = runner.run(
                "native_winsock",
                endpoint_arguments,
                timeout_ms=5000,
                process_time_limit=False,
                process_memory_limit=False,
                job_memory_limit=False,
                final_remediation_diagnostic=True,
                live_companion_attribution_diagnostic=True,
                trusted_pending_connect_watchdog_enabled=True,
                trusted_pending_connect_listener=listeners[listener_index],
                use_appcontainer=True,
                active_process_limit=2,
                completion_quiet_window_ms=250,
            )
            watchdog_process_id = watchdog_run.get("process_id")
            if isinstance(watchdog_process_id, int) and watchdog_process_id > 0:
                child_pids.add(watchdog_process_id)
            child_pids.update(worker_record_pids(parsed_worker_records(watchdog_run)))
            watchdog_identity = watchdog_run.get("identity") or {}
            watchdog_output = watchdog_run.get("output") or {}
            watchdog_limits = watchdog_run.get("effective_job_limits") or {}
            watchdog_membership = watchdog_run.get("job_membership") or {}
            watchdog_quiescence = watchdog_run.get("job_quiescence") or {}
            watchdog = watchdog_run.get("trusted_pending_connect_watchdog") or {}
            live = watchdog_run.get("live_attribution") or {}
            captures = live.get("captured_processes") or []
            for captured in captures:
                if isinstance(captured, dict):
                    captured_pid = captured.get("notification_PID")
                    if isinstance(captured_pid, int) and captured_pid > 0:
                        child_pids.add(captured_pid)
            target_captures = [
                value for value in captures
                if isinstance(value, dict)
                and value.get("relationship") == "target"
                and value.get("notification_PID") == watchdog_process_id
            ]
            companion_captures = [
                value for value in captures
                if isinstance(value, dict) and value.get("relationship") == "companion_candidate"
            ]
            uncontracted_captures = [
                value for value in captures
                if isinstance(value, dict) and value.get("relationship") == "uncontracted_process"
            ]
            target_capture = target_captures[0] if len(target_captures) == 1 else {}
            companion_capture = companion_captures[0] if len(companion_captures) == 1 else {}
            completion_events = watchdog_quiescence.get("messages") or []
            new_process_pids = sorted(
                int(event.get("process_id_value"))
                for event in completion_events
                if isinstance(event, dict)
                and event.get("message") == JOB_OBJECT_MSG_NEW_PROCESS
                and isinstance(event.get("process_id_value"), int)
                and int(event.get("process_id_value")) > 0
            )
            captured_pids = sorted(
                int(value.get("notification_PID"))
                for value in captures
                if isinstance(value, dict)
                and isinstance(value.get("notification_PID"), int)
                and int(value.get("notification_PID")) > 0
            )
            records = watchdog.get("parent_observed_worker_records") or []
            ready_records = [
                value for value in records
                if isinstance(value, dict)
                and value.get("result_code") == "WORKER_NATIVE_WINSOCK_PENDING_READY"
            ]
            sample_records = [
                value for value in records
                if isinstance(value, dict)
                and value.get("result_code") == "WORKER_NATIVE_WINSOCK_PENDING_SAMPLE"
            ]
            terminal_records = [
                value for value in records
                if isinstance(value, dict)
                and value.get("result_code") == "WORKER_NATIVE_WINSOCK_TERMINAL_OBSERVATION"
            ]
            self_close_records = [
                value for value in records
                if isinstance(value, dict)
                and value.get("result_code") == "WORKER_NATIVE_WINSOCK_SELF_CLOSE"
            ]
            ready = ready_records[0] if len(ready_records) == 1 else {}
            sequences = [value.get("sequence") for value in records if isinstance(value, dict)]
            liveness = watchdog.get("target_liveness_observations") or []
            listener_observations = watchdog.get("listener_accept_observations") or []
            termination = watchdog.get("termination") or {}
            expected_target_image = str(runner.python).replace("\\", "/").casefold()
            watchdog_ok = bool(
                watchdog_run.get("created_suspended") is True
                and watchdog_run.get("assigned_before_resume") is True
                and watchdog_run.get("resume_called") is True
                and watchdog_run.get("use_appcontainer") is True
                and watchdog_run.get("inactive_after_termination") is True
                and watchdog_identity.get("token_is_appcontainer") is True
                and watchdog_identity.get("appcontainer_sid") == sid_string
                and watchdog_identity.get("appcontainer_sid_valid") is True
                and watchdog_identity.get("capability_count") == 0
                and watchdog_membership.get("target_in_owned_Job_before_assignment") is False
                and watchdog_membership.get("target_in_owned_Job_after_assignment") is True
                and watchdog_limits.get("LimitFlags") == (
                    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                    | JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION
                    | JOB_OBJECT_LIMIT_ACTIVE_PROCESS
                )
                and watchdog_limits.get("ActiveProcessLimit") == 2
                and len(target_captures) == 1
                and str(target_capture.get("normalized_executable_image_path", "")).casefold()
                == expected_target_image
                and target_capture.get("TokenIsAppContainer") is True
                and target_capture.get("AppContainer_SID") == sid_string
                and target_capture.get("capability_count") == 0
                and target_capture.get("explicit_assignment_by_diagnostic") is True
                and target_capture.get("live_owned_Job_membership") is True
                and len(companion_captures) == 1
                and str(companion_capture.get("normalized_executable_image_path", "")).casefold()
                == "c:/windows/system32/conhost.exe"
                and companion_capture.get("parent_PID") == watchdog_process_id
                and companion_capture.get("TokenIsAppContainer") is True
                and companion_capture.get("AppContainer_SID") == sid_string
                and companion_capture.get("capability_count") == 0
                and companion_capture.get("explicit_assignment_by_diagnostic") is False
                and companion_capture.get("inherited_owned_Job_membership_evidence") is True
                and companion_capture.get("live_owned_Job_membership") is True
                and not uncontracted_captures
                and live.get("blocker") is None
                and live.get("target_notification_seen") is True
                and live.get("non_target_notification_count") == 1
                and len(new_process_pids) == 2
                and len(set(new_process_pids)) == 2
                and new_process_pids == captured_pids
                and len(ready_records) == 1
                and ready.get("sequence") == 1
                and ready.get("family") == family
                and ready.get("endpoint") == {"host": host, "port": port}
                and ready.get("WSAStartup_result") == 0
                and ready.get("socket_created") is True
                and ready.get("nonblocking_result") == 0
                and ready.get("immediate_return") == -1
                and ready.get("immediate_WSA_error") == WSAEWOULDBLOCK
                and ready.get("socket_open") is True
                and watchdog.get("pending_ready_count") == 1
                and isinstance(watchdog.get("checkpoint_latency_ms"), int)
                and 0 <= int(watchdog["checkpoint_latency_ms"]) <= 1500
                and watchdog.get("sample_count") == len(sample_records)
                and len(sample_records) > 0
                and sequences == list(range(1, len(records) + 1))
                and all(
                    value.get("select_return") == 0
                    and value.get("select_WSA_error") == 0
                    and value.get("write_ready") is False
                    and value.get("exception_ready") is False
                    and value.get("socket_open") is True
                    for value in sample_records
                )
                and not terminal_records
                and not self_close_records
                and isinstance(watchdog.get("observation_duration_ms"), int)
                and 2500 <= int(watchdog["observation_duration_ms"]) <= 3000
                and isinstance(watchdog.get("maximum_parent_observed_sample_gap_ms"), int)
                and int(watchdog["maximum_parent_observed_sample_gap_ms"]) <= 250
                and isinstance(watchdog.get("last_sample_age_before_termination_ms"), int)
                and int(watchdog["last_sample_age_before_termination_ms"]) <= 250
                and watchdog.get("listener_accept_count_total") == 0
                and listener_observations != []
                and all(
                    value.get("observed_accept_count") == 0
                    and value.get("cumulative_accept_count") == 0
                    for value in listener_observations
                )
                and liveness != []
                and all(value.get("target_active") is True for value in liveness)
                and termination.get("reason") == "trusted_pending_connect_watchdog_deadline"
                and termination.get("exit_code") == 0xEE51
                and termination.get("TerminateJobObject_BOOL") is True
                and termination.get("immediate_GetLastError") == 0
                and watchdog.get("termination_wait_result") == WAIT_OBJECT_0
                and watchdog.get("target_exit_code") == 0xEE51
                and watchdog.get("failure_reason") is None
                and watchdog_run.get("termination_reason")
                == "trusted_pending_connect_watchdog_deadline"
                and watchdog_run.get("exit_code") == 0xEE51
                and watchdog_output.get("overflow") is False
                and watchdog_output.get("reader_errors") == []
                and (watchdog_run.get("job_messages") or []).count(
                    JOB_OBJECT_MSG_ACTIVE_PROCESS_ZERO
                ) == 1
                and watchdog_quiescence.get("deadline_expired") is False
                and watchdog_quiescence.get("active_process_zero_message_seen") is True
                and watchdog_quiescence.get("quiet_window_ms") == 250
                and watchdog_quiescence.get("quiet_window_completed") is True
                and watchdog_quiescence.get("final_PID_inventory_empty") is True
                and (watchdog_quiescence.get("final_accounting") or {}).get(
                    "active_process_zero"
                ) is True
                and watchdog_quiescence.get("quiescent") is True
            )
            watchdog_evidence = {
                "passed": watchdog_ok,
                "pending_ready_count": len(ready_records),
                "sample_count": len(sample_records),
                "sample_sequence_contiguous": sequences == list(range(1, len(records) + 1)),
                "terminal_observation_count": len(terminal_records),
                "worker_self_close_count": len(self_close_records),
                "listener_accept_observations": listener_observations,
                "target_liveness_observations": liveness,
                "termination": termination,
                "live_attribution": live,
                "uncontracted_process_count": len(uncontracted_captures),
                "live_NEW_PROCESS_PIDs": new_process_pids,
                "live_attributed_PIDs": captured_pids,
                "run": trusted_pending_connect_watchdog_run_projection(watchdog_run),
            }
            return positive_ok and watchdog_ok, {
                "architecture": "trusted_pending_connect_watchdog_enforcement",
                "native_WSAEACCES_proven": False,
                "positive_control": positive_evidence,
                "AppContainer_watchdog": watchdog_evidence,
            }

        ipv4_ok, ipv4_evidence = capture_qualification_network_watchdog_successor(
            "IPv4",
            args.ipv4_host,
            args.ipv4_port,
            0,
        )
        cases.append(case(
            "CP-WIN-15",
            "IPv4_trusted_pending_connect_watchdog_enforcement",
            "BLOCKED_TRUSTED_PENDING_CONNECT_WATCHDOG_IPV4",
            ipv4_ok,
            **ipv4_evidence,
        ))

        ipv6_ok, ipv6_evidence = capture_qualification_network_watchdog_successor(
            "IPv6",
            args.ipv6_host,
            args.ipv6_port,
            1,
        )
        cases.append(case(
            "CP-WIN-16",
            "IPv6_trusted_pending_connect_watchdog_enforcement",
            "BLOCKED_TRUSTED_PENDING_CONNECT_WATCHDOG_IPV6",
            ipv6_ok,
            **ipv6_evidence,
        ))

        canary_final = file_pin(canary)
        residue_processes = [pid for pid in sorted(child_pids) if process_active(native, pid)]
        integrity_ok = canary_final["sha256"] == canary_before and not residue_processes
        cases.append(case("CP-WIN-17", "canary_no_write_through_and_attempt_result_determinism", "PASS_CANARY_AND_RESULT_INTEGRITY", integrity_ok,
                          canary=canary_final, active_process_residue=residue_processes,
                          result_projection=result_projection(cases)))
        if not all(value["passed"] for value in cases):
            failed = [value["id"] for value in cases if not value["passed"]]
            raise ProbeStop("CASE_MATRIX_FAILED", canonical(failed_case_diagnostic_projection(cases)))
    except IdentityDiagnosticComplete:
        pass
    except CaseRemediationDiagnosticComplete:
        pass
    except FinalRemediationDiagnosticComplete:
        pass
    except ActiveProcessAccountingDiagnosticComplete:
        pass
    except ProcessTimeControlDiagnosticComplete:
        pass
    except LiveCompanionAttributionDiagnosticComplete:
        pass
    except NonNestedProcessTimeCausalDiagnosticComplete:
        pass
    except AppContainerProcessTimeInformationClassControlDiagnosticComplete:
        pass
    except AssignedSuspendedTargetFlagPreservationDiagnosticComplete:
        pass
    except TrustedCpuWatchdogDiagnosticComplete:
        pass
    except NativeWinsockIsolationControlDiagnosticComplete:
        pass
    except TrustedPendingConnectWatchdogDiagnosticComplete:
        pass
    finally:
        for listener in listeners:
            try:
                listener.close()
            except BaseException as exc:
                cleanup_errors.append({"stage": "listener_close", "type": type(exc).__name__})
        if sandbox_snapshot is not None:
            try:
                sandbox_snapshot.restore_dacl()
                current = SecurityDescriptorSnapshot(native, sandbox)
                try:
                    if current.sddl != sandbox_snapshot.sddl:
                        cleanup_errors.append({"stage": "sandbox_acl_restore_verify", "mismatch": True})
                finally:
                    current.free()
            except BaseException as exc:
                cleanup_errors.append({"stage": "sandbox_acl_restore", "type": type(exc).__name__, "detail": str(exc)})
            finally:
                sandbox_snapshot.free()
        try:
            remove_tree_no_reparse(root)
        except BaseException as exc:
            cleanup_errors.append({"stage": "root_delete", "type": type(exc).__name__, "detail": str(exc)})
        if profile_created:
            try:
                delete_profile(native, args.profile)
            except BaseException as exc:
                cleanup_errors.append({"stage": "profile_delete", "type": type(exc).__name__, "detail": str(exc)})
            finally:
                if sid:
                    native.advapi32.FreeSid(sid)
                    sid = ct.c_void_p()
        try:
            parent_after = SecurityDescriptorSnapshot(native, parent)
            try:
                if parent_after.sddl != parent_before.sddl:
                    cleanup_errors.append({"stage": "parent_security_descriptor_verify", "mismatch": True})
            finally:
                parent_after.free()
        except BaseException as exc:
            cleanup_errors.append({"stage": "parent_security_descriptor_verify", "type": type(exc).__name__, "detail": str(exc)})
        parent_before.free()

    bfe_after = native.bfe_state()
    exemptions_after = native.loopback_exemptions()
    registry_exists = folder_exists = False
    if sid_string:
        registry_exists, profile_folder = profile_registry_and_folder(sid_string)
        folder_exists = profile_folder.exists()
    cleanup_ok = (
        not cleanup_errors
        and not root.exists()
        and not registry_exists
        and not folder_exists
        and exemptions_after == exemptions_before
        and bfe_after["running"]
    )
    if trusted_pending_connect_watchdog_diagnostic is not None:
        process_residue = [pid for pid in sorted(child_pids) if process_active(native, pid)]
        endpoint_rebind_errors: list[dict[str, object]] = []
        rebound: list[socket.socket] = []
        try:
            rebound.append(exclusive_listener(socket.AF_INET, args.ipv4_host, args.ipv4_port))
            rebound.append(exclusive_listener(socket.AF_INET6, args.ipv6_host, args.ipv6_port))
        except BaseException as exc:
            endpoint_rebind_errors.append({
                "type": type(exc).__name__,
                "message": str(exc)[:512],
                "winerror": getattr(exc, "winerror", None),
                "errno": getattr(exc, "errno", None),
            })
        finally:
            for listener in rebound:
                listener.close()
        canary_unchanged = (
            trusted_pending_connect_watchdog_diagnostic.get(
                "canary_unchanged_before_cleanup"
            ) is True
        )
        job_quiescence_verified = (
            trusted_pending_connect_watchdog_diagnostic.get(
                "job_quiescence_verified_before_cleanup"
            ) is True
        )
        residue_count = (
            len(process_residue)
            + int(bool(registry_exists))
            + int(bool(folder_exists))
            + int(root.exists())
            + len(endpoint_rebind_errors)
            + len(cleanup_errors)
        )
        diagnostic_cleanup_ok = bool(
            cleanup_ok
            and canary_unchanged
            and job_quiescence_verified
            and not process_residue
            and not endpoint_rebind_errors
            and residue_count == 0
        )
        trusted_pending_connect_watchdog_diagnostic["cleanup"] = {
            "verified": diagnostic_cleanup_ok,
            "canary_unchanged_before_cleanup": canary_unchanged,
            "job_quiescence_verified_before_cleanup": job_quiescence_verified,
            "process_residue": process_residue,
            "profile_registry_exists": registry_exists,
            "profile_folder_exists": folder_exists,
            "root_exists": root.exists(),
            "listener_socket_endpoint_rebind_errors": endpoint_rebind_errors,
            "sandbox_ACL_restoration_errors": [
                value for value in cleanup_errors
                if str(value.get("stage", "")).startswith("sandbox_acl")
            ],
            "repository_bytecode_residue": "must_be_confirmed_by_post_process_repository_check",
            "cleanup_errors": cleanup_errors,
            "residue_count": residue_count,
        }
        trusted_pending_connect_watchdog_diagnostic["cleanup_verified"] = diagnostic_cleanup_ok
        trusted_pending_connect_watchdog_diagnostic["residue_count"] = residue_count
        trusted_pending_connect_watchdog_diagnostic["root"] = str(root).replace("\\", "/")
        trusted_pending_connect_watchdog_diagnostic["profile_name"] = args.profile
        trusted_pending_connect_watchdog_diagnostic["profile_sid"] = sid_string
        trusted_pending_connect_watchdog_diagnostic["elapsed_ms"] = int(
            (time.monotonic() - started) * 1000
        )
        if not diagnostic_cleanup_ok:
            trusted_pending_connect_watchdog_diagnostic["status"] = "stop_inconclusive"
            trusted_pending_connect_watchdog_diagnostic["result_code"] = (
                "TRUSTED_PENDING_CONNECT_WATCHDOG_DIAGNOSTIC_CLEANUP_FAILED"
            )
        elif (
            trusted_pending_connect_watchdog_diagnostic["result_code"]
            == "TRUSTED_PENDING_CONNECT_WATCHDOG_DIAGNOSTIC_CAPTURED"
            and (
                trusted_pending_connect_watchdog_diagnostic["matrix_actual_count"] != 4
                or trusted_pending_connect_watchdog_diagnostic["passed_count"] != 4
                or trusted_pending_connect_watchdog_diagnostic["failed_count"] != 0
                or trusted_pending_connect_watchdog_diagnostic["errors_count"] != 0
                or trusted_pending_connect_watchdog_diagnostic["skips_count"] != 0
            )
        ):
            trusted_pending_connect_watchdog_diagnostic["status"] = "stop_inconclusive"
            trusted_pending_connect_watchdog_diagnostic["result_code"] = (
                "TRUSTED_PENDING_CONNECT_WATCHDOG_DIAGNOSTIC_ACCOUNTING_MISMATCH"
            )
        return trusted_pending_connect_watchdog_diagnostic
    if native_winsock_isolation_control_diagnostic is not None:
        process_residue = [pid for pid in sorted(child_pids) if process_active(native, pid)]
        endpoint_rebind_errors: list[dict[str, object]] = []
        rebound: list[socket.socket] = []
        try:
            rebound.append(exclusive_listener(socket.AF_INET, args.ipv4_host, args.ipv4_port))
            rebound.append(exclusive_listener(socket.AF_INET6, args.ipv6_host, args.ipv6_port))
        except BaseException as exc:
            endpoint_rebind_errors.append({
                "type": type(exc).__name__,
                "message": str(exc)[:512],
                "winerror": getattr(exc, "winerror", None),
                "errno": getattr(exc, "errno", None),
            })
        finally:
            for listener in rebound:
                listener.close()
        canary_unchanged = (
            native_winsock_isolation_control_diagnostic.get("canary_unchanged_before_cleanup") is True
        )
        job_quiescence_verified = (
            native_winsock_isolation_control_diagnostic.get(
                "job_quiescence_verified_before_cleanup"
            ) is True
        )
        diagnostic_cleanup_ok = bool(
            cleanup_ok
            and canary_unchanged
            and job_quiescence_verified
            and not process_residue
            and not endpoint_rebind_errors
        )
        native_winsock_isolation_control_diagnostic["cleanup"] = {
            "verified": diagnostic_cleanup_ok,
            "canary_unchanged_before_cleanup": canary_unchanged,
            "job_quiescence_verified_before_cleanup": job_quiescence_verified,
            "process_residue": process_residue,
            "profile_registry_exists": registry_exists,
            "profile_folder_exists": folder_exists,
            "root_exists": root.exists(),
            "listener_socket_endpoint_rebind_errors": endpoint_rebind_errors,
            "sandbox_ACL_restoration_errors": [
                value for value in cleanup_errors if str(value.get("stage", "")).startswith("sandbox_acl")
            ],
            "repository_bytecode_residue": "must_be_confirmed_by_post_process_repository_check",
            "cleanup_errors": cleanup_errors,
        }
        native_winsock_isolation_control_diagnostic["cleanup_verified"] = diagnostic_cleanup_ok
        native_winsock_isolation_control_diagnostic["root"] = str(root).replace("\\", "/")
        native_winsock_isolation_control_diagnostic["profile_name"] = args.profile
        native_winsock_isolation_control_diagnostic["profile_sid"] = sid_string
        native_winsock_isolation_control_diagnostic["elapsed_ms"] = int(
            (time.monotonic() - started) * 1000
        )
        if not diagnostic_cleanup_ok:
            native_winsock_isolation_control_diagnostic["status"] = "stop_inconclusive"
            native_winsock_isolation_control_diagnostic["result_code"] = (
                "NATIVE_WINSOCK_CONTROL_DIAGNOSTIC_CLEANUP_FAILED"
            )
        elif (
            native_winsock_isolation_control_diagnostic["matrix_actual_count"] != 4
            or native_winsock_isolation_control_diagnostic["errors_count"] != 0
            or native_winsock_isolation_control_diagnostic["skips_count"] != 0
        ):
            native_winsock_isolation_control_diagnostic["status"] = "stop_inconclusive"
            native_winsock_isolation_control_diagnostic["result_code"] = (
                "NATIVE_WINSOCK_CONTROL_DIAGNOSTIC_ACCOUNTING_MISMATCH"
            )
        return native_winsock_isolation_control_diagnostic
    if trusted_cpu_watchdog_diagnostic is not None:
        process_residue = [pid for pid in sorted(child_pids) if process_active(native, pid)]
        canary_unchanged = (
            trusted_cpu_watchdog_diagnostic.get("canary_unchanged_before_cleanup") is True
        )
        job_quiescence_verified = (
            trusted_cpu_watchdog_diagnostic.get("job_quiescence_verified_before_cleanup") is True
        )
        diagnostic_cleanup_ok = bool(
            cleanup_ok
            and canary_unchanged
            and job_quiescence_verified
            and not process_residue
            and listeners == []
        )
        trusted_cpu_watchdog_diagnostic["cleanup"] = {
            "verified": diagnostic_cleanup_ok,
            "canary_unchanged_before_cleanup": canary_unchanged,
            "job_quiescence_verified_before_cleanup": job_quiescence_verified,
            "process_residue": process_residue,
            "profile_registry_exists": registry_exists,
            "profile_folder_exists": folder_exists,
            "root_exists": root.exists(),
            "listener_count": len(listeners),
            "sandbox_ACL_restoration_errors": [
                value for value in cleanup_errors if str(value.get("stage", "")).startswith("sandbox_acl")
            ],
            "repository_bytecode_residue": "must_be_confirmed_by_post_process_repository_check",
            "cleanup_errors": cleanup_errors,
        }
        trusted_cpu_watchdog_diagnostic["cleanup_verified"] = diagnostic_cleanup_ok
        trusted_cpu_watchdog_diagnostic["root"] = str(root).replace("\\", "/")
        trusted_cpu_watchdog_diagnostic["profile_name"] = args.profile
        trusted_cpu_watchdog_diagnostic["profile_sid"] = sid_string
        trusted_cpu_watchdog_diagnostic["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        if not diagnostic_cleanup_ok:
            trusted_cpu_watchdog_diagnostic["status"] = "stop_inconclusive"
            trusted_cpu_watchdog_diagnostic["result_code"] = (
                "TRUSTED_CPU_WATCHDOG_DIAGNOSTIC_CLEANUP_FAILED"
            )
        return trusted_cpu_watchdog_diagnostic
    if assigned_suspended_target_flag_preservation_diagnostic is not None:
        process_residue = [pid for pid in sorted(child_pids) if process_active(native, pid)]
        canary_unchanged = (
            assigned_suspended_target_flag_preservation_diagnostic.get(
                "canary_unchanged_before_cleanup"
            ) is True
        )
        job_quiescence_verified = (
            assigned_suspended_target_flag_preservation_diagnostic.get(
                "job_quiescence_verified_before_cleanup"
            ) is True
        )
        diagnostic_cleanup_ok = bool(
            cleanup_ok
            and canary_unchanged
            and job_quiescence_verified
            and not process_residue
            and listeners == []
        )
        assigned_suspended_target_flag_preservation_diagnostic["cleanup"] = {
            "verified": diagnostic_cleanup_ok,
            "canary_unchanged_before_cleanup": canary_unchanged,
            "job_quiescence_verified_before_cleanup": job_quiescence_verified,
            "process_residue": process_residue,
            "profile_registry_exists": registry_exists,
            "profile_folder_exists": folder_exists,
            "root_exists": root.exists(),
            "listener_count": len(listeners),
            "sandbox_ACL_restoration_errors": [
                value for value in cleanup_errors if str(value.get("stage", "")).startswith("sandbox_acl")
            ],
            "repository_bytecode_residue": "must_be_confirmed_by_post_process_repository_check",
            "cleanup_errors": cleanup_errors,
        }
        assigned_suspended_target_flag_preservation_diagnostic["cleanup_verified"] = diagnostic_cleanup_ok
        assigned_suspended_target_flag_preservation_diagnostic["root"] = str(root).replace("\\", "/")
        assigned_suspended_target_flag_preservation_diagnostic["profile_name"] = args.profile
        assigned_suspended_target_flag_preservation_diagnostic["profile_sid"] = sid_string
        assigned_suspended_target_flag_preservation_diagnostic["elapsed_ms"] = int(
            (time.monotonic() - started) * 1000
        )
        if not diagnostic_cleanup_ok:
            assigned_suspended_target_flag_preservation_diagnostic["status"] = "stop_inconclusive"
            assigned_suspended_target_flag_preservation_diagnostic["result_code"] = (
                "ASSIGNED_SUSPENDED_TARGET_FLAG_PRESERVATION_DIAGNOSTIC_CLEANUP_FAILED"
            )
        return assigned_suspended_target_flag_preservation_diagnostic
    if process_time_enforcement_repeatability_diagnostic is not None:
        process_residue = [pid for pid in sorted(child_pids) if process_active(native, pid)]
        canary_unchanged = (
            process_time_enforcement_repeatability_diagnostic.get(
                "canary_unchanged_before_cleanup"
            ) is True
        )
        job_quiescence_verified = (
            process_time_enforcement_repeatability_diagnostic.get(
                "job_quiescence_verified_before_cleanup"
            ) is True
        )
        diagnostic_cleanup_ok = bool(
            cleanup_ok
            and canary_unchanged
            and job_quiescence_verified
            and not process_residue
            and listeners == []
        )
        process_time_enforcement_repeatability_diagnostic["cleanup"] = {
            "verified": diagnostic_cleanup_ok,
            "canary_unchanged_before_cleanup": canary_unchanged,
            "job_quiescence_verified_before_cleanup": job_quiescence_verified,
            "process_residue": process_residue,
            "profile_registry_exists": registry_exists,
            "profile_folder_exists": folder_exists,
            "root_exists": root.exists(),
            "listener_count": len(listeners),
            "sandbox_ACL_restoration_errors": [
                value for value in cleanup_errors if str(value.get("stage", "")).startswith("sandbox_acl")
            ],
            "repository_bytecode_residue": "must_be_confirmed_by_post_process_repository_check",
            "cleanup_errors": cleanup_errors,
        }
        process_time_enforcement_repeatability_diagnostic["cleanup_verified"] = diagnostic_cleanup_ok
        process_time_enforcement_repeatability_diagnostic["root"] = str(root).replace("\\", "/")
        process_time_enforcement_repeatability_diagnostic["profile_name"] = args.profile
        process_time_enforcement_repeatability_diagnostic["profile_sid"] = sid_string
        process_time_enforcement_repeatability_diagnostic["elapsed_ms"] = int(
            (time.monotonic() - started) * 1000
        )
        if not diagnostic_cleanup_ok:
            process_time_enforcement_repeatability_diagnostic["status"] = "stop_inconclusive"
            process_time_enforcement_repeatability_diagnostic["result_code"] = (
                "PROCESS_TIME_ENFORCEMENT_REPEATABILITY_DIAGNOSTIC_CLEANUP_FAILED"
            )
        return process_time_enforcement_repeatability_diagnostic
    if appcontainer_process_time_information_class_control_diagnostic is not None:
        process_residue = [pid for pid in sorted(child_pids) if process_active(native, pid)]
        canary_unchanged = (
            appcontainer_process_time_information_class_control_diagnostic.get(
                "canary_unchanged_before_cleanup"
            ) is True
        )
        job_quiescence_verified = (
            appcontainer_process_time_information_class_control_diagnostic.get(
                "job_quiescence_verified_before_cleanup"
            ) is True
        )
        diagnostic_cleanup_ok = bool(
            cleanup_ok
            and canary_unchanged
            and job_quiescence_verified
            and not process_residue
            and listeners == []
        )
        appcontainer_process_time_information_class_control_diagnostic["cleanup"] = {
            "verified": diagnostic_cleanup_ok,
            "canary_unchanged_before_cleanup": canary_unchanged,
            "job_quiescence_verified_before_cleanup": job_quiescence_verified,
            "process_residue": process_residue,
            "profile_registry_exists": registry_exists,
            "profile_folder_exists": folder_exists,
            "root_exists": root.exists(),
            "listener_count": len(listeners),
            "sandbox_ACL_restoration_errors": [
                value for value in cleanup_errors if str(value.get("stage", "")).startswith("sandbox_acl")
            ],
            "repository_bytecode_residue": "must_be_confirmed_by_post_process_repository_check",
            "cleanup_errors": cleanup_errors,
        }
        appcontainer_process_time_information_class_control_diagnostic["cleanup_verified"] = (
            diagnostic_cleanup_ok
        )
        appcontainer_process_time_information_class_control_diagnostic["root"] = str(root).replace("\\", "/")
        appcontainer_process_time_information_class_control_diagnostic["profile_name"] = args.profile
        appcontainer_process_time_information_class_control_diagnostic["profile_sid"] = sid_string
        appcontainer_process_time_information_class_control_diagnostic["elapsed_ms"] = int(
            (time.monotonic() - started) * 1000
        )
        if not diagnostic_cleanup_ok:
            appcontainer_process_time_information_class_control_diagnostic["status"] = "stop_inconclusive"
            appcontainer_process_time_information_class_control_diagnostic["result_code"] = (
                "APPCONTAINER_PROCESS_TIME_INFORMATION_CLASS_CONTROL_DIAGNOSTIC_CLEANUP_FAILED"
            )
        return appcontainer_process_time_information_class_control_diagnostic
    if non_nested_process_time_causal_diagnostic is not None:
        process_residue = [pid for pid in sorted(child_pids) if process_active(native, pid)]
        canary_unchanged = (
            non_nested_process_time_causal_diagnostic.get("canary_unchanged_before_cleanup") is True
        )
        job_quiescence_verified = (
            non_nested_process_time_causal_diagnostic.get("job_quiescence_verified_before_cleanup") is True
        )
        diagnostic_cleanup_ok = bool(
            cleanup_ok
            and canary_unchanged
            and job_quiescence_verified
            and not process_residue
            and listeners == []
        )
        non_nested_process_time_causal_diagnostic["cleanup"] = {
            "verified": diagnostic_cleanup_ok,
            "canary_unchanged_before_cleanup": canary_unchanged,
            "job_quiescence_verified_before_cleanup": job_quiescence_verified,
            "process_residue": process_residue,
            "profile_registry_exists": registry_exists,
            "profile_folder_exists": folder_exists,
            "root_exists": root.exists(),
            "listener_count": len(listeners),
            "sandbox_ACL_restoration_errors": [
                value for value in cleanup_errors if str(value.get("stage", "")).startswith("sandbox_acl")
            ],
            "repository_bytecode_residue": "must_be_confirmed_by_post_process_repository_check",
            "cleanup_errors": cleanup_errors,
        }
        non_nested_process_time_causal_diagnostic["cleanup_verified"] = diagnostic_cleanup_ok
        non_nested_process_time_causal_diagnostic["root"] = str(root).replace("\\", "/")
        non_nested_process_time_causal_diagnostic["profile_name"] = args.profile
        non_nested_process_time_causal_diagnostic["profile_sid"] = sid_string
        non_nested_process_time_causal_diagnostic["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        if not diagnostic_cleanup_ok:
            non_nested_process_time_causal_diagnostic["status"] = "stop_inconclusive"
            non_nested_process_time_causal_diagnostic["result_code"] = (
                "NON_NESTED_PROCESS_TIME_CAUSAL_DIAGNOSTIC_CLEANUP_FAILED"
            )
        return non_nested_process_time_causal_diagnostic
    if live_companion_attribution_diagnostic is not None:
        process_residue = [pid for pid in sorted(child_pids) if process_active(native, pid)]
        canary_unchanged = live_companion_attribution_diagnostic.get("canary_unchanged_before_cleanup") is True
        job_quiescence_verified = (
            live_companion_attribution_diagnostic.get("job_quiescence_verified_before_cleanup") is True
        )
        diagnostic_cleanup_ok = bool(
            cleanup_ok
            and canary_unchanged
            and job_quiescence_verified
            and not process_residue
            and listeners == []
        )
        live_companion_attribution_diagnostic["cleanup"] = {
            "verified": diagnostic_cleanup_ok,
            "canary_unchanged_before_cleanup": canary_unchanged,
            "job_quiescence_verified_before_cleanup": job_quiescence_verified,
            "process_residue": process_residue,
            "profile_registry_exists": registry_exists,
            "profile_folder_exists": folder_exists,
            "root_exists": root.exists(),
            "listener_count": len(listeners),
            "sandbox_ACL_restoration_errors": [
                value for value in cleanup_errors if str(value.get("stage", "")).startswith("sandbox_acl")
            ],
            "repository_bytecode_residue": "must_be_confirmed_by_post_process_repository_check",
            "cleanup_errors": cleanup_errors,
        }
        live_companion_attribution_diagnostic["cleanup_verified"] = diagnostic_cleanup_ok
        live_companion_attribution_diagnostic["root"] = str(root).replace("\\", "/")
        live_companion_attribution_diagnostic["profile_name"] = args.profile
        live_companion_attribution_diagnostic["profile_sid"] = sid_string
        live_companion_attribution_diagnostic["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        if not diagnostic_cleanup_ok:
            live_companion_attribution_diagnostic["status"] = "stop_inconclusive"
            live_companion_attribution_diagnostic["result_code"] = "LIVE_ATTRIBUTION_INCOMPLETE_EXACT_BLOCKER"
            live_companion_attribution_diagnostic["blocker"] = {
                "code": "LIVE_ATTRIBUTION_DIAGNOSTIC_CLEANUP_FAILED",
                "detail": "exact cleanup or quiescence verification failed",
            }
        return live_companion_attribution_diagnostic
    if process_time_control_diagnostic is not None:
        process_residue = [pid for pid in sorted(child_pids) if process_active(native, pid)]
        canary_unchanged = process_time_control_diagnostic.get("canary_unchanged_before_cleanup") is True
        diagnostic_cleanup_ok = bool(
            cleanup_ok
            and canary_unchanged
            and not process_residue
            and listeners == []
        )
        process_time_control_diagnostic["cleanup"] = {
            "verified": diagnostic_cleanup_ok,
            "canary_unchanged_before_cleanup": canary_unchanged,
            "process_residue": process_residue,
            "profile_registry_exists": registry_exists,
            "profile_folder_exists": folder_exists,
            "root_exists": root.exists(),
            "listener_count": len(listeners),
            "sandbox_ACL_restoration_errors": [
                value for value in cleanup_errors if str(value.get("stage", "")).startswith("sandbox_acl")
            ],
            "repository_bytecode_residue": "must_be_confirmed_by_post_process_repository_check",
            "cleanup_errors": cleanup_errors,
        }
        process_time_control_diagnostic["cleanup_verified"] = diagnostic_cleanup_ok
        process_time_control_diagnostic["root"] = str(root).replace("\\", "/")
        process_time_control_diagnostic["profile_name"] = args.profile
        process_time_control_diagnostic["profile_sid"] = sid_string
        process_time_control_diagnostic["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        if not diagnostic_cleanup_ok:
            process_time_control_diagnostic["status"] = "stop_inconclusive"
            process_time_control_diagnostic["result_code"] = "PROCESS_TIME_CONTROL_DIAGNOSTIC_CLEANUP_FAILED"
        return process_time_control_diagnostic
    if active_process_accounting_diagnostic is not None:
        process_residue = [pid for pid in sorted(child_pids) if process_active(native, pid)]
        endpoint_rebind_errors: list[dict[str, object]] = []
        rebound: list[socket.socket] = []
        try:
            rebound.append(exclusive_listener(socket.AF_INET, args.ipv4_host, args.ipv4_port))
            rebound.append(exclusive_listener(socket.AF_INET6, args.ipv6_host, args.ipv6_port))
        except BaseException as exc:
            endpoint_rebind_errors.append({
                "type": type(exc).__name__,
                "message": str(exc)[:512],
                "winerror": getattr(exc, "winerror", None),
                "errno": getattr(exc, "errno", None),
            })
        finally:
            for listener in rebound:
                listener.close()
        canary_unchanged = active_process_accounting_diagnostic.get("canary_unchanged_before_cleanup") is True
        job_quiescence_verified = active_process_accounting_diagnostic.get("job_quiescence_verified_before_cleanup") is True
        diagnostic_cleanup_ok = bool(
            cleanup_ok
            and canary_unchanged
            and job_quiescence_verified
            and not process_residue
            and not endpoint_rebind_errors
        )
        active_process_accounting_diagnostic["rows"].append({
            "id": "AP-WIN-08",
            "purpose": "final zero active processes, empty PID inventory, and complete cleanup",
            "passed": diagnostic_cleanup_ok,
            "evidence": {
                "canary_unchanged_before_cleanup": canary_unchanged,
                "job_quiescence_verified_before_cleanup": job_quiescence_verified,
                "job_quiescence_evidence": active_process_accounting_diagnostic.get("job_quiescence_evidence"),
                "process_residue": process_residue,
                "profile_registry_exists": registry_exists,
                "profile_folder_exists": folder_exists,
                "root_exists": root.exists(),
                "sandbox_ACL_restoration_errors": [
                    value for value in cleanup_errors if str(value.get("stage", "")).startswith("sandbox_acl")
                ],
                "listener_socket_endpoint_rebind_errors": endpoint_rebind_errors,
                "repository_bytecode_residue": "must_be_confirmed_by_post_process_repository_check",
                "cleanup_errors": cleanup_errors,
            },
        })
        active_process_accounting_diagnostic["matrix_actual_count"] = len(active_process_accounting_diagnostic["rows"])
        active_process_accounting_diagnostic["passed_count"] = sum(
            1 for value in active_process_accounting_diagnostic["rows"] if value.get("passed") is True
        )
        active_process_accounting_diagnostic["failed_count"] = sum(
            1 for value in active_process_accounting_diagnostic["rows"] if value.get("passed") is False
        )
        active_process_accounting_diagnostic["errors_count"] = 0
        active_process_accounting_diagnostic["skips_count"] = 0
        active_process_accounting_diagnostic["cleanup_verified"] = diagnostic_cleanup_ok
        active_process_accounting_diagnostic["root"] = str(root).replace("\\", "/")
        active_process_accounting_diagnostic["profile_name"] = args.profile
        active_process_accounting_diagnostic["profile_sid"] = sid_string
        active_process_accounting_diagnostic["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        if (
            not diagnostic_cleanup_ok
            or active_process_accounting_diagnostic["matrix_actual_count"] != 8
            or active_process_accounting_diagnostic["passed_count"] != 8
            or active_process_accounting_diagnostic["failed_count"] != 0
        ):
            active_process_accounting_diagnostic["status"] = "stop_inconclusive"
            active_process_accounting_diagnostic["result_code"] = "ACTIVE_PROCESS_LIMIT_ENFORCEMENT_NOT_PROVEN"
        return active_process_accounting_diagnostic
    if final_remediation_diagnostic is not None:
        process_residue = [pid for pid in sorted(child_pids) if process_active(native, pid)]
        endpoint_rebind_errors: list[dict[str, object]] = []
        rebound: list[socket.socket] = []
        try:
            rebound.append(exclusive_listener(socket.AF_INET, args.ipv4_host, args.ipv4_port))
            rebound.append(exclusive_listener(socket.AF_INET6, args.ipv6_host, args.ipv6_port))
        except BaseException as exc:
            endpoint_rebind_errors.append({
                "type": type(exc).__name__,
                "message": str(exc)[:512],
                "winerror": getattr(exc, "winerror", None),
                "errno": getattr(exc, "errno", None),
            })
        finally:
            for listener in rebound:
                listener.close()
        canary_unchanged = final_remediation_diagnostic.get("canary_unchanged_before_cleanup") is True
        diagnostic_cleanup_ok = bool(
            cleanup_ok
            and canary_unchanged
            and not process_residue
            and not endpoint_rebind_errors
        )
        final_remediation_diagnostic["rows"].append({
            "id": "FR-WIN-10",
            "purpose": "canary preservation and complete cleanup",
            "passed": diagnostic_cleanup_ok,
            "evidence": {
                "canary_unchanged_before_cleanup": canary_unchanged,
                "process_residue": process_residue,
                "profile_registry_exists": registry_exists,
                "profile_folder_exists": folder_exists,
                "root_exists": root.exists(),
                "sandbox_ACL_restoration_errors": [
                    value for value in cleanup_errors if str(value.get("stage", "")).startswith("sandbox_acl")
                ],
                "listener_socket_endpoint_rebind_errors": endpoint_rebind_errors,
                "repository_bytecode_residue": "must_be_confirmed_by_post_process_repository_check",
                "cleanup_errors": cleanup_errors,
            },
        })
        final_remediation_diagnostic["matrix_actual_count"] = len(final_remediation_diagnostic["rows"])
        final_remediation_diagnostic["passed_count"] = sum(
            1 for value in final_remediation_diagnostic["rows"] if value.get("passed") is True
        )
        final_remediation_diagnostic["failed_count"] = sum(
            1 for value in final_remediation_diagnostic["rows"] if value.get("passed") is False
        )
        final_remediation_diagnostic["cleanup_verified"] = diagnostic_cleanup_ok
        final_remediation_diagnostic["root"] = str(root).replace("\\", "/")
        final_remediation_diagnostic["profile_name"] = args.profile
        final_remediation_diagnostic["profile_sid"] = sid_string
        final_remediation_diagnostic["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        if not diagnostic_cleanup_ok:
            final_remediation_diagnostic["status"] = "stop_inconclusive"
            final_remediation_diagnostic["result_code"] = "FINAL_REMEDIATION_DIAGNOSTIC_CLEANUP_FAILED"
        elif (
            final_remediation_diagnostic.get("result_code") == "FINAL_REMEDIATION_DIAGNOSTIC_CAPTURED"
            and (
                final_remediation_diagnostic["matrix_actual_count"] != 10
                or final_remediation_diagnostic["passed_count"] != 10
                or final_remediation_diagnostic["failed_count"] != 0
            )
        ):
            final_remediation_diagnostic["status"] = "stop_inconclusive"
            final_remediation_diagnostic["result_code"] = "FINAL_REMEDIATION_DIAGNOSTIC_ACCOUNTING_MISMATCH"
        return final_remediation_diagnostic
    if case_remediation_diagnostic is not None:
        process_residue = [pid for pid in sorted(child_pids) if process_active(native, pid)]
        endpoint_rebind_errors: list[dict[str, object]] = []
        rebound: list[socket.socket] = []
        try:
            rebound.append(exclusive_listener(socket.AF_INET, args.ipv4_host, args.ipv4_port))
            rebound.append(exclusive_listener(socket.AF_INET6, args.ipv6_host, args.ipv6_port))
        except BaseException as exc:
            endpoint_rebind_errors.append({
                "type": type(exc).__name__,
                "message": str(exc)[:512],
                "winerror": getattr(exc, "winerror", None),
                "errno": getattr(exc, "errno", None),
            })
        finally:
            for listener in rebound:
                listener.close()
        diagnostic_cleanup_ok = bool(cleanup_ok and not process_residue and not endpoint_rebind_errors)
        case_remediation_diagnostic["rows"].append({
            "id": "RD-WIN-09",
            "purpose": "exact cleanup and zero residue",
            "verified": diagnostic_cleanup_ok,
            "process_residue": process_residue,
            "profile_registry_exists": registry_exists,
            "profile_folder_exists": folder_exists,
            "root_exists": root.exists(),
            "sandbox_ACL_restoration_errors": [
                value for value in cleanup_errors if str(value.get("stage", "")).startswith("sandbox_acl")
            ],
            "listener_socket_endpoint_rebind_errors": endpoint_rebind_errors,
            "repository_bytecode_residue": "must_be_confirmed_by_post_process_repository_check",
            "cleanup_errors": cleanup_errors,
        })
        case_remediation_diagnostic["matrix_actual_count"] = len(case_remediation_diagnostic["rows"])
        case_remediation_diagnostic["cleanup_verified"] = diagnostic_cleanup_ok
        case_remediation_diagnostic["root"] = str(root).replace("\\", "/")
        case_remediation_diagnostic["profile_name"] = args.profile
        case_remediation_diagnostic["profile_sid"] = sid_string
        case_remediation_diagnostic["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        return case_remediation_diagnostic
    if identity_diagnostic is not None:
        return {
            "schema": "pipeline-v2.k0b03-v2-windows-identity-diagnostic-v1",
            "attempt": args.attempt,
            "status": "identity_diagnostic_captured",
            "result_code": "IDENTITY_DIAGNOSTIC_CAPTURED",
            "profile_name": args.profile,
            "profile_sid": sid_string,
            "root": str(root).replace("\\", "/"),
            "diagnostic": identity_diagnostic,
            "cleanup": {
                "verified": cleanup_ok,
                "errors": cleanup_errors,
                "root_exists": root.exists(),
                "profile_registry_exists": registry_exists,
                "profile_folder_exists": folder_exists,
                "BFE_before": bfe_before,
                "BFE_after": bfe_after,
                "exemptions_before": exemptions_before,
                "exemptions_after": exemptions_after,
            },
            "elapsed_ms": int((time.monotonic() - started) * 1000),
        }
    cases.append(case("CP-WIN-18", "complete_process_handle_profile_ACL_listener_socket_and_root_cleanup", "PASS_COMPLETE_CLEANUP", cleanup_ok,
                      cleanup_errors=cleanup_errors, root_exists=root.exists(), profile_registry_exists=registry_exists,
                      profile_folder_exists=folder_exists, BFE_before=bfe_before, BFE_after=bfe_after,
                      exemptions_before=exemptions_before, exemptions_after=exemptions_after))
    passed = len(cases) == 18 and all(value["passed"] for value in cases)
    if not passed:
        raise ProbeStop("FINAL_CASE_ACCOUNTING_FAILED", canonical(result_projection(cases)))
    return {
        "schema": "pipeline-v2.k0b03-v2-windows-capability-attempt-v1",
        "attempt": args.attempt,
        "status": "pass",
        "launcher_gate": getattr(args, "non_nested_launcher_gate", None),
        "profile_name": args.profile,
        "profile_sid": sid_string,
        "root": str(root).replace("\\", "/"),
        "endpoints": [f"{args.ipv4_host}:{args.ipv4_port}", f"[{args.ipv6_host}]:{args.ipv6_port}"],
        "case_count": len(cases),
        "passed": sum(1 for value in cases if value["passed"]),
        "failed": sum(1 for value in cases if not value["passed"]),
        "errors": 0,
        "skips": 0,
        "cases": cases,
        "result_projection": result_projection(cases),
        "result_projection_sha256": sha256_bytes(canonical(result_projection(cases)).encode("utf-8")),
        "suspended_launch_diagnostic_provenance": SUSPENDED_LAUNCH_DIAGNOSTIC_PROVENANCE,
        "runtime_projection": projection_materialization,
        "elapsed_ms": int((time.monotonic() - started) * 1000),
        "cleanup_verified": cleanup_ok,
    }


def non_nested_launcher_membership_gate(
    args: argparse.Namespace,
    *,
    normal_qualification: bool = False,
) -> dict[str, object]:
    if not normal_qualification and args.attempt != "A":
        if args.trusted_cpu_watchdog_diagnostic_only:
            raise ProbeStop("TRUSTED_CPU_WATCHDOG_DIAGNOSTIC_ATTEMPT_FORBIDDEN", args.attempt)
        if args.final_remediation_diagnostic_only:
            raise ProbeStop("FINAL_REMEDIATION_DIAGNOSTIC_ATTEMPT_FORBIDDEN", args.attempt)
        raise ProbeStop("NON_NESTED_PROCESS_TIME_DIAGNOSTIC_ATTEMPT_FORBIDDEN", args.attempt)
    diagnostic_modes = [
        args.identity_diagnostic_only,
        args.case_remediation_diagnostic_only,
        args.final_remediation_diagnostic_only,
        args.active_process_accounting_diagnostic_only,
        args.process_time_control_diagnostic_only,
        args.live_companion_attribution_diagnostic_only,
        args.non_nested_process_time_causal_diagnostic_only,
        args.appcontainer_process_time_information_class_control_diagnostic_only,
        args.process_time_enforcement_repeatability_diagnostic_only,
        args.assigned_suspended_target_flag_preservation_diagnostic_only,
        args.trusted_cpu_watchdog_diagnostic_only,
    ]
    expected_diagnostic_mode_count = 0 if normal_qualification else 1
    if sum(1 for value in diagnostic_modes if value) != expected_diagnostic_mode_count:
        raise ProbeStop("DIAGNOSTIC_MODE_COUNT_MISMATCH", str(sum(bool(value) for value in diagnostic_modes)))
    python_pin = file_pin(Path(PYTHON_PATH))
    projection_request_pin = file_pin(Path(args.projection_request))
    worker_pin = file_pin(Path(args.worker))
    if python_pin["sha256"] != PYTHON_SHA256 or python_pin["bytes"] != PYTHON_BYTES:
        raise ProbeStop("PYTHON_PIN_MISMATCH", canonical(python_pin))
    if (
        projection_request_pin["sha256"] != PROJECTION_REQUEST_SHA256
        or projection_request_pin["bytes"] != PROJECTION_REQUEST_BYTES
    ):
        raise ProbeStop("PROJECTION_REQUEST_PIN_MISMATCH", canonical(projection_request_pin))
    if worker_pin["sha256"] != WORKER_SHA256 or worker_pin["bytes"] != WORKER_BYTES:
        raise ProbeStop("WORKER_PIN_MISMATCH", canonical(worker_pin))
    native = Native()
    get_current_process = native.kernel32.GetCurrentProcess
    get_current_process.argtypes = []
    get_current_process.restype = wt.HANDLE
    current_process = get_current_process()
    in_job = wt.BOOL()
    ct.set_last_error(0)
    query_ok = bool(native.kernel32.IsProcessInJob(current_process, None, ct.byref(in_job)))
    query_error = ct.get_last_error()
    if not query_ok:
        raise ProbeStop("CURRENT_PROCESS_JOB_MEMBERSHIP_QUERY_FAILED", "early_zero_object_gate", query_error)
    return {
        "timing": "after_immutable_pin_and_CLI_validation_before_runtime_objects",
        "API": "IsProcessInJob(GetCurrentProcess(), NULL)",
        "query_result": query_ok,
        "last_error": int(query_error),
        "current_process_in_any_Job": bool(in_job.value),
        "runtime_objects_created": 0,
        "pins": {
            "python": python_pin,
            "projection_request": projection_request_pin,
            "worker": worker_pin,
        },
    }


def parse_endpoint(value: str, family: str) -> tuple[str, int]:
    if family == "IPv6":
        if not value.startswith("[") or "]:" not in value:
            raise argparse.ArgumentTypeError("IPv6 endpoint must be [address]:port")
        host, port = value[1:].split("]:", 1)
    else:
        host, port = value.rsplit(":", 1)
    return host, int(port)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("command", choices=["qualify"])
    parser.add_argument("--attempt", required=True, choices=["A", "B"])
    parser.add_argument("--root", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--ipv4", required=True)
    parser.add_argument("--ipv6", required=True)
    parser.add_argument("--worker", required=True)
    parser.add_argument("--projection-request", required=True)
    parser.add_argument("--identity-diagnostic-only", action="store_true")
    parser.add_argument("--case-remediation-diagnostic-only", action="store_true")
    parser.add_argument("--final-remediation-diagnostic-only", action="store_true")
    parser.add_argument("--active-process-accounting-diagnostic-only", action="store_true")
    parser.add_argument("--process-time-control-diagnostic-only", action="store_true")
    parser.add_argument("--live-companion-attribution-diagnostic-only", action="store_true")
    parser.add_argument("--non-nested-process-time-causal-diagnostic-only", action="store_true")
    parser.add_argument(
        "--appcontainer-process-time-information-class-control-diagnostic-only",
        action="store_true",
    )
    parser.add_argument(
        "--assigned-suspended-target-flag-preservation-diagnostic-only",
        action="store_true",
    )
    parser.add_argument(
        "--process-time-enforcement-repeatability-diagnostic-only",
        action="store_true",
    )
    parser.add_argument(
        "--trusted-cpu-watchdog-diagnostic-only",
        action="store_true",
    )
    parser.add_argument(
        "--native-winsock-isolation-control-diagnostic-only",
        action="store_true",
    )
    parser.add_argument(
        "--trusted-pending-connect-watchdog-diagnostic-only",
        action="store_true",
    )
    args = parser.parse_args()
    args.ipv4_host, args.ipv4_port = parse_endpoint(args.ipv4, "IPv4")
    args.ipv6_host, args.ipv6_port = parse_endpoint(args.ipv6, "IPv6")
    return args


def main() -> int:
    args = parse_args()
    try:
        all_diagnostic_modes = [
            args.identity_diagnostic_only,
            args.case_remediation_diagnostic_only,
            args.final_remediation_diagnostic_only,
            args.active_process_accounting_diagnostic_only,
            args.process_time_control_diagnostic_only,
            args.live_companion_attribution_diagnostic_only,
            args.non_nested_process_time_causal_diagnostic_only,
            args.appcontainer_process_time_information_class_control_diagnostic_only,
            args.assigned_suspended_target_flag_preservation_diagnostic_only,
            args.process_time_enforcement_repeatability_diagnostic_only,
            args.trusted_cpu_watchdog_diagnostic_only,
            args.native_winsock_isolation_control_diagnostic_only,
            args.trusted_pending_connect_watchdog_diagnostic_only,
        ]
        normal_qualification = not any(all_diagnostic_modes)
        if (
            normal_qualification
            or args.final_remediation_diagnostic_only
            or args.non_nested_process_time_causal_diagnostic_only
            or args.appcontainer_process_time_information_class_control_diagnostic_only
            or args.process_time_enforcement_repeatability_diagnostic_only
            or args.assigned_suspended_target_flag_preservation_diagnostic_only
            or args.trusted_cpu_watchdog_diagnostic_only
        ):
            launcher_gate = non_nested_launcher_membership_gate(
                args,
                normal_qualification=normal_qualification,
            )
            if launcher_gate["current_process_in_any_Job"] is True:
                if normal_qualification:
                    schema = "pipeline-v2.k0b03-v2-windows-capability-attempt-v1"
                elif args.final_remediation_diagnostic_only:
                    schema = "pipeline-v2.k0b03-v2-windows-final-remediation-diagnostic-v1"
                elif args.trusted_cpu_watchdog_diagnostic_only:
                    schema = (
                        "pipeline-v2.k0b03-v2-windows-trusted-CPU-watchdog-diagnostic-v1"
                    )
                elif args.process_time_enforcement_repeatability_diagnostic_only:
                    schema = (
                        "pipeline-v2.k0b03-v2-windows-process-time-enforcement-repeatability-diagnostic-v1"
                    )
                elif args.assigned_suspended_target_flag_preservation_diagnostic_only:
                    schema = (
                        "pipeline-v2.k0b03-v2-windows-assigned-suspended-target-flag-preservation-diagnostic-v1"
                    )
                elif args.appcontainer_process_time_information_class_control_diagnostic_only:
                    schema = (
                        "pipeline-v2.k0b03-v2-windows-AppContainer-process-time-information-class-control-diagnostic-v1"
                    )
                else:
                    schema = "pipeline-v2.k0b03-v2-windows-non-nested-process-time-causal-diagnostic-v1"
                value = {
                    "schema": schema,
                    "attempt": args.attempt,
                    "status": "stop_inconclusive",
                    "result_code": "NON_NESTED_LAUNCH_CONTEXT_REQUIRED",
                    "runtime_object_count": 0,
                    "launcher_gate": launcher_gate,
                    "root_exists": Path(args.root).exists(),
                    "retry_in_same_context_permitted": False,
                }
                sys.stdout.write(canonical(value) + "\n")
                return 0
            args.non_nested_launcher_gate = launcher_gate
        value = qualify(args)
    except ProbeStop as exc:
        value = {
            "schema": "pipeline-v2.k0b03-v2-windows-capability-attempt-v1",
            "attempt": args.attempt,
            "status": "stop_inconclusive",
            "stop_code": exc.code,
            "detail": exc.detail,
            "raw_code": exc.raw_code,
            "root_exists_after_cleanup": Path(args.root).exists(),
        }
        sys.stdout.write(canonical(value) + "\n")
        return 2
    except BaseException as exc:
        value = {
            "schema": "pipeline-v2.k0b03-v2-windows-capability-attempt-v1",
            "attempt": args.attempt,
            "status": "stop_inconclusive",
            "stop_code": "UNEXPECTED_PROBE_ERROR",
            "detail": f"{type(exc).__name__}: {exc}",
            "raw_code": getattr(exc, "winerror", None),
            "root_exists_after_cleanup": Path(args.root).exists(),
        }
        sys.stdout.write(canonical(value) + "\n")
        return 3
    sys.stdout.write(canonical(value) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
