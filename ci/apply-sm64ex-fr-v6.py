from pathlib import Path
import re, sys

root = Path(sys.argv[1])

def rp(rel):
    return root / rel

def read(rel):
    return rp(rel).read_text(encoding="utf-8")

def write(rel, text):
    rp(rel).write_text(text, encoding="utf-8", newline="\n")

def once(text, old, new, label):
    if old not in text:
        raise SystemExit(f"Missing anchor: {label}")
    return text.replace(old, new, 1)

# ----------------------------------------------------------------------
# 1) Keep VERSION_US globally. Add one isolated presentation macro only.
# ----------------------------------------------------------------------
p = "ports/uwp/CMakeLists.txt"
s = read(p)
s = once(s, "    VERSION_US=1\n", "    VERSION_US=1\n    SM64EX_FRENCH_RENDERER=1\n", "CMake macro")
write(p, s)

# ----------------------------------------------------------------------
# 2) Generate official French text/courses from text/fr.
# ----------------------------------------------------------------------
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
s = once(s, old, new, "French text generation")
write(p, s)

# ----------------------------------------------------------------------
# 3) US segment/layout, French dialog/course/act table.
# ----------------------------------------------------------------------
p = "bin/segment2.c"
s = read(p)
s = once(s,
'''#elif defined(VERSION_US)
#include "text/us/define_text.inc.c"
#endif
''',
'''#elif defined(VERSION_US)
#ifdef SM64EX_FRENCH_RENDERER
#include "text/fr/define_text.inc.c"
#else
#include "text/us/define_text.inc.c"
#endif
#endif
''',
"French segment2 text")

# Restore the V glyph in the VERSION_US HUD LUT. The texture already exists;
# US simply leaves its LUT slot null. French "VIDE" must render exactly where
# the original game renders "NEW", using the same HUD pipeline and coordinates.
s = once(s,
'''    texture_hud_char_S, texture_hud_char_T, texture_hud_char_U,               0x0,
    texture_hud_char_W,               0x0, texture_hud_char_Y,               0x0,
''',
'''    texture_hud_char_S, texture_hud_char_T, texture_hud_char_U, texture_hud_char_V,
    texture_hud_char_W,               0x0, texture_hud_char_Y,               0x0,
''',
"VERSION_US HUD V glyph")
write(p, s)

# ----------------------------------------------------------------------
# 4) Expose official FR UI strings and alias base names to them.
# ----------------------------------------------------------------------
p = "include/text_strings.h.in"
s = read(p)
s = once(s,
'''\n#ifdef VERSION_EU

/**
 * File Select Text
 */
''',
'''\n#if defined(VERSION_EU) || defined(SM64EX_FRENCH_RENDERER)

/**
 * File Select Text
 */
''',
"French UI definitions")

fr_bases = sorted(set(re.findall(r'^#define\s+(TEXT_[A-Z0-9_]+)_FR\b', s, flags=re.M)))
base_defs = set(re.findall(r'^#define\s+(TEXT_[A-Z0-9_]+)\b', s, flags=re.M))
aliases = [f"#undef {name}\n#define {name} {name}_FR" for name in fr_bases if name in base_defs]
block = "\n#ifdef SM64EX_FRENCH_RENDERER\n/* Official French UI strings on the NTSC-US runtime. */\n" + "\n".join(aliases) + "\n#endif\n\n"
s = once(s, "#endif // TEXT_STRINGS_H", block + "#endif // TEXT_STRINGS_H", "text header end")
write(p, s)

# Accent codes must exist in a VERSION_US build.
p = "src/game/ingame_menu.h"
s = read(p)
s = once(s,
'''enum DialogSpecialChars {
#ifdef VERSION_EU
''',
'''enum DialogSpecialChars {
#if defined(VERSION_EU) || defined(SM64EX_FRENCH_RENDERER)
''',
"accent char enum")
# The scaled centering helper is used by the French file-select title.
s = once(s,
'''#if defined(VERSION_JP) || defined(VERSION_EU)
s16 get_str_x_pos_from_center_scale''',
'''#if defined(VERSION_JP) || defined(VERSION_EU) || defined(SM64EX_FRENCH_RENDERER)
s16 get_str_x_pos_from_center_scale''',
"scaled centering declaration")
write(p, s)

