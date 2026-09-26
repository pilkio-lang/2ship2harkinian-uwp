from pathlib import Path
import sys

root = Path(sys.argv[1])

def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f"{label}: anchor not found")
    return text.replace(old, new, 1)

# 1) Generate US + FR converted text tables.
p = root / "ports" / "uwp" / "tools" / "generate_build_stubs.py"
s = p.read_text(encoding="utf-8")
old = '''    for source_name in ("define_courses.inc.c", "define_text.inc.c"):
        preprocessed = output_root / "text" / "us" / f"{source_name}.preprocessed"
        preprocessed.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                clang,
                "-E",
                "-P",
                "-x",
                "c",
                "-DVERSION_US",
                "-I",
                "text/us",
                "-I",
                "text",
                str(repo_root / "text" / source_name),
                "-o",
                str(preprocessed),
            ],
            cwd=str(repo_root),
            check=True,
        )
        subprocess.run(
            [
                str(repo_root / "tools" / "textconv.exe"),
                "charmap.txt",
                str(preprocessed),
                str(output_root / "text" / "us" / source_name),
            ],
            cwd=str(repo_root),
            env=env,
            check=True,
        )
        preprocessed.unlink()
'''
new = '''    # Keep runtime NTSC-US, but generate the official French text tables too.
    for language in ("us", "fr"):
        for source_name in ("define_courses.inc.c", "define_text.inc.c"):
            preprocessed = output_root / "text" / language / f"{source_name}.preprocessed"
            preprocessed.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [
                    clang,
                    "-E",
                    "-P",
                    "-x",
                    "c",
                    "-DVERSION_US",
                    "-I",
                    f"text/{language}",
                    "-I",
                    "text",
                    str(repo_root / "text" / source_name),
                    "-o",
                    str(preprocessed),
                ],
                cwd=str(repo_root),
                check=True,
            )
            subprocess.run(
                [
                    str(repo_root / "tools" / "textconv.exe"),
                    "charmap.txt",
                    str(preprocessed),
                    str(output_root / "text" / language / source_name),
                ],
                cwd=str(repo_root),
                env=env,
                check=True,
            )
            preprocessed.unlink()
'''
s = replace_once(s, old, new, "text generator")
p.write_text(s, encoding="utf-8")

# 2) Build the true PAL text renderer only for ingame_menu.c.
p = root / "ports" / "uwp" / "CMakeLists.txt"
s = p.read_text(encoding="utf-8")
block = '''target_sources(sm64ex_game PRIVATE
    uwp/compat/dirent.cpp
    uwp/compat/sdl_winrt_stubs.cpp
    uwp/compat/uwp_demo_data.c
    uwp/compat/uwp_display_size.cpp
    uwp/compat/uwp_local_folder.cpp
    uwp/compat/uwp_storage_root.c
    uwp/gfx/gfx_dxgi_uwp.cpp
    ${SM64EX_GAME_SOURCES}
)
'''
replacement = block + '''
# French text-only PAL presentation layer. The rest of the target stays US.
target_sources(sm64ex_game PRIVATE
    "${SM64EX_ROOT}/bin/eu/translation_fr.c"
)

# Compile only the text renderer through the EU presentation path.
set_source_files_properties("${SM64EX_ROOT}/src/game/ingame_menu.c" PROPERTIES
    COMPILE_OPTIONS "/UVERSION_US"
    COMPILE_DEFINITIONS "VERSION_EU=1;SM64EX_FRENCH_TEXT=1"
)
'''
s = replace_once(s, block, replacement, "CMake text renderer")
p.write_text(s, encoding="utf-8")

# 3) Patch US font LUTs so the PAL renderer has French-specific glyph support.
p = root / "bin" / "segment2.c"
s = p.read_text(encoding="utf-8")

def ia4_texture(points):
    pix = [[0 for _ in range(8)] for _ in range(16)]
    for x, y in points:
        if 0 <= x < 8 and 0 <= y < 16:
            pix[y][x] = 0xF
    out = []
    for y in range(16):
        for x in range(0, 8, 2):
            out.append((pix[y][x] << 4) | pix[y][x + 1])
    return out

patterns = {
    "grave": [(2,2),(2,3),(3,3),(3,4)],
    "acute": [(5,2),(5,3),(4,3),(4,4)],
    "circumflex": [(2,4),(3,3),(4,2),(5,3),(6,4)],
    "umlaut": [(2,3),(3,3),(5,3),(6,3)],
    "cedilla": [(3,11),(4,12),(3,13),(2,13)],
}
defs = []
for name, pts in patterns.items():
    vals = ia4_texture(pts)
    rows = []
    for i in range(0, len(vals), 8):
        rows.append("    " + ", ".join(f"0x{v:02X}" for v in vals[i:i+8]) + ",")
    defs.append(f"ALIGNED8 static const u8 texture_font_char_fr_{name}[] = {{\n" + "\n".join(rows) + "\n};\n")
