# Dangerous Mountain Together – Hebrew (Tirgumim)

Hebrew for every string in the game's text table (Game.locres: menus, options, lobby and co-op, saves,
customization, dialogs, loading tip; 138 strings, `tools/make_translation.py`). Hebrew is active only when
the game is started from the Tirgumim launcher ("שחק בעברית"); a Steam start stays English.

## How it works
- `DMT/Binaries/Win64/dsound.dll`: the generic Tirgumim proxy (`tools/proxy`, exports forwarded to the
  system dsound.dll). Only with `-tirgumim_he` on the command line it adds
  `tirgumim/he/zzz_tirgumim_he_P.pak` to the game's `DMT/Content/Paks` listing (`redirect.cfg`), so
  UE5 mounts it after the game's pak.
- The pak (UnrealPak, v11, uncompressed) holds the English `Game.locres` with the Hebrew text and the
  Tango Sans (Regular/Bold) and Akira fonts with Hebrew letters from Rubik (OFL). A cooked `.ufont` here is
  `u32 length + TTF + 4 zero bytes`; Akira (CFF) is converted to TrueType first. UE5 does bidi itself.

## Build
```
python tools/extract.py          (UnrealPak from Unreal Engine 5.8: D:\UE\UE_5.8, or set UNREALPAK)
python tools/make_translation.py
tools\proxy\build.cmd dsound <target dir>   (then copy tirgumim_proxy.dll as the built proxy)
python tools/build.py
tools\make-pack.cmd 1.0.0
```
Fonts: Rubik instances in `../tomb-raider-2013/tools/bin/fonts` (OFL, not committed).
