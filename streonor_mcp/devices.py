"""One registry for community device specs; generic profile tooling lives elsewhere."""
from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceSpec:
    id: str
    name: str
    software_ids: tuple[str, ...]
    key_count: int | None = None
    dial_count: int | None = None
    boot_logo_size: tuple[int, int] | None = None
    boot_logo_format: str | None = None
    boot_logo_upload: str | None = None
    supported: bool = False


# Add new hardware here. Leave unknown values as None/'unknown'; never infer a write protocol.
DEVICES = (
    DeviceSpec('streonor-s6-mini', 'STREONOR S6 Mini', ('StreonorS6',), 6, 3, (320, 240), 'unknown', None, True),
    DeviceSpec('streonor-s10-pro', 'STREONOR S10 Pro', ('StreonorS10',), supported=False),
    DeviceSpec('streonor-s15-standard', 'STREONOR S15 Standard', ('StreonorS15',), supported=False),
    DeviceSpec('streonor-s32-max', 'STREONOR S32 Max', ('StreonorS32',), supported=False),
)


def get_device(device_id):
    for spec in DEVICES:
        if device_id == spec.id or device_id in spec.software_ids:
            return spec
    raise ValueError(f'Unsupported device: {device_id}')


def describe(device_id):
    spec = get_device(device_id)
    return {'id': spec.id, 'name': spec.name, 'software_ids': list(spec.software_ids),
            'keys': spec.key_count, 'dials': spec.dial_count,
            'boot_logo_size': list(spec.boot_logo_size) if spec.boot_logo_size else None,
            'boot_logo_format': spec.boot_logo_format, 'boot_logo_upload': spec.boot_logo_upload,
            'supported': spec.supported}