# ----------------------------------------------------------------------
# 5) Clean French renderer:
#    - original US gameplay and matrix code stays untouched;
#    - generic strings/dialogs dispatch into a dedicated EU-style coordinate
#      renderer using screen rectangles;
#    - accents are tiny embedded IA4 masks, not apostrophe/comma glyphs.
# ----------------------------------------------------------------------
p = "src/game/ingame_menu.c"
s = read(p)

s = once(s,
'''#if defined(VERSION_EU)
s16 gDialogX; // D_8032F69A
s16 gDialogY; // D_8032F69C
#endif
''',
'''#if defined(VERSION_EU) || defined(SM64EX_FRENCH_RENDERER)
s16 gDialogX; // EU-style text cursor
s16 gDialogY;
#endif
''',
"dialog coordinates")

# Use the real EU width entries for all French accent codepoints.
start = s.index("u8 gDialogCharWidths[256]")
end = s.index("s8 gDialogBoxState", start)
region = s[start:end]
region = region.replace("#ifdef VERSION_EU", "#if defined(VERSION_EU) || defined(SM64EX_FRENCH_RENDERER)")
s = s[:start] + region + s[end:]

# Enable the upstream absolute character renderer in this presentation mode.
eu_renderer_start = s.index("#ifdef VERSION_EU\nstatic void alloc_ia4_tex_from_i1")
eu_renderer_end = s.index("#endif // VERSION_EU", eu_renderer_start) + len("#endif // VERSION_EU")
eu_region = s[eu_renderer_start:eu_renderer_end]
eu_region = eu_region.replace("#ifdef VERSION_EU", "#if defined(VERSION_EU) || defined(SM64EX_FRENCH_RENDERER)", 1)
eu_region = eu_region.replace("#endif // VERSION_EU", "#endif // VERSION_EU || SM64EX_FRENCH_RENDERER", 1)
s = s[:eu_renderer_start] + eu_region + s[eu_renderer_end:]

# 8x16 IA4 masks. Two pixels per byte. Marks live only in the top/bottom rows.
def pack(rows):
    out = []
    for row in rows:
        assert len(row) == 8
        for x in range(0, 8, 2):
            out.append(((15 if row[x] else 0) << 4) | (15 if row[x+1] else 0))
    assert len(out) == 64
    return ", ".join(f"0x{b:02X}" for b in out)

blank = [[0]*8 for _ in range(16)]
def mask(points):
    a = [r[:] for r in blank]
    for x,y in points:
        a[y][x] = 1
    return a

grave = mask([(2,1),(3,2),(4,3)])
acute = mask([(5,1),(4,2),(3,3)])
circ = mask([(2,3),(3,2),(4,2),(5,3)])
umlaut = mask([(2,2),(3,2),(5,2),(6,2)])
cedilla = mask([(3,12),(4,12),(4,13),(3,14),(2,15)])

