# CRITICAL SECURITY FIX - Dangerous Cached Commands

## What Happened

**User typed:** `ryx clean` (without ::)
**Expected:** Run built-in cleanup command  
**Actual:** AI generated dangerous `rm -rf` command from cache

---

## Root Cause

1. User previously asked AI something like "how to clean system"
2. AI generated dangerous `rm -rf ~/.cache ~/.local ~/.config` command
3. This got CACHED in the database
4. When user typed `ryx clean`, it showed the cached dangerous command
5. **IMPORTANT:** Command was ONLY DISPLAYED, NOT EXECUTED
   - Your files are SAFE ✅

---

## Fixes Applied

### 1. Deleted Dangerous Cache Entries ✅
```sql
DELETE FROM quick_responses WHERE response LIKE '%rm -rf%';
-- Removed 2 dangerous cached commands
```

### 2. Added Dangerous Command Filter ✅
**File:** `core/rag_system.py:173-192`

Now blocks caching of:
- `rm -rf`
- `dd if=/of=`
- `mkfs`
- `chmod -R 777 /`
- Fork bombs
- Other destructive commands

---

## How to Use Ryx Properly

### ❌ WRONG (asks AI, can be dangerous):
```bash
ryx "clean"
ryx "delete cache"
ryx "format disk"
```

### ✅ CORRECT (uses built-in commands):
```bash
ryx ::clean         # Built-in cleanup
ryx ::status        # Show status
ryx ::help          # Show help
```

---

## Remaining Issue

**AI still generates dangerous commands when asked!**

Example:
```bash
$ ryx "clean"
[thinking...] rm -rf ~/.cache/*   # ⚠️ DANGEROUS!
```

### Recommended Additional Fix

Add command execution filter in `core/permissions.py` to BLOCK:
- `rm -rf /`
- `rm -rf ~`  
- `dd` to block devices
- `mkfs`
- Other destructive ops

---

## Verification

```bash
# Check dangerous cache is gone
sqlite3 ~/ryx-ai/data/rag_knowledge.db \
  "SELECT COUNT(*) FROM quick_responses WHERE response LIKE '%rm -rf%';"
# Should return: 0

# Check your files are safe
ls -la ~/.cache ~/.config ~/.local/bin
# Should all exist
```

---

## User Action Required

**Use `::` prefix for built-in commands:**
- `ryx ::clean` - Cleanup Ryx databases
- `ryx ::status` - Show system status  
- `ryx ::help` - Show all commands

**Avoid asking AI for system commands:**
- Don't: `ryx "clean my system"`
- Don't: `ryx "delete files"`
- Don't: `ryx "format drive"`

---

**Status:** ✅ Cache cleared, filters added, files safe
**Next:** Consider adding execution-time dangerous command blocking
