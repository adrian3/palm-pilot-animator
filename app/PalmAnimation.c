#include <PalmOS.h>
#include "AnimationLibrary.h"
#define PAGE_SIZE 6
#define LIST_TOP 29
#define ROW_HEIGHT 16

static void DrawMenu(UInt16 page, Boolean invert)
{
    UInt16 row, index, pages = (ANIMATION_COUNT + PAGE_SIZE - 1) / PAGE_SIZE;
    FontID oldFont;
    RectangleType rectangle;
    Char counter[12];
    WinEraseWindow();
    oldFont = FntSetFont(boldFont);
    WinDrawChars("Made by Ade", 11, 42, 10);
    FntSetFont(oldFont);
    for (row = 0; row < PAGE_SIZE; ++row) {
        index = page * PAGE_SIZE + row;
        if (index >= ANIMATION_COUNT) break;
        WinDrawChars(animations[index].name, StrLen(animations[index].name), 12, LIST_TOP + row * ROW_HEIGHT + 2);
        WinDrawLine(8, LIST_TOP + (row + 1) * ROW_HEIGHT - 1, 151, LIST_TOP + (row + 1) * ROW_HEIGHT - 1);
    }
    if (pages > 1) {
        if (page > 0) WinDrawChars("< Prev", 6, 8, 128);
        if (page + 1 < pages) WinDrawChars("Next >", 6, 114, 128);
        StrPrintF(counter, "%u/%u", page + 1, pages);
        WinDrawChars(counter, StrLen(counter), 70, 128);
    }
    RctSetRectangle(&rectangle, 9, 146, 10, 10);
    WinDrawRectangleFrame(simpleFrame, &rectangle);
    if (invert) {
        WinDrawLine(10, 151, 13, 154);
        WinDrawLine(13, 154, 18, 147);
    }
    WinDrawChars("Invert", 6, 25, 145);
}

static void DrawFrame(UInt16 clip, UInt16 frame, Boolean invert, UInt8 *scratch)
{
    MemHandle handle;
    BitmapType *bitmap;
    UInt16 i;
    handle = DmGetResource('Tbmp', animations[clip].base + frame);
    if (handle) {
        bitmap = MemHandleLock(handle);
        if (bitmap) {
            if (invert) {
                /* Native version-0 header is 16 bytes; invert pixel payload only. */
                MemMove(scratch, bitmap, 3216);
                for (i = 16; i < 3216; ++i) scratch[i] ^= 0xff;
                WinDrawBitmap((BitmapType *)scratch, 0, 0);
            } else WinDrawBitmap(bitmap, 0, 0);
            MemHandleUnlock(handle);
        }
        DmReleaseResource(handle);
    }
}

static UInt32 FrameTicks(UInt16 clip, UInt16 frame)
{
    MemHandle handle;
    UInt16 *timings;
    UInt32 ticks = SysTicksPerSecond() / 10;
    handle = DmGetResource('ATim', animations[clip].timingID);
    if (handle) {
        timings = MemHandleLock(handle);
        if (timings) {
            if (frame < timings[0]) ticks = ((UInt32)timings[frame + 1] * SysTicksPerSecond() + 500) / 1000;
            MemHandleUnlock(handle);
        }
        DmReleaseResource(handle);
    }
    return ticks ? ticks : 1;
}

UInt32 PilotMain(UInt16 cmd, void *cmdPBP, UInt16 launchFlags)
{
    EventType event;
    UInt16 clip = 0, frame = 0, page = 0, size;
    UInt16 pages = (ANIMATION_COUNT + PAGE_SIZE - 1) / PAGE_SIZE;
    Int16 selected;
    UInt32 nextTick = 0, now;
    Int32 waitTicks;
    Boolean playing = false, paused = false, invert = false;
    UInt8 *scratch;
    if (cmd != sysAppLaunchCmdNormalLaunch) return 0;
    scratch = MemPtrNew(3216);
    size = sizeof(invert);
    if (PrefGetAppPreferences('PAnm', 0, &invert, &size, true) != 1 || size != sizeof(invert)) invert = false;
    if (!scratch) invert = false;
    DrawMenu(page, invert);
    for (;;) {
        now = TimGetTicks();
        waitTicks = (!playing || paused) ? evtWaitForever : (Int32)(nextTick - now);
        if (playing && !paused && waitTicks < 0) waitTicks = 0;
        EvtGetEvent(&event, waitTicks);
        if (event.eType == appStopEvent) break;
        if (event.eType == keyDownEvent && (event.data.keyDown.chr == vchrPageUp || event.data.keyDown.chr == vchrPageDown)) {
            if (playing) { playing = false; paused = false; }
            else if (event.data.keyDown.chr == vchrPageDown && page + 1 < pages) ++page;
            else if (event.data.keyDown.chr == vchrPageUp && page > 0) --page;
            DrawMenu(page, invert);
        } else if (!SysHandleEvent(&event)) {
            if (event.eType == penDownEvent) {
                if (playing) {
                    paused = !paused;
                    nextTick = TimGetTicks() + FrameTicks(clip, frame);
                } else if (event.screenY >= 142 && event.screenY < 160 && event.screenX >= 5 && event.screenX < 70) {
                    if (scratch) invert = !invert;
                    DrawMenu(page, invert);
                } else if (event.screenY >= 125 && event.screenY < 141) {
                    if (event.screenX < 55 && page > 0) --page;
                    else if (event.screenX >= 105 && page + 1 < pages) ++page;
                    DrawMenu(page, invert);
                } else if (event.screenX >= 8 && event.screenX < 152 && event.screenY >= LIST_TOP && event.screenY < LIST_TOP + PAGE_SIZE * ROW_HEIGHT) {
                    selected = page * PAGE_SIZE + (event.screenY - LIST_TOP) / ROW_HEIGHT;
                    if (selected < ANIMATION_COUNT) {
                        clip = selected; frame = 0; paused = false; playing = true;
                        DrawFrame(clip, frame, invert, scratch);
                        nextTick = TimGetTicks() + FrameTicks(clip, frame);
                    }
                }
            } else if (event.eType == winEnterEvent) {
                if (playing) DrawFrame(clip, frame, invert, scratch);
                else DrawMenu(page, invert);
            }
        }
        now = TimGetTicks();
        if (playing && !paused && (Int32)(now - nextTick) >= 0) {
            frame = (frame + 1) % animations[clip].count;
            DrawFrame(clip, frame, invert, scratch);
            nextTick += FrameTicks(clip, frame);
            if ((Int32)(now - nextTick) >= 0) nextTick = now + FrameTicks(clip, frame);
        }
    }
    PrefSetAppPreferences('PAnm', 0, 1, &invert, sizeof(invert), true);
    if (scratch) MemPtrFree(scratch);
    return 0;
}