accent_defs = "\n".join(defs) + "\n"

font_marker = "const u8 *const main_font_lut[] = {"
s = replace_once(s, font_marker, accent_defs + font_marker, "accent texture insertion")

# Patch US main_font_lut slots 0xE3..0xEB.
start = s.index("#elif defined(VERSION_US) // US Font Table")
end = s.index("#elif defined(VERSION_JP) || defined(VERSION_SH)", start)
prefix = s[:start]
section = s[start:end]
suffix = s[end:]
directive, body = section.split("\n", 1)
tokens = [t.strip() for t in body.replace("\n", " ").split(",") if t.strip()]
if len(tokens) != 256:
    raise SystemExit(f"US main_font_lut expected 256 entries, got {len(tokens)}")
for idx, name in {
    0xE3:"texture_font_char_fr_grave",
    0xE4:"texture_font_char_fr_circumflex",
    0xE5:"texture_font_char_fr_umlaut",
    0xE6:"texture_font_char_fr_acute",
    0xE7:"texture_font_char_fr_grave",
    0xE8:"texture_font_char_fr_circumflex",
    0xE9:"texture_font_char_fr_umlaut",
    0xEA:"texture_font_char_fr_acute",
    0xEB:"texture_font_char_fr_cedilla",
}.items():
    tokens[idx] = name
lines = []
for i in range(0, 256, 4):
    lines.append("    " + ", ".join(f"{t:>38}" for t in tokens[i:i+4]) + ",")
s = prefix + directive + "\n" + "\n".join(lines) + "\n" + suffix

# Restore letters omitted from the US HUD LUT. The US ROM does not ship
# RGBA16 HUD glyphs for J/Q/V/X/Z, so embed tiny 16x16 replacements rather
# than pointing the LUT at identifiers which only exist in VERSION_EU.
def rgba16_hud_texture(rows):
    # 5x7 bitmap scaled 2x and centered in a 16x16 RGBA5551 texture.
    pix = [[False for _ in range(16)] for _ in range(16)]
    scale = 2
    ox = 3
    oy = 1
    for yy, row in enumerate(rows):
        for xx, bit in enumerate(row):
            if bit == "1":
                for dy in range(scale):
                    for dx in range(scale):
                        px = ox + xx * scale + dx
                        py = oy + yy * scale + dy
                        if 0 <= px < 16 and 0 <= py < 16:
                            pix[py][px] = True
    out = []
    for y in range(16):
        for x in range(16):
            value = 0xFFFF if pix[y][x] else 0x0000
            out.extend([(value >> 8) & 0xFF, value & 0xFF])
    return out

hud_patterns = {
    "J": ["00111","00010","00010","00010","00010","10010","01100"],
    "Q": ["01110","10001","10001","10001","10101","10010","01101"],
    "V": ["10001","10001","10001","10001","10001","01010","00100"],
    "X": ["10001","10001","01010","00100","01010","10001","10001"],
    "Z": ["11111","00001","00010","00100","01000","10000","11111"],
}
hud_defs = []
for letter, rows in hud_patterns.items():
    vals = rgba16_hud_texture(rows)
    body_rows = []
    for i in range(0, len(vals), 16):
        body_rows.append("    " + ", ".join(f"0x{v:02X}" for v in vals[i:i+16]) + ",")
    hud_defs.append(
        f"ALIGNED8 static const u8 texture_hud_char_fr_{letter}[] = {{\n"
        + "\n".join(body_rows) + "\n};\n"
    )

hud_marker = "const u8 *const main_hud_lut[] = {"
s = replace_once(s, hud_marker, "\n".join(hud_defs) + "\n" + hud_marker, "French HUD glyph insertion")

hud_start = s.index("const u8 *const main_hud_lut[] = {")
hud_end = s.index("};", hud_start)
hud_block = s[hud_start:hud_end]
u0 = hud_block.index("#elif defined(VERSION_US)")
u1 = hud_block.index("#else", u0)
pre = hud_block[:u0]
us_section = hud_block[u0:u1]
post = hud_block[u1:]
udirective, ubody = us_section.split("\n", 1)
utokens = [t.strip() for t in ubody.replace("\n", " ").split(",") if t.strip()]
for idx, name in {
    19:"texture_hud_char_fr_J",
    26:"texture_hud_char_fr_Q",
    31:"texture_hud_char_fr_V",
    33:"texture_hud_char_fr_X",
    35:"texture_hud_char_fr_Z",
}.items():
    if idx >= len(utokens):
        raise SystemExit("US HUD LUT index out of range")
    utokens[idx] = name
