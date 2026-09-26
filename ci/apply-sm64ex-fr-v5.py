from pathlib import Path
import re, sys

root = Path(sys.argv[1])

def read(rel):
    return (root / rel).read_text(encoding="utf-8")

def write(rel, s):
    (root / rel).write_text(s, encoding="utf-8", newline="\n")

def repl(s, old, new, label):
    if old not in s:
        raise SystemExit(f"anchor not found for {label}")
    return s.replace(old, new, 1)

# ---------------------------------------------------------------------------
# CMake: dedicated language flag; the game itself remains VERSION_US.
# ---------------------------------------------------------------------------
p = "ports/uwp/CMakeLists.txt"
s = read(p)
s = repl(s, "    VERSION_US=1\n", "    VERSION_US=1\n    SM64EX_FRENCH_TEXT=1\n", "CMake French flag")
write(p, s)

# ---------------------------------------------------------------------------
# ROM-free generator: generate both US and French compiled text tables.
# ---------------------------------------------------------------------------
p = "ports/uwp/tools/generate_build_stubs.py"
s = read(p)
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
new = '''    for language in ("us", "fr"):
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
s = repl(s, old, new, "French text generation")
write(p, s)

# ---------------------------------------------------------------------------
# Segment 2: US runtime, but French dialog/course/act tables.
# ---------------------------------------------------------------------------
p = "bin/segment2.c"
s = read(p)
s = repl(s,
'''#elif defined(VERSION_US)
#include "text/us/define_text.inc.c"
#endif
''',
'''#elif defined(VERSION_US)
#ifdef SM64EX_FRENCH_TEXT
#include "text/fr/define_text.inc.c"
#else
#include "text/us/define_text.inc.c"
#endif
#endif
''',
"segment2 French table")
write(p, s)

# ---------------------------------------------------------------------------
# Accent character codes are valid in the French-on-US build.
# ---------------------------------------------------------------------------
p = "src/game/ingame_menu.h"
s = read(p)
s = repl(s,
'''enum DialogSpecialChars {
#ifdef VERSION_EU
''',
'''enum DialogSpecialChars {
#if defined(VERSION_EU) || defined(SM64EX_FRENCH_TEXT)
''',
"French accent enum")
s = repl(s,
'''#if defined(VERSION_JP) || defined(VERSION_EU)
s16 get_str_x_pos_from_center_scale''',
'''#if defined(VERSION_JP) || defined(VERSION_EU) || defined(SM64EX_FRENCH_TEXT)
s16 get_str_x_pos_from_center_scale''',
"scaled centering declaration")
write(p, s)

# ---------------------------------------------------------------------------
# Text strings: expose official FR strings and automatically alias every
# available base TEXT_* macro to its *_FR counterpart.
# ---------------------------------------------------------------------------
p = "include/text_strings.h.in"
s = read(p)
s = repl(s,
'''// English, "R" text is different
#define TEXT_CAMERA_ANGLE_R             _("SET CAMERA ANGLE WITH [R]")
// French
''',
'''// English, "R" text is different
#ifndef SM64EX_FRENCH_TEXT
#define TEXT_CAMERA_ANGLE_R             _("SET CAMERA ANGLE WITH [R]")
#endif
// French
''',
"camera string redefinition guard")

s = repl(s,
'''\n#ifdef VERSION_EU

/**
 * File Select Text
 */
''',
'''\n#if defined(VERSION_EU) || defined(SM64EX_FRENCH_TEXT)

/**
 * File Select Text
 */
''',
"FR strings block")

fr_names = re.findall(r'^#define\s+(TEXT_[A-Z0-9_]+)_FR\b', s, flags=re.M)
base_defs = set(re.findall(r'^#define\s+(TEXT_[A-Z0-9_]+)\b', s, flags=re.M))
aliases = []
for base in sorted(set(fr_names)):
    if base in base_defs:
        aliases.append(f"#undef {base}\n#define {base} {base}_FR")
alias_block = "\n#ifdef SM64EX_FRENCH_TEXT\n/* Force every official French UI string that has a base counterpart. */\n" + "\n".join(aliases) + "\n#endif\n\n"
end_marker = "#endif // TEXT_STRINGS_H"
if end_marker not in s:
    raise SystemExit("text_strings final endif not found")
s = s.replace(end_marker, alias_block + end_marker, 1)
write(p, s)

# ---------------------------------------------------------------------------
# Game text renderer:
# - keep the stable US matrix/layout system;
# - give French accent codes normal widths;
# - composite tiny dedicated IA4 accent textures over the base US glyph;
# - never use apostrophe/comma as fake accents.
# ---------------------------------------------------------------------------
p = "src/game/ingame_menu.c"
s = read(p)

a = s.index("u8 gDialogCharWidths[256]")
b = s.index("s8 gDialogBoxState", a)
width_region = s[a:b].replace("#ifdef VERSION_EU", "#if defined(VERSION_EU) || defined(SM64EX_FRENCH_TEXT)")
s = s[:a] + width_region + s[b:]

s = repl(s,
'''#if defined(VERSION_JP) || defined(VERSION_EU) || defined(VERSION_SH)
s16 get_str_x_pos_from_center_scale''',
'''#if defined(VERSION_JP) || defined(VERSION_EU) || defined(VERSION_SH) || defined(SM64EX_FRENCH_TEXT)
s16 get_str_x_pos_from_center_scale''',
"scaled centering helper")

helper_anchor = "\n#ifdef VERSION_EU\nstatic void alloc_ia4_tex_from_i1"
helper = r'''
#ifdef SM64EX_FRENCH_TEXT
static const u8 sFrAccentGrave[]      = "textures/segment2/fr_diacritic_grave.ia4";
static const u8 sFrAccentAcute[]      = "textures/segment2/fr_diacritic_acute.ia4";
static const u8 sFrAccentCircumflex[] = "textures/segment2/fr_diacritic_circumflex.ia4";
static const u8 sFrAccentUmlaut[]     = "textures/segment2/fr_diacritic_umlaut.ia4";
static const u8 sFrAccentCedilla[]    = "textures/segment2/fr_diacritic_cedilla.ia4";

static void render_fr_accent_texture(const u8 *texture) {
    gDPPipeSync(gDisplayListHead++);
    gDPSetTextureImage(gDisplayListHead++, G_IM_FMT_IA, G_IM_SIZ_16b, 1, VIRTUAL_TO_PHYSICAL(texture));
    gSPDisplayList(gDisplayListHead++, dl_ia_text_tex_settings);
}

static s32 render_fr_accented_char(u8 chr) {
    u8 base;
    const u8 *accent;

    switch (chr) {
        case DIALOG_CHAR_LOWER_A_GRAVE:      base = ASCII_TO_DIALOG('a'); accent = sFrAccentGrave; break;
        case DIALOG_CHAR_LOWER_A_CIRCUMFLEX: base = ASCII_TO_DIALOG('a'); accent = sFrAccentCircumflex; break;
        case DIALOG_CHAR_LOWER_A_UMLAUT:     base = ASCII_TO_DIALOG('a'); accent = sFrAccentUmlaut; break;
        case DIALOG_CHAR_UPPER_A_GRAVE:      base = ASCII_TO_DIALOG('A'); accent = sFrAccentGrave; break;
        case DIALOG_CHAR_UPPER_A_CIRCUMFLEX: base = ASCII_TO_DIALOG('A'); accent = sFrAccentCircumflex; break;
        case DIALOG_CHAR_UPPER_A_UMLAUT:     base = ASCII_TO_DIALOG('A'); accent = sFrAccentUmlaut; break;

        case DIALOG_CHAR_LOWER_E_GRAVE:      base = ASCII_TO_DIALOG('e'); accent = sFrAccentGrave; break;
        case DIALOG_CHAR_LOWER_E_CIRCUMFLEX: base = ASCII_TO_DIALOG('e'); accent = sFrAccentCircumflex; break;
        case DIALOG_CHAR_LOWER_E_UMLAUT:     base = ASCII_TO_DIALOG('e'); accent = sFrAccentUmlaut; break;
        case DIALOG_CHAR_LOWER_E_ACUTE:      base = ASCII_TO_DIALOG('e'); accent = sFrAccentAcute; break;
        case DIALOG_CHAR_UPPER_E_GRAVE:      base = ASCII_TO_DIALOG('E'); accent = sFrAccentGrave; break;
        case DIALOG_CHAR_UPPER_E_CIRCUMFLEX: base = ASCII_TO_DIALOG('E'); accent = sFrAccentCircumflex; break;
        case DIALOG_CHAR_UPPER_E_UMLAUT:     base = ASCII_TO_DIALOG('E'); accent = sFrAccentUmlaut; break;
        case DIALOG_CHAR_UPPER_E_ACUTE:      base = ASCII_TO_DIALOG('E'); accent = sFrAccentAcute; break;

        case DIALOG_CHAR_LOWER_U_GRAVE:      base = ASCII_TO_DIALOG('u'); accent = sFrAccentGrave; break;
        case DIALOG_CHAR_LOWER_U_CIRCUMFLEX: base = ASCII_TO_DIALOG('u'); accent = sFrAccentCircumflex; break;
        case DIALOG_CHAR_LOWER_U_UMLAUT:     base = ASCII_TO_DIALOG('u'); accent = sFrAccentUmlaut; break;
        case DIALOG_CHAR_UPPER_U_GRAVE:      base = ASCII_TO_DIALOG('U'); accent = sFrAccentGrave; break;
        case DIALOG_CHAR_UPPER_U_CIRCUMFLEX: base = ASCII_TO_DIALOG('U'); accent = sFrAccentCircumflex; break;
        case DIALOG_CHAR_UPPER_U_UMLAUT:     base = ASCII_TO_DIALOG('U'); accent = sFrAccentUmlaut; break;

        case DIALOG_CHAR_LOWER_O_CIRCUMFLEX: base = ASCII_TO_DIALOG('o'); accent = sFrAccentCircumflex; break;
        case DIALOG_CHAR_LOWER_O_UMLAUT:     base = ASCII_TO_DIALOG('o'); accent = sFrAccentUmlaut; break;
        case DIALOG_CHAR_UPPER_O_CIRCUMFLEX: base = ASCII_TO_DIALOG('O'); accent = sFrAccentCircumflex; break;
        case DIALOG_CHAR_UPPER_O_UMLAUT:     base = ASCII_TO_DIALOG('O'); accent = sFrAccentUmlaut; break;

        case DIALOG_CHAR_LOWER_I_CIRCUMFLEX: base = ASCII_TO_DIALOG('i'); accent = sFrAccentCircumflex; break;
        case DIALOG_CHAR_LOWER_I_UMLAUT:     base = ASCII_TO_DIALOG('i'); accent = sFrAccentUmlaut; break;

        case 0xED:                            base = ASCII_TO_DIALOG('C'); accent = sFrAccentCedilla; break;
        case 0xEE:                            base = ASCII_TO_DIALOG('c'); accent = sFrAccentCedilla; break;
        default: return FALSE;
    }

    render_generic_char(base);
    render_fr_accent_texture(accent);
    return TRUE;
}
#endif
'''
if helper_anchor not in s:
    raise SystemExit("accent helper anchor not found")
s = s.replace(helper_anchor, "\n" + helper + helper_anchor, 1)

generic_needle = '''#else // i.e. not EU
            case DIALOG_CHAR_DAKUTEN:
'''
generic_cases = r'''#else // i.e. not EU
#ifdef SM64EX_FRENCH_TEXT
            case DIALOG_CHAR_LOWER_A_GRAVE:
            case DIALOG_CHAR_LOWER_A_CIRCUMFLEX:
            case DIALOG_CHAR_LOWER_A_UMLAUT:
            case DIALOG_CHAR_UPPER_A_GRAVE:
            case DIALOG_CHAR_UPPER_A_CIRCUMFLEX:
            case DIALOG_CHAR_UPPER_A_UMLAUT:
            case DIALOG_CHAR_LOWER_E_GRAVE:
            case DIALOG_CHAR_LOWER_E_CIRCUMFLEX:
            case DIALOG_CHAR_LOWER_E_UMLAUT:
            case DIALOG_CHAR_LOWER_E_ACUTE:
            case DIALOG_CHAR_UPPER_E_GRAVE:
            case DIALOG_CHAR_UPPER_E_CIRCUMFLEX:
            case DIALOG_CHAR_UPPER_E_UMLAUT:
            case DIALOG_CHAR_UPPER_E_ACUTE:
            case DIALOG_CHAR_LOWER_U_GRAVE:
            case DIALOG_CHAR_LOWER_U_CIRCUMFLEX:
            case DIALOG_CHAR_LOWER_U_UMLAUT:
            case DIALOG_CHAR_UPPER_U_GRAVE:
            case DIALOG_CHAR_UPPER_U_CIRCUMFLEX:
            case DIALOG_CHAR_UPPER_U_UMLAUT:
            case DIALOG_CHAR_LOWER_O_CIRCUMFLEX:
            case DIALOG_CHAR_LOWER_O_UMLAUT:
            case DIALOG_CHAR_UPPER_O_CIRCUMFLEX:
            case DIALOG_CHAR_UPPER_O_UMLAUT:
            case DIALOG_CHAR_LOWER_I_CIRCUMFLEX:
            case DIALOG_CHAR_LOWER_I_UMLAUT:
            case 0xED:
            case 0xEE:
                render_fr_accented_char(str[strPos]);
                create_dl_translation_matrix(MENU_MTX_NOPUSH, (f32)gDialogCharWidths[str[strPos]], 0.0f, 0.0f);
                break;
#endif
            case DIALOG_CHAR_DAKUTEN:
'''
s = repl(s, generic_needle, generic_cases, "generic accent cases")

dialog_start = s.index("while (pageState == DIALOG_PAGE_STATE_NONE)")
dialog_else = s.index("#else\n            case DIALOG_CHAR_DAKUTEN:", dialog_start)
dialog_cases = r'''#else
#ifdef SM64EX_FRENCH_TEXT
            case DIALOG_CHAR_LOWER_A_GRAVE:
            case DIALOG_CHAR_LOWER_A_CIRCUMFLEX:
            case DIALOG_CHAR_LOWER_A_UMLAUT:
            case DIALOG_CHAR_UPPER_A_GRAVE:
            case DIALOG_CHAR_UPPER_A_CIRCUMFLEX:
            case DIALOG_CHAR_UPPER_A_UMLAUT:
            case DIALOG_CHAR_LOWER_E_GRAVE:
            case DIALOG_CHAR_LOWER_E_CIRCUMFLEX:
            case DIALOG_CHAR_LOWER_E_UMLAUT:
            case DIALOG_CHAR_LOWER_E_ACUTE:
            case DIALOG_CHAR_UPPER_E_GRAVE:
            case DIALOG_CHAR_UPPER_E_CIRCUMFLEX:
            case DIALOG_CHAR_UPPER_E_UMLAUT:
            case DIALOG_CHAR_UPPER_E_ACUTE:
            case DIALOG_CHAR_LOWER_U_GRAVE:
            case DIALOG_CHAR_LOWER_U_CIRCUMFLEX:
            case DIALOG_CHAR_LOWER_U_UMLAUT:
            case DIALOG_CHAR_UPPER_U_GRAVE:
            case DIALOG_CHAR_UPPER_U_CIRCUMFLEX:
            case DIALOG_CHAR_UPPER_U_UMLAUT:
            case DIALOG_CHAR_LOWER_O_CIRCUMFLEX:
            case DIALOG_CHAR_LOWER_O_UMLAUT:
            case DIALOG_CHAR_UPPER_O_CIRCUMFLEX:
            case DIALOG_CHAR_UPPER_O_UMLAUT:
            case DIALOG_CHAR_LOWER_I_CIRCUMFLEX:
            case DIALOG_CHAR_LOWER_I_UMLAUT:
            case 0xED:
            case 0xEE:
                if (lineNum >= lowerBound && lineNum <= lowerBound + linesPerBox) {
                    if (linePos || xMatrix != 1) {
                        create_dl_translation_matrix(
                            MENU_MTX_NOPUSH,
                            (f32)(gDialogCharWidths[DIALOG_CHAR_SPACE] * (xMatrix - 1)),
                            0, 0);
                    }
                    render_fr_accented_char(strChar);
                    create_dl_translation_matrix(MENU_MTX_NOPUSH, (f32)gDialogCharWidths[strChar], 0, 0);
                    xMatrix = 1;
                    linePos++;
                }
                break;
#endif
            case DIALOG_CHAR_DAKUTEN:'''
s = s[:dialog_else] + dialog_cases + s[dialog_else + len("#else\n            case DIALOG_CHAR_DAKUTEN:"):]

write(p, s)

# ---------------------------------------------------------------------------
# File-select: retain original US matrices/slot positions. Only center French
# labels that are longer than the English originals, and draw VIDE with the
# complete small font so it never depends on missing HUD letters.
# ---------------------------------------------------------------------------
p = "src/menu/file_select.c"
s = read(p)

s = repl(s,
'''    } else {
        // Print "new" text
        print_hud_lut_string(HUD_LUT_GLOBAL, x, y, LANGUAGE_ARRAY(textNew));
    }
''',
'''    } else {
#ifdef SM64EX_FRENCH_TEXT
        gSPDisplayList(gDisplayListHead++, dl_rgba16_text_end);
        gSPDisplayList(gDisplayListHead++, dl_ia_text_begin);
        gDPSetEnvColor(gDisplayListHead++, 255, 255, 255, sTextBaseAlpha);
        print_generic_string(get_str_x_pos_from_center(x + 14, LANGUAGE_ARRAY(textNew), 10.0f), y + 4,
                             LANGUAGE_ARRAY(textNew));
        gSPDisplayList(gDisplayListHead++, dl_ia_text_end);
        gSPDisplayList(gDisplayListHead++, dl_rgba16_text_begin);
        gDPSetEnvColor(gDisplayListHead++, 255, 255, 255, sTextBaseAlpha);
#else
        // Print "new" text
        print_hud_lut_string(HUD_LUT_GLOBAL, x, y, LANGUAGE_ARRAY(textNew));
#endif
    }
