from image_to_ascii_svg import is_background_pixel, luminance_to_char, RAMP


def test_luminance_to_char_darkest_pixel_maps_to_first_ramp_char():
    assert luminance_to_char(0, RAMP) == RAMP[0]


def test_luminance_to_char_brightest_pixel_maps_to_last_ramp_char():
    assert luminance_to_char(255, RAMP) == RAMP[-1]


def test_luminance_to_char_midpoint_maps_to_middle_of_ramp():
    mid_index = len(RAMP) // 2
    # 128/255 * (len(RAMP)-1) rounds to the middle of the ramp
    assert luminance_to_char(128, RAMP) == RAMP[round(128 / 255 * (len(RAMP) - 1))]


def test_background_detection_keeps_skin_tones():
    background = (238, 170, 153)
    assert is_background_pixel((229, 165, 158), background)
    assert not is_background_pixel((245, 231, 202), background)
    assert not is_background_pixel((30, 30, 28), background)
