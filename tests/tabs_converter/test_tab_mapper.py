from tab_converter.tab_mapper import midi_to_tabs_with_timing


def test_single_note_conversion(simple_c4_midi):
    tabs = midi_to_tabs_with_timing(str(simple_c4_midi))
    assert len(tabs) == 1
    assert tabs[0]['tab'] == 1
    assert tabs[0]['duration'] == 0.5
    assert tabs[0]['time'] == 0.0


def test_unsupported_note_is_skipped(midi_with_unsupported_note):
    tabs = midi_to_tabs_with_timing(str(midi_with_unsupported_note))
    assert isinstance(tabs, list)
    assert len(tabs) == 0


def test_polyphonic_note_conversion(midi_with_polyphony):
    tabs = midi_to_tabs_with_timing(str(midi_with_polyphony))
    assert isinstance(tabs, list)
    assert len(tabs) == 2
    assert sorted([t['tab'] for t in tabs]) == [1, 2]


def test_note_timing_with_gap(midi_with_timing_gap):
    tabs = midi_to_tabs_with_timing(str(midi_with_timing_gap))
    assert isinstance(tabs, list)
    assert len(tabs) == 2
    t0 = tabs[0]['time']
    t1 = tabs[1]['time']
    assert t1 - t0 > 0.3  # some non-zero time gap
