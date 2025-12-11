# Platform-specific implementations
# 平台特定实现

import platform


def get_controller():
    """
    获取当前平台的控制器

    自动检测操作系统并返回对应的控制器实例
    """
    system = platform.system()

    if system == "Darwin":
        from .macos import MacOSController
        return MacOSController()
    elif system == "Windows":
        from .windows import WindowsController
        return WindowsController()
    elif system == "Linux":
        from .linux import LinuxController
        return LinuxController()
    else:
        raise NotImplementedError(f"Platform {system} is not supported")


__all__ = ["get_controller"]
