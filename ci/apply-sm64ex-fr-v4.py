from pathlib import Path
import sys

root = Path(sys.argv[1])
menu = root / "src" / "game" / "ingame_menu.c"
s = menu.read_text(encoding="utf-8")

helper = r'''
#ifdef SM64EX_FRENCH_TEXT
/*
 * Absolute-position renderer for the official French tables on the NTSC-US
 * font/runtime.  The stock US renderer advances by cumulative model-view
 * translations.  That is fine for the original English tables, but French
 * diacritics and different spacing can make later glyphs drift.  Each glyph
 * below is positioned from an explicit x/y coordinate instead.
 */
static void render_fr_us_char_at(s16 x, s16 y, u8 chr) {
    create_dl_translation_matrix(MENU_MTX_PUSH, (f32)x, (f32)y, 0.0f);
    render_generic_char(chr);
    gSPPopMatrix(gDisplayListHead++, G_MTX_MODELVIEW);
}

static s32 render_fr_us_accented_at(s16 x, s16 y, u8 chr) {
    u8 base = 0;
    enum FrenchDiacritic mark = FR_DIA_NONE;

    switch (chr) {
        case DIALOG_CHAR_LOWER_A_GRAVE:      base = ASCII_TO_DIALOG('a'); mark = FR_DIA_GRAVE; break;
        case DIALOG_CHAR_LOWER_A_CIRCUMFLEX: base = ASCII_TO_DIALOG('a'); mark = FR_DIA_CIRCUMFLEX; break;
        case DIALOG_CHAR_LOWER_A_UMLAUT:     base = ASCII_TO_DIALOG('a'); mark = FR_DIA_UMLAUT; break;
        case DIALOG_CHAR_UPPER_A_GRAVE:      base = ASCII_TO_DIALOG('A'); mark = FR_DIA_GRAVE; break;
        case DIALOG_CHAR_UPPER_A_CIRCUMFLEX: base = ASCII_TO_DIALOG('A'); mark = FR_DIA_CIRCUMFLEX; break;
        case DIALOG_CHAR_UPPER_A_UMLAUT:     base = ASCII_TO_DIALOG('A'); mark = FR_DIA_UMLAUT; break;
        case DIALOG_CHAR_LOWER_E_GRAVE:      base = ASCII_TO_DIALOG('e'); mark = FR_DIA_GRAVE; break;
        case DIALOG_CHAR_LOWER_E_CIRCUMFLEX: base = ASCII_TO_DIALOG('e'); mark = FR_DIA_CIRCUMFLEX; break;
        case DIALOG_CHAR_LOWER_E_UMLAUT:     base = ASCII_TO_DIALOG('e'); mark = FR_DIA_UMLAUT; break;
        case DIALOG_CHAR_LOWER_E_ACUTE:      base = ASCII_TO_DIALOG('e'); mark = FR_DIA_ACUTE; break;
        case DIALOG_CHAR_UPPER_E_GRAVE:      base = ASCII_TO_DIALOG('E'); mark = FR_DIA_GRAVE; break;
        case DIALOG_CHAR_UPPER_E_CIRCUMFLEX: base = ASCII_TO_DIALOG('E'); mark = FR_DIA_CIRCUMFLEX; break;
        case DIALOG_CHAR_UPPER_E_UMLAUT:     base = ASCII_TO_DIALOG('E'); mark = FR_DIA_UMLAUT; break;
        case DIALOG_CHAR_UPPER_E_ACUTE:      base = ASCII_TO_DIALOG('E'); mark = FR_DIA_ACUTE; break;
        case DIALOG_CHAR_LOWER_U_GRAVE:      base = ASCII_TO_DIALOG('u'); mark = FR_DIA_GRAVE; break;
        case DIALOG_CHAR_LOWER_U_CIRCUMFLEX: base = ASCII_TO_DIALOG('u'); mark = FR_DIA_CIRCUMFLEX; break;
        case DIALOG_CHAR_LOWER_U_UMLAUT:     base = ASCII_TO_DIALOG('u'); mark = FR_DIA_UMLAUT; break;
        case DIALOG_CHAR_UPPER_U_GRAVE:      base = ASCII_TO_DIALOG('U'); mark = FR_DIA_GRAVE; break;
        case DIALOG_CHAR_UPPER_U_CIRCUMFLEX: base = ASCII_TO_DIALOG('U'); mark = FR_DIA_CIRCUMFLEX; break;
        case DIALOG_CHAR_UPPER_U_UMLAUT:     base = ASCII_TO_DIALOG('U'); mark = FR_DIA_UMLAUT; break;
        case DIALOG_CHAR_LOWER_O_CIRCUMFLEX: base = ASCII_TO_DIALOG('o'); mark = FR_DIA_CIRCUMFLEX; break;
        case DIALOG_CHAR_LOWER_O_UMLAUT:     base = ASCII_TO_DIALOG('o'); mark = FR_DIA_UMLAUT; break;
        case DIALOG_CHAR_UPPER_O_CIRCUMFLEX: base = ASCII_TO_DIALOG('O'); mark = FR_DIA_CIRCUMFLEX; break;
        case DIALOG_CHAR_UPPER_O_UMLAUT:     base = ASCII_TO_DIALOG('O'); mark = FR_DIA_UMLAUT; break;
        case DIALOG_CHAR_LOWER_I_CIRCUMFLEX: base = DIALOG_CHAR_I_NO_DIA; mark = FR_DIA_CIRCUMFLEX; break;
        case DIALOG_CHAR_LOWER_I_UMLAUT:     base = DIALOG_CHAR_I_NO_DIA; mark = FR_DIA_UMLAUT; break;
        case 0xED:                            base = ASCII_TO_DIALOG('C'); mark = FR_DIA_CEDILLA; break;
        case 0xEE:                            base = ASCII_TO_DIALOG('c'); mark = FR_DIA_CEDILLA; break;
        default: return FALSE;
    }

    render_fr_us_char_at(x, y, base);

    switch (mark) {
        case FR_DIA_GRAVE:
            render_fr_us_char_at(x, y + 4, ASCII_TO_DIALOG('\''));
            break;
        case FR_DIA_ACUTE:
            render_fr_us_char_at(x + 2, y + 4, ASCII_TO_DIALOG('\''));
            break;
        case FR_DIA_CIRCUMFLEX:
            render_fr_us_char_at(x + 1, y + 4, ASCII_TO_DIALOG('\''));
            break;
        case FR_DIA_UMLAUT:
            render_fr_us_char_at(x - 1, y + 4, DIALOG_CHAR_PERIOD);
            render_fr_us_char_at(x + 3, y + 4, DIALOG_CHAR_PERIOD);
            break;
        case FR_DIA_CEDILLA:
            render_fr_us_char_at(x, y - 4, DIALOG_CHAR_COMMA);
            break;
        default:
            break;
    }
    return TRUE;
}

static void print_generic_string_fr_us(s16 x, s16 y, const u8 *str) {
    s32 pos = 0;
    s16 curX = x;
    s16 curY = y;

    while (str[pos] != DIALOG_CHAR_TERMINATOR) {
        u8 chr = str[pos++];

        if (chr == DIALOG_CHAR_NEWLINE) {
            curX = x;
            curY -= 16;
            continue;
        }
        if (chr == DIALOG_CHAR_SPACE) {
            curX += gDialogCharWidths[DIALOG_CHAR_SPACE];
            continue;
        }
        if (chr == DIALOG_CHAR_SLASH) {
            curX += gDialogCharWidths[DIALOG_CHAR_SPACE] * 2;
            continue;
        }
        if (render_fr_us_accented_at(curX, curY, chr)) {
            curX += gDialogCharWidths[chr] ? gDialogCharWidths[chr] : 6;
            continue;
        }

        render_fr_us_char_at(curX, curY, chr);
        curX += gDialogCharWidths[chr] ? gDialogCharWidths[chr] : 6;
    }
}
#endif
'''

