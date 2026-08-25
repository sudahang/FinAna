"""DataCore 渠道注册表：按 provider_order 构建可用 provider 列表。"""

from finana.config import Settings
from finana.datacore.providers.em import EastmoneyProvider
from finana.datacore.providers.sina_tencent import SinaTencentProvider

_BUILDERS = {}


def register_builder(name, fn):
    """注册一个按 settings 构建 provider 实例的构建器。"""
    _BUILDERS[name] = fn


register_builder("eastmoney", lambda s: EastmoneyProvider())
register_builder("sina_tencent", lambda s: SinaTencentProvider())


def _try_register_akshare():
    def build(settings):
        from finana.datacore.providers.akshare_p import AkshareProvider

        return AkshareProvider()
    try:
        import akshare  # noqa: F401
        register_builder("akshare", build)
    except ImportError:
        pass


_try_register_akshare()


def _try_register_alltick():
    def build(settings):
        token = getattr(settings, "alltick_token", "")
        if not token:
            raise ImportError("alltick token 未配置")
        from finana.datacore.providers.alltick import AlltickProvider

        return AlltickProvider(token=token)
    register_builder("alltick", build)


_try_register_alltick()


def build_providers(settings: Settings) -> list:
    """按 settings.provider_order 顺序实例化渠道，跳过不可用者并返回实例列表。"""
    default_order = "eastmoney,sina_tencent,akshare,alltick"
    order_str = getattr(settings, "provider_order", "") or default_order
    order = [x.strip() for x in order_str.split(",") if x.strip()]
    out = []
    for name in order:
        builder = _BUILDERS.get(name)
        if not builder:
            continue
        try:
            out.append(builder(settings))
        except ImportError:
            continue
    return out