ulines = []
for i in range(0, len(utokens), 4):
    ulines.append("    " + ", ".join(f"{t:>35}" for t in utokens[i:i+4]) + ",")
new_hud_block = pre + udirective + "\n" + "\n".join(ulines) + "\n" + post
s = s[:hud_start] + new_hud_block + s[hud_end:]
p.write_text(s, encoding="utf-8")

# 4) Force the EU renderer language to French and support cedilla as base+mark.
p = root / "src" / "game" / "ingame_menu.c"
s = p.read_text(encoding="utf-8")
s = s.replace("eu_get_language()", "LANGUAGE_FRENCH")

generic_anchor = '''            case DIALOG_CHAR_LOWER_I_CIRCUMFLEX:
            case DIALOG_CHAR_LOWER_I_UMLAUT:
                render_lowercase_diacritic(&xCoord, &yCoord, DIALOG_CHAR_I_NO_DIA, str[strPos] & 0xF);
                break;
'''
generic_add = generic_anchor + '''            case 0xED: // Ç
                render_generic_char_at_pos(xCoord, yCoord, ASCII_TO_DIALOG('C'));
                render_generic_char_at_pos(xCoord, yCoord, 0xEB);
                xCoord += gDialogCharWidths[ASCII_TO_DIALOG('C')];
                break;
            case 0xEE: // ç
                render_generic_char_at_pos(xCoord, yCoord, ASCII_TO_DIALOG('c'));
                render_generic_char_at_pos(xCoord, yCoord, 0xEB);
                xCoord += gDialogCharWidths[ASCII_TO_DIALOG('c')];
                break;
'''
s = replace_once(s, generic_anchor, generic_add, "generic cedilla")

dialog_anchor = '''            case DIALOG_CHAR_LOWER_I_CIRCUMFLEX:
            case DIALOG_CHAR_LOWER_I_UMLAUT:
                render_dialog_lowercase_diacritic(dialog, DIALOG_CHAR_I_NO_DIA, strChar & 0xF);
                break;
'''
dialog_add = dialog_anchor + '''            case 0xED: // Ç
                render_generic_dialog_char_at_pos(dialog, gDialogX, gDialogY, ASCII_TO_DIALOG('C'));
                render_generic_dialog_char_at_pos(dialog, gDialogX, gDialogY, 0xEB);
                gDialogX += gDialogCharWidths[ASCII_TO_DIALOG('C')];
                break;
            case 0xEE: // ç
                render_generic_dialog_char_at_pos(dialog, gDialogX, gDialogY, ASCII_TO_DIALOG('c'));
                render_generic_dialog_char_at_pos(dialog, gDialogX, gDialogY, 0xEB);
                gDialogX += gDialogCharWidths[ASCII_TO_DIALOG('c')];
                break;
'''
s = replace_once(s, dialog_anchor, dialog_add, "dialog cedilla")
p.write_text(s, encoding="utf-8")

# 5) Keep file-select US logic, but use PAL/French coordinates and centering.
p = root / "src" / "menu" / "file_select.c"
s = p.read_text(encoding="utf-8")

us_constants = '''#elif VERSION_US
    #define SELECT_FILE_X 93
    #define SCORE_X 52
    #define COPY_X 117
    #define ERASE_X 177
    #define SOUNDMODE_X1 sSoundTextX
    #define SAVEFILE_X1 92
    #define SAVEFILE_X2 209
    #define MARIOTEXT_X1 92
    #define MARIOTEXT_X2 207
'''
fr_constants = '''#elif defined(VERSION_US) && defined(SM64EX_FRENCH_TEXT)
    #define SELECT_FILE_X 93
    #define SCORE_X 52
    #define COPY_X 117
    #define ERASE_X 177
    #define SOUNDMODE_X1 sSoundTextX
    #define SAVEFILE_X1 97
    #define SAVEFILE_X2 204
    #define MARIOTEXT_X1 97
    #define MARIOTEXT_X2 204
#elif VERSION_US
    #define SELECT_FILE_X 93
    #define SCORE_X 52
    #define COPY_X 117
    #define ERASE_X 177
    #define SOUNDMODE_X1 sSoundTextX
    #define SAVEFILE_X1 92
    #define SAVEFILE_X2 209
    #define MARIOTEXT_X1 92
    #define MARIOTEXT_X2 207
'''
s = replace_once(s, us_constants, fr_constants, "file-select PAL coords")