marker = "/**\n * Prints a generic white string."
if marker not in s:
    raise SystemExit("generic string insertion point not found")
if "static void print_generic_string_fr_us" not in s:
    s = s.replace(marker, helper + "\n" + marker, 1)

needle = "void print_generic_string(s16 x, s16 y, const u8 *str) {\n"
replacement = needle + """#ifdef SM64EX_FRENCH_TEXT
    print_generic_string_fr_us(x, y, str);
    return;
#endif
"""
if replacement not in s:
    if needle not in s:
        raise SystemExit("print_generic_string function not found")
    s = s.replace(needle, replacement, 1)

dialog_helper = r'''
#ifdef SM64EX_FRENCH_TEXT
static void handle_dialog_text_and_pages_fr_us(s8 colorMode, struct DialogEntry *dialog, s8 lowerBound) {
    u8 *str = segmented_to_virtual(dialog->str);
    s8 lineNum = 1;
    s8 linesPerBox = dialog->linesPerBox;
    s8 totalLines = (gDialogBoxState == DIALOG_STATE_HORIZONTAL) ? (linesPerBox * 2 + 1) : (linesPerBox + 1);
    s8 pageState = DIALOG_PAGE_STATE_NONE;
    s16 strIdx = gDialogTextPos;
    s16 curX = 0;
    s16 scrollY = (gDialogBoxState == DIALOG_STATE_HORIZONTAL) ? gDialogScrollOffsetY : 0;
    s16 curY = 2 - (lineNum * 16) + scrollY;

    gSPDisplayList(gDisplayListHead++, dl_ia_text_begin);

    while (pageState == DIALOG_PAGE_STATE_NONE) {
        u8 chr;
        change_and_flash_dialog_text_color_lines(colorMode, lineNum);
        chr = str[strIdx];

        switch (chr) {
            case DIALOG_CHAR_TERMINATOR:
                pageState = DIALOG_PAGE_STATE_END;
                break;

            case DIALOG_CHAR_NEWLINE:
                lineNum++;
                if (lineNum == totalLines) {
                    pageState = DIALOG_PAGE_STATE_SCROLL;
                } else {
                    curX = 0;
                    curY = 2 - (lineNum * 16) + scrollY;
                }
                break;

            case DIALOG_CHAR_SPACE:
                curX += gDialogCharWidths[DIALOG_CHAR_SPACE];
                break;

            case DIALOG_CHAR_SLASH:
                curX += gDialogCharWidths[DIALOG_CHAR_SPACE] * 2;
                break;

            case DIALOG_CHAR_STAR_COUNT: {
                s8 tens = gDialogVariable / 10;
                s8 ones = gDialogVariable - tens * 10;
                if (lineNum >= lowerBound && lineNum <= lowerBound + linesPerBox) {
                    if (tens != 0) {
                        render_fr_us_char_at(curX, curY, tens);
                        curX += gDialogCharWidths[tens];
                    }
                    render_fr_us_char_at(curX, curY, ones);
                }
                curX += gDialogCharWidths[ones];
                break;
            }

            case DIALOG_CHAR_MULTI_THE:
            case DIALOG_CHAR_MULTI_YOU: {
                static const u8 wordThe[] = { ASCII_TO_DIALOG('t'), ASCII_TO_DIALOG('h'), ASCII_TO_DIALOG('e') };
                static const u8 wordYou[] = { ASCII_TO_DIALOG('y'), ASCII_TO_DIALOG('o'), ASCII_TO_DIALOG('u') };
                const u8 *word = (chr == DIALOG_CHAR_MULTI_THE) ? wordThe : wordYou;
                s32 i;
                for (i = 0; i < 3; i++) {
                    if (lineNum >= lowerBound && lineNum <= lowerBound + linesPerBox) {
                        render_fr_us_char_at(curX, curY, word[i]);
                    }
                    curX += gDialogCharWidths[word[i]];
                }
                break;
            }

            default:
                if (lineNum >= lowerBound && lineNum <= lowerBound + linesPerBox) {
                    if (!render_fr_us_accented_at(curX, curY, chr)) {
                        render_fr_us_char_at(curX, curY, chr);
                    }
                }
                curX += gDialogCharWidths[chr] ? gDialogCharWidths[chr] : 6;
                break;
        }

        strIdx++;
    }

    gSPDisplayList(gDisplayListHead++, dl_ia_text_end);

    if (gDialogBoxState == DIALOG_STATE_VERTICAL) {
        gLastDialogPageStrPos = (pageState == DIALOG_PAGE_STATE_END) ? -1 : strIdx;
    }
    gLastDialogLineNum = lineNum;
}
#endif

'''

