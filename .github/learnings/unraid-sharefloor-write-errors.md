# Unraid shareFloor blocking writes to the Media share

**Date:** 2026-07-24  
**Branch:** main  
**Context:** qBittorrent downloads on Unraid were failing with write errors even though the underlying disk had free space.

---

## Problem

The Media share on the Unraid server rejected file writes from both the host and the qBittorrent container.

### Error observed

```text
touch: cannot touch '/mnt/user/Media/Downloads/test-host-write': No space left on device
```

```text
touch: cannot touch '/downloads/test-write': No space left on device
```

```text
touch: cannot touch '/downloads/incomplete/test-write': No space left on device
```

The same behavior also appeared during later verification attempts:

```text
touch: cannot touch '/mnt/user/Media/Downloads/test-after-fix': No space left on device
```

```text
touch: cannot touch '/downloads/test-container': No space left on device
```

## Root cause

The Unraid share configuration for the Media share had a very high `shareFloor` value:

```text
shareFloor="1171678003"
```

That value is approximately 1.1 TB in KB. The underlying disk had about 1.1 TB free, so the share was effectively sitting at the configured cutoff and Unraid's `shfs` layer blocked writes.

## What we verified

- Writing directly to the underlying disk worked:

```text
touch /mnt/disk3/Media/Downloads/test-direct-write
```

- The filesystem itself was healthy.
- The issue was the Unraid share-level floor policy, not a disk or inode exhaustion problem.

## Fix applied

1. Changed the Media share floor from `1171678003` KB to `104857600` KB (100 GB).
2. Remounted `shfs` so the new floor value was applied.
3. Restarted the qBittorrent container so its bind mounts refreshed.

### Commands used

```bash
# Write the corrected shareFloor value into the Unraid share config
cat > /boot/config/shares/Media.cfg << 'ENDOFFILE'
shareComment=""
shareInclude=""
shareExclude=""
shareUseCache="no"
shareCachePool=""
shareCachePool2=""
shareCOW="auto"
shareAllocator="highwater"
shareSplitLevel=""
shareFloor="104857600"
shareExport="e"
shareCaseSensitive="auto"
shareSecurity="public"
shareReadList=""
shareWriteList=""
shareVolsizelimit=""
shareExportNFS="-"
shareExportNFSFsid="0"
shareSecurityNFS="public"
shareHostListNFS=""
ENDOFFILE

# Verify the new value
cat /boot/config/shares/Media.cfg | grep shareFloor

# Remount shfs so the share policy is reloaded
/usr/libexec/unraid/shfs /mnt/user -disks 11 -o default_permissions,allow_other,noatime -o remember=0

# Restart the qBittorrent container so its bind mounts refresh
docker restart qBittorrentvpn
```

### Commands used

```bash
# Write the corrected shareFloor value into the Unraid share config
cat > /boot/config/shares/Media.cfg << 'ENDOFFILE'
shareComment=""
shareInclude=""
shareExclude=""
shareUseCache="no"
shareCachePool=""
shareCachePool2=""
shareCOW="auto"
shareAllocator="highwater"
shareSplitLevel=""
shareFloor="104857600"
shareExport="e"
shareCaseSensitive="auto"
shareSecurity="public"
shareReadList=""
shareWriteList=""
shareVolsizelimit=""
shareExportNFS="-"
shareExportNFSFsid="0"
shareSecurityNFS="public"
shareHostListNFS=""
ENDOFFILE

# Verify the new value
cat /boot/config/shares/Media.cfg | grep shareFloor

# Remount shfs so the share policy is reloaded
/usr/libexec/unraid/shfs /mnt/user -disks 11 -o default_permissions,allow_other,noatime -o remember=0

# Restart the qBittorrent container so its bind mounts refresh
docker restart qBittorrentvpn
```

## Result

After the change, both host and container writes succeeded:

```text
SUCCESS: Host write works
SUCCESS: Container write works
SUCCESS: Incomplete write works
```

## Lesson learned

A high `shareFloor` can block writes even when the underlying storage still has available space. For troubleshooting, always check:

- `cat /boot/config/shares/Media.cfg`
- `df -h /mnt/disk3`
- direct write tests to the backing disk
- host/container write tests against the mounted share