accent_code = f'''
#ifdef SM64EX_FRENCH_RENDERER
void change_and_flash_dialog_text_color_lines(s8 colorMode, s8 lineNum);
void render_generic_dialog_char_at_pos(struct DialogEntry *dialog, s16 x, s16 y, u8 c);

static const u8 sFrAccentGrave[]      = "__sm64ex_fr_accent_grave";
static const u8 sFrAccentAcute[]      = "__sm64ex_fr_accent_acute";
static const u8 sFrAccentCircumflex[] = "__sm64ex_fr_accent_circumflex";
static const u8 sFrAccentUmlaut[]     = "__sm64ex_fr_accent_umlaut";
static const u8 sFrAccentCedilla[]    = "__sm64ex_fr_accent_cedilla";

static void render_fr_mask_at_pos(s16 xPos, s16 yPos, const u8 *tex) {{
    gDPPipeSync(gDisplayListHead++);
    gDPSetTextureImage(gDisplayListHead++, G_IM_FMT_IA, G_IM_SIZ_16b, 1, VIRTUAL_TO_PHYSICAL(tex));
    gSPDisplayList(gDisplayListHead++, dl_ia_text_tex_settings);
    gSPTextureRectangleFlip(gDisplayListHead++, xPos << 2, (yPos - 16) << 2,
                            (xPos + 8) << 2, yPos << 2, G_TX_RENDERTILE,
                            8 << 6, 4 << 6, 1 << 10, 1 << 10);
}}

static s32 fr_accent_parts(u8 c, u8 *base, const u8 **mark) {{
    switch (c) {{
        case DIALOG_CHAR_LOWER_A_GRAVE:      *base=ASCII_TO_DIALOG('a'); *mark=sFrAccentGrave; break;
        case DIALOG_CHAR_LOWER_A_CIRCUMFLEX: *base=ASCII_TO_DIALOG('a'); *mark=sFrAccentCircumflex; break;
        case DIALOG_CHAR_LOWER_A_UMLAUT:     *base=ASCII_TO_DIALOG('a'); *mark=sFrAccentUmlaut; break;
        case DIALOG_CHAR_UPPER_A_GRAVE:      *base=ASCII_TO_DIALOG('A'); *mark=sFrAccentGrave; break;
        case DIALOG_CHAR_UPPER_A_CIRCUMFLEX: *base=ASCII_TO_DIALOG('A'); *mark=sFrAccentCircumflex; break;
        case DIALOG_CHAR_UPPER_A_UMLAUT:     *base=ASCII_TO_DIALOG('A'); *mark=sFrAccentUmlaut; break;
        case DIALOG_CHAR_LOWER_E_GRAVE:      *base=ASCII_TO_DIALOG('e'); *mark=sFrAccentGrave; break;
        case DIALOG_CHAR_LOWER_E_CIRCUMFLEX: *base=ASCII_TO_DIALOG('e'); *mark=sFrAccentCircumflex; break;
        case DIALOG_CHAR_LOWER_E_UMLAUT:     *base=ASCII_TO_DIALOG('e'); *mark=sFrAccentUmlaut; break;
        case DIALOG_CHAR_LOWER_E_ACUTE:      *base=ASCII_TO_DIALOG('e'); *mark=sFrAccentAcute; break;
        case DIALOG_CHAR_UPPER_E_GRAVE:      *base=ASCII_TO_DIALOG('E'); *mark=sFrAccentGrave; break;
        case DIALOG_CHAR_UPPER_E_CIRCUMFLEX: *base=ASCII_TO_DIALOG('E'); *mark=sFrAccentCircumflex; break;
        case DIALOG_CHAR_UPPER_E_UMLAUT:     *base=ASCII_TO_DIALOG('E'); *mark=sFrAccentUmlaut; break;
        case DIALOG_CHAR_UPPER_E_ACUTE:      *base=ASCII_TO_DIALOG('E'); *mark=sFrAccentAcute; break;
        case DIALOG_CHAR_LOWER_U_GRAVE:      *base=ASCII_TO_DIALOG('u'); *mark=sFrAccentGrave; break;
        case DIALOG_CHAR_LOWER_U_CIRCUMFLEX: *base=ASCII_TO_DIALOG('u'); *mark=sFrAccentCircumflex; break;
        case DIALOG_CHAR_LOWER_U_UMLAUT:     *base=ASCII_TO_DIALOG('u'); *mark=sFrAccentUmlaut; break;
        case DIALOG_CHAR_UPPER_U_GRAVE:      *base=ASCII_TO_DIALOG('U'); *mark=sFrAccentGrave; break;
        case DIALOG_CHAR_UPPER_U_CIRCUMFLEX: *base=ASCII_TO_DIALOG('U'); *mark=sFrAccentCircumflex; break;
        case DIALOG_CHAR_UPPER_U_UMLAUT:     *base=ASCII_TO_DIALOG('U'); *mark=sFrAccentUmlaut; break;
        case DIALOG_CHAR_LOWER_O_CIRCUMFLEX: *base=ASCII_TO_DIALOG('o'); *mark=sFrAccentCircumflex; break;
        case DIALOG_CHAR_LOWER_O_UMLAUT:     *base=ASCII_TO_DIALOG('o'); *mark=sFrAccentUmlaut; break;
        case DIALOG_CHAR_UPPER_O_CIRCUMFLEX: *base=ASCII_TO_DIALOG('O'); *mark=sFrAccentCircumflex; break;
        case DIALOG_CHAR_UPPER_O_UMLAUT:     *base=ASCII_TO_DIALOG('O'); *mark=sFrAccentUmlaut; break;
        case DIALOG_CHAR_LOWER_I_CIRCUMFLEX: *base=DIALOG_CHAR_I_NO_DIA; *mark=sFrAccentCircumflex; break;
        case DIALOG_CHAR_LOWER_I_UMLAUT:     *base=DIALOG_CHAR_I_NO_DIA; *mark=sFrAccentUmlaut; break;
        case 0xED:                            *base=ASCII_TO_DIALOG('C'); *mark=sFrAccentCedilla; break;
        case 0xEE:                            *base=ASCII_TO_DIALOG('c'); *mark=sFrAccentCedilla; break;
        default: return FALSE;
    }}
    return TRUE;
}}

static void render_fr_char_at_pos(s16 x, s16 y, u8 c) {{
    u8 base;
    const u8 *mark;
    if (fr_accent_parts(c, &base, &mark)) {{
        render_generic_char_at_pos(x, y, base);
        render_fr_mask_at_pos(x, y, mark);
    }} else {{
        render_generic_char_at_pos(x, y, c);
    }}
}}

static void print_generic_string_fr(s16 x, s16 y, const u8 *str) {{
    s32 i = 0;
    s16 xCoord = x;
    s16 yCoord = 240 - y;
    while (str[i] != DIALOG_CHAR_TERMINATOR) {{
        u8 c = str[i++];
        if (c == DIALOG_CHAR_SPACE) {{
            xCoord += gDialogCharWidths[DIALOG_CHAR_SPACE];
        }} else if (c == DIALOG_CHAR_NEWLINE) {{
            xCoord = x;
            yCoord += 16;
        }} else if (c == DIALOG_CHAR_SLASH) {{
            xCoord += gDialogCharWidths[DIALOG_CHAR_SPACE] * 2;
        }} else if (c == DIALOG_CHAR_MULTI_THE) {{
            static const u8 w[] = {{ASCII_TO_DIALOG('t'),ASCII_TO_DIALOG('h'),ASCII_TO_DIALOG('e')}};
            s32 n; for (n=0;n<3;n++) {{ render_fr_char_at_pos(xCoord,yCoord,w[n]); xCoord += gDialogCharWidths[w[n]]; }}
        }} else if (c == DIALOG_CHAR_MULTI_YOU) {{
            static const u8 w[] = {{ASCII_TO_DIALOG('y'),ASCII_TO_DIALOG('o'),ASCII_TO_DIALOG('u')}};
            s32 n; for (n=0;n<3;n++) {{ render_fr_char_at_pos(xCoord,yCoord,w[n]); xCoord += gDialogCharWidths[w[n]]; }}
        }} else {{
            render_fr_char_at_pos(xCoord, yCoord, c);
            xCoord += gDialogCharWidths[c] ? gDialogCharWidths[c] : 6;
        }}
    }}
}}

static void render_fr_dialog_char_at_pos(struct DialogEntry *dialog, s16 x, s16 y, u8 c) {{
    s16 width = (8.0 - (gDialogBoxScale * 0.8));
    s16 height = (16.0 - (gDialogBoxScale * 0.8));
    s16 tmpX = (dialog->leftOffset + (65.0 - (65.0 / gDialogBoxScale)));
    s16 tmpY = ((240 - dialog->width) - ((40.0 / gDialogBoxScale) - 40));
    s16 xCoord = (tmpX + (x / gDialogBoxScale));
    s16 yCoord = (tmpY + (y / gDialogBoxScale));
    u8 base;
    const u8 *mark;

    if (fr_accent_parts(c, &base, &mark)) {{
        void **fontLUT = segmented_to_virtual(main_font_lut);
        void *packedTexture = segmented_to_virtual(fontLUT[base]);
        void *unpackedTexture = convert_ia4_char(base, packedTexture, 8, 8);
        gDPSetTextureImage(gDisplayListHead++, G_IM_FMT_IA, G_IM_SIZ_16b, 1, VIRTUAL_TO_PHYSICAL(unpackedTexture));
        gSPDisplayList(gDisplayListHead++, dl_ia_text_tex_settings);
        gSPTextureRectangleFlip(gDisplayListHead++, xCoord << 2, (yCoord - height) << 2,
                                (xCoord + width) << 2, yCoord << 2, G_TX_RENDERTILE,
                                8 << 6, 4 << 6, 1 << 10, 1 << 10);
        gDPSetTextureImage(gDisplayListHead++, G_IM_FMT_IA, G_IM_SIZ_16b, 1, VIRTUAL_TO_PHYSICAL(mark));
        gSPDisplayList(gDisplayListHead++, dl_ia_text_tex_settings);
        gSPTextureRectangleFlip(gDisplayListHead++, xCoord << 2, (yCoord - height) << 2,
                                (xCoord + width) << 2, yCoord << 2, G_TX_RENDERTILE,
                                8 << 6, 4 << 6, 1 << 10, 1 << 10);
    }} else {{
        render_generic_dialog_char_at_pos(dialog, x, y, c);
    }}
}}

static void handle_dialog_text_and_pages_fr(s8 colorMode, struct DialogEntry *dialog, s8 lowerBound) {{
    u8 *str = segmented_to_virtual(dialog->str);
    s8 lineNum = 1;
    s8 linesPerBox = dialog->linesPerBox;
    s8 totalLines = (gDialogBoxState == DIALOG_STATE_HORIZONTAL) ? (linesPerBox * 2 + 1) : (linesPerBox + 1);
    s8 pageState = DIALOG_PAGE_STATE_NONE;
    s16 strIdx = gDialogTextPos;

    gSPDisplayList(gDisplayListHead++, dl_ia_text_begin);
    gDialogX = 0;
    gDialogY = 14;
    if (gDialogBoxState == DIALOG_STATE_HORIZONTAL) gDialogY -= gDialogScrollOffsetY;

    while (pageState == DIALOG_PAGE_STATE_NONE) {{
        u8 c = str[strIdx];
        change_and_flash_dialog_text_color_lines(colorMode, lineNum);

        if (c == DIALOG_CHAR_TERMINATOR) {{
            pageState = DIALOG_PAGE_STATE_END;
        }} else if (c == DIALOG_CHAR_NEWLINE) {{
            lineNum++;
            if (lineNum == totalLines) {{
                pageState = DIALOG_PAGE_STATE_SCROLL;
            }} else {{
                gDialogX = 0;
                gDialogY += 16;
            }}
        }} else if (c == DIALOG_CHAR_SPACE) {{
            gDialogX += gDialogCharWidths[DIALOG_CHAR_SPACE];
        }} else if (c == DIALOG_CHAR_SLASH) {{
            gDialogX += gDialogCharWidths[DIALOG_CHAR_SPACE] * 2;
        }} else if (c == DIALOG_CHAR_STAR_COUNT) {{
            s8 tens = gDialogVariable / 10;
            s8 ones = gDialogVariable - tens * 10;
            if (lineNum >= lowerBound && lineNum <= lowerBound + linesPerBox) {{
                if (tens) {{
                    render_fr_dialog_char_at_pos(dialog, gDialogX, gDialogY, tens);
                    gDialogX += gDialogCharWidths[tens];
                }}
                render_fr_dialog_char_at_pos(dialog, gDialogX, gDialogY, ones);
            }}
            gDialogX += gDialogCharWidths[ones];
        }} else if (c == DIALOG_CHAR_MULTI_THE || c == DIALOG_CHAR_MULTI_YOU) {{
            static const u8 wThe[] = {{ASCII_TO_DIALOG('t'),ASCII_TO_DIALOG('h'),ASCII_TO_DIALOG('e')}};
            static const u8 wYou[] = {{ASCII_TO_DIALOG('y'),ASCII_TO_DIALOG('o'),ASCII_TO_DIALOG('u')}};
            const u8 *w = c == DIALOG_CHAR_MULTI_THE ? wThe : wYou;
            s32 n;
            for (n=0;n<3;n++) {{
                if (lineNum >= lowerBound && lineNum <= lowerBound + linesPerBox)
                    render_fr_dialog_char_at_pos(dialog, gDialogX, gDialogY, w[n]);
                gDialogX += gDialogCharWidths[w[n]];
            }}
        }} else {{
            if (lineNum >= lowerBound && lineNum <= lowerBound + linesPerBox)
                render_fr_dialog_char_at_pos(dialog, gDialogX, gDialogY, c);
            gDialogX += gDialogCharWidths[c] ? gDialogCharWidths[c] : 6;
        }}
        strIdx++;
    }}

    gSPDisplayList(gDisplayListHead++, dl_ia_text_end);
    if (gDialogBoxState == DIALOG_STATE_VERTICAL)
        gLastDialogPageStrPos = (pageState == DIALOG_PAGE_STATE_END) ? -1 : strIdx;
    gLastDialogLineNum = lineNum;
}}
#endif
'''