dialog_marker = "#if defined(VERSION_JP) || defined(VERSION_SH)\nvoid handle_dialog_text_and_pages"
if dialog_marker not in s:
    raise SystemExit("dialog handler insertion point not found")
if "handle_dialog_text_and_pages_fr_us" not in s:
    s = s.replace(dialog_marker, dialog_helper + dialog_marker, 1)

body_needle = "#endif\n{\n    UNUSED s32 pad[2];"
body_replacement = """#endif
{
#ifdef SM64EX_FRENCH_TEXT
    handle_dialog_text_and_pages_fr_us(colorMode, dialog, lowerBound);
    return;
#endif
    UNUSED s32 pad[2];"""
if body_replacement not in s:
    if body_needle not in s:
        raise SystemExit("dialog handler body not found")
    s = s.replace(body_needle, body_replacement, 1)

# Reuse the PAL/French horizontal placement values where they are purely
# presentation constants.  Gameplay and timing stay VERSION_US.
replacements = {
    "#ifdef VERSION_EU\n#define TXT_STAR_X 89": "#if defined(VERSION_EU) || defined(SM64EX_FRENCH_TEXT)\n#define TXT_STAR_X 89",
    "#ifdef VERSION_EU\n    print_hud_lut_string(HUD_LUT_GLOBAL, get_str_x_pos_from_center_scale(": "#if defined(VERSION_EU) || defined(SM64EX_FRENCH_TEXT)\n    print_hud_lut_string(HUD_LUT_GLOBAL, get_str_x_pos_from_center_scale(",
    "#ifdef VERSION_EU\n        print_generic_string(x - 17, y + 30, courseName);": "#if defined(VERSION_EU) || defined(SM64EX_FRENCH_TEXT)\n        print_generic_string(x - 17, y + 30, courseName);",
    "#ifndef VERSION_EU\n    print_generic_string(x - 9, y + 30, courseName);": "#if !defined(VERSION_EU) && !defined(SM64EX_FRENCH_TEXT)\n    print_generic_string(x - 9, y + 30, courseName);",
    "#ifdef VERSION_EU\n#define TXT_NAME_X1 centerX": "#if defined(VERSION_EU) || defined(SM64EX_FRENCH_TEXT)\n#define TXT_NAME_X1 centerX",
    "#ifdef VERSION_EU\n    s16 centerX;\n    switch (gInGameLanguage)": "#if defined(VERSION_EU) || defined(SM64EX_FRENCH_TEXT)\n    s16 centerX;\n#endif\n#ifdef VERSION_EU\n    switch (gInGameLanguage)",
    "#ifdef VERSION_EU\n        centerX = get_str_x_pos_from_center(153, name, 12.0f);": "#if defined(VERSION_EU) || defined(SM64EX_FRENCH_TEXT)\n        centerX = get_str_x_pos_from_center(153, name, 12.0f);",
}
for old, new in replacements.items():
    if old not in s:
        raise SystemExit(f"layout anchor not found: {old[:60]!r}")
    s = s.replace(old, new, 1)

menu.write_text(s, encoding="utf-8")
print("Applied deterministic French renderer v4.")
