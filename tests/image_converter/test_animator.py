from image_converter.animator import create_animation

def test_create_animation_with_fake_data(monkeypatch, tmp_path):
    # Monkeypatch animation functions to avoid file output
    import matplotlib.animation as animation
    monkeypatch.setattr(animation.Animation, 'save', lambda *args, **kwargs: None)

    tabs = [
        {"tab": 4, "time": 0.0, "duration": 1.0},
        {"tab": -5, "time": 1.0, "duration": 1.0},
    ]

    # Use a solid-color in-memory image
    from PIL import Image
    dummy_img = tmp_path / "fake_img.png"
    Image.new('RGB', (600, 100)).save(dummy_img)

    # Use a 2-second silent file (we won't read it — duration can be mocked)
    dummy_audio = tmp_path / "silent.wav"
    dummy_audio.write_bytes(b"RIFF....WAVEfmt ")  # minimal WAV header

    create_animation(tabs, str(dummy_img), str(dummy_audio), output_path=str(tmp_path / "out.mp4"))
