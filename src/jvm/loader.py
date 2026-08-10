from __future__ import annotations

import ctypes
import os
import platform
from ctypes import POINTER, byref, c_char_p, c_void_p

from .config import Config
from .jvm import JVM
from .logger import logger


class JVMLoader:
    """JVMローダー"""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg

    def start(self) -> JVM:
        """JVM起動"""
        libjvm_path = self._find_libjvm(self.cfg.java_version)
        logger.info(f"Using libjvm at: {libjvm_path}")
        libjvm = ctypes.CDLL(libjvm_path)

        class JavaVMOption(ctypes.Structure):
            _fields_ = [("optionString", c_char_p), ("extraInfo", c_void_p)]

        class JavaVMInitArgs(ctypes.Structure):
            _fields_ = [
                ("version", ctypes.c_int),
                ("nOptions", ctypes.c_int),
                ("options", POINTER(JavaVMOption)),
                ("ignoreUnrecognized", ctypes.c_char),
            ]

        has_classpath = bool(self.cfg.classpath)

        # ARM64 macOS用オプション
        resource_management_options = []
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            resource_management_options.extend(
                [
                    b"-Djava.awt.headless=true",
                    b"-XX:+UseG1GC",
                    b"-XX:MaxGCPauseMillis=200",
                    b"-XX:+ExplicitGCInvokesConcurrent",
                ]
            )

        all_options = []
        if has_classpath:
            classpath_option = (
                b"-Djava.class.path=" + self._classpath(self.cfg).encode()
            )
            all_options.append(classpath_option)
            logger.debug(f"JVM option: {classpath_option.decode()}")

        all_options.extend(resource_management_options)

        num_options = len(all_options)
        if num_options > 0:
            opts = (JavaVMOption * num_options)()
            for i, option in enumerate(all_options):
                opts[i].optionString = option
                if i > 0:
                    logger.debug(f"JVM option: {option.decode()}")
        else:
            opts = None
            logger.debug("No JVM options (empty classpath)")

        args = JavaVMInitArgs()
        args.version = 0x00010008
        args.nOptions = num_options
        args.options = opts if num_options > 0 else None
        args.ignoreUnrecognized = 0

        p_vm = POINTER(c_void_p)()
        p_env = POINTER(c_void_p)()

        JNI_CreateJavaVM = libjvm.JNI_CreateJavaVM
        JNI_CreateJavaVM.restype = ctypes.c_int
        rc = JNI_CreateJavaVM(byref(p_vm), byref(p_env), byref(args))
        if rc != 0:
            raise RuntimeError(f"JVM init failed, code {rc}")

        return JVM(p_vm, p_env, self.cfg.classpath)

    def _find_libjvm(self, version: str) -> str:
        """libjvmライブラリパス検索"""
        platform_name = platform.system().lower()

        if platform_name == "windows":
            paths = [
                f"C:\\Program Files\\Java\\jdk-{version}\\bin\\server\\jvm.dll",
                f"C:\\Program Files (x86)\\Java\\jdk-{version}\\bin\\server\\jvm.dll",
                f"C:\\Program Files\\Eclipse Adoptium\\jdk-{version}\\bin\\server\\jvm.dll",
                f"C:\\Program Files (x86)\\Eclipse Adoptium\\jdk-{version}\\bin\\server\\jvm.dll",
                f"C:\\Program Files\\Amazon Corretto\\jdk{version}\\bin\\server\\jvm.dll",
                f"C:\\Program Files (x86)\\Amazon Corretto\\jdk{version}\\bin\\server\\jvm.dll",
                f"C:\\Program Files\\Microsoft\\jdk-{version}\\bin\\server\\jvm.dll",
                f"C:\\Program Files (x86)\\Microsoft\\jdk-{version}\\bin\\server\\jvm.dll",
                f"C:\\Program Files\\Zulu\\zulu-{version}\\bin\\server\\jvm.dll",
                f"C:\\Program Files (x86)\\Zulu\\zulu-{version}\\bin\\server\\jvm.dll",
                f"C:\\Program Files\\OpenJDK\\jdk-{version}\\bin\\server\\jvm.dll",
                f"C:\\Program Files (x86)\\OpenJDK\\jdk-{version}\\bin\\server\\jvm.dll",
                f"C:\\hostedtoolcache\\windows\\Java_Temurin-Hotspot_jdk\\{version}\\x64\\bin\\server\\jvm.dll",
            ]
        elif platform_name == "darwin":
            paths = [
                f"/opt/homebrew/opt/openjdk@{version}/libexec/openjdk.jdk/Contents/Home/lib/server/libjvm.dylib",
                f"/Library/Java/JavaVirtualMachines/jdk-{version}.jdk/Contents/Home/lib/server/libjvm.dylib",
                f"/Library/Java/JavaVirtualMachines/temurin-{version}.jdk/Contents/Home/lib/server/libjvm.dylib",
                f"/Library/Java/JavaVirtualMachines/amazon-corretto-{version}.jdk/Contents/Home/lib/server/libjvm.dylib",
                f"/Library/Java/JavaVirtualMachines/zulu-{version}.jdk/Contents/Home/lib/server/libjvm.dylib",
                f"/Library/Java/JavaVirtualMachines/openjdk-{version}.jdk/Contents/Home/lib/server/libjvm.dylib",
                f"/Users/runner/hostedtoolcache/Java_Temurin-Hotspot_jdk/{version}/arm64/Contents/Home/lib/server/libjvm.dylib",
            ]
        elif platform_name == "linux":
            paths = [
                f"/usr/lib/jvm/java-{version}-openjdk/lib/server/libjvm.so",
                f"/usr/lib/jvm/java-{version}-openjdk-amd64/lib/server/libjvm.so",
                f"/usr/lib/jvm/java-{version}-openjdk-arm64/lib/server/libjvm.so",
                f"/usr/lib/jvm/java-{version}/lib/server/libjvm.so",
                f"/usr/lib/jvm/temurin-{version}-jdk/lib/server/libjvm.so",
                f"/usr/lib/jvm/temurin-{version}-jdk-amd64/lib/server/libjvm.so",
                f"/usr/lib/jvm/amazon-corretto-{version}-jdk/lib/server/libjvm.so",
                f"/usr/lib/jvm/amazon-corretto-{version}-jdk-amd64/lib/server/libjvm.so",
                f"/usr/lib/jvm/zulu-{version}-jdk/lib/server/libjvm.so",
                f"/usr/lib/jvm/zulu-{version}-jdk-amd64/lib/server/libjvm.so",
                f"/usr/lib/jvm/openjdk-{version}-jdk/lib/server/libjvm.so",
                f"/usr/lib/jvm/openjdk-{version}-jdk-amd64/lib/server/libjvm.so",
            ]
        else:
            raise RuntimeError(f"Unsupported platform: {platform_name}")

        for path in paths:
            if os.path.exists(path):
                return path

        raise RuntimeError(
            f"Could not find libjvm for Java {version} on {platform_name}"
        )

    def _classpath(self, cfg: Config) -> str:
        """クラスパス文字列構築"""
        if not cfg.classpath:
            return ""
        return os.pathsep.join(cfg.classpath)
