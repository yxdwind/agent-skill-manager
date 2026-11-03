"""Skill synchronization engine (package since the 2026-11-02 split).

The package owns the historical test seam: ``CENTRAL_DIR`` and
``PRODUCTS`` live as package attributes, and the five names tests patch
on this namespace (``CENTRAL_DIR``, ``PRODUCTS``, ``get_product_path``,
``is_symlink_or_junction``, ``_install_from_url``) are read by the
submodules through ``_pkg`` at call time - so
``patch("...services.sync.<name>")`` keeps intercepting after the split
(architecture health check 2026-10-31, §4).
"""

from ...config.products import CENTRAL_DIR, PRODUCTS, get_product_path
from ...utils.filesystem import is_symlink_or_junction
from .adopt import _patch_products, adopt_from_platform
from .audit_report import audit_all, audit_skill
from .engine import (
    FOOTER,
    _pack_status,
    _platform_key,
    _sync_one_product,
    get_status,
    list_skills,
    print_onboarding,
    remove_skill,
    sync_skill,
)
from .install import (
    _install_from_local,
    _install_from_url,
    _post_install_checks,
    install_skill,
)
from .pack import pack_skill
from .settings_io import _disable_in_settings, _enable_in_settings, _write_json_atomic