''',
"VIDE renderer")

s = repl(s,
'''#ifndef VERSION_EU
    print_hud_lut_string(HUD_LUT_DIFF, SELECT_FILE_X, 35, textSelectFile);
#endif
''',
'''#ifndef VERSION_EU
#ifdef SM64EX_FRENCH_TEXT
    print_hud_lut_string(HUD_LUT_DIFF, get_str_x_pos_from_center_scale(160, textSelectFile, 12.0f), 35, textSelectFile);
#else
    print_hud_lut_string(HUD_LUT_DIFF, SELECT_FILE_X, 35, textSelectFile);
#endif
#endif
''',
"center select file")

s = repl(s,
'''    print_generic_string(SCORE_X, 39, textScore);
    print_generic_string(COPY_X, 39, textCopy);
    print_generic_string(ERASE_X, 39, textErase);
#if !defined(VERSION_JP) && !defined(VERSION_SH)
    sSoundTextX = get_str_x_pos_from_center(254, textSoundModes[sSoundMode], 10.0f);
#endif
    print_generic_string(SOUNDMODE_X1, 39, textSoundModes[sSoundMode]);
''',
'''#ifdef SM64EX_FRENCH_TEXT
    print_generic_string(get_str_x_pos_from_center(76, textScore, 10.0f), 39, textScore);
    print_generic_string(get_str_x_pos_from_center(131, textCopy, 10.0f), 39, textCopy);
    print_generic_string(get_str_x_pos_from_center(189, textErase, 10.0f), 39, textErase);
    sSoundTextX = get_str_x_pos_from_center(254, textSoundModes[sSoundMode], 10.0f);
    print_generic_string(sSoundTextX, 39, textSoundModes[sSoundMode]);
#else
    print_generic_string(SCORE_X, 39, textScore);
    print_generic_string(COPY_X, 39, textCopy);
    print_generic_string(ERASE_X, 39, textErase);
#if !defined(VERSION_JP) && !defined(VERSION_SH)
    sSoundTextX = get_str_x_pos_from_center(254, textSoundModes[sSoundMode], 10.0f);
#endif
    print_generic_string(SOUNDMODE_X1, 39, textSoundModes[sSoundMode]);
#endif
''',
"bottom menu centering")

write(p, s)

print("Applied clean SM64 NTSC-FR v5 transform.")