insert_anchor = "/**\n * Prints a generic white string."
if insert_anchor not in s:
    raise SystemExit("generic renderer insertion anchor missing")
s = s.replace(insert_anchor, accent_code + "\n" + insert_anchor, 1)

s = once(s,
'''void print_generic_string(s16 x, s16 y, const u8 *str) {
''',
'''void print_generic_string(s16 x, s16 y, const u8 *str) {
#ifdef SM64EX_FRENCH_RENDERER
    print_generic_string_fr(x, y, str);
    return;
#endif
''',
"generic dispatcher")

needle = '''#endif
{
    UNUSED s32 pad[2];
'''
replacement = '''#endif
{
#ifdef SM64EX_FRENCH_RENDERER
    handle_dialog_text_and_pages_fr(colorMode, dialog, lowerBound);
    return;
#endif
    UNUSED s32 pad[2];
'''
# Make sure this is the handle_dialog_text_and_pages body, not an earlier function.
pos = s.index("void handle_dialog_text_and_pages")
bodypos = s.index(needle, pos)
s = s[:bodypos] + replacement + s[bodypos + len(needle):]

# Enable the upstream EU dialog coordinate transform without enabling VERSION_EU globally.
s = once(s,
'''#ifdef VERSION_EU
void render_generic_dialog_char_at_pos(struct DialogEntry *dialog, s16 x, s16 y, u8 c) {''',
'''#if defined(VERSION_EU) || defined(SM64EX_FRENCH_RENDERER)
void render_generic_dialog_char_at_pos(struct DialogEntry *dialog, s16 x, s16 y, u8 c) {''',
"EU dialog absolute renderer")