main_start = '''void print_main_menu_strings(void) {
    // Print "SELECT FILE" text
    gSPDisplayList(gDisplayListHead++, dl_rgba16_text_begin);
    gDPSetEnvColor(gDisplayListHead++, 255, 255, 255, sTextBaseAlpha);
#ifndef VERSION_EU
    print_hud_lut_string(HUD_LUT_DIFF, SELECT_FILE_X, 35, textSelectFile);
#endif
'''
main_new = '''void print_main_menu_strings(void) {
#ifdef SM64EX_FRENCH_TEXT
    s16 centeredX;
#endif
    // Print "SELECT FILE" text
    gSPDisplayList(gDisplayListHead++, dl_rgba16_text_begin);
    gDPSetEnvColor(gDisplayListHead++, 255, 255, 255, sTextBaseAlpha);
#ifndef VERSION_EU
#ifdef SM64EX_FRENCH_TEXT
    centeredX = get_str_x_pos_from_center_scale(160, textSelectFile, 12.0f);
    print_hud_lut_string(HUD_LUT_GLOBAL, centeredX, 35, textSelectFile);
#else
    print_hud_lut_string(HUD_LUT_DIFF, SELECT_FILE_X, 35, textSelectFile);
#endif
#endif
'''
s = replace_once(s, main_start, main_new, "file-select title")

menu_names = '''   // Print menu names
    gSPDisplayList(gDisplayListHead++, dl_ia_text_begin);
    gDPSetEnvColor(gDisplayListHead++, 255, 255, 255, sTextBaseAlpha);
    print_generic_string(SCORE_X, 39, textScore);
    print_generic_string(COPY_X, 39, textCopy);
    print_generic_string(ERASE_X, 39, textErase);
#if !defined(VERSION_JP) && !defined(VERSION_SH)
    sSoundTextX = get_str_x_pos_from_center(254, textSoundModes[sSoundMode], 10.0f);
#endif
    print_generic_string(SOUNDMODE_X1, 39, textSoundModes[sSoundMode]);
'''
menu_names_new = '''   // Print menu names
    gSPDisplayList(gDisplayListHead++, dl_ia_text_begin);
    gDPSetEnvColor(gDisplayListHead++, 255, 255, 255, sTextBaseAlpha);
#ifdef SM64EX_FRENCH_TEXT
    centeredX = get_str_x_pos_from_center(76, textScore, 10.0f);
    print_generic_string(centeredX, 39, textScore);
    centeredX = get_str_x_pos_from_center(131, textCopy, 10.0f);
    print_generic_string(centeredX, 39, textCopy);
    centeredX = get_str_x_pos_from_center(189, textErase, 10.0f);
    print_generic_string(centeredX, 39, textErase);
    centeredX = get_str_x_pos_from_center(245, textSoundModes[sSoundMode], 10.0f);
    print_generic_string(centeredX, 39, textSoundModes[sSoundMode]);
#else
    print_generic_string(SCORE_X, 39, textScore);
    print_generic_string(COPY_X, 39, textCopy);
    print_generic_string(ERASE_X, 39, textErase);
#if !defined(VERSION_JP) && !defined(VERSION_SH)
    sSoundTextX = get_str_x_pos_from_center(254, textSoundModes[sSoundMode], 10.0f);
#endif
    print_generic_string(SOUNDMODE_X1, 39, textSoundModes[sSoundMode]);
#endif
'''
s = replace_once(s, menu_names, menu_names_new, "file-select labels")
p.write_text(s, encoding="utf-8")

# 6) Expose the EU centering helper to US file_select when French text is enabled.
p = root / "src" / "game" / "ingame_menu.h"
s = p.read_text(encoding="utf-8")
old_decl = """#if defined(VERSION_JP) || defined(VERSION_EU)
s16 get_str_x_pos_from_center_scale(s16 centerPos, u8 *str, f32 scale);
#endif"""
new_decl = """#if defined(VERSION_JP) || defined(VERSION_EU) || defined(SM64EX_FRENCH_TEXT)
s16 get_str_x_pos_from_center_scale(s16 centerPos, u8 *str, f32 scale);
#endif"""
s = replace_once(s, old_decl, new_decl, "scaled-centering declaration")
p.write_text(s, encoding="utf-8")

print("Applied FR v5: native EU text renderer + PAL layout on NTSC runtime.")
