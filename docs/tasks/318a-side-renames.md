# Task #318, part A: rename the duel side's mage words

A mechanical rename in two files: `src/wowforever/pvp/duel.py` and `src/wowforever/pvp/class_pvp.py`. No behaviour changes. Do not edit the tests.

## The renames
Replace whole words only, everywhere in those two files (code, comments and docstrings):

| Old | New |
|---|---|
| `MageSide` | `Side` |
| `nova_dps` | `melee_bonus_dps` |
| `barrier_per_min` | `absorb_per_min` |
| `t_mage` | `t_side` |
| `mage_uptime` | `side_uptime` |

The simplest way is one PowerShell command per file, run from the repo root:

```powershell
$f = 'src/wowforever/pvp/duel.py'; $s = [IO.File]::ReadAllText($f); foreach ($p in @(@('\bMageSide\b','Side'), @('\bnova_dps\b','melee_bonus_dps'), @('\bbarrier_per_min\b','absorb_per_min'), @('\bt_mage\b','t_side'), @('\bmage_uptime\b','side_uptime'))) { $s = [regex]::Replace($s, $p[0], $p[1]) }; [IO.File]::WriteAllText($f, $s, [Text.UTF8Encoding]::new($false))
```

Then the same with `$f = 'src/wowforever/pvp/class_pvp.py'`. Keep LF line endings; `WriteAllText` with that encoding does.

## Check
`git diff --stat` shows only those two files changed, and `git diff` has no change other than these five renames.

## Environment note
The package is already installed in `.venv` (editable). The tests are already updated for the whole of #318, so many fail now and still fail after this part (parts B-D fix them). That's expected; don't try to fix tests. Install nothing, make no network calls, and ask for no elevation.

## Done when
The two files contain none of the five old names: `Select-String -Path src/wowforever/pvp/duel.py,src/wowforever/pvp/class_pvp.py -Pattern 'MageSide|nova_dps|barrier_per_min|t_mage|mage_uptime'` prints nothing.