# Center-scale helper is useful for French file select title.
s = once(s,
'''#if defined(VERSION_JP) || defined(VERSION_EU) || defined(VERSION_SH)
s16 get_str_x_pos_from_center_scale''',
'''#if defined(VERSION_JP) || defined(VERSION_EU) || defined(VERSION_SH) || defined(SM64EX_FRENCH_RENDERER)
s16 get_str_x_pos_from_center_scale''',
"center scale helper")

write(p, s)

# ----------------------------------------------------------------------
# 6) EXTERNAL_DATA backend: five tiny built-in accent textures.
#    With EXTERNAL_DATA, texture pointers are normally treated as file names.
#    Recognize our reserved names and upload the 8x16 RGBA masks directly,
#    so no companion base.zip or missing-texture checkerboard is involved.
# ----------------------------------------------------------------------
p = "src/pc/gfx/gfx_pc.c"
s = read(p)

builtin_loader = r'''
static bool load_builtin_fr_texture(const char *name) {
    static const u8 grave[16]      = { 0x00,0x20,0x10,0x08,0,0,0,0,0,0,0,0,0,0,0,0 };
    static const u8 acute[16]      = { 0x00,0x04,0x08,0x10,0,0,0,0,0,0,0,0,0,0,0,0 };
    static const u8 circumflex[16] = { 0x00,0x00,0x18,0x24,0,0,0,0,0,0,0,0,0,0,0,0 };
    static const u8 umlaut[16]     = { 0x00,0x00,0x6C,0x00,0,0,0,0,0,0,0,0,0,0,0,0 };
    static const u8 cedilla[16]    = { 0,0,0,0,0,0,0,0,0,0,0,0x18,0x08,0x10,0x20,0x00 };
    const u8 *rows = NULL;
    u8 rgba[8 * 16 * 4];

    if (!strcmp(name, "__sm64ex_fr_accent_grave")) rows = grave;
    else if (!strcmp(name, "__sm64ex_fr_accent_acute")) rows = acute;
    else if (!strcmp(name, "__sm64ex_fr_accent_circumflex")) rows = circumflex;
    else if (!strcmp(name, "__sm64ex_fr_accent_umlaut")) rows = umlaut;
    else if (!strcmp(name, "__sm64ex_fr_accent_cedilla")) rows = cedilla;
    else return false;

    for (int y = 0; y < 16; y++) {
        for (int x = 0; x < 8; x++) {
            const bool on = (rows[y] & (0x80 >> x)) != 0;
            const int o = (y * 8 + x) * 4;
            rgba[o + 0] = 0xFF;
            rgba[o + 1] = 0xFF;
            rgba[o + 2] = 0xFF;
            rgba[o + 3] = on ? 0xFF : 0x00;
        }
    }
    gfx_rapi->upload_texture(rgba, 8, 16);
    return true;
}

'''

