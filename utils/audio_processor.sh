#!/bin/bash

# Exit on error
set -e

if [ $# -ne 1 ]; then
    echo "Usage: $0 <input_wav_file>"
    exit 1
fi

input_file="$1"

if [ ! -f "$input_file" ]; then
    echo "File not found: $input_file"
    exit 1
fi

# Extract base name without extension
base_name=$(basename "$input_file" .wav)
output_dir=$(dirname "$input_file")
output_file="$output_dir/${base_name}_midi_ready.wav"

echo "Processing $input_file for MIDI conversion..."

# Step 1: Convert to mono (pitch detectors work better on mono)
# Step 2: Apply bandpass filter (200Hz–5000Hz keeps melody-relevant frequencies)
# Step 3: Normalize loudness
# Step 4: Light harmonic emphasis (remove some percussive noise)

ffmpeg -i "$input_file" \
    -ac 1 \
    -af "highpass=f=200, lowpass=f=5000, \
         afftdn=nf=-25, \
         loudnorm=I=-16:TP=-1.5:LRA=11" \
    -ar 44100 \
    -y "$output_file"

echo "Done! Output written to: $output_file"
