IMAGE_WIDTH = 1536
IMAGE_HEIGHT = 512

C_BASIC_MODEL_WIDTH = 40
C_BASIC_MODEL_HEIGHT = 84

OUT_COLOR = "#41dd65"  # GREEN
IN_COLOR = "#fd4444"  # RED
BEND_COLOR = "#ff8c00"  # ORANGE (DarkOrange)

# Standard hole mapping used for ALL harmonica models
STANDARD_MODEL_HOLE_MAPPING = {
    1: {"top_left": {"x": 243, "y": 355}, "bottom_right": {"x": 308, "y": 430}},
    2: {"top_left": {"x": 350, "y": 355}, "bottom_right": {"x": 412, "y": 430}},
    3: {"top_left": {"x": 454, "y": 355}, "bottom_right": {"x": 516, "y": 430}},
    4: {"top_left": {"x": 558, "y": 355}, "bottom_right": {"x": 623, "y": 430}},
    5: {"top_left": {"x": 661, "y": 355}, "bottom_right": {"x": 728, "y": 430}},
    6: {"top_left": {"x": 768, "y": 355}, "bottom_right": {"x": 833, "y": 430}},
    7: {"top_left": {"x": 873, "y": 355}, "bottom_right": {"x": 938, "y": 430}},
    8: {"top_left": {"x": 977, "y": 355}, "bottom_right": {"x": 1042, "y": 430}},
    9: {"top_left": {"x": 1085, "y": 355}, "bottom_right": {"x": 1147, "y": 430}},
    10: {"top_left": {"x": 1191, "y": 355}, "bottom_right": {"x": 1251, "y": 430}},
}

# All harmonica keys use the same standard mapping
A_MODEL_HOLE_MAPPING = STANDARD_MODEL_HOLE_MAPPING
AB_MODEL_HOLE_MAPPING = STANDARD_MODEL_HOLE_MAPPING
B_MODEL_HOLE_MAPPING = STANDARD_MODEL_HOLE_MAPPING
BB_MODEL_HOLE_MAPPING = STANDARD_MODEL_HOLE_MAPPING
C_MODEL_HOLE_MAPPING = STANDARD_MODEL_HOLE_MAPPING
CS_MODEL_HOLE_MAPPING = STANDARD_MODEL_HOLE_MAPPING
D_MODEL_HOLE_MAPPING = STANDARD_MODEL_HOLE_MAPPING
E_MODEL_HOLE_MAPPING = STANDARD_MODEL_HOLE_MAPPING
EB_MODEL_HOLE_MAPPING = STANDARD_MODEL_HOLE_MAPPING
F_MODEL_HOLE_MAPPING = STANDARD_MODEL_HOLE_MAPPING
FS_MODEL_HOLE_MAPPING = STANDARD_MODEL_HOLE_MAPPING
G_MODEL_HOLE_MAPPING = STANDARD_MODEL_HOLE_MAPPING