s = once(s,
'''#else // EXTERNAL_DATA

static inline void load_texture(const char *fullpath) {''',
'''#else // EXTERNAL_DATA

''' + builtin_loader + '''static inline void load_texture(const char *fullpath) {''',
"built-in French accent loader")

s = once(s,
'''#ifdef EXTERNAL_DATA
    // the "texture data" is actually a C string with the path to our texture in it
    // load it from an external image in our data path
    char texname[SYS_MAX_PATH];
    snprintf(texname, sizeof(texname), FS_TEXTUREDIR "/%s.png", (const char*)rdp.loaded_texture[tile].addr);
    load_texture(texname);
#else''',
'''#ifdef EXTERNAL_DATA
    // Most external-data textures are file names. Five reserved French accent
    // names are generated internally instead, so they never touch base.zip.
    const char *external_name = (const char*)rdp.loaded_texture[tile].addr;
    if (!load_builtin_fr_texture(external_name)) {
        char texname[SYS_MAX_PATH];
        snprintf(texname, sizeof(texname), FS_TEXTUREDIR "/%s.png", external_name);
        load_texture(texname);
    }
#else''',
"built-in French accent import")

write(p, s)

# ----------------------------------------------------------------------
# 7) File Select stays on its original US object/matrix layout.
#    Only French text widths are centered where English hardcoded X values
#    were too short. MARIO A/B/C/D and slot geometry are left untouched.
# ----------------------------------------------------------------------
p = "src/menu/file_select.c"
s = read(p)

