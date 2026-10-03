typedef struct { const Char *name; UInt16 base; UInt16 count; UInt16 timingID; } AnimationInfo;
#define ANIMATION_COUNT 1
static const AnimationInfo animations[ANIMATION_COUNT] = {
    {"Golden Eagle", 1000, 19, 1000},
};