s = once(s,
'''#ifndef VERSION_EU
    print_hud_lut_string(HUD_LUT_DIFF, SELECT_FILE_X, 35, textSelectFile);
#endif
''',
'''#ifndef VERSION_EU
#ifdef SM64EX_FRENCH_RENDERER
    print_hud_lut_string(HUD_LUT_DIFF,
                         get_str_x_pos_from_center_scale(160, textSelectFile, 12.0f),
                         35, textSelectFile);
#else
    print_hud_lut_string(HUD_LUT_DIFF, SELECT_FILE_X, 35, textSelectFile);
#endif
#endif
''',
"file select title")

s = once(s,
'''    print_generic_string(SCORE_X, 39, textScore);
    print_generic_string(COPY_X, 39, textCopy);
    print_generic_string(ERASE_X, 39, textErase);
#if !defined(VERSION_JP) && !defined(VERSION_SH)
    sSoundTextX = get_str_x_pos_from_center(254, textSoundModes[sSoundMode], 10.0f);
#endif
    print_generic_string(SOUNDMODE_X1, 39, textSoundModes[sSoundMode]);
''',
'''#ifdef SM64EX_FRENCH_RENDERER
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
"bottom main menu labels")

write(p, s)

print("SM64 NTSC-FR v6 targeted fixes applied.")
